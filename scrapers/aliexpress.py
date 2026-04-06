"""AliExpress Top-Selling products scraper."""
# scrapers/aliexpress.py  — Fixed for 2026
# AliExpress = 100% JavaScript rendered, needs render=true via ScraperAPI
import requests, time, urllib.parse
from bs4 import BeautifulSoup

KEYWORDS = [
    "home decor", "kitchen gadgets", "phone accessories",
    "beauty tools", "fitness equipment", "pet accessories",
    "car accessories", "baby products",
]


def _get_rendered(url: str, scraperapi_key: str) -> str | None:
    """
    AliExpress requires JavaScript rendering.
    ScraperAPI free plan handles this with render=true.
    Without a key → returns None (can't scrape AliExpress without JS).
    """
    if not scraperapi_key:
        print("  [AliExpress] ✗ ScraperAPI key required (AliExpress is JS-only)")
        print("     → Sign up FREE at scraperapi.com (1000 req/month)")
        return None

    endpoint = (
        "http://api.scraperapi.com"
        f"?api_key={scraperapi_key}"
        f"&url={urllib.parse.quote(url, safe='')}"
        "&render=true"
        "&country_code=us"
    )
    try:
        r = requests.get(endpoint, timeout=90)  # longer timeout for JS render
        return r.text if r.status_code == 200 else None
    except Exception as e:
        print(f"  [AliExpress] fetch error: {e}")
        return None


def _parse_search(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    products = []

    # 2026 working selectors (multiple fallbacks)
    cards = (
        soup.select("[class*='search-item-card']") or
        soup.select("[class*='list--gallery']") or
        soup.select("div[class*='card--']")
    )

    for card in cards:
        try:
            title_el = (
                card.select_one("[class*='item-title']") or
                card.select_one("[class*='title--']") or
                card.select_one("h3")
            )
            price_el = (
                card.select_one("[class*='price-current']") or
                card.select_one("[class*='price--current']") or
                card.select_one("[class*='sale-price']")
            )
            orders_el = (
                card.select_one("[class*='trade--']") or
                card.select_one("[class*='order']")
            )
            img_el  = card.select_one("img")
            link_el = card.select_one("a[href*='/item/']") or card.select_one("a")

            if not title_el or not price_el:
                continue

            title = title_el.get_text(strip=True)
            price_str = price_el.get_text(strip=True)
            price = float(
                price_str.replace("US $", "").replace("$", "")
                         .replace(",", "").strip().split("-")[0]
                or 0
            )
            orders_str = orders_el.get_text(strip=True) if orders_el else "0"
            orders = int(
                orders_str.replace(" sold", "").replace(",", "")
                          .replace("+", "").strip() or 0
            )
            href = link_el.get("href", "") if link_el else ""
            url  = ("https:" + href if href.startswith("//") else href)

            if title and price > 0:
                products.append({
                    "source":  "aliexpress",
                    "title":   title,
                    "price":   price,
                    "rating":  0.0,   # needs detail page
                    "reviews": orders,
                    "orders":  orders,
                    "rank":    0,
                    "url":     url,
                    "image":   img_el.get("src", img_el.get("data-src","")) if img_el else "",
                })
        except Exception:
            continue

    return products


def fetch_aliexpress(keywords: list[str] = None,
                     scraperapi_key: str = "",
                     pages: int = 1) -> list[dict]:
    kws = keywords or KEYWORDS
    all_products = []

    for kw in kws:
        print(f"  [AliExpress] Scraping: {kw}")
        for page in range(1, pages + 1):
            url = (
                "https://www.aliexpress.com/wholesale"
                f"?SearchText={urllib.parse.quote(kw)}"
                f"&SortType=total_tranpro_desc&page={page}"
            )
            html = _get_rendered(url, scraperapi_key)
            if not html:
                break
            products = _parse_search(html)
            print(f"    [AliExpress] ✓ {len(products)} products for '{kw}' p{page}")
            all_products.extend(products)
            time.sleep(2)

    return all_products
