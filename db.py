import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DB_PATH = Path(__file__).parent / "data" / "tracker.db"


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS ad_periods (
            id          INTEGER PRIMARY KEY,
            advertiser  TEXT    NOT NULL,
            platform    TEXT    NOT NULL CHECK(platform IN ('tv','youtube','meta')),
            year        INTEGER NOT NULL,
            month       INTEGER NOT NULL,
            start_day   INTEGER NOT NULL,
            end_day     INTEGER NOT NULL,
            crawled_at  TEXT    NOT NULL,
            UNIQUE(advertiser, platform, year, month, start_day, end_day)
        );
        CREATE TABLE IF NOT EXISTS crawl_coverage (
            advertiser  TEXT    NOT NULL,
            platform    TEXT    NOT NULL,
            year        INTEGER NOT NULL,
            month       INTEGER NOT NULL,
            crawled_at  TEXT    NOT NULL,
            PRIMARY KEY (advertiser, platform, year, month)
        );
        CREATE TABLE IF NOT EXISTS crawl_log (
            id         INTEGER PRIMARY KEY,
            platform   TEXT,
            crawled_at TEXT,
            status     TEXT,
            count      INTEGER DEFAULT 0,
            message    TEXT
        );
        """)


def mark_crawled(advertiser: str, platform: str, year: int, month: int,
                 crawled_at: str = None):
    """Record that this advertiser/platform/month was crawled (even if no ads found)."""
    ts = crawled_at or datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO crawl_coverage
               (advertiser, platform, year, month, crawled_at) VALUES (?,?,?,?,?)""",
            (advertiser, platform, year, month, ts)
        )


def upsert_periods(advertiser: str, platform: str, year: int, month: int,
                   periods: list[dict], crawled_at: str = None):
    """Insert or ignore periods. periods = [{"s": int, "e": int}, ...]"""
    if not periods:
        return
    ts = crawled_at or datetime.now().isoformat()
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO ad_periods
               (advertiser, platform, year, month, start_day, end_day, crawled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(advertiser, platform, year, month, p["s"], p["e"], ts) for p in periods]
        )


def log_crawl(platform: str, status: str, count: int = 0, message: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO crawl_log (platform, crawled_at, status, count, message) VALUES (?,?,?,?,?)",
            (platform, datetime.now().isoformat(), status, count, message)
        )


def get_periods() -> dict:
    """Return periods dict for JS injection.
    Format: { advertiser: { "year_month": { tv:[{s,e}], yt:[...], meta:[...] } } }
    """
    init_db()
    rows = []
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT advertiser, platform, year, month, start_day, end_day FROM ad_periods"
            ).fetchall()
    except Exception:
        return {}

    out = defaultdict(lambda: defaultdict(lambda: {"tv": [], "youtube": [], "meta": []}))
    for r in rows:
        key = f"{r['year']}_{r['month']}"
        out[r["advertiser"]][key][r["platform"]].append({"s": r["start_day"], "e": r["end_day"]})

    # Rename 'youtube' → 'yt' for JS compatibility
    result = {}
    for adv, months in out.items():
        result[adv] = {}
        for mk, channels in months.items():
            result[adv][mk] = {
                "tv": channels["tv"],
                "yt": channels["youtube"],
                "meta": channels["meta"],
            }
    return result


def get_coverage() -> dict:
    """Return coverage dict for JS injection.
    Format: { advertiser: { "year_month": { tv:True, youtube:True, meta:False } } }
    """
    init_db()
    try:
        rows = get_conn().execute(
            "SELECT advertiser, platform, year, month FROM crawl_coverage"
        ).fetchall()
    except Exception:
        return {}

    out: dict = {}
    for r in rows:
        adv = r["advertiser"]
        key = f"{r['year']}_{r['month']}"
        out.setdefault(adv, {}).setdefault(key, {})[r["platform"]] = True
    return out


def get_last_crawl() -> str:
    init_db()
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT crawled_at FROM crawl_log WHERE status='ok' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            dt = datetime.fromisoformat(row["crawled_at"])
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return ""
