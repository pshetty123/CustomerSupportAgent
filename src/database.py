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

CREATE TABLE IF NOT EXISTS strategy_pillars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batches(id),
    pillar_id INTEGER REFERENCES strategy_pillars(id),
    theme TEXT NOT NULL,
    evidence_count INTEGER NOT NULL,
    rationale TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    created_at TEXT NOT NULL,
    reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS usage_log (
    day TEXT PRIMARY KEY,
    call_count INTEGER NOT NULL DEFAULT 0
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
    total_reviews = conn.execute("SELECT COUNT(*) FROM reviews WHERE sentiment != 'ERROR'").fetchone()[0]
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


def insert_pillar(conn: sqlite3.Connection, name: str, description: str) -> int:
    cursor = conn.execute(
        "INSERT INTO strategy_pillars (name, description, created_at) VALUES (?, ?, ?)",
        (name, description, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_pillars(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM strategy_pillars ORDER BY created_at").fetchall()
    return [dict(row) for row in rows]


def delete_pillar(conn: sqlite3.Connection, pillar_id: int) -> None:
    conn.execute("DELETE FROM strategy_pillars WHERE id = ?", (pillar_id,))
    conn.commit()


DEMO_PILLARS = [
    (
        "Reliability & Performance",
        "Keep core product flows fast, stable, and error-free.",
    ),
    (
        "Billing & Pricing Transparency",
        "Make charges, fees, and plan changes clear and predictable for customers.",
    ),
    (
        "Support Responsiveness",
        "Resolve customer issues quickly and consistently across channels.",
    ),
]


def ensure_demo_pillars(conn: sqlite3.Connection) -> None:
    if get_pillars(conn):
        return
    for name, description in DEMO_PILLARS:
        insert_pillar(conn, name, description)


def insert_opportunities(conn: sqlite3.Connection, batch_id: int, proposals: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        """INSERT INTO opportunities
           (batch_id, pillar_id, theme, evidence_count, rationale, title, description, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'proposed', ?)""",
        [
            (
                batch_id,
                p["pillar_id"],
                p["theme"],
                p["evidence_count"],
                p["rationale"],
                p["title"],
                p["description"],
                now,
            )
            for p in proposals
        ],
    )
    conn.commit()


def get_opportunities(conn: sqlite3.Connection, status: str | None = None) -> list[dict]:
    if status is not None:
        rows = conn.execute(
            "SELECT * FROM opportunities WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM opportunities ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def update_opportunity(
    conn: sqlite3.Connection,
    opportunity_id: int,
    *,
    title: str,
    description: str,
    pillar_id: int | None,
    status: str,
) -> None:
    conn.execute(
        """UPDATE opportunities
           SET title = ?, description = ?, pillar_id = ?, status = ?, reviewed_at = ?
           WHERE id = ?""",
        (title, description, pillar_id, status, datetime.now(timezone.utc).isoformat(), opportunity_id),
    )
    conn.commit()


def get_today_usage(conn: sqlite3.Connection) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute("SELECT call_count FROM usage_log WHERE day = ?", (today,)).fetchone()
    return row["call_count"] if row else 0


def record_usage(conn: sqlite3.Connection, count: int) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn.execute(
        """INSERT INTO usage_log (day, call_count) VALUES (?, ?)
           ON CONFLICT(day) DO UPDATE SET call_count = call_count + excluded.call_count""",
        (today, count),
    )
    conn.commit()
