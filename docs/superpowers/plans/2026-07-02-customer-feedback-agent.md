# AI Customer Feedback Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit app that analyzes customer feedback CSVs via the Gemini API (sentiment, emotion, category, priority, summary, suggested reply), stores results in SQLite, and displays charts with CSV export.

**Architecture:** Thin Streamlit pages (`app.py`, `pages/1_Dashboard.py`) call into isolated `src/` modules — `config` (env), `schemas` (Pydantic contract), `gemini_client` (AI calls), `database` (SQLite), `csv_processor` (orchestration). Each module has one job and no knowledge of Streamlit.

**Tech Stack:** Python 3.10+, Streamlit, pandas, `google-genai` SDK (gemini-2.0-flash, structured output), Pydantic v2, SQLite (`sqlite3` stdlib), Plotly, `python-dotenv`, `tenacity`.

## Global Constraints

- Python 3.10+ (uses `X | None` and `list[dict]` built-in generic syntax).
- Dependency floors: `streamlit>=1.38`, `pandas>=2.2`, `google-genai>=0.3.0`, `pydantic>=2.7`, `python-dotenv>=1.0`, `tenacity>=8.5`, `plotly>=5.22`.
- **No automated test suite (pytest) in this version** — this was an explicit scope decision in the approved design doc (`docs/superpowers/specs/2026-07-02-customer-feedback-agent-design.md`, "Explicitly Out of Scope"). Every task instead ends with a manual verification step (a runnable command with expected output) rather than a pytest step. Do not add a `tests/` directory or pytest as a dependency.
- Local-only deployment: secrets come from a `.env` file loaded by `python-dotenv`, never from `st.secrets`.
- SQLite file lives at `data/feedback.db`, created automatically on first run via `init_db()`. It must never be committed to git.
- Fixed taxonomies (exact strings, must match across `schemas.py`, `database.py` queries, and any UI code): Sentiment = `Positive`/`Negative`/`Neutral`; Emotion = `Happy`/`Satisfied`/`Neutral`/`Confused`/`Disappointed`/`Frustrated`/`Angry`; Category = `Bug`/`Feature Request`/`Billing`/`UX/Usability`/`Customer Support`/`Performance`/`Other`; Priority = `Low`/`Medium`/`High`/`Critical`.
- Virtual environment name: `.venv` (created with `python3 -m venv .venv`).

---

### Task 1: Project Scaffolding & Dependencies

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `data/.gitkeep`

**Interfaces:**
- Produces: a working Python environment with all dependencies installed, importable `src` package, and a `data/` directory that exists but is empty (git-tracked via `.gitkeep`, actual `.db` file gitignored).

- [ ] **Step 1: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
data/*.db
!data/.gitkeep
.DS_Store
```

- [ ] **Step 2: Create `requirements.txt`**

```
streamlit>=1.38
pandas>=2.2
google-genai>=0.3.0
pydantic>=2.7
python-dotenv>=1.0
tenacity>=8.5
plotly>=5.22
```

- [ ] **Step 3: Create `.env.example`**

```
# Copy this file to .env and fill in your real values.
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.0-flash
DB_PATH=data/feedback.db
```

- [ ] **Step 4: Create empty `src/__init__.py`**

```python
```

- [ ] **Step 5: Create `data/.gitkeep`**

```
```

- [ ] **Step 6: Create venv and install dependencies**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Expected: install completes with no errors, ending in something like `Successfully installed streamlit-... pandas-... google-genai-... pydantic-... python-dotenv-... tenacity-... plotly-...`

- [ ] **Step 7: Verify the package imports cleanly**

Run: `source .venv/bin/activate && python -c "import src; import streamlit, pandas, google.genai, pydantic, dotenv, tenacity, plotly; print('OK')"`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add .gitignore requirements.txt .env.example src/__init__.py data/.gitkeep
git commit -m "chore: scaffold project structure and dependencies"
```

---

### Task 2: Config Module

**Files:**
- Create: `src/config.py`

**Interfaces:**
- Consumes: environment variables `GEMINI_API_KEY`, `GEMINI_MODEL` (optional, defaults to `gemini-2.0-flash`), `DB_PATH` (optional, defaults to `data/feedback.db`), loaded from a `.env` file via `python-dotenv`.
- Produces: `get_config() -> Config`, where `Config` is a frozen dataclass with fields `gemini_api_key: str`, `gemini_model: str`, `db_path: str`. Raises `ValueError` with a user-readable message if `GEMINI_API_KEY` is missing. Used by Task 7 (`app.py`) and Task 8 (`pages/1_Dashboard.py`).

- [ ] **Step 1: Write `src/config.py`**

```python
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    gemini_model: str
    db_path: str


def get_config() -> Config:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Config(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        db_path=os.getenv("DB_PATH", "data/feedback.db"),
    )
```

- [ ] **Step 2: Verify missing-key behavior**

Run: `source .venv/bin/activate && python -c "
import os
os.environ.pop('GEMINI_API_KEY', None)
from src.config import get_config
try:
    get_config()
    print('FAIL: should have raised')
except ValueError as e:
    print('OK:', e)
"`
Expected: `OK: GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.`

- [ ] **Step 3: Verify happy-path behavior**

Run: `source .venv/bin/activate && python -c "
import os
os.environ['GEMINI_API_KEY'] = 'test-key-123'
from src.config import get_config
c = get_config()
assert c.gemini_api_key == 'test-key-123'
assert c.gemini_model == 'gemini-2.0-flash'
assert c.db_path == 'data/feedback.db'
print('OK')
"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/config.py
git commit -m "feat: add config module for env var loading"
```

---

### Task 3: Pydantic Schemas Module

**Files:**
- Create: `src/schemas.py`

**Interfaces:**
- Produces: enums `Sentiment`, `Emotion`, `Category`, `Priority` (all `str, Enum` subclasses using the exact taxonomy strings from Global Constraints), and `AnalysisResult(BaseModel)` with fields `sentiment: Sentiment`, `emotion: Emotion`, `category: Category`, `priority: Priority`, `summary: str`, `suggested_reply: str`. Used by Task 5 (`gemini_client.py`), Task 6 (`csv_processor.py`).

- [ ] **Step 1: Write `src/schemas.py`**

```python
from enum import Enum

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"


class Emotion(str, Enum):
    HAPPY = "Happy"
    SATISFIED = "Satisfied"
    NEUTRAL = "Neutral"
    CONFUSED = "Confused"
    DISAPPOINTED = "Disappointed"
    FRUSTRATED = "Frustrated"
    ANGRY = "Angry"


class Category(str, Enum):
    BUG = "Bug"
    FEATURE_REQUEST = "Feature Request"
    BILLING = "Billing"
    UX_USABILITY = "UX/Usability"
    CUSTOMER_SUPPORT = "Customer Support"
    PERFORMANCE = "Performance"
    OTHER = "Other"


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AnalysisResult(BaseModel):
    sentiment: Sentiment
    emotion: Emotion
    category: Category
    priority: Priority
    summary: str = Field(..., description="1-2 sentence summary of the review")
    suggested_reply: str = Field(..., description="Draft support reply, ready to send or edit")
```

- [ ] **Step 2: Verify schema validates good and bad input**

Run: `source .venv/bin/activate && python -c "
from src.schemas import AnalysisResult
import json

good = json.dumps({
    'sentiment': 'Negative', 'emotion': 'Frustrated', 'category': 'Bug',
    'priority': 'High', 'summary': 'App crashes on login.',
    'suggested_reply': 'Sorry about that, we are looking into it.'
})
result = AnalysisResult.model_validate_json(good)
print('OK:', result.sentiment)

bad = good.replace('Negative', 'Sad')
try:
    AnalysisResult.model_validate_json(bad)
    print('FAIL: should have raised')
except Exception as e:
    print('OK rejected bad enum')
"`
Expected:
```
OK: Sentiment.NEGATIVE
OK rejected bad enum
```

- [ ] **Step 3: Commit**

```bash
git add src/schemas.py
git commit -m "feat: add Pydantic schemas for analysis result and taxonomies"
```

---

### Task 4: Database Module

**Files:**
- Create: `src/database.py`

**Interfaces:**
- Consumes: nothing from other `src/` modules (only stdlib `sqlite3` and `datetime`).
- Produces:
  - `get_connection(db_path: str) -> sqlite3.Connection`
  - `init_db(db_path: str) -> None`
  - `insert_batch(conn, filename: str, row_count: int) -> int` (returns new batch id)
  - `insert_reviews(conn, batch_id: int, reviews: list[dict]) -> None` (each dict has keys `original_text`, `sentiment`, `emotion`, `category`, `priority`, `summary`, `suggested_reply`)
  - `get_batches(conn) -> list[dict]` (each dict is a full `batches` row, newest first)
  - `get_reviews(conn, batch_id: int | None = None) -> list[dict]` (each dict is a full `reviews` row; all reviews if `batch_id` is `None`)
  - `get_kpis(conn) -> dict` with keys `total_reviews`, `total_batches`, `pct_negative`, `pct_critical`
  - Used by Task 7 (`app.py`) and Task 8 (`pages/1_Dashboard.py`).

- [ ] **Step 1: Write `src/database.py`**

```python
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
```

- [ ] **Step 2: Verify end-to-end against a throwaway database file**

Run: `source .venv/bin/activate && python -c "
import os
from src.database import get_connection, init_db, insert_batch, insert_reviews, get_batches, get_reviews, get_kpis

test_db = '/tmp/test_feedback.db'
if os.path.exists(test_db):
    os.remove(test_db)

init_db(test_db)
conn = get_connection(test_db)

batch_id = insert_batch(conn, 'sample.csv', 2)
insert_reviews(conn, batch_id, [
    {'original_text': 'Great app!', 'sentiment': 'Positive', 'emotion': 'Happy', 'category': 'Other', 'priority': 'Low', 'summary': 'User is happy.', 'suggested_reply': 'Thanks!'},
    {'original_text': 'It crashes constantly', 'sentiment': 'Negative', 'emotion': 'Angry', 'category': 'Bug', 'priority': 'Critical', 'summary': 'App crashes.', 'suggested_reply': 'Sorry, investigating now.'},
])

assert len(get_batches(conn)) == 1
assert len(get_reviews(conn)) == 2
assert len(get_reviews(conn, batch_id=batch_id)) == 2
kpis = get_kpis(conn)
assert kpis['total_reviews'] == 2
assert kpis['pct_critical'] == 50.0
conn.close()
os.remove(test_db)
print('OK')
"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/database.py
git commit -m "feat: add SQLite database layer for batches and reviews"
```

---

### Task 5: Gemini Client Module

**Files:**
- Create: `src/gemini_client.py`

**Interfaces:**
- Consumes: `AnalysisResult` from `src/schemas.py` (Task 3).
- Produces: `class GeminiClient` with constructor `GeminiClient(api_key: str, model: str)` and method `analyze_review(self, review_text: str) -> AnalysisResult`. Used by Task 6 (`csv_processor.py`) and Task 7 (`app.py`).

- [ ] **Step 1: Write `src/gemini_client.py`**

```python
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.schemas import AnalysisResult

PROMPT_TEMPLATE = """You are a customer support analyst. Analyze the following customer \
review and extract structured information about it.

Priority guidance:
- Critical: an angry or churn-risk customer, or a broken core feature
- High: strong negative sentiment or a blocking issue
- Medium: negative or neutral feedback with moderate impact
- Low: positive or minor feedback

Also write a short summary and a draft support reply the team could send as-is or lightly edit.

Review:
\"\"\"{review_text}\"\"\"
"""


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def analyze_review(self, review_text: str) -> AnalysisResult:
        response = self._client.models.generate_content(
            model=self._model,
            contents=PROMPT_TEMPLATE.format(review_text=review_text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisResult,
            ),
        )
        return AnalysisResult.model_validate_json(response.text)
```

- [ ] **Step 2: Verify against the real Gemini API**

This step needs your real `GEMINI_API_KEY`, so run it yourself rather than me running it, since I don't have access to your key:

```bash
source .venv/bin/activate
export GEMINI_API_KEY=your-real-key-here
python -c "
from src.gemini_client import GeminiClient
client = GeminiClient(api_key='$GEMINI_API_KEY', model='gemini-2.0-flash')
result = client.analyze_review('The app keeps crashing every time I try to check out. Extremely frustrating.')
print(result)
"
```
Expected: prints an `AnalysisResult` with `sentiment=Sentiment.NEGATIVE`, a `Bug` or similar category, and non-empty `summary`/`suggested_reply` — confirming the schema-constrained call round-trips correctly.

- [ ] **Step 3: Commit**

```bash
git add src/gemini_client.py
git commit -m "feat: add Gemini client with structured output and retries"
```

---

### Task 6: CSV Processor Module

**Files:**
- Create: `src/csv_processor.py`

**Interfaces:**
- Consumes: `GeminiClient.analyze_review(text: str) -> AnalysisResult` (Task 5), `AnalysisResult` (Task 3).
- Produces:
  - `load_csv(file) -> pandas.DataFrame`
  - `get_text_columns(df: pandas.DataFrame) -> list[str]`
  - `process_reviews(df, text_column: str, gemini_client, progress_callback=None) -> tuple[list[dict], int]` — returns `(results, skipped_count)` where each result dict has keys `original_text`, `sentiment`, `emotion`, `category`, `priority`, `summary`, `suggested_reply` (matching `insert_reviews`'s expected shape from Task 4); failed rows get `"ERROR"` in the taxonomy fields instead of raising. `progress_callback`, if given, is called as `progress_callback(current_index_1_based, total)` after every row (including skipped ones).
  - Used by Task 7 (`app.py`).

- [ ] **Step 1: Write `src/csv_processor.py`**

```python
import pandas as pd


def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


def get_text_columns(df: pd.DataFrame) -> list[str]:
    return list(df.columns)


def process_reviews(
    df: pd.DataFrame,
    text_column: str,
    gemini_client,
    progress_callback=None,
) -> tuple[list[dict], int]:
    results = []
    skipped = 0
    total = len(df)

    for i, raw_text in enumerate(df[text_column]):
        text = str(raw_text).strip() if pd.notna(raw_text) else ""

        if not text:
            skipped += 1
            if progress_callback:
                progress_callback(i + 1, total)
            continue

        try:
            analysis = gemini_client.analyze_review(text)
            results.append({
                "original_text": text,
                "sentiment": analysis.sentiment.value,
                "emotion": analysis.emotion.value,
                "category": analysis.category.value,
                "priority": analysis.priority.value,
                "summary": analysis.summary,
                "suggested_reply": analysis.suggested_reply,
            })
        except Exception:
            results.append({
                "original_text": text,
                "sentiment": "ERROR",
                "emotion": "ERROR",
                "category": "ERROR",
                "priority": "ERROR",
                "summary": "Analysis failed after retries.",
                "suggested_reply": "",
            })

        if progress_callback:
            progress_callback(i + 1, total)

    return results, skipped
```

- [ ] **Step 2: Verify with a fake Gemini client (no real API calls)**

Run: `source .venv/bin/activate && python -c "
import io
import pandas as pd
from src.csv_processor import load_csv, get_text_columns, process_reviews
from src.schemas import AnalysisResult, Sentiment, Emotion, Category, Priority

class FakeGeminiClient:
    def analyze_review(self, text):
        if 'boom' in text:
            raise RuntimeError('simulated failure')
        return AnalysisResult(
            sentiment=Sentiment.NEGATIVE, emotion=Emotion.FRUSTRATED,
            category=Category.BUG, priority=Priority.HIGH,
            summary='summary', suggested_reply='reply',
        )

csv_text = 'review_text\nApp crashes on login\n\"  \"\nboom this failed\n'
df = load_csv(io.StringIO(csv_text))
assert get_text_columns(df) == ['review_text']

calls = []
results, skipped = process_reviews(df, 'review_text', FakeGeminiClient(), lambda c, t: calls.append((c, t)))

assert skipped == 1, skipped
assert len(results) == 2, results
assert results[0]['sentiment'] == 'Negative'
assert results[1]['sentiment'] == 'ERROR'
assert calls[-1] == (3, 3)
print('OK')
"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/csv_processor.py
git commit -m "feat: add CSV processing orchestration with per-row error handling"
```

---

### Task 7: Streamlit Analyze Page

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `get_config` (Task 2), `get_connection`/`init_db`/`insert_batch`/`insert_reviews` (Task 4), `GeminiClient` (Task 5), `load_csv`/`get_text_columns`/`process_reviews` (Task 6).
- Produces: the Streamlit entrypoint page. No other module depends on this one.

- [ ] **Step 1: Write `app.py`**

```python
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import get_config
from src.csv_processor import get_text_columns, load_csv, process_reviews
from src.database import get_connection, init_db, insert_batch, insert_reviews
from src.gemini_client import GeminiClient

st.set_page_config(page_title="AI Customer Feedback Agent", page_icon="💬", layout="wide")
st.title("AI Customer Feedback Agent")

try:
    config = get_config()
except ValueError as e:
    st.error(str(e))
    st.stop()

init_db(config.db_path)

uploaded_file = st.file_uploader("Upload a CSV of customer reviews", type=["csv"])

if uploaded_file is not None:
    df = load_csv(uploaded_file)
    st.write("Preview:")
    st.dataframe(df.head())

    text_column = st.selectbox("Which column contains the review text?", get_text_columns(df))

    if st.button("Analyze", type="primary"):
        gemini_client = GeminiClient(config.gemini_api_key, config.gemini_model)
        progress_bar = st.progress(0, text="Analyzing reviews...")

        def update_progress(current: int, total: int) -> None:
            progress_bar.progress(current / total, text=f"Analyzing review {current}/{total}")

        results, skipped = process_reviews(df, text_column, gemini_client, update_progress)
        progress_bar.empty()

        error_count = sum(1 for r in results if r["sentiment"] == "ERROR")
        if error_count:
            st.warning(f"{error_count} of {len(results)} rows failed to analyze after retries.")
        if skipped:
            st.info(f"Skipped {skipped} empty rows.")

        conn = get_connection(config.db_path)
        batch_id = insert_batch(conn, uploaded_file.name, len(results))
        insert_reviews(conn, batch_id, results)
        conn.close()

        st.session_state["last_results"] = results
        st.success(f"Analyzed {len(results)} reviews (batch #{batch_id}).")

if "last_results" in st.session_state:
    results_df = pd.DataFrame(st.session_state["last_results"])
    st.subheader("Results")
    st.dataframe(results_df)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.plotly_chart(px.pie(results_df, names="sentiment", title="Sentiment"), use_container_width=True)
    with col2:
        priority_counts = results_df["priority"].value_counts().reset_index()
        st.plotly_chart(px.bar(priority_counts, x="priority", y="count", title="Priority"), use_container_width=True)
    with col3:
        category_counts = results_df["category"].value_counts().reset_index()
        st.plotly_chart(px.bar(category_counts, x="category", y="count", title="Category"), use_container_width=True)

    csv_bytes = results_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download analyzed CSV", csv_bytes, "analyzed_reviews.csv", "text/csv")
```

- [ ] **Step 2: Create a tiny sample CSV for manual testing**

```bash
mkdir -p samples
cat > samples/sample_reviews.csv << 'EOF'
review_text
The app crashes every time I try to check out. Very frustrating!
Love the new dashboard, so much easier to use now.
Support took 3 days to respond to my billing question.
EOF
```

- [ ] **Step 3: Run the app and manually verify in the browser**

Run: `source .venv/bin/activate && streamlit run app.py`
Expected: browser opens to `http://localhost:8501`. Upload `samples/sample_reviews.csv`, confirm the column picker shows `review_text`, click Analyze, watch the progress bar move, and confirm a results table, three charts, and a working "Download analyzed CSV" button appear. This step requires your real `GEMINI_API_KEY` in `.env` — let me know once you've confirmed it works, or tell me what you see if something looks wrong.

- [ ] **Step 4: Commit**

```bash
git add app.py samples/sample_reviews.csv
git commit -m "feat: add Streamlit Analyze page"
```

---

### Task 8: Streamlit Dashboard Page

**Files:**
- Create: `pages/1_Dashboard.py`

**Interfaces:**
- Consumes: `get_config` (Task 2), `get_connection`/`init_db`/`get_batches`/`get_reviews`/`get_kpis` (Task 4).
- Produces: the Streamlit Dashboard page, auto-registered in the sidebar nav by Streamlit's `pages/` convention. No other module depends on this one.

- [ ] **Step 1: Write `pages/1_Dashboard.py`**

```python
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import get_config
from src.database import get_batches, get_connection, get_kpis, get_reviews, init_db

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("Feedback Dashboard")

try:
    config = get_config()
except ValueError as e:
    st.error(str(e))
    st.stop()

init_db(config.db_path)
conn = get_connection(config.db_path)

kpis = get_kpis(conn)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Reviews", kpis["total_reviews"])
col2.metric("Total Batches", kpis["total_batches"])
col3.metric("% Negative", f"{kpis['pct_negative']}%")
col4.metric("% Critical", f"{kpis['pct_critical']}%")

batches = get_batches(conn)
if not batches:
    conn.close()
    st.info("No reviews analyzed yet. Go to the Analyze page to upload a CSV.")
    st.stop()

batch_options = {"All batches": None}
batch_options.update({f"{b['filename']} ({b['uploaded_at'][:10]})": b["id"] for b in batches})
selected_label = st.sidebar.selectbox("Batch", list(batch_options.keys()))
selected_batch_id = batch_options[selected_label]

reviews = get_reviews(conn, batch_id=selected_batch_id)
conn.close()

reviews_df = pd.DataFrame(reviews)
reviews_df["analyzed_date"] = pd.to_datetime(reviews_df["analyzed_at"]).dt.date

min_date = reviews_df["analyzed_date"].min()
max_date = reviews_df["analyzed_date"].max()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    reviews_df = reviews_df[
        (reviews_df["analyzed_date"] >= start_date) & (reviews_df["analyzed_date"] <= end_date)
    ]

if reviews_df.empty:
    st.info("No reviews in the selected filters.")
    st.stop()

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(px.pie(reviews_df, names="sentiment", title="Sentiment Distribution"), use_container_width=True)
with c2:
    priority_counts = reviews_df["priority"].value_counts().reset_index()
    st.plotly_chart(px.bar(priority_counts, x="priority", y="count", title="Priority Breakdown"), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    category_counts = reviews_df["category"].value_counts().reset_index()
    st.plotly_chart(px.bar(category_counts, x="category", y="count", title="Category Breakdown"), use_container_width=True)
with c4:
    emotion_counts = reviews_df["emotion"].value_counts().reset_index()
    st.plotly_chart(px.bar(emotion_counts, x="emotion", y="count", title="Emotion Distribution"), use_container_width=True)

volume = reviews_df.groupby("analyzed_date").size().reset_index(name="count")
st.plotly_chart(px.line(volume, x="analyzed_date", y="count", title="Review Volume Over Time"), use_container_width=True)

st.subheader("Reviews")
st.dataframe(reviews_df)

csv_bytes = reviews_df.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered CSV", csv_bytes, "dashboard_reviews.csv", "text/csv")
```

- [ ] **Step 2: Run the app and manually verify the dashboard**

Run: `source .venv/bin/activate && streamlit run app.py` (Streamlit auto-discovers `pages/1_Dashboard.py` and adds it to the sidebar)
Expected: after analyzing at least one CSV on the Analyze page (Task 7, Step 3), click "Dashboard" in the sidebar and confirm the KPI row, batch selector, date range picker, five charts, reviews table, and download button all render without errors. Upload a second CSV on the Analyze page and confirm the Dashboard's "All batches" view and totals update to include both.

- [ ] **Step 3: Commit**

```bash
git add pages/1_Dashboard.py
git commit -m "feat: add Streamlit Dashboard page with history and filters"
```

---

### Task 9: README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: nothing (documentation only).
- Produces: the repo's front door for a portfolio reviewer.

- [ ] **Step 1: Write `README.md`**

```markdown
# AI Customer Feedback Agent

A Streamlit app that analyzes customer feedback CSVs using the Gemini API, extracting
sentiment, emotion, category, priority, a summary, and a suggested support reply for
every row. Results are stored in SQLite and browsable via an interactive dashboard.

## Features

- Upload any CSV and pick which column holds the review text
- Per-review AI analysis: sentiment, emotion, category, priority, summary, suggested reply
- Results persisted in SQLite across uploads (full history, not just the current session)
- Dashboard with KPIs, filters (batch, date range), and charts (sentiment, priority,
  category, emotion, volume over time)
- Download analyzed results as CSV from either page

## Architecture

```
app.py                    Streamlit "Analyze" page
pages/1_Dashboard.py      Streamlit "Dashboard" page (all-time history)
src/config.py             Environment variable loading/validation
src/schemas.py            Pydantic models + fixed taxonomies for AI output
src/gemini_client.py      Gemini API wrapper (structured output + retries)
src/database.py           SQLite schema and query functions
src/csv_processor.py      CSV loading and per-row analysis orchestration
```

See `docs/superpowers/specs/2026-07-02-customer-feedback-agent-design.md` for the full
design rationale.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your Gemini API key from https://aistudio.google.com/
streamlit run app.py
```

## Tech Stack

- **Streamlit** — UI framework
- **google-genai** — official Gemini SDK, used with structured output so the model's
  response is constrained to a validated schema
- **Pydantic** — defines and validates the AI output schema
- **SQLite** — lightweight persistent storage, no server required
- **Plotly** — interactive charts
- **tenacity** — retry logic for transient Gemini API failures
- **python-dotenv** — loads the API key from a local `.env` file
```

- [ ] **Step 2: Verify the README renders sensibly**

Run: `source .venv/bin/activate && python -c "print(open('README.md').read()[:200])"`
Expected: prints the opening lines without error (confirms the file was written correctly; visually re-check the full file in your editor for formatting).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions and architecture overview"
```
