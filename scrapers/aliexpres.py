import requests
from bs4 import BeautifulSoup
def fetch_aliexpress(keyword, api_key):
    search_url = (
        f"https://www.aliexpress.com/wholesale"
        f"?SearchText={keyword.replace(' ','+')}"
        f"&SortType=total_tranpro_desc"
    )
    endpoint = (
        f"http://api.scraperapi.com"
        f"?api_key={api_key}"
        f"&url={requests.utils.quote(search_url, safe='')}"
        f"&render=true"
        f"&country_code=us"
    )
    resp = requests.get(endpoint, timeout=60)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    products = []
    for card in soup.select("[class*='card--']"):
        title = card.select_one("[class*='title--']")
        price = card.select_one("[class*='price--current']") \
             or card.select_one("[class*='price--']")
        orders= card.select_one("[class*='trade--']")
        img   = card.select_one("img")
        link  = card.select_one("a")
        if not title or not price:
            continue
        products.append({
            "source":  "aliexpress",
            "title":   title.get_text(strip=True),
            "price":   price.get_text(strip=True),
            "orders":  orders.get_text(strip=True) if orders else "0",
            "url":     "https:" + link["href"] if link else "",
            "image":   img.get("src", img.get("data-src", "")) if img else "",
        })
    return products
