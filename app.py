import streamlit as st

st.set_page_config(
    page_title="Macro",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.styles import inject_styles
from utils.state import init_state
from pages import (
    page_overview,
    page_real,
    page_extern,
    page_monetar,
    page_public,
    page_social,
    page_surse,
)

inject_styles()
init_state()

PAGES = {
    "Indicatorii MacroEconomici": {"icon": "", "module": page_overview,  "color": "#185FA5"},
    "Sectorul Real":              {"icon": "", "module": page_real,      "color": "#1D9E75"},
    "Sectorul Extern":            {"icon": "", "module": page_extern,    "color": "#534AB7"},
    "Sectorul Monetar":           {"icon": "", "module": page_monetar,   "color": "#993556"},
    "Sectorul Public":            {"icon": "", "module": page_public,    "color": "#854F0B"},
    "Sectorul Social":            {"icon": "", "module": page_social,    "color": "#0F6E56"},
    #   "Surse & API":                {"icon": "", "module": page_surse,    "color": "#444441"},
}

with st.sidebar:
    st.markdown("""
     <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }

        /* Elimină spațiul gol de sus */
        [data-testid="stSidebarNavSeparator"] {
            display: none;
        }
    </style>           
    <div class="sidebar-brand">
        <div class="sidebar-logo">MDED</div>
        <div class="sidebar-subtitle">Indicatorii Macroeconomici<br/>ai Republicii Moldova</div>
    </div>
    """, unsafe_allow_html=True)

    # st.markdown('<div class="sidebar-nav-label">SECTOARE</div>', unsafe_allow_html=True)

    for name, meta in PAGES.items():
        active = st.session_state.get("current_page") == name
        cls = "nav-btn nav-btn-active" if active else "nav-btn"
        if st.button(
            f"{meta['icon']}  {name}",
            key=f"nav_{name}",
            use_container_width=True,
        ):
            st.session_state["current_page"] = name
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="padding:10px 16px;font-size:10px;color:#1a498d;line-height:1.7">
    DAPM — Directia Analiza<br>si Prognoza Macroeconomica<br>
    <span style="color:#1a3a5a">Ministerul Dezvoltarii Economice si Digitalizării</span>
    </div>
    """, unsafe_allow_html=True)

current = st.session_state.get("current_page", "Indicatorii MacroEconomici")
PAGES[current]["module"].render()
