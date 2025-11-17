"""
Optimized agent architecture for efficiency and reduced token usage.
This version focuses on lean prompts and specialized tools to minimize LLM calls.
"""
import asyncio
import logging
import json
import os
from typing import Optional, List, Dict

from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    InferenceClientModel,
    DuckDuckGoSearchTool,
    OpenAIServerModel
)
from dotenv import load_dotenv

from config import AgentConfig, setup_logging
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

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

load_dotenv()

STATE_FILE = "research_state.json"

def load_state() -> Dict:
    """Loads the research state from a file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"all_urls": [], "processed_urls": []}

def save_state(state: Dict):
    """Saves the research state to a file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)


class OptimizedAgentOrchestrator:
    """
    Optimized multi-agent orchestrator with a focus on efficient tool usage.
    """
    
    def __init__(self, db_manager: AsyncDatabaseManager, config: AgentConfig):
        self.db = db_manager
        self.config = config
        self.agents: dict = {}
        self._setup_agents()
    
    def _create_model(self, model_id: str) -> Optional[object]:
        """Creates a model instance based on the configured provider."""
        logger.info(f"Creating model {model_id} for provider {self.config.PROVIDER}")
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
            logger.error(f"Unsupported provider: {self.config.PROVIDER}")
            raise ValueError(f"Unsupported provider: {self.config.PROVIDER}")
    
    def _setup_agents(self):
        """
        Setup agents with clear roles and token-efficient tools.
        """
        logger.info("Setting up specialized agents...")
        
        # Browser Agent for navigation tasks
        self.agents['browser'] = CodeAgent(
            tools=[enhanced_close_popups, enhanced_search_item],
            model=self._create_model(self.config.BROWSER_MODEL),
            max_steps=self.config.MAX_STEPS_WORKER,
            verbosity_level=self.config.VERBOSITY,
            name="Browser_Navigation_Agent",
            description="Handles browser navigation, popups, and searching for text on pages.",
            additional_authorized_imports=["helium", "time"],
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
        logger.info("All agents created successfully.")
    
    async def run_research_task(self, task_description: str) -> str:
        """
        Run the research task with the optimized agent workflow.
        """
        logger.info("Starting research task...")
        try:
            manager = self.agents['manager']
            result = await asyncio.to_thread(manager.run, task_description, max_steps=self.config.MAX_STEPS_MANAGER)
            logger.info("Research task completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Research task failed: {e}", exc_info=True)
            return f"Research task failed: {str(e)}"
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        try:
            helium.kill_browser()
            logger.info("Browser session terminated.")
        except Exception as e:
            logger.warning(f"Could not terminate browser session: {e}")
            pass


def create_optimized_task_prompt(unprocessed_urls: List[str]) -> str:
    """
    Creates a lean, optimized task prompt that reduces token usage.
    """
    return f"""
        **TASK: ART EXHIBITION RESEARCH COORDINATOR**

        **OBJECTIVE:**
        Systematically process the provided list of URLs to extract and catalog UK art exhibitions.
        The goal is to collect 1000+ unique exhibition entries to analyze trends in entry fees, prizes, and exhibition frequency.

        **AGENT WORKFLOW:**

        1.  **URL Processing (Iterative Loop):**
            *   Process the following URLs one by one: {unprocessed_urls}
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
    """


async def create_research_system() -> OptimizedAgentOrchestrator:
    """
    Factory function to create the optimized research system.
    """
    logger.info("Initializing research system...")
    config = AgentConfig()
    db_manager = AsyncDatabaseManager()
    await db_manager.initialize_database()
    logger.info("Database initialized.")
    return OptimizedAgentOrchestrator(db_manager, config)


async def run_optimized_research():
    """
    Main function to run the optimized research system with resumability.
    """
    orchestrator = None
    try:
        logger.info("Starting optimized research process...")
        orchestrator = await create_research_system()
        
        state = load_state()
        all_urls = state["all_urls"]
        processed_urls = state["processed_urls"]

        if not all_urls:
            logger.info("No URLs found in state file. Starting initial search.")
            search_agent = orchestrator.agents['search']
            search_prompt = "Find UK art exhibition aggregator sites (e.g., ArtRabbit, Artlyst) and collect an initial batch of 50-100 relevant URLs."
            search_result = await asyncio.to_thread(search_agent.run, search_prompt)
            # This is a simplified approach. A more robust solution would parse the search result.
            all_urls = [line for line in search_result.split('\n') if line.startswith("http")]
            state["all_urls"] = all_urls
            save_state(state)
            logger.info(f"Found {len(all_urls)} initial URLs.")

        unprocessed_urls = [url for url in all_urls if url not in processed_urls]
        logger.info(f"Processing {len(unprocessed_urls)} unprocessed URLs.")

        for url in unprocessed_urls:
            task_prompt = create_optimized_task_prompt([url])
            result = await orchestrator.run_research_task(task_prompt)
            logger.info(f"Research completed for {url}! Result: {result}")

            processed_urls.append(url)
            state["processed_urls"] = processed_urls
            save_state(state)

        return "All URLs processed."

    except Exception as e:
        logger.critical(f"A critical error occurred in the research system: {e}", exc_info=True)
        return None
    finally:
        if orchestrator:
            orchestrator.cleanup()
            await orchestrator.db.close()
            logger.info("System shut down gracefully.")


if __name__ == "__main__":
    asyncio.run(run_optimized_research())
