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
    DuckDuckGoSearchTool
)
from dotenv import load_dotenv

from tools.web_tools import (
    scrape_website_safely, 
    enhanced_close_popups, 
    enhanced_search_item,

)
from tools.database_tools import (
    add_entry_fee_async,
    add_exhibition_async,
    add_url_async,
    add_prize_async,
    describe_schema,
    get_unprocessed_urls_async,
    get_exhibition_stats_async
)
from models.db import AsyncDatabaseManager
import helium

load_dotenv()


class AgentConfig:
    """Configuration for agents following SmolAgents best practices."""
    
    # Model configurations
    SCRAPE_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
    WEB_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
    MANAGER_MODEL = "Qwen/Qwen3-32B"
    BROWSER_MODEL = "Qwen/Qwen2.5-VL-32B-Instruct"
    DATABASE_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"
    
    # Agent parameters following best practices
    MAX_STEPS_WORKER = 2  # Reduced from 20 for efficiency
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
    
    def _setup_agents(self):
        """
        Setup agents following SmolAgents best practices.
        According to docs: Clear role definition and appropriate tools.
        """
        
        # Browser Agent - Specialized for navigation only
        # According to best practices: Minimal, focused responsibilities
        self.agents['browser'] = CodeAgent(
            tools=[enhanced_close_popups, enhanced_search_item],
            model=self._create_base_model(self.config.BROWSER_MODEL),
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
            model=self._create_base_model(self.config.WEB_MODEL),
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
            model=self._create_base_model(self.config.SCRAPE_MODEL),
            tools=[scrape_website_safely],
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
            model=self._create_base_model(self.config.DATABASE_MODEL),
            tools=[add_entry_fee_async, add_exhibition_async, add_url_async, add_prize_async, describe_schema, get_unprocessed_urls_async, get_exhibition_stats_async],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            planning_interval=self.config.PLANNING_INTERVAL,
            provide_run_summary=True,
            name="Database_Management_Specialist",
            description=(
                "Specialized agent for database operations. "
                "Stores exhibition data, entry fees, prizes, and URLs with validation. "
                "Ensures data consistency and handles duplicates properly."
            ),
        )
        
        # Manager Agent - Following best practices for coordination
        self.agents['manager'] = CodeAgent(
            model=self._create_base_model(self.config.MANAGER_MODEL),
            tools=[get_exhibition_stats_async, get_unprocessed_urls_async],  # Manager doesn't need direct tools
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
    **TASK: ART EXHIBITION RESEARCH COORDINATOR**

    **OBJECTIVE:**

    Systematically discover, extract, and catalog UK art exhibitions and open calls for the period of January 2023 to July 2026. 
    The current date is June 11, 2025 and therefore looking for data on past, present and future events. The primary goal is to build a comprehensive database to analyze trends in entry fees, prizes, and exhibition frequency.

    **SUCCESS CRITERIA:**

    * **Volume:** Collect and store 1000+ unique exhibition entries.
    * **Completeness:** Include complete entry fee structures (tiered, flat) and capture prize information where available.
    * **Data Integrity:** Maintain high standards of data quality and consistency.

    **AGENT WORKFLOW (Iterative Sequence):**

    This task follows a structured, iterative workflow. After an initial search phase, you will process and save data for one URL at a time.
    It may be helpful to review the database schema before starting the task. The schema is available in the `describe_schema_async` tool.

    1.  **SEARCH PHASE (Web_Search_Specialist):**
        * **Find Aggregators:** Identify UK art exhibition aggregator sites, prioritizing `ArtRabbit`, `Artlyst`, and `The Art Newspaper`.
        * **Search Topics:** Use queries like `"UK art open call 2023"`, `"UK art open call 2024"`, `"UK art open call 2025"`, 
        `"UK art open call 2026"`, `"UK art exhibition 2024"`, and `"UK art fair 2025"`.
        * **URL Collection:** Collect an initial batch of 100-200 relevant URLs before proceeding to the next phase.

    2.  **ITERATIVE PROCESSING LOOP (For each URL):**

        * **A. NAVIGATION PHASE (Browser_Navigation_Agent):**
            * Navigate to the next URL in the queue.
            * Handle any pop-ups or cookie banners to access page content.
            * Search the page for key terms: `"entry fee"`, `"submission fee"`, `"prize"`.

        * **B. EXTRACTION & STORAGE PHASE (Content_Extraction_Specialist & Database_Management_Specialist):**
            * This phase must be completed for each URL before starting the next.
            * **Extraction:**
                * **Exhibition Details:** Extract `title`, `dates`, `venue`, `location`, `county`, `description`.
                * **Fee Structures:** Extract `fee type` (tiered vs flat) and associated costs.
                * **Prize Information:** Extract `prize rank`, `amount`, and `type`.
            * **Storage (Immediate & Sequential):**
                * **First:** Store the URL with its raw, unprocessed data using a function like `add_url()`.
                * **Then:** Store the structured exhibition details using `add_exhibition()`.
                * **Then:** Store the structured entry fee information using `add_entry_fee()`.
                * **Finally:** Store the structured prize information using `add_prize()`.

    **DATA QUALITY REQUIREMENTS:**

    * **Date Format:** Validate all dates are in `YYYY-MM-DD` format.
    * **Numeric Fees:** Ensure all fee and prize amounts are numeric (e.g., `25.00`).
    * **Deduplication:** Check for and prevent duplicate URL or exhibition entries.
    * **Field Verification:** Verify that all required database fields are present before storage.

    **ERROR HANDLING:**

    * **Retries:** Retry failed network requests up to 3 times.
    * **Skip & Log:** If a URL remains problematic, log the error and skip to the next URL. The process must not stop.
    * **Rate Limiting:** Implement a randomized delay of 2-8 seconds between requests.

    **EFFICIENCY & COORDINATION STRATEGY:**

    * **Batching:** Process URLs in logical batches of 10-20 to manage workflow.
    * **Prioritization:** Prioritize high-value aggregator sites and exhibitions with clear fee structures.
    * **SmolAgents Best Practices:** Reduce LLM calls by batching similar operations (like the initial search) and using deterministic validation (e.g., regex for dates) wherever possible. Delegate specialized tasks to the appropriate agents and integrate results efficiently.
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
