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
    sentiment_counts = reviews_df["sentiment"].value_counts().reset_index()
    st.plotly_chart(px.pie(sentiment_counts, names="sentiment", values="count", title="Sentiment Distribution"), use_container_width=True)
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
