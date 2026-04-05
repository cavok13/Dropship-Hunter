"""AliExpress Top-Selling products scraper."""
import re, json
from bs4 import BeautifulSoup
from rich.console import Console
from .base import BaseScraper

console = Console()
BASE = "https://www.aliexpress.com"


class AliExpressScraper(BaseScraper):
    """Scrapes AliExpress category bestseller pages."""

    def scrape_category(self, cat_id: str) -> list[dict]:
        url = (
            f"{BASE}/category/{cat_id}/all.html"
            f"?SortType=total_transy_desc&page=1"
        )
        console.print(f"  [magenta]→ AliExpress:[/magenta] cat={cat_id}")
        try:
            resp = self.get(url)
        except Exception as e:
            console.print(f"  [red]✗ Failed:[/red] {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        products = []

        # Try JSON embedded data first (AliExpress embeds runParams)
        products = self._try_parse_json(resp.text)
        if not products:
            products = self._parse_html(soup, cat_id)

        console.print(f"    [green]✓ {len(products)} products[/green]")
        return products

    def _try_parse_json(self, html: str) -> list[dict]:
        """Extract product data from embedded JSON (window.runParams)."""
        m = re.search(r"window\.runParams\s*=\s*(\{.*?\});", html, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(1))
            items = (
                data.get("data", {})
                    .get("root", {})
                    .get("fields", {})
                    .get("mods", {})
                    .get("itemList", {})
                    .get("content", [])
            )
            products = []
            for item in items:
                title = item.get("title", {}).get("displayTitle", "")
                if not title:
                    continue
                price_info = item.get("prices", {}).get("salePrice", {})
                price = price_info.get("minPrice", 0)
                rating = float(item.get("evaluation", {}).get("starRating", 0) or 0)
                reviews = int(item.get("evaluation", {}).get("totalValidNum", 0) or 0)
                orders = self._parse_orders(
                    item.get("trade", {}).get("tradeDesc", "0")
                )
                prod_id = item.get("productId", "")
                url = f"https://www.aliexpress.com/item/{prod_id}.html"
                image = item.get("image", {}).get("imgUrl", "")
                if image and not image.startswith("http"):
                    image = "https:" + image
                products.append({
                    "title": title[:120],
                    "url": url,
                    "image": image,
                    "price": float(price or 0),
                    "rating": rating,
                    "reviews": reviews,
                    "orders": orders,
                    "bsr_rank": 999,
                    "platform": "AliExpress",
                    "category": prod_id,
                    "seller_count": 0,
                })
            return products
        except Exception:
            return []

    def _parse_html(self, soup: BeautifulSoup, cat_id: str) -> list[dict]:
        products = []
        for item in soup.select("a.manhattan--container--1lP57Ag, div.JiIWFCFz"):
            try:
                prod = self._parse_html_item(item)
                if prod:
                    products.append(prod)
            except Exception:
                continue
        return products

    def _parse_html_item(self, item) -> dict | None:
        title_el = item.select_one(
            "h3.manhattan--titleText--WccSjUS, "
            "div._1AtVbE, span.manhattan--titleText"
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        href = item.get("href", "")
        url = href if href.startswith("http") else BASE + href

        img_el = item.select_one("img")
        image = img_el.get("src") or img_el.get("data-src", "") if img_el else ""

        price_el = item.select_one(".manhattan--price-sale--1CCSe9Y, .price-sale")
        price = 0.0
        if price_el:
            m = re.search(r"[\d.]+", price_el.get_text())
            if m:
                price = float(m.group())

        rating_el = item.select_one(".overview-rating-average, .manhattan--evaluation-average")
        rating = float(rating_el.get_text(strip=True)) if rating_el else 0.0

        orders_el = item.select_one(".manhattan--trade--2PeJIEB, .trade")
        orders = self._parse_orders(orders_el.get_text() if orders_el else "0")

        return {
            "title": title[:120],
            "url": url,
            "image": image,
            "price": price,
            "rating": rating,
            "reviews": 0,
            "orders": orders,
            "bsr_rank": 999,
            "platform": "AliExpress",
            "category": str(cat_id),
            "seller_count": 0,
        }

    @staticmethod
    def _parse_orders(text: str) -> int:
        text = text.strip().lower().replace(",", "")
        m = re.search(r"([\d.]+)\s*([km]?)", text)
        if not m:
            return 0
        val = float(m.group(1))
        suffix = m.group(2)
        if suffix == "k":
            val *= 1_000
        elif suffix == "m":
            val *= 1_000_000
        return int(val)

    def scrape_all(self) -> list[dict]:
        cats = self.cfg["scraping"]["categories"]["aliexpress"]
        max_p = self.cfg["scraping"].get("max_products_per_source", 60)
        all_products = []
        for cat in cats:
            products = self.scrape_category(str(cat))
            all_products.extend(products)
            if len(all_products) >= max_p:
                break
        return all_products[:max_p]
