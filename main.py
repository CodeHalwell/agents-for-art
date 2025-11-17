"""
Optimized agent architecture for efficiency and reduced token usage.
This version focuses on lean prompts and specialized tools to minimize LLM calls.
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
    extract_exhibition_data
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
    """Optimized configuration for agents to reduce token usage."""

    PROVIDER = "openai"  # 'hf-inference' or 'openai'
    
    # Model selection focuses on cost-effective models for specialized tasks
    if PROVIDER == "hf-inference":
        SCRAPE_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
        WEB_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
        MANAGER_MODEL = "Qwen/Qwen3-32B"
        BROWSER_MODEL = "Qwen/Qwen2.5-VL-32B-Instruct"
        DATABASE_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"
    else:
        SCRAPE_MODEL = "gpt-4o-mini"
        WEB_MODEL = "gpt-4o-mini"
        MANAGER_MODEL = "gpt-4o"
        BROWSER_MODEL = "gpt-4o-mini"
        DATABASE_MODEL = "gpt-4o-mini"
    
    # Reduced max steps for more focused agent execution
    MAX_STEPS_WORKER = 8
    MAX_STEPS_MANAGER = 25
    VERBOSITY = 1
    PLANNING_INTERVAL = 2


class OptimizedAgentOrchestrator:
    """
    Optimized multi-agent orchestrator with a focus on efficient tool usage.
    """
    
    def __init__(self, db_manager: AsyncDatabaseManager):
        self.db = db_manager
        self.config = AgentConfig()
        self.agents: dict = {}
        self._setup_agents()
    
    def _create_model(self, model_id: str) -> Optional[object]:
        """Creates a model instance based on the configured provider."""
        if self.config.PROVIDER == "hf-inference":
            return InferenceClientModel(
                model_id=model_id,
                provider="hf-inference",
                token=os.environ.get('HF_TOKEN')
            )
        elif self.config.PROVIDER == "openai":
            return OpenAIServerModel(
                model_id=model_id,
                api_key=os.environ.get('OPENAI_API_KEY')
            )
        else:
            raise ValueError(f"Unsupported provider: {self.config.PROVIDER}")
    
    def _setup_agents(self):
        """
        Setup agents with clear roles and token-efficient tools.
        """
        
        # Browser Agent for navigation tasks
        self.agents['browser'] = CodeAgent(
            tools=[enhanced_close_popups, enhanced_search_item],
            model=self._create_model(self.config.BROWSER_MODEL),
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            name="Browser_Navigation_Agent",
            description="Handles browser navigation, popups, and searching for text on pages."
        )
        
        # Web Search Agent for discovering URLs
        self.agents['search'] = ToolCallingAgent(
            model=self._create_model(self.config.WEB_MODEL),
            tools=[DuckDuckGoSearchTool()],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            name="Web_Search_Specialist",
            description="Discovers art exhibition URLs in the UK using search queries."
        )
        
        # Content Extraction Specialist with optimized tools
        self.agents['scraper'] = ToolCallingAgent(
            model=self._create_model(self.config.SCRAPE_MODEL),
            tools=[scrape_website, extract_exhibition_data],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            name="Content_Extraction_Specialist",
            description="Extracts structured data from web pages using efficient parsing."
        )
        
        # Database Agent with schema description capabilities
        self.agents['database'] = ToolCallingAgent(
            model=self._create_model(self.config.DATABASE_MODEL),
            tools=[
                add_url, add_exhibition, add_entry_fee, add_prize,
                describe_schema, get_unprocessed_urls, get_exhibition_stats,
                bulk_insert_exhibitions, get_exhibitions_by_criteria,
                generate_fee_analysis_report, cleanup_duplicate_entries,
                add_database_indexes
            ],
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            name="Database_Management_Specialist",
            description=(
                "Manages all database operations, including data storage and validation. "
                "Can describe table schemas to understand data structures."
            )
        )
        
        # Manager Agent to coordinate the workflow
        self.agents['manager'] = CodeAgent(
            model=self._create_model(self.config.MANAGER_MODEL),
            tools=[get_exhibition_stats, get_unprocessed_urls],
            managed_agents=list(self.agents.values()),
            max_steps=self.config.MAX_STEPS_MANAGER,
            verbosity_level=self.config.VERBOSITY,
            name="Research_Coordinator",
            description="Coordinates the research process by delegating tasks to specialized agents."
        )
    
    async def run_research_task(self, task_description: str) -> str:
        """
        Run the research task with the optimized agent workflow.
        """
        try:
            manager = self.agents['manager']
            result = await asyncio.to_thread(manager.run, task_description, max_steps=self.config.MAX_STEPS_MANAGER)
            return result
        except Exception as e:
            return f"Research task failed: {str(e)}"
    
    def cleanup(self):
        """Clean up resources."""
        try:
            helium.kill_browser()
        except Exception:
            pass


def create_optimized_task_prompt() -> str:
    """
    Creates a lean, optimized task prompt that reduces token usage.
    """
    return """
        **TASK: ART EXHIBITION RESEARCH COORDINATOR**

        **OBJECTIVE:**
        Systematically discover, extract, and catalog UK art exhibitions and open calls from January 2023 to July 2026.
        The goal is to collect 1000+ unique exhibition entries to analyze trends in entry fees, prizes, and exhibition frequency.

        **AGENT WORKFLOW:**

        1.  **SEARCH (Web_Search_Specialist):**
            *   Find UK art exhibition aggregator sites (e.g., ArtRabbit, Artlyst).
            *   Use search queries like "UK art open call 2024" to find relevant URLs.
            *   Collect an initial batch of 50-100 URLs.

        2.  **PROCESS URLs (Iterative Loop):**
            *   For each URL, use the `Content_Extraction_Specialist` to scrape and extract data.
            *   If the page is dynamic, use the `Browser_Navigation_Agent` to handle interactions.
            *   Use the `Database_Management_Specialist` to store the extracted data.
                - Use `describe_schema` to understand the database structure before storing data.

        **DATA QUALITY:**
        *   Ensure dates are in YYYY-MM-DD format.
        *   Validate that fee and prize amounts are numeric.
        *   Prevent duplicate entries.

        **EFFICIENCY:**
        *   Use `extract_exhibition_data` to minimize the content sent to the LLM.
        *   Process URLs in batches to optimize performance.
    """


async def create_research_system() -> OptimizedAgentOrchestrator:
    """
    Factory function to create the optimized research system.
    """
    db_manager = AsyncDatabaseManager()
    await db_manager.initialize_database()
    return OptimizedAgentOrchestrator(db_manager)


async def run_optimized_research():
    """
    Main function to run the optimized research system.
    """
    orchestrator = None
    try:
        orchestrator = await create_research_system()
        task_prompt = create_optimized_task_prompt()
        result = await orchestrator.run_research_task(task_prompt)
        print(f"Research completed! Result: {result}")
        return result
    except Exception as e:
        print(f"Research system error: {e}")
        return None
    finally:
        if orchestrator:
            orchestrator.cleanup()
            await orchestrator.db.close()


if __name__ == "__main__":
    asyncio.run(run_optimized_research())
