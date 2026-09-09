import streamlit as st

PLOTLY_DARK_LAYOUT = {
    "paper_bgcolor": "#12181F",
    "plot_bgcolor": "#12181F",
    "font_color": "#E7EEF0",
    "title_font_color": "#E7EEF0",
    "legend_font_color": "#C4CCD1",
    "xaxis": {"gridcolor": "#1E2530", "linecolor": "#1E2530"},
    "yaxis": {"gridcolor": "#1E2530", "linecolor": "#1E2530"},
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

[data-testid="stMetric"] {
    background-color: #12181F;
    border: 1px solid #1E2530;
    border-radius: 12px;
    padding: 16px 20px;
}

[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace;
}

[data-testid="stExpander"] {
    background-color: #12181F;
    border: 1px solid #1E2530;
    border-radius: 12px;
}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
