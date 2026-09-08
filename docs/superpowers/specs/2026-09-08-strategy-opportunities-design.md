# Strategy → Opportunities Workflow — Design

**Date:** 2026-09-08
**Status:** Approved

## Overview

A new PM-facing workflow: AI compares analyzed customer feedback against the
product's stated strategy, proposes candidate "opportunities," a PM reviews
each proposal (approve as-is, edit then approve, or reject), and approved
opportunities become durable records in the app.

```
AI compares against strategy → PM reviews → Approved opportunity created
```

This builds on the existing, already-shipped app (`app.py`,
`pages/1_Dashboard.py`, `src/config.py`, `src/schemas.py`,
`src/gemini_client.py`, `src/database.py`, `src/csv_processor.py`) — see
`docs/superpowers/specs/2026-07-02-customer-feedback-agent-design.md` and
`docs/superpowers/specs/2026-07-04-dashboard-summary-and-theme-design.md`
for prior work.

## New Files & Responsibilities

```
pages/2_Strategy.py       # NEW — manage strategy pillars (add/list/delete)
pages/3_Opportunities.py  # NEW — trigger AI comparison, PM review queue, approved list
src/schemas.py             # MODIFIED — add OpportunityProposal, OpportunityProposals
src/gemini_client.py       # MODIFIED — add generate_opportunities()
src/database.py            # MODIFIED — add strategy_pillars, opportunities tables + CRUD
```

No changes to `app.py` or `pages/1_Dashboard.py` — this is an additive
workflow, not a modification of the existing analyze/dashboard flow.

## Data Model (`src/database.py`)

```sql
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
```

- `pillar_id` is nullable: a real feedback theme may not map to any current
  strategic pillar. That mismatch is itself useful signal for a PM ("we're
  getting a lot of X and it isn't on our roadmap") and must be representable,
  not forced into a false match.
- `status` is one of `proposed` / `approved` / `rejected`. Rejected rows are
  kept, not deleted, for audit — rejecting is a PM decision worth remembering,
  not an undo.
- `theme`, `evidence_count`, and `rationale` are the AI's supporting evidence
  for the proposal; `title` and `description` are the PM-facing, editable
  opportunity text. Keeping these separate means an edited `title`/`description`
  never destroys the reasoning that produced it.
- No separate table for individual review-to-theme linkage. `evidence_count`
  (a plain integer from the AI's own clustering) is sufficient signal for a
  PM deciding whether to act — not selected for this round.

### CRUD additions to `src/database.py`

```python
def insert_pillar(conn, name: str, description: str) -> int: ...
def get_pillars(conn) -> list[dict]: ...
def delete_pillar(conn, pillar_id: int) -> None: ...

def insert_opportunities(conn, batch_id: int, proposals: list[dict]) -> None: ...
def get_opportunities(conn, status: str | None = None) -> list[dict]: ...
def update_opportunity(conn, opportunity_id: int, *, title: str, description: str,
                        pillar_id: int | None, status: str) -> None: ...
```

Same shape as the existing `insert_batch`/`insert_reviews`/`get_batches`
functions — plain sqlite3, no ORM, consistent with the rest of the module.

## AI Layer

### Schema (`src/schemas.py`)

```python
class OpportunityProposal(BaseModel):
    theme: str = Field(..., description="The recurring feedback pattern observed")
    evidence_count: int = Field(..., description="Number of reviews supporting this theme")
    matched_pillar: str | None = Field(..., description="Name of the strategy pillar this relates to, or null if none")
    rationale: str = Field(..., description="Why this theme is or isn't aligned with strategy")
    title: str = Field(..., description="Proposed opportunity title")
    description: str = Field(..., description="1-3 sentence proposed opportunity description")


class OpportunityProposals(BaseModel):
    proposals: list[OpportunityProposal]
```

Structured output, same rationale as `AnalysisResult` and `ExecutiveSummary`:
Gemini cannot return a malformed shape, so the UI never defensively parses
free text.

### `GeminiClient.generate_opportunities` (`src/gemini_client.py`)

```python
def generate_opportunities(self, digest_text: str, pillars: list[dict]) -> OpportunityProposals:
    ...
```

- Same `@retry` policy as `analyze_review`/`generate_executive_summary` (3
  attempts, exponential backoff, `reraise=True`), same
  `response_mime_type="application/json"` + `response_schema=OpportunityProposals`
  structured-output pattern.
- `digest_text` is built the same way as the Executive Summary's digest: each
  review's `summary` field (not `original_text`), paired with `category` and
  `priority` — not raw review text. This keeps the prompt bounded regardless
  of original review length and reuses a pattern already proven in this
  codebase.
- `pillars` (name + description for each `strategy_pillars` row) is
  interpolated into the prompt so the model has a concrete strategy to
  compare against. If no pillars exist yet, the prompt still runs — every
  proposal will simply come back with `matched_pillar=null`, which is a
  correct and informative result ("no proposed opportunity aligns with
  strategy" is meaningful before any strategy is entered too, but the UI
  should nudge the PM to add pillars first — see UI flow below).
- One call per "Find opportunities" click, over the reviews in one selected
  batch. The model is prompted to first cluster the batch's feedback into
  recurring themes, then evaluate each theme against the supplied pillars.

### Resolving `matched_pillar` to `pillar_id`

After the call returns, each proposal's `matched_pillar` (a name string, or
`None`) is resolved against `strategy_pillars` by exact name match. No match
(including `None`) stores `pillar_id = NULL`. This is a simple in-app lookup,
not part of the Gemini call — keeps the structured-output schema free of
database IDs the model has no reason to know.

## UI Flow

### `pages/2_Strategy.py`

1. Form: `name` + `description` text inputs, "Add Pillar" button → inserts a
   row via `insert_pillar`.
2. List of existing pillars below (name, description, "Delete" button per
   row) via `get_pillars`.
3. No in-place editing — deleting and re-adding covers corrections. Matches
   the low-frequency, low-volume nature of strategy pillars (a handful of
   rows, rarely changed).
4. If no pillars exist, an `st.info` prompts the PM to add at least one
   before generating opportunities on the Opportunities page (a soft nudge,
   not a hard block — `generate_opportunities` still works with zero
   pillars, per the AI layer section above).

### `pages/3_Opportunities.py`

1. Batch selector, same pattern as the Dashboard page's batch filter.
2. "Find Opportunities" button. On click: build the digest from that batch's
   reviews (reusing the existing `get_reviews(conn, batch_id)`), call
   `generate_opportunities(digest_text, pillars)`, resolve `pillar_id` for
   each proposal, insert via `insert_opportunities` with `status='proposed'`.
3. **Review queue** — one `st.expander` per `status='proposed'` opportunity,
   showing `theme`, `evidence_count`, `rationale`, and the resolved pillar
   name (or "No matching pillar"). Inside: editable `title` (text_input) and
   `description` (text_area), a pillar `selectbox` (defaulting to the AI's
   match, in case it was wrong), and **Approve** / **Reject** buttons.
   - Approve → `update_opportunity(..., status='approved')` using whatever
     is currently in the edit fields (so an edit-then-approve is one action,
     not two).
   - Reject → `update_opportunity(..., status='rejected')`, fields as
     currently proposed (edits before rejecting are allowed but not required).
4. **Approved opportunities** table below the queue (title, pillar, batch,
   created date) via `get_opportunities(status='approved')` — the durable,
   at-a-glance output of the workflow.
5. Rejected opportunities are hidden by default behind a "Show rejected"
   checkbox, to keep the page focused on what's still actionable.
6. Empty/error handling mirrors the existing Analyze flow: zero reviews in
   the selected batch disables the button with an `st.info`; a
   `generate_opportunities` failure after retries is caught and shown via
   `st.error`, with no partial inserts (matching `pages/1_Dashboard.py`'s
   Executive Summary error handling).

## Error Handling

- `generate_opportunities` failures (network error, API error, exhausted
  retries) are caught at the call site in `pages/3_Opportunities.py` and
  shown via `st.error(...)`, identical in shape to the existing Executive
  Summary and Analyze error handling elsewhere in the app.
- `insert_opportunities` only runs after a successful, fully-parsed
  `OpportunityProposals` response — no partial batches of proposals.
- No new failure modes in `pages/2_Strategy.py` — `insert_pillar`/
  `delete_pillar` are plain synchronous SQLite writes, same risk profile as
  the existing `insert_batch`.

## Testing

The project has no automated test suite today; verification for prior
features (Dashboard, Executive Summary) has been manual, running the app
end-to-end. This feature follows the same practice: run the app, add one or
two strategy pillars, run "Find Opportunities" against a real batch (the
`samples/tp_ai_product_feedback.csv` sample data works well here — it spans
several recurring themes), and walk through approve / edit-then-approve /
reject. Adding an automated test suite is a separate, larger decision not
part of this spec.

## Explicitly Out of Scope (this round)

- Exporting approved opportunities to an external tracker (Jira, Linear,
  CSV) — stored in-app only.
- Editing or reverting an opportunity after it's been approved or rejected.
- Automatic/scheduled opportunity generation — manual, per-batch trigger only.
- Per-review-level opportunity flagging — the AI works at the clustered-theme
  level only.
- In-place editing of strategy pillars (delete-and-re-add only).
- Linking individual review rows to the theme that produced an opportunity
  (only an `evidence_count` integer is stored).
