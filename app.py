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
    try:
        df = load_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read this CSV file: {e}")
        st.stop()
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

    if results_df.empty:
        st.info("No reviews were analyzed (all rows were empty or skipped).")
    else:
        st.subheader("Results")
        st.dataframe(results_df)

        chart_df = results_df[results_df["sentiment"] != "ERROR"]
        if chart_df.empty:
            st.info("All rows failed to analyze — no chart data to show.")
        else:
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

        csv_bytes = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download analyzed CSV", csv_bytes, "analyzed_reviews.csv", "text/csv")
