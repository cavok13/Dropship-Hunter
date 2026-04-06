import requests
from bs4 import BeautifulSoup
def fetch_amazon_bestsellers(category_url, api_key):
    endpoint = (
        f"http://api.scraperapi.com"
        f"?api_key={api_key}"
        f"&url={requests.utils.quote(category_url, safe='')}"
        f"&autoparse=true"
    )
    resp = requests.get(endpoint, timeout=60)
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
        results = data.get("results", [])
    except Exception:
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select(".zg-grid-general-faceout"):
            title = item.select_one(".p13n-sc-truncated")
            price = item.select_one(".p13n-sc-price")
            rating= item.select_one(".a-icon-alt")
            img   = item.select_one("img")
            link  = item.select_one("a")
            if not title:
                continue
            results.append({
                "source": "amazon",
                "title":  title.get_text(strip=True),
                "price":  price.get_text(strip=True) if price else "0",
                "rating": rating.get_text(strip=True)[:3] if rating else "0",
                "bsr":    "top_100",
                "url":    "https://amazon.com" + link["href"] if link else "",
                "image":  img.get("src", "") if img else "",
            })
    return results
