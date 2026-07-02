import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    row_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    original_text TEXT NOT NULL,
    sentiment TEXT NOT NULL,
    emotion TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    summary TEXT NOT NULL,
    suggested_reply TEXT NOT NULL,
    analyzed_at TEXT NOT NULL
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_batch(conn: sqlite3.Connection, filename: str, row_count: int) -> int:
    cursor = conn.execute(
        "INSERT INTO batches (filename, uploaded_at, row_count) VALUES (?, ?, ?)",
        (filename, datetime.now(timezone.utc).isoformat(), row_count),
    )
    conn.commit()
    return cursor.lastrowid


def insert_reviews(conn: sqlite3.Connection, batch_id: int, reviews: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        """INSERT INTO reviews
           (batch_id, original_text, sentiment, emotion, category, priority, summary, suggested_reply, analyzed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                batch_id,
                r["original_text"],
                r["sentiment"],
                r["emotion"],
                r["category"],
                r["priority"],
                r["summary"],
                r["suggested_reply"],
                now,
            )
            for r in reviews
        ],
    )
    conn.commit()


def get_batches(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM batches ORDER BY uploaded_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_reviews(conn: sqlite3.Connection, batch_id: int | None = None) -> list[dict]:
    if batch_id is not None:
        rows = conn.execute(
            "SELECT * FROM reviews WHERE batch_id = ? ORDER BY id", (batch_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM reviews ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_kpis(conn: sqlite3.Connection) -> dict:
    total_reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    total_batches = conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
    if total_reviews == 0:
        return {"total_reviews": 0, "total_batches": total_batches, "pct_negative": 0.0, "pct_critical": 0.0}
    negative = conn.execute("SELECT COUNT(*) FROM reviews WHERE sentiment = 'Negative'").fetchone()[0]
    critical = conn.execute("SELECT COUNT(*) FROM reviews WHERE priority = 'Critical'").fetchone()[0]
    return {
        "total_reviews": total_reviews,
        "total_batches": total_batches,
        "pct_negative": round(negative / total_reviews * 100, 1),
        "pct_critical": round(critical / total_reviews * 100, 1),
    }
