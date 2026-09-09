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

ACCENT_BLUE = "#3B82F6"
ACCENT_RED = "#E8002D"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Space Grotesk', sans-serif;
}}

[data-testid="stMetric"] {{
    background-color: #12181F;
    border: 1px solid #1E2530;
    border-radius: 12px;
    padding: 16px 20px;
}}

[data-testid="stMetricValue"] {{
    font-family: 'JetBrains Mono', monospace;
}}

[data-testid="stExpander"] {{
    background-color: #12181F;
    border: 1px solid #1E2530;
    border-radius: 12px;
}}

.page-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}}
.page-header-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {ACCENT_BLUE};
    font-weight: 700;
}}

.demo-intro {{
    border-left: 3px solid {ACCENT_RED};
    padding: 2px 0 2px 16px;
    margin-bottom: 18px;
}}
.demo-step-eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.2em;
    color: {ACCENT_RED};
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
    font-size: 16px;
    color: rgba(255,255,255,0.55);
    min-width: 44px;
    height: 44px;
    width: 44px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.2);
    background: #1A1A1A;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
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
    border: 1px solid rgba(255,255,255,0.2);
    color: rgba(255,255,255,0.6);
    background: rgba(255,255,255,0.05);
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
    border-color: {ACCENT_BLUE};
    color: #ffffff;
}}

/* Active step (Step 02) — the real Streamlit container the picker lives in */
.st-key-step-02-card {{
    border: 1px solid {ACCENT_BLUE} !important;
    background: #141414;
    border-radius: 12px;
    box-shadow: 0 0 28px rgba(59,130,246,0.22);
    padding: 6px 22px 18px 22px !important;
    margin-bottom: 12px;
}}
.demo-step-number-active {{
    background: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
    color: #ffffff;
    box-shadow: 0 0 16px rgba(59,130,246,0.5);
}}
.demo-step-badge-active {{
    border-color: rgba(59,130,246,0.5);
    background: rgba(59,130,246,0.12);
    color: #93c5fd;
}}

.st-key-dataset-picker {{
    border: 1px dashed rgba(59,130,246,0.5) !important;
    background: rgba(59,130,246,0.05);
    border-radius: 10px;
    padding: 14px 16px 4px 16px;
    margin-top: 10px;
}}
.dataset-picker-eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    color: {ACCENT_BLUE};
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 4px;
}}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


_TERMINAL_ICON_SVG = (
    f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none">'
    f'<rect x="2.5" y="4.5" width="19" height="15" rx="2.5" stroke="{ACCENT_BLUE}" stroke-width="1.6"/>'
    f'<path d="M6.5 9.5L10 12L6.5 14.5" stroke="{ACCENT_BLUE}" stroke-width="1.6" '
    f'stroke-linecap="round" stroke-linejoin="round"/>'
    f'<path d="M12.5 14.5H17" stroke="{ACCENT_BLUE}" stroke-width="1.6" stroke-linecap="round"/>'
    f"</svg>"
)


def page_header_html(title: str) -> str:
    return (
        f'<div class="page-header">{_TERMINAL_ICON_SVG}'
        f'<span class="page-header-title">{title}</span></div>'
    )


_STEPS = [
    {
        "number": "01",
        "title": "Strategic Pillars",
        "badge": "Pre-work — already done",
        "description": "Three default pillars are pre-loaded. Peek at them, edit them, or add your own before moving on.",
        "links": [("Open Strategy", "Strategy")],
    },
    {
        "number": "03",
        "title": "See It In Action",
        "badge": "The payoff",
        "description": "Check the Dashboard for an AI summary, then Opportunities for AI-proposed, strategy-aligned action.",
        "links": [("Open Dashboard", "Dashboard"), ("Open Opportunities", "Opportunities")],
    },
]

STEP_02 = {
    "number": "02",
    "title": "Upload Feedback",
    "badge": "~1 minute",
    "description": "Pick a sample dataset below and click Analyze.",
}

_ARROW_SVG = (
    f'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;">'
    f'<path d="M7 17L17 7M17 7H8M17 7V16" stroke="{ACCENT_BLUE}" stroke-width="2.2" '
    f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
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


def demo_intro_html() -> str:
    return """
    <div class="demo-intro">
        <div class="demo-step-eyebrow">HOW TO TRY IT</div>
        <div class="demo-step-heading">Three steps, no setup required</div>
        <div class="demo-step-subhead">Everything you need is already here — default strategy pillars and sample feedback datasets included.</div>
    </div>
    """


def demo_step_html(step_number: str) -> str:
    """Render step 01 or 03 as a standalone (inactive) card."""
    step = next(s for s in _STEPS if s["number"] == step_number)
    return _step_card_html(step)


def demo_step_02_header_html() -> str:
    """Active-step (blue) header content for Step 02, meant to sit inside a real st.container."""
    return f"""
    <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;padding-top:16px;">
        <div class="demo-step-number demo-step-number-active">{STEP_02["number"]}</div>
        <div class="demo-step-body">
            <div class="demo-step-head">
                <span class="demo-step-title">{STEP_02["title"]}</span>
                <span class="demo-step-badge demo-step-badge-active">{STEP_02["badge"]}</span>
            </div>
            <div class="demo-step-desc">{STEP_02["description"]}</div>
        </div>
    </div>
    """


def dataset_picker_eyebrow_html() -> str:
    return '<div class="dataset-picker-eyebrow">👉 STEP 02 — CHOOSE YOUR DATASET TO BEGIN</div>'
