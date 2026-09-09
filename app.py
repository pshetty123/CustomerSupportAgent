from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import get_config
from src.csv_processor import get_text_columns, load_csv, process_reviews
from src.database import get_connection, get_today_usage, init_db, insert_batch, insert_reviews, record_usage
from src.gemini_client import GeminiClient
from src.chart_colors import TAXONOMY_COLORS
from src.theme import PLOTLY_DARK_LAYOUT, apply_theme, demo_walkthrough_html

DEMO_SAMPLE_DATASETS = {
    "Meridian Financial Firm": "meridian_financial_feedback.csv",
    "ABC AI Product Solutions": "abc_ai_product_feedback.csv",
    "PS Marketplace (like Amazon, Etsy)": "ps_marketplace_feedback.csv",
    "Y HealthCare": "y_healthcare_feedback.csv",
    "Large Tech Enterprise": "large_tech_enterprise_feedback.csv",
}

st.set_page_config(page_title="AI Customer Feedback Agent", page_icon="💬", layout="wide")
apply_theme()
st.title("AI Customer Feedback Agent")

try:
    config = get_config()
except ValueError as e:
    st.error(str(e))
    st.stop()

init_db(config.db_path)

if config.demo_mode:
    conn = get_connection(config.db_path)
    today_usage = get_today_usage(conn)
    conn.close()
    remaining = max(config.demo_daily_call_limit - today_usage, 0)

    st.markdown(demo_walkthrough_html(), unsafe_allow_html=True)

    st.caption(f"Demo mode — {remaining} of {config.demo_daily_call_limit} AI calls left today.")

    selected_label = st.selectbox(
        "Choose a sample dataset to analyze",
        list(DEMO_SAMPLE_DATASETS.keys()),
        index=None,
        placeholder="Select a dataset…",
    )
    uploaded_file = None
    df = None
    uploaded_filename = None
    if selected_label:
        sample_path = Path("samples") / DEMO_SAMPLE_DATASETS[selected_label]
        uploaded_filename = sample_path.name
        try:
            df = load_csv(sample_path)
        except Exception as e:
            st.error(f"Could not read this CSV file: {e}")
            st.stop()
else:
    uploaded_file = st.file_uploader("Upload a CSV of customer reviews", type=["csv"])
    df = None
    uploaded_filename = uploaded_file.name if uploaded_file is not None else None
    if uploaded_file is not None:
        try:
            df = load_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not read this CSV file: {e}")
            st.stop()

if df is not None:
    st.write("Preview:")
    st.dataframe(df.head())

    text_column = st.selectbox("Which column contains the review text?", get_text_columns(df))

    if config.demo_mode and today_usage >= config.demo_daily_call_limit:
        st.warning("Demo usage limit reached for today. Please check back tomorrow!")
    elif st.button("Analyze", type="primary"):
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
        batch_id = insert_batch(conn, uploaded_filename, len(results))
        insert_reviews(conn, batch_id, results)
        if config.demo_mode and results:
            record_usage(conn, len(results))
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
                st.plotly_chart(
                    px.pie(sentiment_counts, names="sentiment", values="count", title="Sentiment", color="sentiment", color_discrete_map=TAXONOMY_COLORS).update_layout(**PLOTLY_DARK_LAYOUT),
                    use_container_width=True,
                )
            with col2:
                priority_counts = chart_df["priority"].value_counts().reset_index()
                st.plotly_chart(
                    px.bar(priority_counts, x="priority", y="count", title="Priority", color="priority", color_discrete_map=TAXONOMY_COLORS).update_layout(**PLOTLY_DARK_LAYOUT),
                    use_container_width=True,
                )
            with col3:
                category_counts = chart_df["category"].value_counts().reset_index()
                st.plotly_chart(
                    px.bar(category_counts, x="category", y="count", title="Category", color="category", color_discrete_map=TAXONOMY_COLORS).update_layout(**PLOTLY_DARK_LAYOUT),
                    use_container_width=True,
                )

        csv_bytes = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download analyzed CSV", csv_bytes, "analyzed_reviews.csv", "text/csv")
