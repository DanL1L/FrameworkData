import streamlit as st

def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .page-header-title {
    font-size: 28.6px; /* era 26px */
    }

    .kpi-value {
        font-size: 26.4px; /* era 24px */
    }

    .kpi-label {
        font-size: 11.5px; /* era 10.5px */
    }

    .chart-card-title {
        font-size: 13.2px; /* era 12px */
    }

    .stDataFrame {
        font-size: 13.2px !important; /* era 12px */
    }

    /* ── Hide default Streamlit chrome ── */
    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 2.5rem; padding-bottom: 2rem; max-width: 95% !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: white !important;
        border-right: 1px solid #1a2d45;
    }
    [data-testid="stSidebar"] > div { padding: 0; }

    .sidebar-brand {
        padding: 24px 20px 16px;
        border-bottom: 1px solid #1a2d45;
        margin-bottom: 8px;
    }
    .sidebar-logo {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 22px;
        font-weight: 500;
        color: #1a498d;
        letter-spacing: 0.12em;
        margin-bottom: 6px;
    }
    .sidebar-subtitle {
        font-size: 11px;
        color: #4a6080;
        line-height: 1.5;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .sidebar-nav-label {
        font-size: 10px;
        color: #2d4a6a;
        letter-spacing: 0.15em;
        font-weight: 600;
        padding: 8px 20px 4px;
        text-transform: uppercase;
    }
    .sidebar-source-item {
        font-size: 11px;
        color: #3a5570;
        padding: 3px 20px;
        line-height: 1.8;
    }

    /* Nav buttons */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        color: #5a7a9a !important;
        font-size: 12.5px !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 400 !important;
        padding: 8px 20px !important;
        text-align: left !important;
        width: 100% !important;
        transition: all 0.15s ease;
        letter-spacing: 0.01em;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #1a498d !important;
        color: white !important;
    }
    [data-testid="stSidebar"] .stButton > button:focus {
        background: #1a498d !important;
        color: white !important;
        border-left: 2px solid #5DCAA5 !important;
        box-shadow: none !important;
    }

    /* ── Page header ── */
    .page-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        padding-bottom: 16px;
        border-bottom: 1px solid #e8e4dc;
        margin-bottom: 20px;
    }
    .page-header-title {
        font-size: 26px;
        font-weight: 600;
        color: #0C1929;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }
    .page-header-sub {
        font-size: 12px;
        color: #888780;
        margin-top: 4px;
        font-family: 'IBM Plex Mono', monospace;
    }
    .page-header-badge {
        font-size: 10px;
        font-family: 'IBM Plex Mono', monospace;
        background: #E1F5EE;
        color: #0F6E56;
        padding: 4px 10px;
        border-radius: 3px;
        border: 1px solid #9FE1CB;
        margin-top: 4px;
    }

    /* ── KPI cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background: #fff;
        border: 1px solid #e8e4dc;
        border-radius: 6px;
        padding: 14px 16px;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
    }
    .kpi-label {
        font-size: 10.5px;
        color: #888780;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 8px;
        font-family: 'IBM Plex Mono', monospace;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 600;
        color: #0C1929;
        letter-spacing: -0.02em;
        line-height: 1;
        margin-bottom: 6px;
    }
    .kpi-unit {
        font-size: 13px;
        color: #888780;
        font-weight: 400;
    }
    .kpi-delta-pos { font-size: 11px; color: #1D9E75; font-family: 'IBM Plex Mono', monospace; }
    .kpi-delta-neg { font-size: 11px; color: #A32D2D; font-family: 'IBM Plex Mono', monospace; }
    .kpi-delta-neu { font-size: 11px; color: #888780; font-family: 'IBM Plex Mono', monospace; }

    /* ── Chart cards ── */
    .chart-card {
        background: #fff;
        border: 1px solid #e8e4dc;
        border-radius: 6px;
        padding: 16px 18px;
        margin-bottom: 14px;
    }
    .chart-card-title {
        font-size: 12px;
        font-weight: 600;
        color: #0C1929;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }
    .chart-source {
        font-size: 10px;
        color: #b4b2a9;
        font-family: 'IBM Plex Mono', monospace;
        margin-top: 6px;
    }

    /* ── Table ── */
    .stDataFrame { font-size: 12px !important; }

    /* ── Divider ── */
    hr { border: none; border-top: 1px solid #e8e4dc; margin: 16px 0; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #e8e4dc;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 12px !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        color: #888780 !important;
        padding: 8px 18px !important;
        border-radius: 0 !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: #185FA5 !important;
        border-bottom: 2px solid #d2d91a !important;
        font-weight: 500 !important;
    }

    /* ── Metric overrides ── */
    [data-testid="stMetric"] {
        background: #f9f8f5;
        border: 1px solid #e8e4dc;
        border-radius: 6px;
        padding: 12px 14px;
    }
    [data-testid="stMetricLabel"] { font-size: 10.5px !important; color: #888780 !important; }
    [data-testid="stMetricValue"] { font-size: 22px !important; color: #0C1929 !important; font-weight: 600 !important; }

    /* ── Selectbox / filters ── */
    .stSelectbox label { font-size: 11px !important; color: #888780 !important; }

    /* ── Upload ── */
    [data-testid="stFileUploader"] {
        border: 1px dashed #b4b2a9 !important;
        border-radius: 6px !important;
        background: #fafaf8 !important;
        padding: 8px !important;
    }

    /* ── Color accent strips per sector ── */
    .accent-blue::before   { background: #185FA5; }
    .accent-green::before  { background: #1D9E75; }
    .accent-purple::before { background: #534AB7; }
    .accent-pink::before   { background: #993556; }
    .accent-amber::before  { background: #854F0B; }
    .accent-teal::before   { background: #0F6E56; }
    </style>
    """, unsafe_allow_html=True)
