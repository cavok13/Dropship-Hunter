"""Amazon Best Sellers scraper."""

"""Amazon Best Sellers scraper — Fixed selectors 2026 + ScraperAPI"""
import re
import time
import requests
from bs4 import BeautifulSoup


class AmazonScraper:
    def __init__(self, cfg):
        self.cfg = cfg
        scraping = cfg.get("scraping", {})
        # ─── support both key names ───────────────────────────────────────────
        self.api_key = (
            scraping.get("scraperapi_key") or
            scraping.get("scraper_api_key") or ""
        )
        self.use_api = scraping.get("use_scraper_api", False)
        self.urls    = cfg.get("amazon", {}).get("start_urls", [])

    # ── public ────────────────────────────────────────────────────────────────
    def scrape_all(self):
        all_products = []
        for url in self.urls:
            products = self.scrape_url(url)
            print(f"  [Amazon] {url[:60]}… → {len(products)} products")
            all_products.extend(products)
            time.sleep(1)
        return all_products

    # ── internal ──────────────────────────────────────────────────────────────
    def _fetch(self, url: str) -> str | None:
        if self.use_api and self.api_key:
            endpoint = (
                "http://api.scraperapi.com"
                f"?api_key={self.api_key}"
                f"&url={requests.utils.quote(url, safe='')}"
                "&render=true"
                "&country_code=us"
            )
            try:
                r = requests.get(endpoint, timeout=90)
                if r.status_code == 200:
                    return r.text
                print(f"  [Amazon] ScraperAPI error {r.status_code}")
                return None
            except Exception as e:
                print(f"  [Amazon] fetch error: {e}")
                return None
        else:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language":  "en-US,en;q=0.9",
                "Accept-Encoding":  "gzip, deflate, br",
                "Accept":           "text/html,application/xhtml+xml,*/*;q=0.8",
                "Referer":          "https://www.google.com/",
                "DNT":              "1",
            }
            try:
                time.sleep(3)
                r = requests.get(url, headers=headers, timeout=25)
                return r.text if r.status_code == 200 else None
            except Exception as e:
                print(f"  [Amazon] direct fetch error: {e}")
                return None

    def scrape_url(self, url: str) -> list[dict]:
        html = self._fetch(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        products = []

        # ── 2026 correct selector: zg-no-numbers (NOT zg-grid-general-faceout) ─
        cards = (
            soup.select("div.zg-no-numbers")            or   # ← current 2024–2026
            soup.select("li.zg-item-immersion")         or   # ← older layout fallback
            soup.select("div[data-asin][data-index]")        # ← last resort
        )

        if not cards:
            print("  [Amazon] ⚠ No cards found — selector may have changed")
            return []

        for rank, card in enumerate(cards, start=1):
            try:
                # Skip if no ASIN (means it's an ad or placeholder)
                asin = card.get("data-asin", "")

                # ── title ──────────────────────────────────────────────────
                title_el = (
                    card.select_one("._cDEzb_p13n-sc-css-line-clamp-3_g3dy1") or
                    card.select_one(".p13n-sc-truncated")                       or
                    card.select_one("span.a-size-base.a-color-base")            or
                    card.select_one("div._p13n-zg-list-grid-desktop_style_p13n-grid-fn_26S0J a")
                )
                # title from link if not found
                if not title_el:
                    for a in card.find_all("a", class_="a-link-normal"):
                        if a.get_text(strip=True) and "/dp/" in a.get("href",""):
                            title_el = a
                            break
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                # ── price ───────────────────────────────────────────────────
                price_el = (
                    card.select_one("span.p13n-sc-price")      or
                    card.select_one("span._p13n-zg-list-grid-desktop_style_price-drop-indicator__XN8OS") or
                    card.select_one("span.a-price > span.a-offscreen")
                )
                price_text  = price_el.get_text(strip=True) if price_el else "0"
                price_match = re.search(r"[\d.]+", price_text.replace(",", ""))
                price       = float(price_match.group()) if price_match else 0.0

                # ── rating ──────────────────────────────────────────────────
                rating_el = card.select_one("i.a-icon-star")
                rating = 4.5
                if rating_el:
                    txt = rating_el.get("class", [])
                    for cls in txt:
                        m = re.search(r"a-star-([\d-]+)", cls)
                        if m:
                            rating = float(m.group(1).replace("-", "."))
                            break

                # ── reviews ─────────────────────────────────────────────────
                reviews_el  = card.select_one("span.a-size-small")
                reviews_str = (
                    reviews_el.get("aria-label", "") or
                    reviews_el.get_text(strip=True)
                ) if reviews_el else ""
                rm      = re.search(r"([\d,]+)", reviews_str)
                reviews = int(rm.group(1).replace(",", "")) if rm else 100

                # ── link ────────────────────────────────────────────────────
                link_el  = card.select_one("a.a-link-normal[href*='/dp/']")
                href     = link_el.get("href", "") if link_el else ""
                full_url = ("https://www.amazon.com" + href
                            if href and not href.startswith("http") else href)

                # ── image ───────────────────────────────────────────────────
                img_el = card.select_one("img")
                image  = img_el.get("src", "") if img_el else ""

                products.append({
                    "title":        title[:120],
                    "url":          full_url,
                    "image":        image,
                    "price":        price,
                    "rating":       rating,
                    "reviews":      reviews,
                    "bsr_rank":     rank,
                    "orders":       0,
                    "platform":     "Amazon",
                    "category":     "amazon",
                    "seller_count": 0,
                    "asin":         asin,
                })
            except Exception:
                continue

        return products[:30]

    def close(self):
        pass
