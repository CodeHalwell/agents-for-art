"""
Enhanced web scraping tools with proper rate limiting and anti-bot measures.
According to web scraping best practices: Use rate limiting, proxy rotation, and proper error handling.
"""
import asyncio
import atexit
import hashlib
import re
import random
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

import requests

# Handle missing dependencies gracefully
try:
    from bs4 import BeautifulSoup
except ImportError:
    class BeautifulSoup:
        def __init__(self, *args, **kwargs):
            self.text = ""
        def __call__(self, *args, **kwargs):
            return []
        def get_text(self, *args, **kwargs):
            return ""
        def find_all(self, *args, **kwargs):
            return []
        def decompose(self):
            pass

try:
    from smolagents import tool
    from smolagents.agents import ActionStep
except ImportError:
    def tool(func):
        return func
    ActionStep = object

try:
    import helium
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    # Mock selenium classes
    class MockWebDriver:
        def quit(self): pass
        def execute_script(self, *args): pass
        def find_elements(self, *args): return []
    
    class MockHelium:
        @staticmethod
        def start_chrome(*args, **kwargs):
            return MockWebDriver()
        @staticmethod
        def get_driver():
            return MockWebDriver()
    
    helium = MockHelium()
    webdriver = MockWebDriver()
    By = object()
    Keys = object()
    WebDriverWait = object
    EC = object()
    TimeoutException = Exception
    WebDriverException = Exception
    SELENIUM_AVAILABLE = False


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
async def scrape_website_safely(url: str, optimize_tokens: bool = True) -> str:
    """
    Enhanced website scraping with rate limiting and error handling.
    Now includes token optimization features.
    
    Args:
        url (str): The URL to scrape for text and links.
        optimize_tokens (bool): Whether to use token optimization preprocessing
        
    Returns:
        A string containing the extracted text content and links from the website.
        Returns an error message string if scraping fails.
    """
    try:
        html_content = await _scraper.scrape_url(url)
        if not html_content:
            return f"Failed to scrape {url} - no content retrieved"
        
        # Use token optimization if requested
        if optimize_tokens:
            optimized_content = preprocess_content_for_extraction(html_content)
            return f"URL: {url}\n\n{optimized_content}"
        
        # Original processing for backward compatibility
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
        if SELENIUM_AVAILABLE:
            self._setup_chrome_options()
    
    def _setup_chrome_options(self):
        """Configure Chrome options for better scraping."""
        if not SELENIUM_AVAILABLE:
            return
        
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
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium not available - browser management requires selenium installation")
        
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
        text (str): The text to search for on the current page.
        nth_result (int): Which occurrence to jump to (default: 1).
        timeout (int): Maximum time to wait for elements in seconds (default: 10).
        
    Returns:
        A string indicating the search result or error message.
    """
    if not SELENIUM_AVAILABLE:
        return "Error: Selenium not available - enhanced search requires selenium installation"
    
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
    if not SELENIUM_AVAILABLE:
        return "Error: Selenium not available - popup closing requires selenium installation"
    
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


# Token Usage Optimization Features
# ====================================

# Content caching system
_content_cache: Dict[str, Any] = {}

@tool
def cache_similar_content_patterns(content_hash: str, content: str = None) -> str:
    """
    Cache content patterns for similar content to reduce duplicate processing.
    
    Args:
        content_hash (str): Hash key for the content
        content (str, optional): Content to cache. If None, retrieves cached content.
        
    Returns:
        String indicating cache operation result or cached content.
    """
    global _content_cache
    
    if content is None:
        # Retrieve cached content
        if content_hash in _content_cache:
            return f"Cache hit: Retrieved content for hash {content_hash[:8]}..."
        else:
            return f"Cache miss: No content found for hash {content_hash[:8]}..."
    else:
        # Cache the content
        _content_cache[content_hash] = {
            'content': content,
            'timestamp': time.time()
        }
        return f"Cached content with hash {content_hash[:8]}... (size: {len(content)} chars)"


@tool
def extract_prices_with_regex(text: str) -> str:
    """
    Extract prices and fees using deterministic regex patterns.
    
    Args:
        text (str): Text content to extract prices from
        
    Returns:
        String containing extracted price information
    """
    price_patterns = [
        # UK currency formats
        r'£\s*(\d+(?:\.\d{2})?)',                    # £25, £25.00
        r'(\d+(?:\.\d{2})?)\s*(?:pounds?|GBP)',      # 25 pounds, 25.00 GBP
        r'entry\s+fee[:\s]*£?\s*(\d+(?:\.\d{2})?)',  # entry fee: £25
        r'submission\s+fee[:\s]*£?\s*(\d+(?:\.\d{2})?)',  # submission fee £25
        r'cost[:\s]*£?\s*(\d+(?:\.\d{2})?)',         # cost: £25
        r'price[:\s]*£?\s*(\d+(?:\.\d{2})?)',        # price: £25
        r'fee[:\s]*£?\s*(\d+(?:\.\d{2})?)',          # fee: £25
        r'£(\d+)\s*-\s*£(\d+)',                      # £25 - £50 (range)
        r'(\d+)\s*-\s*(\d+)\s*(?:pounds?|GBP)',      # 25 - 50 pounds (range)
        # Commission percentages
        r'(\d+(?:\.\d+)?)\s*%\s*commission',         # 30% commission
        r'commission[:\s]*(\d+(?:\.\d+)?)\s*%',      # commission: 30%
    ]
    
    extracted_prices = []
    
    for pattern in price_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end].strip()
            
            extracted_prices.append({
                'price': match.group(0),
                'context': context,
                'groups': match.groups()
            })
    
    if not extracted_prices:
        return "No prices found in text"
    
    result = "Extracted Prices:\n"
    for i, price_info in enumerate(extracted_prices[:10]):  # Limit to first 10 matches
        result += f"{i+1}. {price_info['price']} (context: ...{price_info['context']}...)\n"
    
    if len(extracted_prices) > 10:
        result += f"... and {len(extracted_prices) - 10} more prices found"
    
    return result


@tool  
def extract_dates_with_regex(text: str) -> str:
    """
    Extract dates using deterministic regex patterns.
    
    Args:
        text (str): Text content to extract dates from
        
    Returns:
        String containing extracted date information
    """
    date_patterns = [
        # Various date formats common in UK
        r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',           # DD/MM/YYYY, DD-MM-YY
        r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{2,4})',  # DD Month YYYY
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{2,4})',  # Month DD, YYYY
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{2,4})',  # Month YYYY
        r'(\d{2,4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})',           # YYYY/MM/DD
        # Deadline specific patterns
        r'deadline[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',  # deadline: DD/MM/YYYY
        r'deadline[:\s]*(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{2,4})',  # deadline: DD Month YYYY
        r'submission\s+deadline[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',  # submission deadline DD/MM/YYYY
        r'apply\s+by[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',  # apply by DD/MM/YYYY
        r'closes?[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',     # closes DD/MM/YYYY
        r'opens?[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',      # opens DD/MM/YYYY
        # Exhibition date ranges
        r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})\s*-\s*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})',  # DD/MM/YYYY - DD/MM/YYYY
    ]
    
    extracted_dates = []
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end].strip()
            
            extracted_dates.append({
                'date': match.group(0),
                'context': context,
                'groups': match.groups()
            })
    
    if not extracted_dates:
        return "No dates found in text"
    
    result = "Extracted Dates:\n"
    for i, date_info in enumerate(extracted_dates[:10]):  # Limit to first 10 matches
        result += f"{i+1}. {date_info['date']} (context: ...{date_info['context']}...)\n"
    
    if len(extracted_dates) > 10:
        result += f"... and {len(extracted_dates) - 10} more dates found"
    
    return result


@tool
def reduce_content_to_relevant_sections(content: str, keywords: List[str]) -> str:
    """
    Reduce content to sections relevant to the given keywords.
    
    Args:
        content (str): Full content to filter
        keywords (List[str]): Keywords to search for relevant sections
        
    Returns:
        String containing only relevant sections of content
    """
    if isinstance(keywords, str):
        keywords = [keywords]
    
    # Split content into sentences and paragraphs for better filtering
    # Try different splitting methods
    sections = []
    
    # First try splitting by double newlines (paragraphs)
    if '\n\n' in content:
        sections = re.split(r'\n\s*\n', content)
    # If no paragraphs, split by sentences
    elif '. ' in content:
        sections = re.split(r'\. ', content)
        # Add periods back except for the last one
        sections = [s + '.' if i < len(sections) - 1 else s for i, s in enumerate(sections)]
    # If no sentences, split by single newlines
    elif '\n' in content:
        sections = content.split('\n')
    # Otherwise, treat as single section
    else:
        sections = [content]
    
    relevant_sections = []
    
    # Art exhibition specific keywords if none provided
    if not keywords:
        keywords = [
            'exhibition', 'entry fee', 'submission', 'deadline', 'prize', 'award',
            'competition', 'open call', 'gallery', 'artist', 'artwork', 'entry',
            'cost', 'fee', 'commission', 'apply', 'deadline', 'closes', 'opens'
        ]
    
    # Create pattern to match any keyword
    keyword_pattern = '|'.join(re.escape(keyword.lower()) for keyword in keywords)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        # Check if section contains any keywords
        if re.search(keyword_pattern, section.lower()):
            relevant_sections.append(section)
    
    # If no relevant sections found, return first few sections as fallback
    if not relevant_sections:
        relevant_sections = sections[:3]  # First 3 sections as fallback
    
    # Join relevant sections
    if sections and '. ' in content:
        # If we split by sentences, join with periods and spaces
        result = ' '.join(relevant_sections)
    else:
        # Otherwise join with double newlines
        result = '\n\n'.join(relevant_sections)
    
    # Ensure result doesn't exceed reasonable size
    if len(result) > 5000:
        result = result[:5000] + "\n... [CONTENT TRUNCATED FOR TOKEN EFFICIENCY]"
    
    return result


@tool  
def preprocess_content_for_extraction(html_content: str) -> str:
    """
    Preprocess HTML content to extract relevant sections before LLM analysis.
    Combines multiple optimization strategies to reduce token usage.
    
    Args:
        html_content (str): Raw HTML content to preprocess
        
    Returns:
        String containing preprocessed, optimized content ready for LLM analysis
    """
    import re  # Import re at function level to ensure it's available
    
    # Generate content hash for caching
    content_hash = hashlib.md5(html_content.encode()).hexdigest()
    
    # Check cache first
    cached_result = cache_similar_content_patterns(content_hash)
    if "Cache hit" in cached_result:
        cached_data = _content_cache.get(content_hash, {}).get('content', '')
        if cached_data:
            return f"[CACHED CONTENT]\n{cached_data}"
    
    try:
        # Try to use BeautifulSoup if available, otherwise use regex fallback
        text_content = ""
        
        # Check if we have a real BeautifulSoup implementation
        if hasattr(BeautifulSoup, '__module__') and BeautifulSoup.__module__ == 'bs4':
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements that don't contain useful information
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 
                                'aside', 'iframe', 'noscript', 'meta', 'link']):
                element.decompose()
            
            # Extract text content
            text_content = soup.get_text(strip=True, separator=' ')
        else:
            # Use regex fallback (BeautifulSoup not available or mock being used)
            # Remove script and style tags
            text_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text_content = re.sub(r'<[^>]+>', ' ', text_content)
            # Clean up whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # If text_content is still empty, force regex extraction
        if not text_content or len(text_content) < 10:
            # Remove script and style tags
            text_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text_content = re.sub(r'<[^>]+>', ' ', text_content)
            # Clean up whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Clean up whitespace one more time
        text_content = re.sub(r'\s+', ' ', text_content)
        
        # Use content reduction with exhibition-specific keywords
        relevant_content = reduce_content_to_relevant_sections(
            text_content, 
            ['exhibition', 'entry fee', 'submission', 'deadline', 'prize', 
             'competition', 'open call', 'cost', 'commission', 'apply']
        )
        
        # Extract structured data with regex
        prices = extract_prices_with_regex(relevant_content)
        dates = extract_dates_with_regex(relevant_content)
        
        # Combine into optimized format
        processed_content = f"""PREPROCESSED CONTENT (Token Optimized):

RELEVANT TEXT:
{relevant_content}

EXTRACTED STRUCTURED DATA:
{prices}

{dates}
"""
        
        # Cache the result
        cache_similar_content_patterns(content_hash, processed_content)
        
        return processed_content
        
    except Exception as e:
        # Fallback processing
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        if len(text_content) > 5000:
            text_content = text_content[:5000] + "... [TRUNCATED]"
        
        return f"FALLBACK PROCESSING:\n{text_content}\n\nError: {str(e)}"


# Clean up resources on module unload

def cleanup_resources():
    """Clean up global resources."""
    global _scraper, _browser_manager, _content_cache
    if _scraper:
        _scraper.close()
    if _browser_manager:
        _browser_manager.close_browser()
    # Clear content cache
    _content_cache.clear()

@tool
def scrape_website(url: str, optimize_tokens: bool = True) -> str:
    """
    Enhanced website scraping with rate limiting and error handling (synchronous implementation).
    Now includes token optimization features.
    
    Args:
        url (str): The URL to scrape for text and links.
        optimize_tokens (bool): Whether to use token optimization preprocessing
        
    Returns:
        A string containing the extracted text content and links from the website.
        Returns an error message string if scraping fails.
    """
    try:
        import time
        import random
        import requests
        
        # Try BeautifulSoup first, fall back to basic parsing if not available
        try:
            from bs4 import BeautifulSoup
            use_bs4 = True
        except ImportError:
            use_bs4 = False
        
        # Simple rate limiting
        time.sleep(random.uniform(2.0, 8.0))
        
        # Create session with user agent
        session = requests.Session()
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        session.headers.update({
            'User-Agent': random.choice(user_agents)
        })
        
        # Make the request
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        # Use token optimization if requested
        if optimize_tokens:
            optimized_content = preprocess_content_for_extraction(response.text)
            session.close()
            return f"URL: {url}\n\n{optimized_content}"
        
        # Original processing for backward compatibility
        if use_bs4:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
        else:
            # Fallback: basic text extraction using regex
            import re
            
            # Remove script and style tags
            text_content = re.sub(r'<script[^>]*>.*?</script>', '', response.text, flags=re.DOTALL | re.IGNORECASE)
            text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML tags
            text_content = re.sub(r'<[^>]+>', ' ', text_content)
            
            # Clean up whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Extract links using regex
            link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
            links = re.findall(link_pattern, response.text, re.IGNORECASE)
            
            # Filter links
            links = [href for href in links if href and not href.startswith(('#', 'javascript:', 'mailto:'))]
        
        # Limit output size to prevent token overflow
        if len(text_content) > 10000:
            text_content = text_content[:10000] + "... [TRUNCATED]"
        
        if len(links) > 50:
            links = links[:50] + ["... [MORE LINKS TRUNCATED]"]
        
        result = f"Text Content:\n{text_content}\n\nLinks:\n" + '\n'.join(links)
        session.close()
        return result
        
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"


atexit.register(cleanup_resources)
