# Dashboard Executive Summary & Theme Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Gemini-generated Executive Summary + product next-steps section to the Dashboard page, and retint the app (Streamlit theme + chart colors) to a shared teal/brick-amber palette.

**Architecture:** A new shared `TAXONOMY_COLORS` map drives consistent chart coloring on both existing pages; a new `ExecutiveSummary` Pydantic model and a second `GeminiClient` method reuse the existing structured-output + retry pattern; the Dashboard gains an on-demand, session-only summary section built from already-analyzed data (aggregate counts + each review's `summary` field), not raw review text.

**Tech Stack:** Same as the existing app — Streamlit, `google-genai`, Pydantic, Plotly, pandas. No new dependencies.

## Global Constraints

- No automated test suite (pytest) — explicit, ongoing project decision. Every task ends with a manual verification step (a runnable command with expected output), not a pytest step.
- Python 3.10+, existing venv at `.venv`.
- `ExecutiveSummary` fields: `summary: str`, `next_steps: list[str]` — exact names, used by both `src/gemini_client.py` and `pages/1_Dashboard.py`.
- `TAXONOMY_COLORS` (exact key set — must match `src/schemas.py`'s enum values verbatim):
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
- Streamlit theme colors (exact values):
  `primaryColor = "#0E6E63"`, `backgroundColor = "#F1F3F1"`, `secondaryBackgroundColor = "#E6EAE7"`, `textColor = "#1A2220"`, `font = "sans serif"`.
- Executive Summary is on-demand (button click) only, never automatic on Dashboard rerun. Session-only (`st.session_state["exec_summary"]`) — no new SQLite table.
- Executive Summary digest is built from `chart_df` (the ERROR-excluded, already-filtered DataFrame the Dashboard already computes), using each row's `summary`/`category`/`priority` fields — never `original_text`.
- No live Gemini API key is available in the implementer's sandbox. Any step requiring a real Gemini response either uses `unittest.mock.patch` to substitute a fake return value, or is explicitly deferred to a human with a real key (matching the pattern already used for `src/gemini_client.py` in the original project plan).

---

### Task 1: Theme Pass — Streamlit Theme & Shared Chart Colors

**Files:**
- Create: `.streamlit/config.toml`
- Create: `src/chart_colors.py`
- Modify: `app.py` (import block and the three chart calls in the results section)
- Modify: `pages/1_Dashboard.py` (import block and the five chart calls)

**Interfaces:**
- Produces: `TAXONOMY_COLORS: dict[str, str]` in `src/chart_colors.py`, importable as `from src.chart_colors import TAXONOMY_COLORS`. Used by both `app.py` and `pages/1_Dashboard.py`, and by Task 4 (which adds more content to `pages/1_Dashboard.py` after this task's edits).

- [ ] **Step 1: Create `.streamlit/config.toml`**

```toml
[theme]
primaryColor = "#0E6E63"
backgroundColor = "#F1F3F1"
secondaryBackgroundColor = "#E6EAE7"
textColor = "#1A2220"
font = "sans serif"
```

- [ ] **Step 2: Create `src/chart_colors.py`**

```python
TAXONOMY_COLORS = {
    "Positive": "#1F7A5C",
    "Negative": "#B5472A",
    "Neutral": "#5C6866",
    "Critical": "#B5472A",
    "High": "#A9780A",
    "Medium": "#5C6866",
    "Low": "#1F7A5C",
    "Bug": "#B5472A",
    "Feature Request": "#0E6E63",
    "Billing": "#A9780A",
    "UX/Usability": "#0E6E63",
    "Customer Support": "#A9780A",
    "Performance": "#5C6866",
    "Other": "#5C6866",
    "Happy": "#1F7A5C",
    "Satisfied": "#1F7A5C",
    "Confused": "#A9780A",
    "Disappointed": "#A9780A",
    "Frustrated": "#B5472A",
    "Angry": "#B5472A",
}
```

- [ ] **Step 3: Verify Plotly's color-mapping requirement (context for the next two steps)**

Plotly Express only applies `color_discrete_map` when a `color=` argument is also passed (pointing at the same categorical column being charted) — passing `color_discrete_map` alone silently does nothing and leaves the chart on Plotly's default blue. Confirm this before editing the chart calls:

Run: `source .venv/bin/activate && python -c "
import pandas as pd
import plotly.express as px
df = pd.DataFrame({'priority': ['Critical', 'Low'], 'count': [1, 2]})
cmap = {'Critical': '#B5472A', 'Low': '#1F7A5C'}
fig_without = px.bar(df, x='priority', y='count', color_discrete_map=cmap)
fig_with = px.bar(df, x='priority', y='count', color='priority', color_discrete_map=cmap)
print('without color=:', fig_without.data[0].marker.color)
print('with color=:', [(t.name, t.marker.color) for t in fig_with.data])
"`
Expected:
```
without color=: #636efa
with color=: [('Critical', '#B5472A'), ('Low', '#1F7A5C')]
```

- [ ] **Step 4: Modify `app.py` — add the import**

Find this line near the top of `app.py`:
```python
from src.gemini_client import GeminiClient
```
Add a new import line directly after it:
```python
from src.gemini_client import GeminiClient
from src.chart_colors import TAXONOMY_COLORS
```

- [ ] **Step 5: Modify `app.py` — wire `color=`/`color_discrete_map` into the three chart calls**

Find this block (the three charts inside the `else:` branch of the results section):
```python
            col1, col2, col3 = st.columns(3)
            with col1:
                sentiment_counts = chart_df["sentiment"].value_counts().reset_index()
                st.plotly_chart(px.pie(sentiment_counts, names="sentiment", values="count", title="Sentiment"), use_container_width=True)
            with col2:
                priority_counts = chart_df["priority"].value_counts().reset_index()
                st.plotly_chart(px.bar(priority_counts, x="priority", y="count", title="Priority"), use_container_width=True)
            with col3:
                category_counts = chart_df["category"].value_counts().reset_index()
                st.plotly_chart(px.bar(category_counts, x="category", y="count", title="Category"), use_container_width=True)
```
Replace it with:
```python
            col1, col2, col3 = st.columns(3)
            with col1:
                sentiment_counts = chart_df["sentiment"].value_counts().reset_index()
                st.plotly_chart(
                    px.pie(sentiment_counts, names="sentiment", values="count", title="Sentiment", color="sentiment", color_discrete_map=TAXONOMY_COLORS),
                    use_container_width=True,
                )
            with col2:
                priority_counts = chart_df["priority"].value_counts().reset_index()
                st.plotly_chart(
                    px.bar(priority_counts, x="priority", y="count", title="Priority", color="priority", color_discrete_map=TAXONOMY_COLORS),
                    use_container_width=True,
                )
            with col3:
                category_counts = chart_df["category"].value_counts().reset_index()
                st.plotly_chart(
                    px.bar(category_counts, x="category", y="count", title="Category", color="category", color_discrete_map=TAXONOMY_COLORS),
                    use_container_width=True,
                )
```

- [ ] **Step 6: Modify `pages/1_Dashboard.py` — add the import**

Find this line near the top:
```python
from src.database import get_batches, get_connection, get_kpis, get_reviews, init_db
```
Add directly after it:
```python
from src.database import get_batches, get_connection, get_kpis, get_reviews, init_db
from src.chart_colors import TAXONOMY_COLORS
```

- [ ] **Step 7: Modify `pages/1_Dashboard.py` — wire `color=`/`color_discrete_map` into the five chart calls**

Find this block:
```python
    c1, c2 = st.columns(2)
    with c1:
        sentiment_counts = chart_df["sentiment"].value_counts().reset_index()
        st.plotly_chart(px.pie(sentiment_counts, names="sentiment", values="count", title="Sentiment Distribution"), use_container_width=True)
    with c2:
        priority_counts = chart_df["priority"].value_counts().reset_index()
        st.plotly_chart(px.bar(priority_counts, x="priority", y="count", title="Priority Breakdown"), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        category_counts = chart_df["category"].value_counts().reset_index()
        st.plotly_chart(px.bar(category_counts, x="category", y="count", title="Category Breakdown"), use_container_width=True)
    with c4:
        emotion_counts = chart_df["emotion"].value_counts().reset_index()
        st.plotly_chart(px.bar(emotion_counts, x="emotion", y="count", title="Emotion Distribution"), use_container_width=True)

    volume = chart_df.groupby("analyzed_date").size().reset_index(name="count")
    st.plotly_chart(px.line(volume, x="analyzed_date", y="count", title="Review Volume Over Time"), use_container_width=True)
```
Replace it with:
```python
    c1, c2 = st.columns(2)
    with c1:
        sentiment_counts = chart_df["sentiment"].value_counts().reset_index()
        st.plotly_chart(
            px.pie(sentiment_counts, names="sentiment", values="count", title="Sentiment Distribution", color="sentiment", color_discrete_map=TAXONOMY_COLORS),
            use_container_width=True,
        )
    with c2:
        priority_counts = chart_df["priority"].value_counts().reset_index()
        st.plotly_chart(
            px.bar(priority_counts, x="priority", y="count", title="Priority Breakdown", color="priority", color_discrete_map=TAXONOMY_COLORS),
            use_container_width=True,
        )

    c3, c4 = st.columns(2)
    with c3:
        category_counts = chart_df["category"].value_counts().reset_index()
        st.plotly_chart(
            px.bar(category_counts, x="category", y="count", title="Category Breakdown", color="category", color_discrete_map=TAXONOMY_COLORS),
            use_container_width=True,
        )
    with c4:
        emotion_counts = chart_df["emotion"].value_counts().reset_index()
        st.plotly_chart(
            px.bar(emotion_counts, x="emotion", y="count", title="Emotion Distribution", color="emotion", color_discrete_map=TAXONOMY_COLORS),
            use_container_width=True,
        )

    volume = chart_df.groupby("analyzed_date").size().reset_index(name="count")
    st.plotly_chart(px.line(volume, x="analyzed_date", y="count", title="Review Volume Over Time"), use_container_width=True)
```
(The volume line chart is left uncolored — it's a single time series, not a per-category breakdown, so `TAXONOMY_COLORS` doesn't apply to it.)

- [ ] **Step 8: Verify both pages still boot cleanly**

Run: `source .venv/bin/activate && echo "GEMINI_API_KEY=dummy-key-for-boot-smoke-test" > .env && python -c "
from streamlit.testing.v1 import AppTest
at1 = AppTest.from_file('app.py')
at1.run()
assert not at1.exception, at1.exception
at2 = AppTest.from_file('pages/1_Dashboard.py')
at2.run()
assert not at2.exception, at2.exception
print('OK - both pages boot with theme/chart-color changes')
" && rm -f .env`
Expected: `OK - both pages boot with theme/chart-color changes`

- [ ] **Step 9: Commit**

```bash
git add .streamlit/config.toml src/chart_colors.py app.py pages/1_Dashboard.py
git commit -m "feat: add Streamlit theme and shared taxonomy chart colors"
```

---

### Task 2: `ExecutiveSummary` Schema

**Files:**
- Modify: `src/schemas.py` (add one class at the end of the file)

**Interfaces:**
- Produces: `ExecutiveSummary(BaseModel)` with fields `summary: str`, `next_steps: list[str]`. Used by Task 3 (`src/gemini_client.py`) and Task 4 (`pages/1_Dashboard.py`).

- [ ] **Step 1: Add `ExecutiveSummary` to `src/schemas.py`**

Find the end of the file (after the existing `AnalysisResult` class):
```python
class AnalysisResult(BaseModel):
    sentiment: Sentiment
    emotion: Emotion
    category: Category
    priority: Priority
    summary: str = Field(..., description="1-2 sentence summary of the review")
    suggested_reply: str = Field(..., description="Draft support reply, ready to send or edit")
```
Add directly after it:
```python


class ExecutiveSummary(BaseModel):
    summary: str = Field(..., description="2-4 sentence narrative summary of patterns in the feedback")
    next_steps: list[str] = Field(..., description="3-5 concrete next steps for the product team")
```

- [ ] **Step 2: Verify the schema validates good and bad input**

Run: `source .venv/bin/activate && python -c "
from src.schemas import ExecutiveSummary
import json

good = json.dumps({
    'summary': 'Customers are largely satisfied, with one critical checkout bug reported.',
    'next_steps': ['Fix the checkout crash', 'Monitor for repeat reports', 'Follow up with the affected customer'],
})
result = ExecutiveSummary.model_validate_json(good)
print('OK:', result.next_steps)

bad = json.dumps({'summary': 'Missing next_steps field'})
try:
    ExecutiveSummary.model_validate_json(bad)
    print('FAIL: should have raised')
except Exception:
    print('OK rejected missing field')
"`
Expected:
```
OK: ['Fix the checkout crash', 'Monitor for repeat reports', 'Follow up with the affected customer']
OK rejected missing field
```

- [ ] **Step 3: Commit**

```bash
git add src/schemas.py
git commit -m "feat: add ExecutiveSummary schema"
```

---

### Task 3: `GeminiClient.generate_executive_summary`

**Files:**
- Modify: `src/gemini_client.py`

**Interfaces:**
- Consumes: `ExecutiveSummary` from `src/schemas.py` (Task 2).
- Produces: `GeminiClient.generate_executive_summary(self, digest_text: str) -> ExecutiveSummary`. Used by Task 4 (`pages/1_Dashboard.py`).

- [ ] **Step 1: Modify the import line in `src/gemini_client.py`**

Find:
```python
from src.schemas import AnalysisResult
```
Replace with:
```python
from src.schemas import AnalysisResult, ExecutiveSummary
```

- [ ] **Step 2: Add the new prompt template**

Find:
```python
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
```
Add directly after it (before the `class GeminiClient:` line):
```python
EXECUTIVE_SUMMARY_PROMPT_TEMPLATE = """You are a product analyst preparing a briefing for a product \
team based on a set of already-triaged customer feedback.

Write a short executive summary (2-4 sentences) describing the overall patterns in this data: \
what customers are saying, which issues are most common, and how urgent they are. Then suggest \
3-5 concrete, specific next steps for the product team, grounded in the actual categories and \
priorities present in the data below — not generic advice.

Feedback data:
{digest}
"""
```

- [ ] **Step 3: Add the `generate_executive_summary` method**

Find the end of the `analyze_review` method:
```python
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
Add directly after it (still inside the `GeminiClient` class, same indentation):
```python

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def generate_executive_summary(self, digest_text: str) -> ExecutiveSummary:
        response = self._client.models.generate_content(
            model=self._model,
            contents=EXECUTIVE_SUMMARY_PROMPT_TEMPLATE.format(digest=digest_text),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExecutiveSummary,
            ),
        )
        return ExecutiveSummary.model_validate_json(response.text)
```

- [ ] **Step 4: Verify import and instantiation (no live API key in this environment)**

Run: `source .venv/bin/activate && python -c "
from src.gemini_client import GeminiClient, EXECUTIVE_SUMMARY_PROMPT_TEMPLATE
client = GeminiClient(api_key='dummy-key-for-instantiation-test', model='gemini-2.5-flash')
assert hasattr(client, 'generate_executive_summary')
assert '{digest}' in EXECUTIVE_SUMMARY_PROMPT_TEMPLATE
print('OK')
"`
Expected: `OK`

Do NOT call `client.generate_executive_summary(...)` — that requires a real API key. A human with a real key should verify this method against the live API before relying on it (same pattern already used for `analyze_review` in this project).

- [ ] **Step 5: Commit**

```bash
git add src/gemini_client.py
git commit -m "feat: add generate_executive_summary to GeminiClient"
```

---

### Task 4: Dashboard Executive Summary Section

**Files:**
- Modify: `pages/1_Dashboard.py` (this task assumes Task 1's edits to this file — the `TAXONOMY_COLORS` import and the five colored chart calls — are already applied)

**Interfaces:**
- Consumes: `GeminiClient.generate_executive_summary(digest_text: str) -> ExecutiveSummary` (Task 3), `ExecutiveSummary` (Task 2, accessed via `.summary` and `.next_steps` attributes — no explicit import needed since the page never constructs one directly).
- Produces: nothing new consumed by other files — this is the final task.

- [ ] **Step 1: Add the `GeminiClient` import**

Find (this line was added by Task 1, Step 6):
```python
from src.database import get_batches, get_connection, get_kpis, get_reviews, init_db
from src.chart_colors import TAXONOMY_COLORS
```
Replace with:
```python
from src.database import get_batches, get_connection, get_kpis, get_reviews, init_db
from src.chart_colors import TAXONOMY_COLORS
from src.gemini_client import GeminiClient
```

- [ ] **Step 2: Add the digest-builder helper function**

Find:
```python
st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("Feedback Dashboard")
```
Replace with:
```python
st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")


def build_summary_digest(chart_df: pd.DataFrame) -> str:
    lines = ["Aggregate counts:"]
    for col in ["sentiment", "emotion", "category", "priority"]:
        counts = chart_df[col].value_counts().to_dict()
        counts_str = ", ".join(f"{k}: {v}" for k, v in counts.items())
        lines.append(f"- {col.capitalize()}: {counts_str}")
    lines.append("")
    lines.append("Individual review summaries:")
    for _, row in chart_df.iterrows():
        lines.append(f"- [{row['priority']} priority, {row['category']}] {row['summary']}")
    return "\n".join(lines)


st.title("Feedback Dashboard")
```

- [ ] **Step 3: Insert the Executive Summary section before the charts**

Find (this is the start of the `else:` branch that Task 1 already colored — find the line right after it):
```python
if chart_df.empty:
    st.info("All rows in this selection failed to analyze — no chart data to show.")
else:
    c1, c2 = st.columns(2)
```
Replace with:
```python
if chart_df.empty:
    st.info("All rows in this selection failed to analyze — no chart data to show.")
else:
    st.subheader("Executive Summary")
    if st.button("Generate Executive Summary"):
        gemini_client = GeminiClient(config.gemini_api_key, config.gemini_model)
        digest = build_summary_digest(chart_df)
        try:
            st.session_state["exec_summary"] = gemini_client.generate_executive_summary(digest)
        except Exception as e:
            st.error(f"Could not generate executive summary: {e}")

    if "exec_summary" in st.session_state:
        exec_summary = st.session_state["exec_summary"]
        st.markdown(exec_summary.summary)
        st.markdown("**Suggested next steps:**")
        for step in exec_summary.next_steps:
            st.markdown(f"- {step}")

    c1, c2 = st.columns(2)
```

- [ ] **Step 4: Verify the full button-click flow with a mocked Gemini call (no live API key needed)**

Run:
```bash
cd /Users/Pri/Documents/CustomerSupportAgent
source .venv/bin/activate
echo "GEMINI_API_KEY=dummy-key-for-boot-smoke-test" > .env

python3 -c "
from src.database import get_connection, init_db, insert_batch, insert_reviews
init_db('data/feedback.db')
conn = get_connection('data/feedback.db')
batch_id = insert_batch(conn, 'test.csv', 1)
insert_reviews(conn, batch_id, [
    {'original_text': 'Great app', 'sentiment': 'Positive', 'emotion': 'Happy', 'category': 'Other', 'priority': 'Low', 'summary': 'User is happy with the app.', 'suggested_reply': 'Thanks!'},
])
conn.close()

from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.schemas import ExecutiveSummary

fake_summary = ExecutiveSummary(
    summary='Overall sentiment is positive with no urgent issues.',
    next_steps=['Keep monitoring feedback', 'Highlight this in the next release notes', 'Share with the team'],
)

with patch('src.gemini_client.GeminiClient.generate_executive_summary', return_value=fake_summary):
    at = AppTest.from_file('pages/1_Dashboard.py')
    at.run()
    assert not at.exception, at.exception

    buttons = [b for b in at.button if b.label == 'Generate Executive Summary']
    assert len(buttons) == 1, f'expected 1 Generate Executive Summary button, found {len(buttons)}'

    buttons[0].click()
    at.run()
    assert not at.exception, at.exception

    markdown_text = ' '.join(m.value for m in at.markdown)
    assert 'Overall sentiment is positive' in markdown_text, 'summary text not rendered'
    assert 'Keep monitoring feedback' in markdown_text, 'next step not rendered'
    print('OK - button click, mocked Gemini call, and rendered output all verified')
"
rm -f data/feedback.db .env
```
Expected: `OK - button click, mocked Gemini call, and rendered output all verified`

- [ ] **Step 5: Commit**

```bash
git add pages/1_Dashboard.py
git commit -m "feat: add Executive Summary section to Dashboard"
```
