"""
Enhanced web scraping tools with proper rate limiting and anti-bot measures.
According to web scraping best practices: Use rate limiting, proxy rotation, and proper error handling.
"""
import asyncio
import atexit
import logging
import random
import re
import time
from typing import Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager

import requests
from bs4 import BeautifulSoup
from smolagents import tool
import helium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)


@dataclass
class ScrapingConfig:
    """Configuration for web scraping operations"""
    min_delay: float = 2.0
    max_delay: float = 8.0
    timeout: int = 30
    max_retries: int = 3
    user_agents: list[str] = None
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]


class RateLimitedScraper:
    """Rate-limited web scraper following best practices."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': random.choice(self.config.user_agents)})
    
    async def _wait_for_rate_limit(self) -> None:
        """Implement rate limiting with randomized delays."""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
    
    async def scrape_url(self, url: str, **kwargs) -> Optional[str]:
        """Scrape URL with proper rate limiting and error handling."""
        await self._wait_for_rate_limit()
        for attempt in range(self.config.max_retries):
            try:
                self.session.headers.update({'User-Agent': random.choice(self.config.user_agents)})
                response = self.session.get(url, timeout=self.config.timeout, **kwargs)
                response.raise_for_status()
                self.last_request_time = time.time()
                logger.info(f"Successfully scraped {url}")
                return response.text
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.config.max_retries - 1:
                    logger.error(f"Failed to scrape {url} after {self.config.max_retries} attempts.")
                    return None
                backoff = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(backoff)
        return None
    
    def close(self):
        """Close the session properly."""
        self.session.close()


_scraper = RateLimitedScraper()


async def scrape_website_func(url: str) -> str:
    """
    Enhanced website scraping with rate limiting and error handling.
    
    Args:
        url (str): The URL to scrape.
    """
    logger.info(f"Scraping website: {url}")
    try:
        html_content = await _scraper.scrape_url(url)
        if not html_content:
            return f"Failed to scrape {url} - no content retrieved"
        return await extract_exhibition_data(html_content)
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}", exc_info=True)
        return f"Error scraping {url}: {str(e)}"

scrape_website = tool(scrape_website_func)


class EnhancedBrowserManager:
    """Enhanced browser management with proper error handling and resource cleanup."""
    
    def __init__(self):
        self.driver = None
        self.chrome_options = None
        self._setup_chrome_options()
    
    def _setup_chrome_options(self):
        """Configure Chrome options for better scraping."""
        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument("--force-device-scale-factor=1")
        self.chrome_options.add_argument("--window-size=1000,1350")
        self.chrome_options.add_argument("--disable-pdf-viewer")
        self.chrome_options.add_argument("--window-position=0,0")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
    
    @asynccontextmanager
    async def get_browser(self):
        """Context manager for browser instances with proper cleanup."""
        try:
            if not self.driver:
                logger.info("Starting new browser instance...")
                self.driver = helium.start_chrome(headless=False, options=self.chrome_options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            yield self.driver
        except Exception as e:
            logger.error(f"Browser error: {e}", exc_info=True)
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as close_error:
                    logger.error(f"Error closing browser: {close_error}", exc_info=True)
                self.driver = None
            raise
    
    def close_browser(self):
        """Properly close browser and clean up resources."""
        if self.driver:
            try:
                logger.info("Closing browser instance...")
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing browser: {e}", exc_info=True)
            finally:
                self.driver = None


_browser_manager = EnhancedBrowserManager()


@tool
def enhanced_search_item(text: str, nth_result: int = 1, timeout: int = 10) -> str:
    """
    Enhanced search with proper error handling and timeouts.
    
    Args:
        text (str): The text to search for on the current page.
        nth_result (int): Which occurrence to jump to (default: 1).
        timeout (int): Maximum time to wait for elements in seconds (default: 10).
    """
    logger.info(f"Searching for text: '{text}' (result #{nth_result})")
    try:
        driver = helium.get_driver()
        if not driver:
            return "Error: No browser instance available"
        wait = WebDriverWait(driver, timeout)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        xpath = f"//*[contains(text(), '{text}')]"
        elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
        if nth_result > len(elements):
            return f"Match n°{nth_result} not found (only {len(elements)} matches found)"
        element = elements[nth_result - 1]
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(1)
        logger.info(f"Found {len(elements)} matches for '{text}'. Focused on element {nth_result}.")
        return f"Found {len(elements)} matches for '{text}'. Focused on element {nth_result} of {len(elements)}"
    except TimeoutException:
        logger.warning(f"Timeout while searching for '{text}'")
        return f"Timeout: Could not find text '{text}' within {timeout} seconds"
    except WebDriverException as e:
        logger.error(f"Browser error while searching for '{text}': {e}", exc_info=True)
        return f"Browser error while searching for '{text}': {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error while searching for '{text}': {e}", exc_info=True)
        return f"Unexpected error while searching for '{text}': {str(e)}"


@tool
def enhanced_close_popups() -> str:
    """Enhanced popup closing with multiple strategies."""
    logger.info("Attempting to close popups...")
    try:
        driver = helium.get_driver()
        if not driver:
            return "Error: No browser instance available"
        
        success_count = 0
        # Strategy 1: Press Escape key
        try:
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            success_count += 1
            time.sleep(0.5)
        except WebDriverException:
            pass
        
        # Strategy 2: Common close button selectors
        close_selectors = ["[data-dismiss='modal']", ".modal-close", ".close", "[aria-label='Close']", ".popup-close", "[title='Close']"]
        for selector in close_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        element.click()
                        success_count += 1
                        time.sleep(0.5)
            except WebDriverException:
                continue
        
        if success_count > 0:
            logger.info(f"Successfully closed {success_count} popups.")
            return f"Successfully attempted to close popups using {success_count} methods"
        else:
            logger.info("No popups detected or unable to close them.")
            return "No popups detected or unable to close them"
            
    except Exception as e:
        logger.error(f"Error while trying to close popups: {e}", exc_info=True)
        return f"Error while trying to close popups: {str(e)}"


def cleanup_resources():
    """Clean up global resources."""
    global _scraper, _browser_manager
    if _scraper:
        _scraper.close()
    if _browser_manager:
        _browser_manager.close_browser()


def extract_prices_with_regex(text: str) -> list[str]:
    """Extracts prices from text using regex."""
    price_pattern = r'(\£|\$|€|GBP|USD|EUR)\s?\d{1,3}(?:,?\d{3})*(?:\.\d{2})?'
    return re.findall(price_pattern, text)


def extract_dates_with_regex(text: str) -> list[str]:
    """Extracts dates from text using regex."""
    date_pattern = r'\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4})\b'
    return re.findall(date_pattern, text)


async def extract_exhibition_data_func(html_content: str) -> str:
    """
    Extracts relevant exhibition data from HTML content.
    
    Args:
        html_content (str): The HTML content of the page.
    """
    logger.info("Extracting exhibition data from HTML...")
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text_content = soup.get_text(strip=True, separator=' ')
        
        keywords = ["entry fee", "submission fee", "prize", "deadline", "exhibition dates"]
        relevant_sections = [s for keyword in keywords if keyword in text_content.lower() for match in re.finditer(keyword, text_content, re.IGNORECASE) for s in [text_content[max(0, match.start() - 200):min(len(text_content), match.end() + 200)]]]
        
        if relevant_sections:
            text_content = " ".join(relevant_sections)
        
        if len(text_content) > 4000:
            text_content = text_content[:4000] + "... [TRUNCATED]"
            
        prices = extract_prices_with_regex(text_content)
        dates = extract_dates_with_regex(text_content)
        
        result = f"Extracted Text Content:\n{text_content}\n\nDetected Prices: {prices}\nDetected Dates: {dates}"
        logger.info("Exhibition data extracted successfully.")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting exhibition data: {e}", exc_info=True)
        return f"Error extracting exhibition data: {str(e)}"

extract_exhibition_data = tool(extract_exhibition_data_func)


atexit.register(cleanup_resources)
