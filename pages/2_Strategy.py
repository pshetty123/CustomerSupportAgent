import streamlit as st

from src.config import get_config
from src.database import delete_pillar, ensure_demo_pillars, get_connection, get_pillars, init_db, insert_pillar
from src.text_utils import escape_markdown_dollars
from src.theme import apply_theme

st.set_page_config(page_title="Strategy", page_icon="🧭", layout="wide")
apply_theme()
st.title("Strategy Pillars")

try:
    config = get_config()
except ValueError as e:
    st.error(str(e))
    st.stop()

init_db(config.db_path)
conn = get_connection(config.db_path)
if config.demo_mode:
    ensure_demo_pillars(conn)

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
            st.markdown(f"**{escape_markdown_dollars(pillar['name'])}**")
            st.write(escape_markdown_dollars(pillar["description"]))
        with col2:
            if st.button("Delete", key=f"delete_pillar_{pillar['id']}"):
                delete_conn = get_connection(config.db_path)
                delete_pillar(delete_conn, pillar["id"])
                delete_conn.close()
                st.rerun()
        st.divider()
