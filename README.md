# 🏆 Dropship Hunter

**Daily automated scraper** that finds trending products on AliExpress & Amazon,
scores them by demand + opportunity, and emails you the Top 10 winners every morning.

---

## Quick Start

### 1 · Install dependencies
```bash
pip install -r requirements.txt
```

### 2 · Configure
Edit **`config.yaml`**:
- Set your Gmail address and [App Password](https://support.google.com/accounts/answer/185833)
- Set `recipient` to where you want the report
- Adjust `categories` and `scoring` thresholds

### 3 · Test it (no network, mock data)
```bash
python main.py --test
```

### 4 · Run once (live)
```bash
python main.py
```

### 5 · Run on daily schedule (keeps running)
```bash
python main.py --daemon
```

### 6 · Install as cron job (Linux/Mac – runs at 08:00)
```bash
python scheduler.py install
```

---

## How Scoring Works

| Score | Formula | What it means |
|---|---|---|
| **Demand Score** (0–100) | Reviews + Rating + Orders + BSR rank | How popular the product already is |
| **Opportunity Score** (0–100) | Review/order gap + price margins + BSR position | How much room there is for a new seller |
| **Winner Score** | Demand×0.60 + Opportunity×0.40 | Overall dropship worthiness |

### Demand Signals
- **Review count** (log scale, max at 5,000+) — `30 pts`
- **Rating quality** (4.0–5.0 mapped linearly) — `25 pts`
- **Order volume** (AliExpress, log scale, max at 100k+) — `25 pts`
- **BSR rank** (Amazon Best Sellers, top-100 range) — `20 pts`

### Opportunity Signals
- High orders + low reviews → undiscovered niche
- Price in $15–$60 → good margin room
- BSR 10–50 → demand proven but not dominated

---

## Avoiding Blocks

For best results with live scraping:

1. **Use ScraperAPI** (free tier: 1,000 req/month):
   ```yaml
   # config.yaml
   scraping:
     use_scraper_api: true
     scraper_api_key: "YOUR_KEY"
   ```
   Sign up free at [scraperapi.com](https://www.scraperapi.com)

2. **Increase delay**: Set `request_delay: 5` in config.yaml

3. **Reduce categories**: Comment out categories you don't need

---

## File Structure
```
dropship-hunter/
├── main.py              ← Entry point
├── scheduler.py         ← Cron/service installer
├── config.yaml          ← Your settings
├── requirements.txt
├── scrapers/
│   ├── base.py          ← HTTP client with retries
│   ├── aliexpress.py    ← AliExpress scraper
│   └── amazon.py        ← Amazon Best Sellers scraper
├── core/
│   ├── scorer.py        ← Scoring algorithm
│   ├── emailer.py       ← HTML email report
│   └── storage.py       ← SQLite history
└── data/
    └── results.db       ← Auto-created run history
```

---

## Gmail App Password Setup

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Search "App Passwords" → Generate one for "Mail"
4. Paste the 16-character password in `config.yaml` → `app_password`

---

## Windows Task Scheduler

Instead of cron, use Task Scheduler:
1. Open **Task Scheduler** → Create Basic Task
2. Trigger: Daily at 08:00
3. Action: Start program → `python.exe`
4. Arguments: `C:\path\to\dropship-hunter\main.py`
