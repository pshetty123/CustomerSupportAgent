import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import get_config
from src.database import get_batches, get_connection, get_kpis, get_reviews, get_today_usage, init_db, record_usage
from src.chart_colors import TAXONOMY_COLORS
from src.gemini_client import GeminiClient
from src.text_utils import escape_markdown_dollars
from src.theme import PLOTLY_DARK_LAYOUT, apply_theme

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
apply_theme()


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
batch_options.update({f"{b['filename']} ({b['uploaded_at'][:10]}) #{b['id']}": b["id"] for b in batches})
selected_label = st.sidebar.selectbox("Batch", list(batch_options.keys()))
selected_batch_id = batch_options[selected_label]

reviews = get_reviews(conn, batch_id=selected_batch_id)
conn.close()

reviews_df = pd.DataFrame(reviews)
if reviews_df.empty:
    st.info("No reviews in the selected batch.")
    st.stop()
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

chart_df = reviews_df[reviews_df["sentiment"] != "ERROR"]
if chart_df.empty:
    st.info("All rows in this selection failed to analyze — no chart data to show.")
else:
    st.subheader("Executive Summary")

    demo_conn = get_connection(config.db_path) if config.demo_mode else None
    demo_usage = get_today_usage(demo_conn) if demo_conn else 0
    if demo_conn:
        demo_conn.close()

    if config.demo_mode and demo_usage >= config.demo_daily_call_limit:
        st.warning("Demo usage limit reached for today. Please check back tomorrow!")
    elif st.button("Generate Executive Summary"):
        gemini_client = GeminiClient(config.gemini_api_key, config.gemini_model)
        digest = build_summary_digest(chart_df)
        try:
            with st.spinner("Generating executive summary..."):
                st.session_state["exec_summary"] = gemini_client.generate_executive_summary(digest)
            if config.demo_mode:
                usage_conn = get_connection(config.db_path)
                record_usage(usage_conn, 1)
                usage_conn.close()
        except Exception as e:
            st.error(f"Could not generate executive summary: {e}")

    if "exec_summary" in st.session_state:
        exec_summary = st.session_state["exec_summary"]
        st.markdown(escape_markdown_dollars(exec_summary.summary))
        if exec_summary.next_steps:
            st.markdown("**Suggested next steps:**")
            for step in exec_summary.next_steps:
                st.markdown(f"- {escape_markdown_dollars(step)}")

    c1, c2 = st.columns(2)
    with c1:
        sentiment_counts = chart_df["sentiment"].value_counts().reset_index()
        st.plotly_chart(
            px.pie(sentiment_counts, names="sentiment", values="count", title="Sentiment Distribution", color="sentiment", color_discrete_map=TAXONOMY_COLORS).update_layout(**PLOTLY_DARK_LAYOUT),
            use_container_width=True,
        )
    with c2:
        priority_counts = chart_df["priority"].value_counts().reset_index()
        st.plotly_chart(
            px.bar(priority_counts, x="priority", y="count", title="Priority Breakdown", color="priority", color_discrete_map=TAXONOMY_COLORS).update_layout(**PLOTLY_DARK_LAYOUT),
            use_container_width=True,
        )

    c3, c4 = st.columns(2)
    with c3:
        category_counts = chart_df["category"].value_counts().reset_index()
        st.plotly_chart(
            px.bar(category_counts, x="category", y="count", title="Category Breakdown", color="category", color_discrete_map=TAXONOMY_COLORS).update_layout(**PLOTLY_DARK_LAYOUT),
            use_container_width=True,
        )
    with c4:
        emotion_counts = chart_df["emotion"].value_counts().reset_index()
        st.plotly_chart(
            px.bar(emotion_counts, x="emotion", y="count", title="Emotion Distribution", color="emotion", color_discrete_map=TAXONOMY_COLORS).update_layout(**PLOTLY_DARK_LAYOUT),
            use_container_width=True,
        )

    volume = chart_df.groupby("analyzed_date").size().reset_index(name="count")
    st.plotly_chart(
        px.line(volume, x="analyzed_date", y="count", title="Review Volume Over Time").update_layout(**PLOTLY_DARK_LAYOUT),
        use_container_width=True,
    )

st.subheader("Reviews")
st.dataframe(reviews_df)

csv_bytes = reviews_df.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered CSV", csv_bytes, "dashboard_reviews.csv", "text/csv")
