"""
Enhanced agent architecture following SmolAgents best practices.
According to SmolAgents docs: Use clear role definition, proper error handling, and efficient workflows.
"""
import asyncio
import os
from typing import Optional
from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    InferenceClientModel,
    DuckDuckGoSearchTool,
    OpenAIServerModel
)
from dotenv import load_dotenv

from tools.web_tools import (
    scrape_website, 
    enhanced_close_popups, 
    enhanced_search_item,
    preprocess_content_for_extraction,
    cache_similar_content_patterns,
    extract_dates_with_regex,
    extract_prices_with_regex,
    reduce_content_to_relevant_sections
)
from tools.database_tools import (
    add_entry_fee,
    add_exhibition,
    add_url,
    add_prize,
    describe_schema,
    get_unprocessed_urls,
    get_exhibition_stats,
    bulk_insert_exhibitions,
    get_exhibitions_by_criteria,
    generate_fee_analysis_report,
    cleanup_duplicate_entries,
    add_database_indexes
)
from models.db import AsyncDatabaseManager
import helium

load_dotenv()


class AgentConfig:
    """Configuration for agents following SmolAgents best practices."""

    PROVIDER = "openai"  # 'hf-inference' or 'openai'
    
    if PROVIDER == "hf-inference":
        SCRAPE_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
        WEB_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
        MANAGER_MODEL = "Qwen/Qwen3-32B"
        BROWSER_MODEL = "Qwen/Qwen2.5-VL-32B-Instruct"
        DATABASE_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"
    else:
        SCRAPE_MODEL = "gpt-4o-mini"
        WEB_MODEL = "gpt-4o-mini"
        MANAGER_MODEL = "gpt-4.1-mini"
        BROWSER_MODEL = "gpt-4o-mini"
        DATABASE_MODEL = "gpt-4o-mini"
    
    # Agent parameters following best practices
    MAX_STEPS_WORKER = 10  # Reduced from 20 for efficiency
    MAX_STEPS_MANAGER = 40  # Reduced from 50 for efficiency
    VERBOSITY = 1  # Reduced verbosity for cleaner logs
    
    # According to SmolAgents best practices: Use planning intervals
    PLANNING_INTERVAL = 3


class EnhancedAgentOrchestrator:
    """
    Enhanced multi-agent orchestrator following SmolAgents best practices.
    According to docs: Clear role definition, minimal overlap, proper error handling.
    """
    
    def __init__(self, db_manager: AsyncDatabaseManager):
        self.db = db_manager
        self.config = AgentConfig()
        self.agents: dict = {}
        self._setup_agents()
    
    def _create_base_model(self, model_id: str) -> InferenceClientModel:
        """Create base model with consistent configuration."""
        return InferenceClientModel(
            model_id=model_id,
            provider="hf-inference",
            token=os.environ['HF_TOKEN']
        )
    
    def _create_server_model(self, model_id: str) -> OpenAIServerModel:
        """Create server model with consistent configuration."""
        return OpenAIServerModel(
            model_id=model_id,
            api_key=os.environ['OPENAI_API_KEY']
        )
    
    def _create_model(self, model_id: str) -> Optional[object]:
        """
        Create model based on provider.
        According to SmolAgents best practices: Use consistent model creation.
        """
        if self.config.PROVIDER == "hf-inference":
            return self._create_base_model(model_id)
        elif self.config.PROVIDER == "openai":
            return self._create_server_model(model_id)
        else:
            raise ValueError(f"Unsupported provider: {self.config.PROVIDER}")
    
    def _setup_agents(self):
        """
        Setup agents following SmolAgents best practices.
        According to docs: Clear role definition and appropriate tools.
        """
        
        # Browser Agent - Specialized for navigation only
        # According to best practices: Minimal, focused responsibilities
        self.agents['browser'] = CodeAgent(
            tools=[enhanced_close_popups, enhanced_search_item],
            model=self._create_model(self.config.BROWSER_MODEL),
            additional_authorized_imports=["helium", "time"],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            planning_interval=self.config.PLANNING_INTERVAL,
            name="Browser_Navigation_Agent",
            description=(
                "Specialized agent for browser navigation tasks. "
                "Can close popups, search for text on pages, and navigate browser elements. "
                "Does NOT scrape content - only handles navigation."
            ),
        )
        
        # Web Search Agent - Enhanced with better descriptions
        self.agents['search'] = ToolCallingAgent(
            model=self._create_model(self.config.WEB_MODEL),
            tools=[DuckDuckGoSearchTool()],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            planning_interval=self.config.PLANNING_INTERVAL,
            provide_run_summary=True,  # According to best practices
            name="Web_Search_Specialist",
            description=(
                "Specialized agent for web search operations. "
                "Finds relevant URLs for art exhibitions, open calls, and art fairs in the UK. "
                "Returns structured lists of URLs with descriptions."
            ),
        )
        
        # Content Scraper - Separated from navigation
        self.agents['scraper'] = ToolCallingAgent(
            model=self._create_model(self.config.SCRAPE_MODEL),
            tools=[scrape_website, preprocess_content_for_extraction,
                    cache_similar_content_patterns,
                    extract_dates_with_regex,
                    extract_prices_with_regex,
                    reduce_content_to_relevant_sections],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            planning_interval=self.config.PLANNING_INTERVAL,
            provide_run_summary=True,
            name="Content_Extraction_Specialist",
            description=(
                "Specialized agent for content extraction from websites. "
                "Extracts exhibition details, entry fees, prizes, and venue information. "
                "Uses rate-limited scraping to avoid blocking."
            ),
        )
        
        # Database Agent - Enhanced with validation
        self.agents['database'] = ToolCallingAgent(
            model=self._create_model(self.config.DATABASE_MODEL),
            tools=[
                add_entry_fee, add_exhibition, add_url, add_prize, describe_schema, 
                get_unprocessed_urls, get_exhibition_stats, bulk_insert_exhibitions,
                get_exhibitions_by_criteria, generate_fee_analysis_report,
                cleanup_duplicate_entries, add_database_indexes
            ],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            planning_interval=self.config.PLANNING_INTERVAL,
            provide_run_summary=True,
            name="Database_Management_Specialist",
            description=(
                "Specialized agent for database operations. "
                "Stores exhibition data, entry fees, prizes, and URLs with validation. "
                "Includes advanced features like bulk operations, criteria-based queries, "
                "analytics reporting, duplicate cleanup, and performance optimization. "
                "Ensures data consistency and handles duplicates properly."
            ),
        )
        
        # Manager Agent - Following best practices for coordination
        self.agents['manager'] = CodeAgent(
            model=self._create_model(self.config.MANAGER_MODEL),
            tools=[get_exhibition_stats, get_unprocessed_urls],  # Manager doesn't need direct tools
            managed_agents=list(self.agents.values()),
            max_steps=self.config.MAX_STEPS_MANAGER,
            verbosity_level=self.config.VERBOSITY,
            planning_interval=self.config.PLANNING_INTERVAL,
            name="Research_Coordinator",
            description=(
                "Coordinates the art exhibition research process. "
                "Delegates tasks to specialized agents and ensures efficient workflow. "
                "Can monitor database statistics and track unprocessed URLs. "
                "Focuses on high-level strategy and result integration."
            ),
            additional_authorized_imports=["asyncio", "time", "random", "json", "re", "datetime", "logging", "helium"],
        )
    
    def get_agent(self, agent_type: str) -> Optional[object]:
        """Get agent by type with validation."""
        return self.agents.get(agent_type)
    
    def get_manager(self) -> CodeAgent:
        """Get the manager agent."""
        return self.agents['manager']
    
    async def run_research_task(self, task_description: str) -> str:
        """
        Run the research task with proper error handling.
        According to best practices: Implement proper error recovery.
        """
        try:
            # Initialize browser for the browser agent
            browser_agent = self.get_agent('browser')
            if browser_agent:
                browser_agent.python_executor("from helium import *")
            
            # Run the task through the manager
            manager = self.get_manager()
            result = manager.run(task_description, max_steps=self.config.MAX_STEPS_MANAGER)
            
            return result
            
        except Exception as e:
            error_msg = f"Research task failed: {str(e)}"
            print(error_msg)
            return error_msg
    
    def cleanup(self):
        """Clean up agent resources."""
        # Close any browser sessions
        try:
            helium.kill_browser()
        except Exception:
            pass


def create_enhanced_task_prompt() -> str:
    """
    Create enhanced task prompt following SmolAgents best practices.
    According to docs: Make task very clear and provide specific guidance.
    """
    
    with open("helium_instructions.txt", "r") as f:
        helium_instructions = f.read()
    
    task = """
        **MISSION BRIEFING: ART EXHIBITION RESEARCH COORDINATOR**

        **PRIMARY OBJECTIVE:**
        Your mission is to orchestrate a team of specialized agents to systematically discover, extract, and catalog UK art exhibitions, open calls, 
        and art fairs for the period of January 2023 to July 2026. The current date is June 11, 2025. The ultimate goal is to populate a comprehensive 
        database for analyzing trends in artist entry fees (fees paid to the gallery, host etc. from the artist), gallery commissions (recieved by the gallery, host etc. from sales), prizes, and exhibition frequency.
        There may be a range of entry fees and prizes, so you must capture all available data. Some are free, some have a flat rate fee, and some have a tiered structure based on the number of works submitted.
        You will work with a team of specialized agents to achieve this.

        **DATABASE SCHEMA OVERVIEW:**
        You have access to a database with four main tables: `urls` (for raw scraped links), `exhibitions` (for structured event data), 
        `entry_fees`, and `prizes`. You can query the schema if needed using the `Database_Management_Specialist`'s `describe_schema` tool.

        **SUCCESS CRITERIA:**
        *   **Volume:** Collect and store data for at least 1000 unique exhibitions.
        *   **Data Integrity:** Ensure all data is validated, especially dates (`YYYY-MM-DD`) and numeric values, before storage. Prevent duplicate entries.
        *   **Completeness:** Capture detailed entry fee structures and prize information whenever available.

        ---
        **STRATEGIC WORKFLOW (Your Plan of Action)**

        You will manage the following iterative workflow. After an initial broad search, you will coordinate agents to process each discovered URL individually.

        **PHASE 1: INITIAL URL DISCOVERY**
        1.  **Delegate to `Web_Search_Specialist`:** Instruct this agent to find URLs.
        2.  **Search Strategy:** Use a variety of search queries like `"UK art open call 2023"`, `"UK art exhibition 2024"`, `"UK art fair 2025"`, and `"UK art open call 2026"`.
        Include searches to regional areas like 'North West', 'Midlands', 'South West', 'South East', 'East of England', 'London', 'North East', 'Yorkshire and the Humber', 'Wales', 'Scotland', and 'Northern Ireland'.
        This could also include county searches like 'Cheshire', 'Lancashire', 'Cumbria', 'Greater Manchester', 'Merseyside', 'Derbyshire', 'Nottinghamshire', 'Leicestershire', 'Lincolnshire', 'Northamptonshire', 'Warwickshire', 'Staffordshire', 'Shropshire', 'Herefordshire', 'Worcestershire', and 'Gloucestershire'. 
        Prioritize well-known aggregator sites like `ArtRabbit`, `Artlyst`, and `The Art Newspaper`.
        Extract details of events with links to their official pages for saving in the database. These can then be scraped later.
        3. **Filter Results:** Ensure the URLs are relevant to UK art exhibitions, open calls, and art fairs.
        4. **Store URLs:** Use the `Database_Management_Specialist` to store these URLs in the database for later processing.
        5. You may need to collect links from within links on aggregator sites, so you may need to use the `Web_Search_Specialist`or `Browser_Navigation_Agent` to navigate to these pages and extract links.
        6.  **Collect:** Gather an initial batch of around 200 unique URLs and store them in a list for processing.

        **PHASE 2: ITERATIVE URL PROCESSING (Loop through the URL's)**

        For the URL' in your list, you will coordinate the following sequence (extracting in batches if possible):

        **Step A: ATTEMPT DIRECT SCRAPING**
        *   **Delegate to `Content_Extraction_Specialist`:** Use its `scrape_website` scrape_website, `enhanced_close_popups`, `enhanced_search_item`,`preprocess_content_for_extraction`,`cache_similar_content_patterns`,`extract_dates_with_regex`,
        `extract_prices_with_regex`,`reduce_content_to_relevant_sections` tools to perform a fast, direct scrape of the URL's HTML content.
        *   **Assess Result:** If the tool returns complete, structured data (title, dates, fees, etc.), proceed directly to Step C.

        **Step B: FALLBACK TO BROWSER AUTOMATION (If Step A fails or is incomplete)**
        *   **Condition:** Execute this step only if the direct scrape fails to extract key information, likely because the content is rendered by JavaScript.
        *   **Delegate to `Browser_Navigation_Agent`:** Instruct it to navigate to the URL. It should use its tools (`enhanced_close_popups`, `enhanced_search_item`) to handle cookie banners and find relevant sections of the page.
        *   **Delegate to `Content_Extraction_Specialist`:** Once the page is ready in the browser, delegate back to the scraper agent, but this time it will extract content from the browser's rendered HTML.

        **Step C: EXTRACT & STORE DATA**
        *   **Delegate Extraction to `Content_Extraction_Specialist`:** Use its specialized tools (`extract_dates_with_regex`, `extract_prices_with_regex`, etc.) to parse the raw content into structured data:
            - Exhibition: `title`, `dates`, `venue`, `location`.
            - Fees: `fee_type`, `amount`, `currency`.
            - Prizes: `prize_name`, `amount`, `currency`.
        *   **Delegate Storage to `Database_Management_Specialist`:** After validating the extracted data, use the database agent's tools sequentially to ensure data integrity:
            1.  `add_url`: Store the source URL and raw data.
            2.  `add_exhibition`: Store the structured exhibition details.
            3.  `add_entry_fee`: Store any associated entry fees.
            4.  `add_prize`: Store any associated prizes.

            full list of tools here:
                add_entry_fee,
                add_exhibition,
                add_url,
                add_prize,
                describe_schema,
                get_unprocessed_urls,
                get_exhibition_stats,
                bulk_insert_exhibitions,
                get_exhibitions_by_criteria,
                generate_fee_analysis_report,
                cleanup_duplicate_entries,
                add_database_indexes

        ---
        **GUIDING PRINCIPLES & RULES OF ENGAGEMENT**

        *   **Delegate, Don't Do:** Your primary role is to coordinate. Delegate tasks to the specialist agent best suited for the job. You write the high-level Python script that calls the agents.
        *   **Validate Before Storing:** Ensure data (especially dates and numbers) is in the correct format before calling the database agent.
        *   **Error Handling:** If a URL consistently fails after 3 retries, log the problematic URL and move to the next. Do not let one bad URL halt the entire operation.
        *   **Efficiency:** Implement a randomized delay (2-8 seconds) between requests to any single domain to avoid being blocked. Process URLs in logical batches.
        *   **Deduplication:** Before processing a URL, check if it might already be in the database to avoid redundant work. Use the `Database_Management_Specialist` for this.
        """
    
    return task + "\n\n" + helium_instructions


# Usage example and factory function
async def create_research_system() -> EnhancedAgentOrchestrator:
    """
    Factory function to create the enhanced research system.
    According to best practices: Proper initialization and resource management.
    """
    # Initialize async database
    db_manager = AsyncDatabaseManager()
    await db_manager.initialize_database()
    
    # Create agent orchestrator
    orchestrator = EnhancedAgentOrchestrator(db_manager)
    
    return orchestrator


# Main execution function
async def run_enhanced_research():
    """
    Main function to run the enhanced research system.
    According to best practices: Proper async handling and cleanup.
    """
    orchestrator = None
    try:
        # Create and initialize system
        orchestrator = await create_research_system()
        
        # Create enhanced task prompt
        task_prompt = create_enhanced_task_prompt()
        
        # Run the research task
        result = await orchestrator.run_research_task(task_prompt)
        
        print("Research completed!")
        print(f"Result: {result}")
        
        return result
        
    except Exception as e:
        print(f"Research system error: {e}")
        return None
        
    finally:
        # Clean up resources
        if orchestrator:
            orchestrator.cleanup()
            await orchestrator.db.close()


if __name__ == "__main__":
    # Run the enhanced research system
    asyncio.run(run_enhanced_research())
