"""Amazon Best Sellers scraper."""
import requests
import re
from bs4 import BeautifulSoup
class AmazonScraper:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api_key = cfg.get("scraping", {}).get("scraper_api_key", "")
        self.use_api = cfg.get("scraping", {}).get("use_scraper_api", False)
        self.urls = cfg.get("amazon", {}).get("start_urls", [])
    
    def scrape_all(self):
        all_products = []
        for url in self.urls:
            products = self.scrape_url(url)
            all_products.extend(products)
        return all_products
    
    def scrape_url(self, url):
        if self.use_api and self.api_key:
            endpoint = (
                f"http://api.scraperapi.com"
                f"?api_key={self.api_key}"
                f"&url={requests.utils.quote(url, safe='')}"
                f"&autoparse=true"
            )
            resp = requests.get(endpoint, timeout=60)
        else:
            resp = requests.get(url, timeout=30)
        
        if resp.status_code != 200:
            return []
        
        products = []
        
        try:
            data = resp.json()
            results = data.get("results", [])
            for item in results:
                products.append({
                    "title": item.get("title", "")[:120],
                    "url": item.get("url", ""),
                    "image": item.get("image", ""),
                    "price": self._parse_price(item.get("price", "0")),
                    "rating": float(item.get("rating", "0")[:3] or 0),
                    "reviews": self._parse_number(item.get("reviews", "0")),
                    "bsr_rank": self._parse_number(item.get("bsr", "999")),
                    "orders": 0,
                    "platform": "Amazon",
                    "category": "amazon",
                    "seller_count": 0,
                })
        except Exception:
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select("div.zg-grid-general-faceout, li.zg-item-immersion"):
                try:
                    title_el = item.select_one(".p13n-sc-truncated, span.a-size-base")
                    price_el = item.select_one(".p13n-sc-price")
                    rating_el = item.select_one(".a-icon-alt")
                    rank_el = item.select_one(".zg-bdg-text")
                    img_el = item.select_one("img")
                    link_el = item.select_one("a")
                    
                    if not title_el:
                        continue
                    
                    products.append({
                        "title": title_el.get_text(strip=True)[:120],
                        "url": "https://amazon.com" + link_el["href"] if link_el else "",
                        "image": img_el.get("src", "") if img_el else "",
                        "price": self._parse_price(price_el.get_text(strip=True) if price_el else "0"),
                        "rating": float(rating_el.get_text(strip=True)[:3] or 0) if rating_el else 0,
                        "reviews": 0,
                        "bsr_rank": self._parse_number(rank_el.get_text(strip=True) if rank_el else "999"),
                        "orders": 0,
                        "platform": "Amazon",
                        "category": "amazon",
                        "seller_count": 0,
                    })
                except Exception:
                    continue
        
        return products
    
    def _parse_price(self, text):
        m = re.search(r"[\d.]+", text)
        return float(m.group()) if m else 0
    
    def _parse_number(self, text):
        m = re.search(r"[\d,]+", str(text))
        return int(m.group().replace(",", "")) if m else 0
    
    def close(self):
        pass
