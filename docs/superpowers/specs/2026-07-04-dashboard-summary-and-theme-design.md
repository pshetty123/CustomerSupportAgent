# Dashboard Executive Summary & Theme Pass — Design

**Date:** 2026-07-04
**Status:** Approved

## Overview

Two additions to the AI Customer Feedback Agent, scoped together as one round of near-term work:

1. **Executive Summary** — a Gemini-generated narrative summary and product next-steps,
   added to the Dashboard page, built from the currently-filtered review data.
2. **Theme pass** — a Streamlit theme and a shared chart color map, retinting the app
   from Streamlit's defaults to the teal/brick-amber palette used in the
   "AI Customer Feedback Agent — Product Review & Roadmap" executive report shared
   with the user on 2026-07-04, so the app and executive materials share one visual
   language.

This builds on the existing, already-shipped app (`app.py`, `pages/1_Dashboard.py`,
`src/config.py`, `src/schemas.py`, `src/gemini_client.py`, `src/database.py`,
`src/csv_processor.py`) — see
`docs/superpowers/specs/2026-07-02-customer-feedback-agent-design.md` for that design.

## New Files & Responsibilities

```
.streamlit/config.toml       # NEW — Streamlit native theme (colors, font)
src/chart_colors.py          # NEW — shared taxonomy -> color map for Plotly charts
src/schemas.py                # MODIFIED — add ExecutiveSummary model
src/gemini_client.py          # MODIFIED — add generate_executive_summary() method
pages/1_Dashboard.py          # MODIFIED — add Executive Summary section
app.py                        # MODIFIED — apply TAXONOMY_COLORS to its charts
```

`chart_colors.py` is a separate module (not inlined per-page) because both `app.py`
and `pages/1_Dashboard.py` chart the same taxonomy values and must render identical
colors for identical values (e.g. "Critical" is brick-red everywhere) — a shared
constant is the only way to guarantee that without the two files' color choices
silently drifting apart.

`generate_executive_summary` is added to the existing `GeminiClient` class rather
than a new class: it is still "make a structured-output call to Gemini with this
api key/model," just a different prompt and schema than `analyze_review`. Same
responsibility, same retry needs.

## Executive Summary

### Schema (`src/schemas.py`)

```python
class ExecutiveSummary(BaseModel):
    summary: str            # 2-4 sentence narrative of what the data shows
    next_steps: list[str]   # 3-5 concrete suggestions for the product team
```

Structured output, for the same reason as `AnalysisResult`: Gemini cannot return a
malformed shape, so the UI never defensively parses free text.

### What gets sent to Gemini

Not raw `original_text` — a compact digest built from data that has *already been
analyzed*, for whichever reviews are currently filtered on the Dashboard (respecting
the existing batch and date-range filters):

- Aggregate counts by sentiment, emotion, category, and priority (the same numbers
  the KPI strip and charts already compute from `reviews_df`)
- Each filtered review's `summary` field (not `original_text`), paired with its
  `category` and `priority`

Using the AI-written `summary` field instead of the original review text keeps the
prompt small and cost roughly constant regardless of how long individual reviews
were. This first version sends every row in the filtered set with no sampling or
truncation — acceptable at pilot scale; revisit only if a filtered view grows into
the thousands of rows.

### `GeminiClient.generate_executive_summary` (`src/gemini_client.py`)

```python
def generate_executive_summary(self, digest_text: str) -> ExecutiveSummary:
    ...
```

Same `@retry` policy as `analyze_review` (3 attempts, exponential backoff,
`reraise=True`), same `response_mime_type="application/json"` +
`response_schema=ExecutiveSummary` structured-output pattern, different prompt
template instructing Gemini to write a short narrative summary of the patterns in
the digest and 3-5 concrete, specific next steps for a product team (not generic
advice — grounded in the actual categories/priorities present).

### Dashboard UI flow (`pages/1_Dashboard.py`)

1. New section titled "Executive Summary," placed immediately after the KPI strip
   and before the existing charts — summary first, detail after.
2. A "Generate Executive Summary" button. On click: build the digest from the
   currently-filtered `reviews_df`, call `gemini_client.generate_executive_summary(...)`,
   store the result in `st.session_state["exec_summary"]`.
3. Once present in session state, render `summary` as a paragraph and `next_steps`
   as a bulleted list.
4. Wrapped in try/except, consistent with every other Gemini call site in the app —
   failure shows `st.error(...)` and does not crash the page.
5. Session-only persistence, matching the Analyze page's existing `last_results`
   pattern in `st.session_state` — no new SQLite table, no migration.

Because this section sits after the Dashboard's existing
`if reviews_df.empty: st.stop()` guard, there is no empty-data case to handle
separately here — the button can only render when there is already data to
summarize.

### Regeneration trigger

On-demand only (button click), not automatic on every Dashboard rerun. The
Dashboard already reruns on every filter change (batch selector, date range); an
automatic Gemini call on every such rerun would fire an API call for every filter
tweak. A generated summary is not invalidated automatically when filters change
afterward — clicking the button again regenerates it for whatever is currently
filtered.

## Theme Pass

### `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#0E6E63"
backgroundColor = "#F1F3F1"
secondaryBackgroundColor = "#E6EAE7"
textColor = "#1A2220"
font = "sans serif"
```

Retints Streamlit's native widgets (buttons, active sidebar item, selectbox focus,
progress bar) to the teal accent and warm-neutral paper background from the roadmap
report, replacing Streamlit's default white/red. Single static light theme — a
light/dark toggle is out of scope for this round (not selected during scoping).

### `src/chart_colors.py`

```python
TAXONOMY_COLORS = {
    "Positive": "#1F7A5C", "Negative": "#B5472A", "Neutral": "#5C6866",
    "Critical": "#B5472A", "High": "#A9780A", "Medium": "#5C6866", "Low": "#1F7A5C",
    "Bug": "#B5472A", "Feature Request": "#0E6E63", "Billing": "#A9780A",
    "UX/Usability": "#0E6E63", "Customer Support": "#A9780A",
    "Performance": "#5C6866", "Other": "#5C6866",
    "Happy": "#1F7A5C", "Satisfied": "#1F7A5C", "Confused": "#A9780A",
    "Disappointed": "#A9780A", "Frustrated": "#B5472A", "Angry": "#B5472A",
}
```

Every `px.pie`/`px.bar` call in both `app.py` and `pages/1_Dashboard.py` passes
`color_discrete_map=TAXONOMY_COLORS`, keyed on whichever column it charts
(sentiment/priority/category/emotion all share one map, since their value sets don't
overlap). This makes Critical/Negative/Bug consistently read as the same brick-red
everywhere in the app, matching the roadmap report's severity-chip colors, rather
than leaving charts on Plotly's default blue palette while only the buttons are
retinted.

## Error Handling

- `generate_executive_summary` failures (network error, API error, exhausted
  retries) are caught at the call site in `pages/1_Dashboard.py` and shown via
  `st.error(...)`, identical in shape to the existing malformed-CSV handling in
  `app.py`. The page does not crash; the user can click the button again.
- No new failure modes are introduced elsewhere — `chart_colors.py` is a pure
  constant with no runtime behavior, and `.streamlit/config.toml` is static
  configuration Streamlit reads at startup.

## Explicitly Out of Scope (this round)

Deferred from the broader roadmap report, not part of this spec:
- Severity/sentiment chips replacing the raw results table
- Progressive (streaming) results on the Analyze page
- Critical-priority alerting (Slack/email)
- Basic auth
- Light/dark theme toggle (this round ships one static light theme only)
- Persisting executive summaries to SQLite (session-only for now)
