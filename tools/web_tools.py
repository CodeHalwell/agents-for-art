"""
Enhanced web scraping tools with proper rate limiting and anti-bot measures.
According to web scraping best practices: Use rate limiting, proxy rotation, and proper error handling.
"""
import asyncio
import atexit
import random
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
from smolagents.agents import ActionStep


@dataclass
class ScrapingConfig:
    """Configuration for web scraping operations"""
    min_delay: float = 2.0  # Minimum delay between requests
    max_delay: float = 8.0  # Maximum delay between requests
    timeout: int = 30       # Request timeout in seconds
    max_retries: int = 3    # Maximum retry attempts
    user_agents: list[str] = None  # List of user agents to rotate
    
    def __post_init__(self):
        if self.user_agents is None:
            # According to best practices: Rotate user agents to appear more human
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]


class RateLimitedScraper:
    """
    Rate-limited web scraper following best practices.
    According to scraping best practices: Implement proper delays and retry mechanisms.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.last_request_time = 0.0
        self.session = requests.Session()
        
        # Set a default user agent
        self.session.headers.update({
            'User-Agent': random.choice(self.config.user_agents)
        })
    
    async def _wait_for_rate_limit(self) -> None:
        """Implement rate limiting with randomized delays."""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        
        if elapsed < delay:
            wait_time = delay - elapsed
            await asyncio.sleep(wait_time)
    
    async def scrape_url(self, url: str, **kwargs) -> Optional[str]:
        """
        Scrape URL with proper rate limiting and error handling.
        According to best practices: Implement exponential backoff and proper error handling.
        """
        await self._wait_for_rate_limit()
        
        for attempt in range(self.config.max_retries):
            try:
                # Rotate user agent for each request
                self.session.headers.update({
                    'User-Agent': random.choice(self.config.user_agents)
                })
                
                response = self.session.get(
                    url, 
                    timeout=self.config.timeout,
                    **kwargs
                )
                response.raise_for_status()
                
                self.last_request_time = time.time()
                return response.text
                
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    print(f"Failed to scrape {url} after {self.config.max_retries} attempts: {e}")
                    return None
                
                # Exponential backoff with jitter
                backoff = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(backoff)
        
        return None
    
    def close(self):
        """Close the session properly."""
        self.session.close()


# Global scraper instance
_scraper = RateLimitedScraper()


@tool
async def scrape_website_safely(url: str) -> str:
    """
    Enhanced website scraping with rate limiting and error handling.
    
    Args:
        url: The URL to scrape for text and links.
        
    Returns:
        A string containing the extracted text content and links from the website.
        Returns error message if scraping fails.
    """
    try:
        html_content = await _scraper.scrape_url(url)
        if not html_content:
            return f"Failed to scrape {url} - no content retrieved"
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text content more efficiently
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text_content = soup.get_text(strip=True, separator=' ')
        
        # Extract all links with better filtering
        links = []
        for link in soup.find_all('a', href=True):
            # Ensure we have a Tag element that supports the get method
            if hasattr(link, 'get'):
                href = link.get('href')
                if href and not href.startswith(('#', 'javascript:', 'mailto:')):
                    links.append(href)
        
        # Limit output size to prevent token overflow
        if len(text_content) > 10000:
            text_content = text_content[:10000] + "... [TRUNCATED]"
        
        if len(links) > 50:
            links = links[:50] + ["... [MORE LINKS TRUNCATED]"]
        
        result = f"Text Content:\n{text_content}\n\nLinks:\n" + '\n'.join(links)
        return result
        
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"


class EnhancedBrowserManager:
    """
    Enhanced browser management with proper error handling and resource cleanup.
    According to Selenium best practices: Proper browser lifecycle management.
    """
    
    def __init__(self):
        self.driver = None
        self.chrome_options = None
        self._setup_chrome_options()
    
    def _setup_chrome_options(self):
        """Configure Chrome options for better scraping."""
        self.chrome_options = webdriver.ChromeOptions()
        
        # According to anti-detection best practices
        self.chrome_options.add_argument("--force-device-scale-factor=1")
        self.chrome_options.add_argument("--window-size=1000,1350")
        self.chrome_options.add_argument("--disable-pdf-viewer")
        self.chrome_options.add_argument("--window-position=0,0")
        
        # Additional anti-detection measures
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Performance optimizations
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
    
    @asynccontextmanager
    async def get_browser(self):
        """Context manager for browser instances with proper cleanup."""
        try:
            if not self.driver:
                self.driver = helium.start_chrome(
                    headless=False, 
                    options=self.chrome_options
                )
                
                # Execute script to remove webdriver property
                self.driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
            
            yield self.driver
            
        except Exception as e:
            print(f"Browser error: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as close_error:
                    print(f"Error closing browser: {close_error}")
                    pass
                self.driver = None
            raise
    
    def close_browser(self):
        """Properly close browser and clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error closing browser: {e}")
                pass
            finally:
                self.driver = None


# Global browser manager
_browser_manager = EnhancedBrowserManager()


@tool
def enhanced_search_item(text: str, nth_result: int = 1, timeout: int = 10) -> str:
    """
    Enhanced search with proper error handling and timeouts.
    
    Args:
        text: The text to search for on the current page.
        nth_result: Which occurrence to jump to (default: 1).
        timeout: Maximum time to wait for elements in seconds (default: 10).
        
    Returns:
        A string indicating the search result or error message.
    """
    try:
        driver = helium.get_driver()
        if not driver:
            return "Error: No browser instance available"
        
        # Use WebDriverWait for better reliability
        wait = WebDriverWait(driver, timeout)
        
        # Wait for page to be ready
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        # Find elements with explicit wait
        xpath = f"//*[contains(text(), '{text}')]"
        elements = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, xpath))
        )
        
        if nth_result > len(elements):
            return f"Match n°{nth_result} not found (only {len(elements)} matches found)"
        
        element = elements[nth_result - 1]
        
        # Scroll to element with retry logic
        for attempt in range(3):
            try:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                # Wait a bit for smooth scrolling
                time.sleep(1)
                break
            except Exception as e:
                if attempt == 2:
                    return f"Failed to scroll to element: {e}"
                time.sleep(1)
        
        return f"Found {len(elements)} matches for '{text}'. Focused on element {nth_result} of {len(elements)}"
        
    except TimeoutException:
        return f"Timeout: Could not find text '{text}' within {timeout} seconds"
    except WebDriverException as e:
        return f"Browser error while searching for '{text}': {str(e)}"
    except Exception as e:
        return f"Unexpected error while searching for '{text}': {str(e)}"


@tool
def enhanced_close_popups() -> str:
    """
    Enhanced popup closing with multiple strategies.
    
    Args:
        None
        
    Returns:
        A string indicating the success or failure of popup closing attempts.
    """
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
        
        # Strategy 2: Look for common close button selectors
        close_selectors = [
            "[data-dismiss='modal']",
            ".modal-close",
            ".close",
            "[aria-label='Close']",
            ".popup-close",
            "[title='Close']"
        ]
        
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
        
        # Strategy 3: Look for overlay elements to click
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, ".modal-backdrop, .overlay, .popup-overlay")
            for overlay in overlays:
                if overlay.is_displayed():
                    overlay.click()
                    success_count += 1
                    time.sleep(0.5)
        except WebDriverException:
            pass
        
        if success_count > 0:
            return f"Successfully attempted to close popups using {success_count} methods"
        else:
            return "No popups detected or unable to close them"
            
    except Exception as e:
        return f"Error while trying to close popups: {str(e)}"


# Clean up resources on module unload

def cleanup_resources():
    """Clean up global resources."""
    global _scraper, _browser_manager
    if _scraper:
        _scraper.close()
    if _browser_manager:
        _browser_manager.close_browser()

atexit.register(cleanup_resources)
