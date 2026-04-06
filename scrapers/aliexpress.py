"""AliExpress Top-Selling products scraper."""
import requests
from bs4 import BeautifulSoup
class AliExpressScraper:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api_key = cfg.get("scraping", {}).get("scraper_api_key", "")
        self.use_api = cfg.get("scraping", {}).get("use_scraper_api", False)
        self.urls = cfg.get("aliexpress", {}).get("start_urls", [])
    
    def scrape_all(self):
        all_products = []
        for url in self.urls:
            products = self.scrape_url(url)
            all_products.extend(products)
        return all_products
    
    def scrape_url(self, url):
        if self.use_api and self.api_key:
            proxy_url = f"http://scraperapi:{self.api_key}@proxy-server.scraperapi.com:8001"
            proxies = {"http": proxy_url, "https": proxy_url}
            resp = requests.get(url, proxies=proxies, verify=False, timeout=60)
        else:
            resp = requests.get(url, timeout=30)
        
        if resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        products = []
        
        for item in soup.select(".manhattan--container--1lP57Ag, div[data-product-id]"):
            try:
                title_el = item.select_one("h3, span.manhattan--titleText")
                price_el = item.select_one(".manhattan--price-sale, .price--current")
                orders_el = item.select_one(".manhattan--trade, [class*='trade']")
                img_el = item.select_one("img")
                link_el = item.select_one("a")
                
                if not title_el:
                    continue
                
                title = title_el.get_text(strip=True)
                
                price_text = price_el.get_text(strip=True) if price_el else "0"
                import re
                price_match = re.search(r"[\d.]+", price_text)
                price = float(price_match.group()) if price_match else 0
                
                orders_text = orders_el.get_text(strip=True) if orders_el else "0"
                orders_match = re.search(r"([\d.]+)\s*([km])?", orders_text.lower())
                orders = 0
                if orders_match:
                    val = float(orders_match.group(1))
                    suffix = orders_match.group(2)
                    if suffix == "k": val *= 1000
                    elif suffix == "m": val *= 1000000
                    orders = int(val)
                
                url = "https:" + link_el["href"] if link_el else ""
                image = img_el.get("src", img_el.get("data-src", "")) if img_el else ""
                
                products.append({
                    "title": title[:120],
                    "url": url,
                    "image": image,
                    "price": price,
                    "rating": 4.5,
                    "reviews": orders // 10,
                    "orders": orders,
                    "bsr_rank": 999,
                    "platform": "AliExpress",
                    "category": "aliexpress",
                    "seller_count": 0,
                })
            except Exception:
                continue
        
        return products
    
    def close(self):
        pass
