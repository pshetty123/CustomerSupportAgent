# AI Customer Feedback Agent — Design

**Date:** 2026-07-02
**Status:** Approved

## Overview

A production-ready, portfolio-quality Streamlit app that ingests a CSV of customer
reviews/feedback, uses the Gemini API to extract structured insights per row
(sentiment, emotion, category, priority, summary, suggested reply), stores results
in SQLite, and presents them via interactive charts with CSV export.

## Tech Stack

- **Frontend:** Streamlit (multi-page: Analyze + Dashboard)
- **AI:** Gemini API via the `google-genai` SDK, model `gemini-2.0-flash`, using
  structured output (`response_schema`) to get validated JSON directly instead of
  parsing free text.
- **Validation:** Pydantic — defines the exact output shape (enums for sentiment,
  emotion, category, priority) and validates Gemini's response before it is stored.
- **Storage:** SQLite via the standard library `sqlite3` module, raw SQL wrapped in
  named functions (no ORM — two tables with one FK doesn't justify the dependency).
- **Charts:** Plotly via `st.plotly_chart`.
- **Config:** `python-dotenv` + `.env` for `GEMINI_API_KEY` (local-only deployment).
- **Retries:** `tenacity` for transient Gemini API failures.

## Project Structure

```
CustomerSupportAgent/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── app.py                    # Streamlit entrypoint — "Analyze" page
├── pages/
│   └── 1_Dashboard.py        # All-time history dashboard
├── src/
│   ├── __init__.py
│   ├── config.py              # env var loading/validation
│   ├── schemas.py             # Pydantic models + enums
│   ├── gemini_client.py       # Gemini API wrapper: prompt + structured output + retries
│   ├── database.py            # SQLite schema + insert/query functions
│   └── csv_processor.py       # CSV loading, column selection, orchestration
└── data/
    └── feedback.db             # gitignored, created on first run
```

Each `src/` module owns exactly one responsibility: `gemini_client.py` only talks to
Gemini, `database.py` only talks to SQLite, `csv_processor.py` orchestrates the two.
`app.py` and `pages/1_Dashboard.py` stay thin — display logic only.

## Data Schema

### Taxonomies (fixed enums in `src/schemas.py`)

- **Sentiment:** Positive, Negative, Neutral
- **Emotion:** Happy, Satisfied, Neutral, Confused, Disappointed, Frustrated, Angry
- **Category:** Bug, Feature Request, Billing, UX/Usability, Customer Support,
  Performance, Other
- **Priority:** Low, Medium, High, Critical
  - Prompt gives explicit criteria: Critical = angry/churn-risk customer or broken
    core functionality; High = strong negative sentiment or blocking issue;
    Medium = negative/neutral with moderate impact; Low = positive or minor feedback.

### `AnalysisResult` (Pydantic model, Gemini's structured output target)

```python
class AnalysisResult(BaseModel):
    sentiment: Sentiment
    emotion: Emotion
    category: Category
    priority: Priority
    summary: str
    suggested_reply: str
```

Using enums + structured output means Gemini cannot return a value outside the
defined taxonomy — eliminates typo/synonym drift that would otherwise pollute charts
and filters, and removes the need for brittle text-parsing of the API response.

### SQLite Schema

```sql
CREATE TABLE batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    row_count INTEGER NOT NULL
);

CREATE TABLE reviews (
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
```

Two tables (not one flat table) so the Dashboard can query batch-level metadata
cheaply and so "download this batch's results" / "which batch did this row come
from" are simple queries. Enum columns are stored as TEXT — SQLite has no native
enum type, and Pydantic already guarantees validity before insert, so a normalized
lookup table would be over-engineering at this scale.

## End-to-End Data Flow (Analyze page)

1. User uploads CSV via `st.file_uploader`; loaded with `pandas`.
2. User picks the review-text column via `st.selectbox` (populated from actual CSV
   columns) — supports any CSV shape, no fixed input format assumed.
3. User clicks "Analyze".
4. `csv_processor.py` loops rows **sequentially** (chosen over concurrency for
   simplicity/debuggability as a first version):
   - Skip empty/whitespace-only rows (no wasted API call), report as skipped.
   - Call `gemini_client.analyze_review(text)` → validated `AnalysisResult`.
   - Retry transient failures via `tenacity` (2 retries, short backoff).
   - On persistent failure, mark row as errored rather than dropping it or crashing
     the batch.
   - Update `st.progress()` per row.
5. Insert one `batches` row + N `reviews` rows in a single DB transaction.
6. Display results table + this-batch-only charts (sentiment pie, priority bar,
   category bar).
7. `st.download_button` exports original text + all AI fields as CSV.

Startup checks `GEMINI_API_KEY` presence in `config.py` and shows `st.error()`
instead of a raw stack trace if missing.

## Dashboard Page (`pages/1_Dashboard.py`)

Separate Streamlit page (auto-registered via `pages/` convention) rather than a tab,
so that expensive Analyze-page reruns (which trigger Gemini calls) are never
conflated with cheap read-only Dashboard reruns (which trigger on every filter
change).

- **KPIs** (`st.metric`): total reviews, total batches, % negative, % critical.
- **Filters** (sidebar): date range, batch selector.
- **Charts** (Plotly, filtered): sentiment distribution, priority breakdown,
  category breakdown, emotion distribution, volume-over-time line chart.
- **Reviews table** below charts, same filters applied, same CSV download option.

Both pages share `src/database.py` query functions — no duplicated SQL.

## Explicitly Out of Scope (this version)

- Automated tests (pytest) — deferred; can be added later without architecture
  changes since `src/` modules are already isolated and mockable.
- Concurrent/batched Gemini calls — sequential-only for v1; the per-row call
  boundary in `gemini_client.py` makes this a future non-breaking change.
- Cloud deployment (Streamlit Cloud / Docker) — local-only via `.env` for now.
