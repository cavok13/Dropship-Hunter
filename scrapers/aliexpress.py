"""AliExpress Top-Selling products scraper."""
"""AliExpress scraper — Fixed selectors 2026 + ScraperAPI render=true"""
import re
import time
import requests
from bs4 import BeautifulSoup


class AliExpressScraper:
    def __init__(self, cfg):
        self.cfg = cfg
        scraping = cfg.get("scraping", {})
        # ─── support both key names in config ────────────────────────────────
        self.api_key = (
            scraping.get("scraperapi_key") or
            scraping.get("scraper_api_key") or ""
        )
        self.use_api = scraping.get("use_scraper_api", False)
        self.urls    = cfg.get("aliexpress", {}).get("start_urls", [])

    # ── public ────────────────────────────────────────────────────────────────
    def scrape_all(self):
        all_products = []
        for url in self.urls:
            products = self.scrape_url(url)
            print(f"  [AliExpress] {url[:60]}… → {len(products)} products")
            all_products.extend(products)
            time.sleep(2)
        return all_products

    # ── internal ──────────────────────────────────────────────────────────────
    def _fetch(self, url: str) -> str | None:
        """Fetch page HTML — with or without ScraperAPI."""
        if self.use_api and self.api_key:
            endpoint = (
                "http://api.scraperapi.com"
                f"?api_key={self.api_key}"
                f"&url={requests.utils.quote(url, safe='')}"
                "&render=true"       # ← critical for AliExpress JS
                "&country_code=us"
            )
            try:
                r = requests.get(endpoint, timeout=90)
                if r.status_code == 200:
                    return r.text
                print(f"  [AliExpress] ScraperAPI error {r.status_code}")
                return None
            except Exception as e:
                print(f"  [AliExpress] fetch error: {e}")
                return None
        else:
            # Without ScraperAPI → AliExpress will likely return empty JS page
            print("  [AliExpress] ⚠ No ScraperAPI key — results may be empty")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            try:
                r = requests.get(url, headers=headers, timeout=30)
                return r.text if r.status_code == 200 else None
            except Exception as e:
                print(f"  [AliExpress] direct fetch error: {e}")
                return None

    def scrape_url(self, url: str) -> list[dict]:
        html = self._fetch(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        products = []

        # ── 2026 selector cascade (most → least specific) ─────────────────
        cards = (
            soup.select("div[class*='search-item-card']")   or
            soup.select("div[class*='SearchItem']")          or
            soup.select("div[class*='list-item']")           or
            soup.select("div[class*='card--']")              or
            soup.select("a[href*='/item/'][class*='card']")
        )

        if not cards:
            print("  [AliExpress] ⚠ No cards found — page may need render=true")
            return []

        for card in cards:
            try:
                # ── title ──────────────────────────────────────────────────
                title_el = (
                    card.select_one("[class*='item-title']")  or
                    card.select_one("[class*='title--']")      or
                    card.select_one("h3")                      or
                    card.select_one("a[title]")
                )
                title = (
                    (title_el.get("title") or title_el.get_text(strip=True))
                    if title_el else ""
                )
                if not title or len(title) < 5:
                    continue

                # ── price ───────────────────────────────────────────────────
                price_el = (
                    card.select_one("[class*='price-sale']")   or
                    card.select_one("[class*='price--current']") or
                    card.select_one("[class*='price']")
                )
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price_match = re.search(r"[\d.]+", price_text.replace(",", "."))
                price = float(price_match.group()) if price_match else 0.0

                # ── orders ──────────────────────────────────────────────────
                orders_el = (
                    card.select_one("[class*='trade--']")   or
                    card.select_one("[class*='sold']")      or
                    card.select_one("[class*='order']")
                )
                orders = 0
                if orders_el:
                    txt = orders_el.get_text(strip=True).lower()
                    m = re.search(r"([\d.]+)\s*([km])?", txt)
                    if m:
                        val = float(m.group(1))
                        if m.group(2) == "k":   val *= 1_000
                        elif m.group(2) == "m": val *= 1_000_000
                        orders = int(val)

                # ── link ────────────────────────────────────────────────────
                link_el = card.select_one("a[href*='/item/']") or card.select_one("a")
                href = link_el.get("href", "") if link_el else ""
                if href.startswith("//"):
                    href = "https:" + href
                elif href and not href.startswith("http"):
                    href = "https://www.aliexpress.com" + href

                # ── image ───────────────────────────────────────────────────
                img_el = card.select_one("img")
                image  = (
                    img_el.get("src") or img_el.get("data-src", "")
                ) if img_el else ""

                if price == 0:
                    continue   # skip unparseable products

                products.append({
                    "title":        title[:120],
                    "url":          href,
                    "image":        image,
                    "price":        price,
                    "rating":       4.5,
                    "reviews":      max(orders // 10, 50),
                    "orders":       orders if orders else 500,
                    "bsr_rank":     999,
                    "platform":     "AliExpress",
                    "category":     "aliexpress",
                    "seller_count": 0,
                })
            except Exception:
                continue

        return products[:30]

    def close(self):
        pass
