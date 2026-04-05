"""Base scraper with rotating UA, retry logic, and optional ScraperAPI proxy."""
import time, random, httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fake_useragent import UserAgent
from rich.console import Console

console = Console()
_ua = UserAgent()

DESKTOP_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


class BaseScraper:
    """Shared HTTP client with rate-limiting, proxy support, and retries."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.delay = cfg["scraping"].get("request_delay", 3)
        self.timeout = cfg["scraping"].get("timeout", 20)
        self.use_scraper_api = cfg["scraping"].get("use_scraper_api", False)
        self.api_key = cfg["scraping"].get("scraper_api_key", "")
        self._client = self._build_client()

    def _build_client(self) -> httpx.Client:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        return httpx.Client(
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
            http2=True,
        )

    def _get_url(self, url: str) -> str:
        """Wrap URL through ScraperAPI if enabled."""
        if self.use_scraper_api and self.api_key:
            return f"https://api.scraperapi.com?api_key={self.api_key}&url={url}&render=false"
        return url

    def _random_headers(self) -> dict:
        return {"User-Agent": random.choice(DESKTOP_AGENTS)}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=15),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    def get(self, url: str) -> httpx.Response:
        time.sleep(self.delay + random.uniform(0, 1.5))
        target = self._get_url(url)
        resp = self._client.get(target, headers=self._random_headers())
        resp.raise_for_status()
        return resp

    def close(self):
        self._client.close()
