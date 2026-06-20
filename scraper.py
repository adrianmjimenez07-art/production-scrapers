"""Resilient base scraper: retries, backoff, rate-limiting, idempotent upserts.

Subclass `Scraper` and implement `parse(page)` to return a list of dict rows.
The base class handles the parts that actually break in production.
"""
import argparse
import random
import sqlite3
import time

UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
]


class Scraper:
    def __init__(self, db_path="data.db", table="rows", key="id", min_interval=1.5):
        self.con = sqlite3.connect(db_path)
        self.table = table
        self.key = key
        self.min_interval = min_interval   # polite per-request floor (seconds)
        self._last = 0.0

    def _throttle(self):
        wait = self.min_interval - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait + random.uniform(0, 0.4))  # jitter avoids lockstep
        self._last = time.time()

    def fetch(self, url, attempts=4):
        """Fetch with exponential backoff. Replace with Playwright for JS sites."""
        import requests
        for i in range(attempts):
            self._throttle()
            try:
                r = requests.get(url, headers={"User-Agent": random.choice(UAS)}, timeout=20)
                if r.status_code == 200:
                    return r.text
                if r.status_code in (429, 503):       # rate-limited / unavailable
                    time.sleep(2 ** i)                 # 1, 2, 4, 8s
                    continue
            except requests.RequestException:
                time.sleep(2 ** i)
        return None

    def parse(self, html):
        raise NotImplementedError("implement parse() in your subclass")

    def upsert(self, rows):
        """Idempotent write: re-running never duplicates a row."""
        if not rows:
            return 0
        cols = list(rows[0].keys())
        self.con.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table} "
            f"({', '.join(c + ' TEXT' for c in cols)}, "
            f"PRIMARY KEY ({self.key}))"
        )
        ph = ", ".join("?" for _ in cols)
        self.con.executemany(
            f"INSERT OR REPLACE INTO {self.table} ({', '.join(cols)}) VALUES ({ph})",
            [[str(r.get(c, "")) for c in cols] for r in rows],
        )
        self.con.commit()
        return len(rows)

    def run(self, url):
        html = self.fetch(url)
        if not html:
            print("fetch failed after retries")
            return
        n = self.upsert(self.parse(html))
        print(f"upserted {n} rows into {self.table}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="data.db")
    args = ap.parse_args()
    print("Subclass Scraper and implement parse(); this is the resilient base.")
