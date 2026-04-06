"""Amazon Best Sellers scraper."""

  # scrapers/amazon.py  — Fixed for 2026
import requests, time, random, urllib.parse
from bs4 import BeautifulSoup

# ── الـ URLs الصحيحة لـ Amazon Best Sellers ──────────────────────────────────
AMAZON_CATEGORIES = {
    "electronics":    "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
    "home_kitchen":   "https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/kitchen/",
    "beauty":         "https://www.amazon.com/Best-Sellers-Beauty/zgbs/beauty/",
    "health":         "https://www.amazon.com/Best-Sellers-Health-Personal-Care/zgbs/hpc/",
    "toys":           "https://www.amazon.com/Best-Sellers-Toys-Games/zgbs/toys-and-games/",
    "sports":         "https://www.amazon.com/Best-Sellers-Sports-Outdoors/zgbs/sporting-goods/",
    "pet_supplies":   "https://www.amazon.com/Best-Sellers-Pet-Supplies/zgbs/pet-supplies/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "DNT": "1",
}


def _get(url: str, scraperapi_key: str = "") -> str | None:
    """Fetch URL — via ScraperAPI (recommended) or direct."""
    try:
        if scraperapi_key:
            # ScraperAPI handles JS + anti-bot automatically
            endpoint = (
                "http://api.scraperapi.com"
                f"?api_key={scraperapi_key}"
                f"&url={urllib.parse.quote(url, safe='')}"
                "&render=true"
                "&country_code=us"
            )
            r = requests.get(endpoint, timeout=60)
        else:
            time.sleep(random.uniform(3, 7))
            r = requests.get(url, headers=HEADERS, timeout=20)

        return r.text if r.status_code == 200 else None
    except Exception as e:
        print(f"  [Amazon] fetch error: {e}")
        return None


def _parse_page(html: str, page: int = 1) -> list[dict]:
    """Parse HTML using the 2026 correct selector: zg-no-numbers"""
    soup = BeautifulSoup(html, "lxml")
    items = soup.find_all(class_="zg-no-numbers")

    if not items:
        # fallback selector sometimes used
        items = soup.find_all("div", {"data-asin": True})

    products = []
    for idx, item in enumerate(items, start=1):
        try:
            # ASIN
            asin_el = item.find(attrs={"data-asin": True})
            asin = asin_el.get("data-asin", "") if asin_el else ""

            # Name + URL
            name, link = "", ""
            for a in item.find_all("a", class_="a-link-normal"):
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if "/dp/" in href and text and not text.startswith("$"):
                    link = ("https://www.amazon.com" + href
                            if not href.startswith("http") else href)
                    name = text
                    break

            # Price
            price_tag = item.find("span", class_=lambda x: x and "p13n-sc-price" in str(x))
            price_str = price_tag.get_text(strip=True) if price_tag else "0"
            price = float(price_str.replace("$", "").replace(",", "").strip() or 0)

            # Rating + reviews
            rating, reviews = 0.0, 0
            star = item.find("i", class_=lambda x: x and "a-icon-star" in str(x))
            if star:
                parent = star.find_parent("a")
                if parent:
                    aria = parent.get("aria-label", "")
                    if "stars" in aria:
                        parts = aria.split("stars")
                        try: rating = float(parts[0].strip().split()[-1])
                        except: pass
                        if len(parts) > 1:
                            rev = parts[1].strip().lstrip(",").strip()
                            try: reviews = int(rev.replace(" ratings","").replace(",",""))
                            except: pass

            # Image
            img = item.find("img")
            image = img.get("src", img.get("data-src", "")) if img else ""

            if name and price > 0:
                products.append({
                    "source":   "amazon",
                    "asin":     asin,
                    "title":    name,
                    "price":    price,
                    "rating":   rating,
                    "reviews":  reviews,
                    "rank":     idx + (page - 1) * 50,
                    "url":      link,
                    "image":    image,
                })
        except Exception:
            continue

    return products


def fetch_amazon(categories: list[str] = None,
                 scraperapi_key: str = "",
                 pages: int = 1) -> list[dict]:
    """Main function — returns list of product dicts."""
    cats = categories or list(AMAZON_CATEGORIES.keys())
    all_products = []

    for cat in cats:
        base_url = AMAZON_CATEGORIES.get(cat)
        if not base_url:
            continue
        print(f"  [Amazon] Scraping: {cat}")

        for page in range(1, pages + 1):
            if page == 1:
                url = base_url
            else:
                slug = base_url.rstrip("/").split("/")[-1]
                url = (f"{base_url}ref=zg_bs_pg_{page}_{slug}"
                       f"?_encoding=UTF8&pg={page}")

            html = _get(url, scraperapi_key)
            if not html:
                print(f"    [Amazon] ✗ No response for {cat} p{page}")
                continue

            products = _parse_page(html, page)
            print(f"    [Amazon] ✓ {len(products)} products from {cat} p{page}")
            all_products.extend(products)
            time.sleep(1)

    return all_products
