"""Amazon Best Sellers scraper."""
import re
from bs4 import BeautifulSoup
from rich.console import Console
from .base import BaseScraper

console = Console()
BASE = "https://www.amazon.com"


class AmazonScraper(BaseScraper):
    """Scrapes Amazon Best Sellers pages for product signals."""

    def scrape_category(self, path: str) -> list[dict]:
        """
        path: e.g. 'zgbs/beauty'  →  amazon.com/Best-Sellers-{path}
        Returns list of raw product dicts.
        """
        url = f"{BASE}/Best-Sellers-{path.replace('zgbs/', '')}/" \
              f"zgbs/{path.split('/')[-1]}"
        # Simpler approach – just use the /zgbs/ path directly
        url = f"{BASE}/{path}"
        console.print(f"  [cyan]→ Amazon:[/cyan] {url}")
        try:
            resp = self.get(url)
        except Exception as e:
            console.print(f"  [red]✗ Failed:[/red] {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        products = []

        # Amazon Best Sellers grid items
        for item in soup.select("div.zg-grid-general-faceout, li.zg-item-immersion"):
            try:
                prod = self._parse_item(item, path)
                if prod:
                    products.append(prod)
            except Exception:
                continue

        console.print(f"    [green]✓ {len(products)} products[/green]")
        return products

    def _parse_item(self, item, category_path: str) -> dict | None:
        # Title
        title_el = item.select_one(
            "div._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y, "
            "span.a-size-base.a-color-base, "
            "div.p13n-sc-truncate-desktop-type2, "
            ".p13n-sc-truncated"
        )
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            return None

        # URL
        link_el = item.select_one("a.a-link-normal")
        url = BASE + link_el["href"] if link_el and link_el.get("href") else ""

        # Image
        img_el = item.select_one("img")
        image = img_el.get("src", "") if img_el else ""

        # Price
        price_raw = item.select_one(
            "span.p13n-sc-price, span._cDEzb_p13n-sc-price_3mJ9Z"
        )
        price = 0.0
        if price_raw:
            m = re.search(r"[\d,.]+", price_raw.get_text())
            if m:
                price = float(m.group().replace(",", ""))

        # Rating
        rating_el = item.select_one("span.a-icon-alt")
        rating = 0.0
        if rating_el:
            m = re.search(r"([\d.]+)", rating_el.get_text())
            if m:
                rating = float(m.group(1))

        # Review count
        reviews_el = item.select_one("span.a-size-small, span[aria-label]")
        reviews = 0
        if reviews_el:
            aria = reviews_el.get("aria-label", reviews_el.get_text())
            m = re.search(r"([\d,]+)", aria)
            if m:
                reviews = int(m.group(1).replace(",", ""))

        # BSR rank
        rank_el = item.select_one("span.zg-bdg-text")
        rank = 999
        if rank_el:
            m = re.search(r"#?([\d,]+)", rank_el.get_text())
            if m:
                rank = int(m.group(1).replace(",", ""))

        return {
            "title": title[:120],
            "url": url,
            "image": image,
            "price": price,
            "rating": rating,
            "reviews": reviews,
            "bsr_rank": rank,
            "orders": 0,            # Amazon doesn't show order count
            "platform": "Amazon",
            "category": category_path,
            "seller_count": 0,      # enriched later if needed
        }

    def scrape_all(self) -> list[dict]:
        cats = self.cfg["scraping"]["categories"]["amazon"]
        max_p = self.cfg["scraping"].get("max_products_per_source", 60)
        all_products = []
        for cat in cats:
            products = self.scrape_category(cat)
            all_products.extend(products)
            if len(all_products) >= max_p:
                break
        return all_products[:max_p]
