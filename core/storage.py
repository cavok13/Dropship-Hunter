"""SQLite storage – keeps a history of daily runs and winner products."""
import sqlite3, json
from pathlib import Path
from datetime import date


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "results.db"


class ResultsStorage:
    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT,
                total_scanned INTEGER,
                runtime_s REAL,
                top10_json TEXT
            )
        """)
        self.conn.commit()

    def save_run(self, products: list[dict], total_scanned: int, runtime: float):
        self.conn.execute(
            "INSERT INTO runs (run_date, total_scanned, runtime_s, top10_json) "
            "VALUES (?, ?, ?, ?)",
            (str(date.today()), total_scanned, runtime, json.dumps(products[:10]))
        )
        self.conn.commit()

    def get_history(self, limit: int = 30) -> list[dict]:
        cur = self.conn.execute(
            "SELECT run_date, total_scanned, runtime_s, top10_json "
            "FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = []
        for row in cur.fetchall():
            rows.append({
                "date": row[0],
                "total_scanned": row[1],
                "runtime_s": row[2],
                "products": json.loads(row[3]),
            })
        return rows

    def close(self):
        self.conn.close()
