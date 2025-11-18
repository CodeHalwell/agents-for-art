"""
Centralized configuration for the Art Agent system.
This file contains settings for agent models, parameters, and logging.
"""
import logging
import os

# --- AGENT CONFIGURATION ---
class AgentConfig:
    """Optimized configuration for agents to reduce token usage."""

    PROVIDER = os.getenv("AGENT_PROVIDER", "openai")  # 'hf-inference' or 'openai'

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
    MAX_STEPS_WORKER = int(os.getenv("MAX_STEPS_WORKER", 8))
    MAX_STEPS_MANAGER = int(os.getenv("MAX_STEPS_MANAGER", 25))
    VERBOSITY = int(os.getenv("VERBOSITY", 1))
    PLANNING_INTERVAL = int(os.getenv("PLANNING_INTERVAL", 2))

# --- LOGGING CONFIGURATION ---
def setup_logging():
    """Configures logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("art_agent.log"),
            logging.StreamHandler()
        ]
    )
