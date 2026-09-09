import pandas as pd
import streamlit as st

from src.config import get_config
from src.database import (
    ensure_demo_pillars,
    get_batches,
    get_connection,
    get_opportunities,
    get_pillars,
    get_reviews,
    get_today_usage,
    init_db,
    insert_opportunities,
    record_usage,
    update_opportunity,
)
from src.gemini_client import GeminiClient
from src.text_utils import escape_markdown_dollars
from src.theme import apply_theme, page_header_html

st.set_page_config(page_title="Opportunities", page_icon="🎯", layout="wide")
apply_theme()
st.markdown(page_header_html("Opportunities"), unsafe_allow_html=True)


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
if config.demo_mode:
    ensure_demo_pillars(conn)

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
    demo_conn = get_connection(config.db_path) if config.demo_mode else None
    demo_usage = get_today_usage(demo_conn) if demo_conn else 0
    if demo_conn:
        demo_conn.close()

    if config.demo_mode and demo_usage >= config.demo_daily_call_limit:
        st.warning("Demo usage limit reached for today. Please check back tomorrow!")
    elif st.button("Find Opportunities", type="primary"):
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
            if config.demo_mode:
                record_usage(insert_conn, 1)
            insert_conn.close()
            st.success(f"Found {len(proposal_dicts)} opportunities — see the review queue below.")
        except Exception as e:
            st.error(f"Could not generate opportunities: {e}")

conn = get_connection(config.db_path)
proposed = [o for o in get_opportunities(conn, status="proposed") if o["batch_id"] == selected_batch_id]
pillars_by_id = {p["id"]: p["name"] for p in pillars}
pillar_names = ["(no matching pillar)"] + [p["name"] for p in pillars]

if proposed:
    st.subheader("Review Queue")
    for opp in proposed:
        current_pillar_name = pillars_by_id.get(opp["pillar_id"], "(no matching pillar)")
        with st.expander(f"{escape_markdown_dollars(opp['title'])} — {escape_markdown_dollars(opp['theme'])}"):
            st.caption(f"Evidence: {opp['evidence_count']} reviews")
            st.write(escape_markdown_dollars(opp["rationale"]))
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
