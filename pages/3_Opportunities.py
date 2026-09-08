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
