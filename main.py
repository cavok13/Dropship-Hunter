#!/usr/bin/env python3
"""
Dropship Hunter – Daily automation entrypoint.
Run:  python main.py          →  run once now
      python main.py --daemon →  run on schedule (see config.yaml run_time)
      python main.py --test   →  dry run with mock data
"""
import sys, time, argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load .env overrides first
load_dotenv()

console = Console()
ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def run_once(cfg: dict, dry_run: bool = False):
    from scrapers import AliExpressScraper, AmazonScraper
    from core import ProductScorer, ReportEmailer, ResultsStorage

    t_start = time.time()
    console.rule("[bold cyan]🔍 Dropship Hunter – Daily Scan")

    if dry_run:
        console.print("[yellow]⚠  DRY RUN – using mock data[/yellow]")
        products = _mock_products()
    else:
        # ── Scrape ────────────────────────────────────────────────────────────
        console.print("\n[bold]1/3  Scraping products…[/bold]")
        ali = AliExpressScraper(cfg)
        amz = AmazonScraper(cfg)

        ali_products = ali.scrape_all()
        amz_products = amz.scrape_all()

        ali.close()
        amz.close()

        products = ali_products + amz_products
        console.print(
            f"  Collected [bold]{len(products)}[/bold] raw products "
            f"(AliExpress: {len(ali_products)}, Amazon: {len(amz_products)})"
        )

    # ── Score ─────────────────────────────────────────────────────────────────
    console.print("\n[bold]2/3  Scoring & ranking…[/bold]")
    scorer = ProductScorer(cfg)
    ranked = scorer.score_and_filter(products)
    top10 = ranked[:10]

    # ── Print table ───────────────────────────────────────────────────────────
    tbl = Table(title="🏆 Top 10 Winners", show_lines=True)
    tbl.add_column("#", style="bold cyan", width=3)
    tbl.add_column("Title", min_width=30, max_width=45)
    tbl.add_column("Platform", width=11)
    tbl.add_column("Winner", justify="right", style="bold green")
    tbl.add_column("Demand", justify="right")
    tbl.add_column("Opp", justify="right")
    tbl.add_column("Details")
    for i, p in enumerate(top10, 1):
        tbl.add_row(
            str(i), p["title"][:44], p["platform"],
            str(p["winner_score"]), str(p["demand_score"]),
            str(p["opportunity_score"]), p.get("score_breakdown", "")
        )
    console.print(tbl)

    runtime = time.time() - t_start

    # ── Email ─────────────────────────────────────────────────────────────────
    console.print("\n[bold]3/3  Sending email report…[/bold]")
    try:
        emailer = ReportEmailer(cfg)
        emailer.send(top10, len(products), runtime)
    except Exception as e:
        console.print(f"[red]Email error:[/red] {e}\nCheck config.yaml email settings.")

    # ── Save to DB ────────────────────────────────────────────────────────────
    try:
        db = ResultsStorage()
        db.save_run(top10, len(products), runtime)
        db.close()
    except Exception:
        pass

    console.rule(f"[green]✓ Done in {runtime:.1f}s")
    return top10


def _mock_products() -> list[dict]:
    """Mock data for --test mode – no network needed."""
    import random
    mock = [
        ("Portable LED Ring Light with Phone Holder", "AliExpress", 28.99),
        ("Resistance Bands Set 5-Pack", "Amazon", 19.99),
        ("Wireless Earbud Charging Case", "AliExpress", 14.50),
        ("Stainless Steel Water Bottle 32oz", "Amazon", 24.95),
        ("Jade Facial Roller & Gua Sha Set", "AliExpress", 9.99),
        ("Electric Facial Cleansing Brush", "AliExpress", 22.00),
        ("Car Phone Mount Magnetic", "Amazon", 16.99),
        ("Silicone Cooking Utensils 6-Piece", "Amazon", 29.00),
        ("Posture Corrector Adjustable", "AliExpress", 18.50),
        ("LED Strip Lights 20ft Smart", "Amazon", 27.95),
        ("Foldable Laptop Stand Aluminium", "AliExpress", 32.00),
        ("Vitamin C Serum 30ml", "Amazon", 21.99),
    ]
    products = []
    for title, platform, price in mock:
        products.append({
            "title": title,
            "platform": platform,
            "price": price,
            "rating": round(random.uniform(4.0, 4.9), 1),
            "reviews": random.randint(200, 8000),
            "orders": random.randint(500, 50000) if platform == "AliExpress" else 0,
            "bsr_rank": random.randint(5, 80) if platform == "Amazon" else 999,
            "url": "https://example.com",
            "image": "",
            "category": "test",
            "seller_count": 0,
        })
    return products


def main():
    parser = argparse.ArgumentParser(description="Dropship Hunter")
    parser.add_argument("--daemon", action="store_true", help="Run on daily schedule")
    parser.add_argument("--test", action="store_true", help="Dry run with mock data")
    args = parser.parse_args()

    cfg = load_config()

    if args.daemon:
        import schedule
        run_time = cfg["scheduling"].get("run_time", "08:00")
        console.print(f"[cyan]⏰ Scheduler started – runs daily at {run_time}[/cyan]")
        console.print("   Press Ctrl+C to stop\n")
        schedule.every().day.at(run_time).do(run_once, cfg=cfg)
        # Also run immediately on first launch
        run_once(cfg, dry_run=args.test)
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_once(cfg, dry_run=args.test)


if __name__ == "__main__":
    main()
