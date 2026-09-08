# Strategy → Opportunities Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a PM define strategy pillars, have the AI cluster a batch's analyzed feedback into themes and compare them against those pillars, and let the PM approve, edit-then-approve, or reject each proposed opportunity — approved ones become durable in-app records.

**Architecture:** Two new SQLite tables (`strategy_pillars`, `opportunities`) with plain-function CRUD in `src/database.py`, one new Gemini structured-output call (`generate_opportunities`) in `src/gemini_client.py`, and two new Streamlit pages (`pages/2_Strategy.py`, `pages/3_Opportunities.py`) — no changes to the existing Analyze (`app.py`) or Dashboard (`pages/1_Dashboard.py`) pages.

**Tech Stack:** Python, Streamlit, SQLite (stdlib `sqlite3`), Pydantic, `google-genai`, `tenacity`, `pandas`.

**Spec:** `docs/superpowers/specs/2026-09-08-strategy-opportunities-design.md`

## Global Constraints

- No new automated test framework — this codebase has none today, and the spec explicitly scopes that decision out. Every task below is verified by running real code against a real (temp or dev) SQLite database, and by running the actual Streamlit app.
- Match existing code style exactly: plain functions (no classes) in `database.py`, `sqlite3.Row` → `dict` conversion, `datetime.now(timezone.utc).isoformat()` timestamps, Pydantic `BaseModel` + `Field(..., description=...)` schemas, `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)` on every Gemini call, `response_mime_type="application/json"` + `response_schema=<Model>` structured output, try/except around Gemini calls in pages showing `st.error(...)`.
- `pillar_id` on `opportunities` is nullable — never force a match.
- Rejected opportunities are kept (status update), never deleted.

---

### Task 1: Database layer — strategy pillars and opportunities

**Files:**
- Modify: `src/database.py`

**Interfaces:**
- Produces: `insert_pillar(conn, name: str, description: str) -> int`, `get_pillars(conn) -> list[dict]`, `delete_pillar(conn, pillar_id: int) -> None`, `insert_opportunities(conn, batch_id: int, proposals: list[dict]) -> None` (each proposal dict has keys `pillar_id`, `theme`, `evidence_count`, `rationale`, `title`, `description`), `get_opportunities(conn, status: str | None = None) -> list[dict]`, `update_opportunity(conn, opportunity_id: int, *, title: str, description: str, pillar_id: int | None, status: str) -> None`.

- [ ] **Step 1: Add the two new tables to `SCHEMA`**

In `src/database.py`, extend the `SCHEMA` string (currently ending after the `reviews` table's closing `);`) by appending:

```python
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
"""
```

(Keep the existing `batches` and `reviews` table definitions exactly as they are — only append the two new `CREATE TABLE` statements.)

- [ ] **Step 2: Add pillar CRUD functions**

Append to `src/database.py`, after the existing `get_kpis` function:

```python
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
```

- [ ] **Step 3: Add opportunity CRUD functions**

Append to `src/database.py`, after the pillar functions:

```python
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
```

- [ ] **Step 4: Verify with a throwaway script against a temp database**

Run:

```bash
source .venv/bin/activate && python3 -c "
import tempfile, os
from src.database import (
    init_db, get_connection, insert_batch, insert_reviews,
    insert_pillar, get_pillars, delete_pillar,
    insert_opportunities, get_opportunities, update_opportunity,
)

db_path = tempfile.mktemp(suffix='.db')
init_db(db_path)
conn = get_connection(db_path)

pillar_id = insert_pillar(conn, 'Reliability', 'Keep core flows fast and error-free')
pillars = get_pillars(conn)
assert len(pillars) == 1, pillars
assert pillars[0]['id'] == pillar_id
assert pillars[0]['name'] == 'Reliability'
assert pillars[0]['description'] == 'Keep core flows fast and error-free'

batch_id = insert_batch(conn, 'test.csv', 1)
insert_reviews(conn, batch_id, [{
    'original_text': 'slow', 'sentiment': 'Negative', 'emotion': 'Frustrated',
    'category': 'Performance', 'priority': 'High', 'summary': 'App is slow',
    'suggested_reply': 'Sorry, looking into it.',
}])

insert_opportunities(conn, batch_id, [{
    'pillar_id': pillar_id, 'theme': 'Latency complaints', 'evidence_count': 1,
    'rationale': 'Matches Reliability pillar', 'title': 'Investigate latency',
    'description': 'Several users report slowness.',
}])
proposed = get_opportunities(conn, status='proposed')
assert len(proposed) == 1, proposed
opp_id = proposed[0]['id']

update_opportunity(conn, opp_id, title='Fix latency', description='Edited desc', pillar_id=pillar_id, status='approved')
approved = get_opportunities(conn, status='approved')
assert len(approved) == 1 and approved[0]['title'] == 'Fix latency', approved
assert get_opportunities(conn, status='proposed') == []

delete_pillar(conn, pillar_id)
assert get_pillars(conn) == []

conn.close()
os.remove(db_path)
print('OK')
"
```

Expected output: `OK` (no assertion errors).

- [ ] **Step 5: Commit**

```bash
git add src/database.py
git commit -m "feat: add strategy_pillars and opportunities tables with CRUD"
```

---

### Task 2: Opportunity schemas

**Files:**
- Modify: `src/schemas.py`

**Interfaces:**
- Consumes: nothing new (pure Pydantic models).
- Produces: `OpportunityProposal` (fields: `theme: str`, `evidence_count: int`, `matched_pillar: str | None`, `rationale: str`, `title: str`, `description: str`), `OpportunityProposals` (field: `proposals: list[OpportunityProposal]`).

- [ ] **Step 1: Add the two models**

Append to `src/schemas.py`, after the existing `ExecutiveSummary` class:

```python
class OpportunityProposal(BaseModel):
    theme: str = Field(..., description="The recurring feedback pattern observed")
    evidence_count: int = Field(..., description="Number of reviews supporting this theme")
    matched_pillar: str | None = Field(
        ..., description="Name of the strategy pillar this relates to, or null if none"
    )
    rationale: str = Field(..., description="Why this theme is or isn't aligned with strategy")
    title: str = Field(..., description="Proposed opportunity title")
    description: str = Field(..., description="1-3 sentence proposed opportunity description")


class OpportunityProposals(BaseModel):
    proposals: list[OpportunityProposal]
```

- [ ] **Step 2: Verify the models validate correctly**

Run:

```bash
source .venv/bin/activate && python3 -c "
from src.schemas import OpportunityProposal, OpportunityProposals

p = OpportunityProposal(
    theme='Latency complaints', evidence_count=3, matched_pillar='Reliability',
    rationale='Directly affects core flow speed', title='Investigate latency',
    description='Several users report slowness in checkout.',
)
batch = OpportunityProposals(proposals=[p])
assert batch.proposals[0].matched_pillar == 'Reliability'

p2 = OpportunityProposal(
    theme='Dark mode requests', evidence_count=2, matched_pillar=None,
    rationale='Not covered by any current pillar', title='Consider dark mode',
    description='A few users asked for a dark theme.',
)
assert p2.matched_pillar is None
print('OK')
"
```

Expected output: `OK`.

- [ ] **Step 3: Commit**

```bash
git add src/schemas.py
git commit -m "feat: add OpportunityProposal and OpportunityProposals schemas"
```

---

### Task 3: GeminiClient.generate_opportunities

**Files:**
- Modify: `src/gemini_client.py`

**Interfaces:**
- Consumes: `OpportunityProposals` from Task 2 (`src/schemas.py`).
- Produces: `GeminiClient.generate_opportunities(self, digest_text: str, pillars: list[dict]) -> OpportunityProposals`, where each `pillars` item is a dict with `name` and `description` keys (the shape returned by `get_pillars`).

- [ ] **Step 1: Add the prompt template and import**

In `src/gemini_client.py`, update the import line:

```python
from src.schemas import AnalysisResult, ExecutiveSummary, OpportunityProposals
```

Add, after `EXECUTIVE_SUMMARY_PROMPT_TEMPLATE`:

```python
OPPORTUNITIES_PROMPT_TEMPLATE = """You are a product strategist reviewing a batch of already-triaged \
customer feedback against your team's current strategic pillars.

First, cluster the feedback below into recurring themes — patterns that show up across multiple \
reviews, not one-off complaints. For each theme, propose a concrete product opportunity: a title, a \
1-3 sentence description, and a rationale for how it relates to the strategy pillars listed below. If \
a theme does not clearly relate to any pillar, say so in the rationale and set matched_pillar to null \
rather than forcing a match. Report how many reviews support each theme as evidence_count.

Strategy pillars:
{pillars}

Feedback data:
{digest}
"""
```

- [ ] **Step 2: Add the method**

Append to the `GeminiClient` class in `src/gemini_client.py`, after `generate_executive_summary`:

```python
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def generate_opportunities(self, digest_text: str, pillars: list[dict]) -> OpportunityProposals:
        if pillars:
            pillars_text = "\n".join(f"- {p['name']}: {p['description']}" for p in pillars)
        else:
            pillars_text = "(no strategy pillars defined yet)"
        response = self._client.models.generate_content(
            model=self._model,
            contents=OPPORTUNITIES_PROMPT_TEMPLATE.format(pillars=pillars_text, digest=digest_text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=OpportunityProposals,
            ),
        )
        return OpportunityProposals.model_validate_json(response.text)
```

- [ ] **Step 3: Verify against the real Gemini API**

This project has no mocking layer — every existing Gemini call is verified against the real API using the key in `.env`, and this follows the same practice.

Run:

```bash
source .venv/bin/activate && python3 -c "
from src.config import get_config
from src.gemini_client import GeminiClient

config = get_config()
client = GeminiClient(config.gemini_api_key, config.gemini_model)

digest = '''Individual review summaries:
- [High priority, Performance] Checkout latency has increased significantly over two weeks.
- [High priority, Performance] Users report the app feels much slower than before.
- [Medium priority, Billing] Customer was charged for a tier they never upgraded to.
'''
pillars = [{'name': 'Reliability', 'description': 'Keep core flows fast and error-free'}]

result = client.generate_opportunities(digest, pillars)
assert len(result.proposals) >= 1, result
for p in result.proposals:
    print(p.theme, '->', p.matched_pillar, '|', p.title)
print('OK')
"
```

Expected output: at least one proposed theme printed, ending with `OK`. (Exact theme text will vary — this is a live model call, not a fixed assertion on content.)

- [ ] **Step 4: Commit**

```bash
git add src/gemini_client.py
git commit -m "feat: add generate_opportunities to GeminiClient"
```

---

### Task 4: Strategy page

**Files:**
- Create: `pages/2_Strategy.py`

**Interfaces:**
- Consumes: `get_config` (`src/config.py`), `get_connection`, `init_db`, `insert_pillar`, `get_pillars`, `delete_pillar` (`src/database.py`, Task 1).
- Produces: a working Streamlit page at the "Strategy" sidebar entry — no interfaces consumed by later tasks (Task 5/6 call `get_pillars` directly, not anything from this page).

- [ ] **Step 1: Write the page**

Create `pages/2_Strategy.py`:

```python
import streamlit as st

from src.config import get_config
from src.database import delete_pillar, get_connection, get_pillars, init_db, insert_pillar

st.set_page_config(page_title="Strategy", page_icon="🧭", layout="wide")
st.title("Strategy Pillars")

try:
    config = get_config()
except ValueError as e:
    st.error(str(e))
    st.stop()

init_db(config.db_path)
conn = get_connection(config.db_path)

st.write("Define the strategic pillars the AI should compare customer feedback against on the Opportunities page.")

with st.form("add_pillar", clear_on_submit=True):
    name = st.text_input("Pillar name")
    description = st.text_area("Description")
    submitted = st.form_submit_button("Add Pillar")
    if submitted:
        if name.strip() and description.strip():
            insert_pillar(conn, name.strip(), description.strip())
            st.success(f"Added pillar: {name.strip()}")
        else:
            st.warning("Both name and description are required.")

pillars = get_pillars(conn)
conn.close()

st.subheader("Current Pillars")
if not pillars:
    st.info("No strategy pillars yet. Add one above before generating opportunities on the Opportunities page.")
else:
    for pillar in pillars:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"**{pillar['name']}**")
            st.write(pillar["description"])
        with col2:
            if st.button("Delete", key=f"delete_pillar_{pillar['id']}"):
                delete_conn = get_connection(config.db_path)
                delete_pillar(delete_conn, pillar["id"])
                delete_conn.close()
                st.rerun()
        st.divider()
```

- [ ] **Step 2: Verify by running the app**

Run:

```bash
source .venv/bin/activate && streamlit run app.py --server.headless true --server.port 8502 > /tmp/strategy_page.log 2>&1 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8502/Strategy
```

Expected output: `200`. Then open `http://localhost:8502/Strategy` in a browser, add a pillar (e.g. name "Reliability", description "Keep core flows fast and error-free"), confirm it appears in the "Current Pillars" list, click "Delete", and confirm it disappears. Stop the server afterward:

```bash
lsof -ti:8502 -sTCP:LISTEN | xargs -r kill
```

- [ ] **Step 3: Commit**

```bash
git add pages/2_Strategy.py
git commit -m "feat: add Strategy page for managing strategy pillars"
```

---

### Task 5: Opportunities page — generation flow

**Files:**
- Create: `pages/3_Opportunities.py`

**Interfaces:**
- Consumes: `get_config` (`src/config.py`); `get_connection`, `init_db`, `get_batches`, `get_pillars`, `get_reviews`, `insert_opportunities` (`src/database.py`, Task 1); `GeminiClient.generate_opportunities` (`src/gemini_client.py`, Task 3).
- Produces: `build_opportunity_digest(reviews_df: pandas.DataFrame) -> str` and `resolve_pillar_id(pillars: list[dict], matched_pillar_name: str | None) -> int | None` — both module-level functions in `pages/3_Opportunities.py` that Task 6 extends the same file around (Task 6 adds code below this task's code in the same file; it does not import from it).

- [ ] **Step 1: Write the generation half of the page**

Create `pages/3_Opportunities.py`:

```python
import pandas as pd
import streamlit as st

from src.config import get_config
from src.database import (
    get_batches,
    get_connection,
    get_pillars,
    get_reviews,
    init_db,
    insert_opportunities,
)
from src.gemini_client import GeminiClient

st.set_page_config(page_title="Opportunities", page_icon="🎯", layout="wide")
st.title("Opportunities")


def build_opportunity_digest(reviews_df: pd.DataFrame) -> str:
    lines = ["Individual review summaries:"]
    for _, row in reviews_df.iterrows():
        lines.append(f"- [{row['priority']} priority, {row['category']}] {row['summary']}")
    return "\n".join(lines)


def resolve_pillar_id(pillars: list[dict], matched_pillar_name: str | None) -> int | None:
    if not matched_pillar_name:
        return None
    for pillar in pillars:
        if pillar["name"] == matched_pillar_name:
            return pillar["id"]
    return None


try:
    config = get_config()
except ValueError as e:
    st.error(str(e))
    st.stop()

init_db(config.db_path)
conn = get_connection(config.db_path)

batches = get_batches(conn)
if not batches:
    conn.close()
    st.info("No reviews analyzed yet. Go to the Analyze page to upload a CSV.")
    st.stop()

pillars = get_pillars(conn)
if not pillars:
    st.info("No strategy pillars yet. Add some on the Strategy page for the AI to compare feedback against.")

batch_options = {f"{b['filename']} ({b['uploaded_at'][:10]}) #{b['id']}": b["id"] for b in batches}
selected_label = st.selectbox("Batch", list(batch_options.keys()))
selected_batch_id = batch_options[selected_label]

reviews = get_reviews(conn, batch_id=selected_batch_id)
conn.close()

reviews_df = pd.DataFrame(reviews)
chart_df = reviews_df[reviews_df["sentiment"] != "ERROR"] if not reviews_df.empty else reviews_df

if chart_df.empty:
    st.info("No analyzed reviews in the selected batch.")
else:
    if st.button("Find Opportunities", type="primary"):
        gemini_client = GeminiClient(config.gemini_api_key, config.gemini_model)
        digest = build_opportunity_digest(chart_df)
        try:
            with st.spinner("Comparing feedback against strategy..."):
                proposals = gemini_client.generate_opportunities(digest, pillars)
            proposal_dicts = [
                {
                    "pillar_id": resolve_pillar_id(pillars, p.matched_pillar),
                    "theme": p.theme,
                    "evidence_count": p.evidence_count,
                    "rationale": p.rationale,
                    "title": p.title,
                    "description": p.description,
                }
                for p in proposals.proposals
            ]
            insert_conn = get_connection(config.db_path)
            insert_opportunities(insert_conn, selected_batch_id, proposal_dicts)
            insert_conn.close()
            st.success(f"Found {len(proposal_dicts)} opportunities — see the review queue below.")
        except Exception as e:
            st.error(f"Could not generate opportunities: {e}")
```

- [ ] **Step 2: Verify by running the app end-to-end**

First make sure there's a batch to work with — via the running app's Analyze page, upload `samples/tp_ai_product_feedback.csv` if you haven't already (or reuse an existing batch from earlier testing).

Run:

```bash
source .venv/bin/activate && streamlit run app.py --server.headless true --server.port 8502 > /tmp/opportunities_page.log 2>&1 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8502/Opportunities
```

Expected output: `200`. Then open `http://localhost:8502/Opportunities` in a browser, pick the batch from the TP sample data, click "Find Opportunities", and confirm a success message with a count appears (no `st.error`). Verify rows actually landed in the database:

```bash
source .venv/bin/activate && python3 -c "
from src.config import get_config
from src.database import get_connection, get_opportunities

config = get_config()
conn = get_connection(config.db_path)
proposed = get_opportunities(conn, status='proposed')
conn.close()
assert len(proposed) >= 1, proposed
print(f'{len(proposed)} proposed opportunities in DB')
"
```

Expected output: `N proposed opportunities in DB` with `N >= 1`. Stop the server afterward:

```bash
lsof -ti:8502 -sTCP:LISTEN | xargs -r kill
```

- [ ] **Step 3: Commit**

```bash
git add pages/3_Opportunities.py
git commit -m "feat: add Opportunities page — batch selection and AI generation"
```

---

### Task 6: Opportunities page — review queue and approved list

**Files:**
- Modify: `pages/3_Opportunities.py`

**Interfaces:**
- Consumes: `get_opportunities`, `update_opportunity` (`src/database.py`, Task 1); `pillars`, `batches`, `selected_batch_id` (module-level variables already defined earlier in the same file by Task 5).
- Produces: nothing consumed elsewhere — this is the final task in the plan.

- [ ] **Step 1: Add the review queue, approved table, and rejected toggle**

Append to the end of `pages/3_Opportunities.py` (after the `if chart_df.empty: ... else: ...` block from Task 5):

```python
conn = get_connection(config.db_path)
proposed = [o for o in get_opportunities(conn, status="proposed") if o["batch_id"] == selected_batch_id]
pillars_by_id = {p["id"]: p["name"] for p in pillars}
pillar_names = ["(no matching pillar)"] + [p["name"] for p in pillars]

if proposed:
    st.subheader("Review Queue")
    for opp in proposed:
        current_pillar_name = pillars_by_id.get(opp["pillar_id"], "(no matching pillar)")
        with st.expander(f"{opp['title']} — {opp['theme']}"):
            st.caption(f"Evidence: {opp['evidence_count']} reviews")
            st.write(opp["rationale"])
            title = st.text_input("Title", value=opp["title"], key=f"title_{opp['id']}")
            description = st.text_area("Description", value=opp["description"], key=f"desc_{opp['id']}")
            pillar_choice = st.selectbox(
                "Strategy pillar",
                pillar_names,
                index=pillar_names.index(current_pillar_name) if current_pillar_name in pillar_names else 0,
                key=f"pillar_{opp['id']}",
            )
            chosen_pillar_id = next((p["id"] for p in pillars if p["name"] == pillar_choice), None)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Approve", key=f"approve_{opp['id']}", type="primary"):
                    update_opportunity(
                        conn, opp["id"], title=title, description=description,
                        pillar_id=chosen_pillar_id, status="approved",
                    )
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"reject_{opp['id']}"):
                    update_opportunity(
                        conn, opp["id"], title=title, description=description,
                        pillar_id=chosen_pillar_id, status="rejected",
                    )
                    st.rerun()

st.subheader("Approved Opportunities")
approved = get_opportunities(conn, status="approved")
if not approved:
    st.info("No approved opportunities yet.")
else:
    batches_by_id = {b["id"]: b["filename"] for b in batches}
    approved_rows = [
        {
            "Title": o["title"],
            "Pillar": pillars_by_id.get(o["pillar_id"], "—"),
            "Batch": batches_by_id.get(o["batch_id"], "—"),
            "Created": o["created_at"][:10],
        }
        for o in approved
    ]
    st.dataframe(pd.DataFrame(approved_rows), use_container_width=True)

if st.checkbox("Show rejected"):
    rejected = get_opportunities(conn, status="rejected")
    if not rejected:
        st.info("No rejected opportunities.")
    else:
        rejected_rows = [
            {"Title": o["title"], "Theme": o["theme"], "Reviewed": (o["reviewed_at"] or "")[:10]}
            for o in rejected
        ]
        st.dataframe(pd.DataFrame(rejected_rows), use_container_width=True)

conn.close()
```

- [ ] **Step 2: Verify the full review workflow by running the app**

Run:

```bash
source .venv/bin/activate && streamlit run app.py --server.headless true --server.port 8502 > /tmp/opportunities_page2.log 2>&1 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8502/Opportunities
```

Expected output: `200`. In the browser, on the Opportunities page for the batch used in Task 5, confirm the "Review Queue" section lists the proposed opportunities from Task 5's verification. For one, edit the title, then click "Approve" — confirm it disappears from the queue and appears in "Approved Opportunities" with the edited title. For another, click "Reject" without editing — confirm it disappears from the queue and does NOT appear in "Approved Opportunities". Check "Show rejected" and confirm the rejected one now appears there.

Then confirm the database reflects this:

```bash
source .venv/bin/activate && python3 -c "
from src.config import get_config
from src.database import get_connection, get_opportunities

config = get_config()
conn = get_connection(config.db_path)
approved = get_opportunities(conn, status='approved')
rejected = get_opportunities(conn, status='rejected')
conn.close()
assert len(approved) >= 1, approved
assert len(rejected) >= 1, rejected
assert all(o['reviewed_at'] for o in approved + rejected)
print(f'{len(approved)} approved, {len(rejected)} rejected, all have reviewed_at')
"
```

Expected output: a line like `1 approved, 1 rejected, all have reviewed_at`. Stop the server afterward:

```bash
lsof -ti:8502 -sTCP:LISTEN | xargs -r kill
```

- [ ] **Step 3: Commit**

```bash
git add pages/3_Opportunities.py
git commit -m "feat: add Opportunities review queue, approved list, and rejected view"
```
