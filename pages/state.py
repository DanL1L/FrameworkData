import streamlit as st

def init_state():
    defaults = {
        "current_page": "Indicatorii MacroEconomici",
        "uploaded_file": None,
        "year_range": (2019, 2024),
        "freq": "Anual",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def page_header(title: str, subtitle: str, source: str, accent: str = "blue"):
    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-header-title">{title}</div>
            <div class="page-header-sub">{subtitle}</div>
        </div>
        <div class="page-header-badge">Sursa: {source}</div>
    </div>
    """, unsafe_allow_html=True)

def kpi_card(label: str, value: str, unit: str, delta: str, positive: bool = True, accent: str = "blue"):
    delta_cls = "kpi-delta-pos" if positive else "kpi-delta-neg"
    arrow = "▲" if positive else "▼"
    return f"""
    <div class="kpi-card accent-{accent}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value} <span class="kpi-unit">{unit}</span></div>
        <div class="{delta_cls}">{arrow} {delta}</div>
    </div>"""

def kpi_row(cards_html: list):
    inner = "".join(cards_html)
    st.markdown(f'<div class="kpi-grid">{inner}</div>', unsafe_allow_html=True)

def chart_card_start(title: str, source: str = ""):
    st.markdown(f"""
    <div class="chart-card">
        <div class="chart-card-title">{title}</div>
    """, unsafe_allow_html=True)

def chart_card_end(source: str = ""):
    if source:
        st.markdown(f'<div class="chart-source">Sursa: {source}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
