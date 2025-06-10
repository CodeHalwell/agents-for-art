from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    InferenceClientModel,
    DuckDuckGoSearchTool
)

from tools.web_tools import scrape_website, close_popups, go_back, search_item_ctrl_f, save_screenshot
from tools.database_tools import add_entry_fee, add_exhibition, add_url, add_prize, describe_schema

from models.db import DatabaseManager

from dotenv import load_dotenv
import os
load_dotenv()

db = DatabaseManager("art_events.db")

scrape_model_id = "meta-llama/Llama-3.3-70B-Instruct"
web_model_id = "meta-llama/Llama-3.3-70B-Instruct"
manager_model_id = "Qwen/Qwen3-235B-A22B"
browser_agent_model_id = "Qwen/Qwen2.5-VL-32B-Instruct"
database_agent_model_id = "Qwen/Qwen2.5-Coder-32B-Instruct"

# Create the agent
browser_agent = CodeAgent(
    tools=[go_back, close_popups, search_item_ctrl_f],
    model=InferenceClientModel(model_id=browser_agent_model_id, provider="hf-inference", token=os.environ['HF_TOKEN']),
    additional_authorized_imports=["helium"],
    step_callbacks=[save_screenshot],
    max_steps=20,
    verbosity_level=2,
    name="Browser_Agent",
    description="Can navigate with Helium, close pop-ups, press back, and do Ctrl+F searches.",
)

browser_agent.python_executor("from helium import *")

websearch_agent = ToolCallingAgent(
    model=InferenceClientModel(model_id=web_model_id, provider="hf-inference", token=os.environ['HF_TOKEN']),
    tools=[DuckDuckGoSearchTool()],
    max_steps=20,
    name="Web_Search_Agent",
    description="An agent that can search the web and collect useful URLs to add to the database",)

website_scraper_agent = ToolCallingAgent(
    model=InferenceClientModel(model_id=scrape_model_id, provider="hf-inference", token=os.environ['HF_TOKEN']),
    tools=[scrape_website],
    max_steps=20,
    name="Website_Scraper_Agent",
    description="An agent that can scrape websites for information and add it to the database",)

database_agent = ToolCallingAgent(
    model=InferenceClientModel(model_id=database_agent_model_id, provider="hf-inference", token=os.environ['HF_TOKEN']),
    tools=[add_entry_fee, add_exhibition, add_url, add_prize, describe_schema],
    max_steps=20,
    name="Database_Agent",
    description="An agent that can add entries to the database, including entry fees, exhibitions, URLs, and prizes.",)

manager_agent = CodeAgent(
    model=InferenceClientModel(model_id=manager_model_id, provider="hf-inference", token=os.environ['HF_TOKEN']),
    tools=[],
    managed_agents=[
        browser_agent,
        websearch_agent,
        website_scraper_agent,  
        database_agent
    ],
    max_steps=50,
    name="Manager_Agent",
    description="An agent that manages other agents, coordinating their actions and ensuring they work together effectively.",
    additional_authorized_imports=["os", "time", "random"],)

with open("helium_instructions.txt", "r") as f:
    helium_instructions = f.read()


task = """
Your goal is to discover every open-call art exhibition or art fair in the UK from January 2023 to July 2026, where the current date is 10th June 2025.
The aim is to look at past exhibitions to find patterns in the data, such as the number of entries, fees, and prizes as well as future exhibitions.

To achieve this, you will use the following agents:
1. **Web Search Agent**: To find URLs of open-call art exhibitions in the UK.
2. **Browser Agent**: To navigate to the URLs, close pop-ups, and perform searches on the pages.
3. **Website Scraper Agent**: To scrape the relevant information from the websites.
4. **Database Agent**: To add the scraped information to the database.

The database schema is available in the `describe_schema` tool, which provides the structure of the database and the fields required for each table.
Please review this schema before starting the task to ensure you understand how to populate the database correctly.
The aim is to populate the database with the following information for each exhibition:
- **Title**: The name of the exhibition.
- **Date Start**: The start date of the exhibition.
- **Date End**: The end date of the exhibition.
- **Venue**: The venue where the exhibition is held.
- **Location**: The city or town where the exhibition is located.
- **County**: The county where the exhibition is located.
- **Description**: A brief description of the exhibition.

Then to populate the database with the following information for each entry fee:
- **Fee Type**: The type of fee (e.g., tiered or flat).
- **Number of Entries**: The number of entries for tiered fees, or None for flat fees.
- **Fee Amount**: The amount of the fee for each entry (e.g., 25.00).
- **Flat Rate**: The flat rate fee for the exhibition, if applicable.
- **Commission Percent**: The commission percentage for the exhibition, if applicable.

Then to populate the database with the following information for each prize:
- **Prize Rank**: The rank of the prize (e.g., 1st, 2nd, etc.).
- **Prize Amount**: The amount of the prize for each award type.
- **Prize Type**: The type of the prize (e.g., cash, gift card, etc.).
- **Prize Description**: A description of the prize.

The urls during the research should be saved in the database and for each URL, the following information should be saved:
- **raw_title**: The raw title of the page.
- **raw_date**: The raw date of the exhibition.
- **raw_location**: The raw location of the exhibition.
- **raw_description**: The raw description of the exhibition.

You will start by using the Web Search Agent to find URLs of open-call art exhibitions in the UK in the specified date range.
Try to find URLs that are likely to contain information about the exhibitions, such as "open call", "art exhibition", "art fair", etc. and save them in the database.
Try to look at aggregator websites that list multiple exhibitions, such as "ArtRabbit", "Artlyst", "The Art Newspaper", etc. These websites often have a list of exhibitions and open calls, which can be useful for your research.
During this research process the URLs should be saved in the database with the following information if available:
- **raw_title**: The raw title of the page.
- **raw_date**: The raw date of the exhibition.
- **raw_location**: The raw location of the exhibition.
- **raw_description**: The raw description of the exhibition.

Then, use the Browser Agent to navigate to these URLs, close any pop-ups, and perform searches on the pages to find the relevant information.
Once you have found the relevant information, use the Website Scraper Agent to scrape the information and add it to the database using the Database Agent.
The information required for the database is as follows:
- **Title**: The name of the exhibition.
- **Date Start**: The start date of the exhibition.
- **Date End**: The end date of the exhibition.
- **Venue**: The venue where the exhibition is held.
- **Location**: The city or town where the exhibition is located.
- **County**: The county where the exhibition is located.
- **Description**: A brief description of the exhibition.
Once you have scraped the information, use the Database Agent to add the entry fees and prizes to the database.

You will also need to add the entry fees and prizes to the database.
The entry fees should include the following information:
- **Fee Type**: The type of fee (e.g., tiered or flat).
- **Number of Entries**: The number of entries for tiered fees, or None for flat fees.
- **Fee Amount**: The amount of the fee for each entry (e.g., 25.00).
- **Flat Rate**: The flat rate fee for the exhibition, if applicable.
- **Commission Percent**: The commission percentage for the exhibition, if applicable.

The prizes should include the following information:
- **Prize Rank**: The rank of the prize (e.g., 1st, 2nd, etc.).
- **Prize Amount**: The amount of the prize for each award type.
- **Prize Type**: The type of the prize (e.g., cash, gift card, etc.).

The agents will work together to ensure that all relevant information is collected and added to the database.

The summary of the task is as follows:
1. Use the Web Search Agent to find URLs of open-call art exhibitions in the UK.
2. Use the Browser Agent to navigate to the URLs, close pop-ups, and perform searches on the pages.
3. Use the Website Scraper Agent to scrape the relevant information from the websites.
4. Use the Database Agent to add the scraped information to the database, including exhibitions, entry fees, and prizes.

The aim is to find as many open-call art exhibitions as possible in the UK from January 2023 to July 2026, idealy with the fee information artists pay to enter.
Aim for around 1000 entries in the database.
"""

prompt = task + "\n\n" + helium_instructions

# Run the manager agent with the task
manager_agent.run(prompt, max_steps=50)