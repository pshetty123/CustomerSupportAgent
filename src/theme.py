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


_STEPS = [
    {
        "number": "01",
        "title": "Strategic Pillars",
        "badge": "Pre-work — already done",
        "description": "Three default pillars are pre-loaded. Peek at them, edit them, or add your own before moving on.",
        "links": [("Open Strategy", "Strategy")],
    },
    {
        "number": "02",
        "title": "Upload Feedback",
        "badge": "~1 minute",
        "description": "Pick a sample dataset below and click Analyze.",
        "links": [],
    },
    {
        "number": "03",
        "title": "See It In Action",
        "badge": "The payoff",
        "description": "Check the Dashboard for an AI summary, then Opportunities for AI-proposed, strategy-aligned action.",
        "links": [("Open Dashboard", "Dashboard"), ("Open Opportunities", "Opportunities")],
    },
]

_ARROW_SVG = (
    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;">'
    '<path d="M7 17L17 7M17 7H8M17 7V16" stroke="#E8002D" stroke-width="2.2" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def _step_card_html(step: dict) -> str:
    links_html = "".join(
        f'<a href="{href}" target="_self" class="demo-step-cta">{label} {_ARROW_SVG}</a>'
        for label, href in step["links"]
    )
    return f"""
    <div class="demo-step-card">
        <div class="demo-step-number">{step["number"]}</div>
        <div class="demo-step-body">
            <div class="demo-step-head">
                <span class="demo-step-title">{step["title"]}</span>
                <span class="demo-step-badge">{step["badge"]}</span>
            </div>
            <div class="demo-step-desc">{step["description"]}</div>
        </div>
        <div class="demo-step-links">{links_html}</div>
    </div>
    """


def demo_walkthrough_html() -> str:
    cards = "".join(_step_card_html(step) for step in _STEPS)
    return f"""
    <style>
    .demo-step-eyebrow {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        letter-spacing: 0.2em;
        color: #E8002D;
        font-weight: 700;
        text-transform: uppercase;
    }}
    .demo-step-heading {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 20px;
        color: #ffffff;
        margin: 4px 0 6px 0;
    }}
    .demo-step-subhead {{
        color: #C4CCD1;
        font-size: 14px;
        line-height: 1.6;
        max-width: 640px;
        margin-bottom: 16px;
    }}
    .demo-step-card {{
        border: 1px solid rgba(255,255,255,0.15);
        background: #141414;
        border-radius: 12px;
        padding: 18px 22px;
        display: flex;
        align-items: center;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 12px;
        transition: border-color 0.2s ease;
    }}
    .demo-step-card:hover {{
        border-color: rgba(255,255,255,0.3);
    }}
    .demo-step-number {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 28px;
        color: rgba(232,0,45,0.7);
        min-width: 44px;
    }}
    .demo-step-body {{
        flex: 1;
        min-width: 220px;
    }}
    .demo-step-head {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 4px;
    }}
    .demo-step-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 16px;
        color: #ffffff;
    }}
    .demo-step-badge {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 2px 10px;
        border-radius: 999px;
        border: 1px solid rgba(34,211,238,0.4);
        color: #67e8f9;
        background: rgba(6,182,212,0.1);
        font-weight: 600;
    }}
    .demo-step-desc {{
        color: #C4CCD1;
        font-size: 13px;
        line-height: 1.5;
    }}
    .demo-step-links {{
        flex-shrink: 0;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .demo-step-cta {{
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.05em;
        color: rgba(255,255,255,0.9);
        transition: border-color 0.2s ease, color 0.2s ease;
        white-space: nowrap;
    }}
    .demo-step-cta:hover {{
        border-color: #E8002D;
        color: #ffffff;
    }}
    .st-key-dataset-picker {{
        border: 2px solid #E8002D !important;
        background: rgba(232,0,45,0.06);
        border-radius: 12px;
        box-shadow: 0 0 28px rgba(232,0,45,0.18);
        padding: 6px 6px 2px 6px;
        margin-top: 6px;
        margin-bottom: 6px;
    }}
    .dataset-picker-eyebrow {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        letter-spacing: 0.15em;
        color: #E8002D;
        font-weight: 700;
        text-transform: uppercase;
    }}
    </style>
    <div>
        <div class="demo-step-eyebrow">HOW TO TRY IT</div>
        <div class="demo-step-heading">Three steps, no setup required</div>
        <div class="demo-step-subhead">Everything you need is already here — default strategy pillars and sample feedback datasets included.</div>
        {cards}
    </div>
    """


def dataset_picker_eyebrow_html() -> str:
    return '<div class="dataset-picker-eyebrow">👉 Step 02 — Choose Your Dataset to Begin</div>'
