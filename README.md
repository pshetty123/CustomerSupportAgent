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
