# pages/Sector_Monetar.py

import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Sector monetar", layout="wide")

# =========================
# SETARE: date fictive vs Excel
# =========================
USE_FAKE_DATA = True  # <- când vei avea Excel complet, pune False

# ========== STIL GENERAL ==========
st.markdown("""
<style>
    html, body, [class*="css"]  {
        font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
        color: #1a1a1a;
    }
    h1, h2, h3, h4 { font-family: 'Segoe UI Semibold', 'Roboto', sans-serif; }
    .stMarkdown p { font-size: 15px; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

st.title("Sectorul monetar")

# =====================================================
# 1) DATE FICTIVE (TEMPORAR)
# =====================================================
COL_YEAR = "An"
COL_GDP  = "PIB, mil lei"
COL_INFL = "Rata inflației (%)"
COL_RES  = "Rezerve valutare brute ale BNM, mil. USD"
COL_CPI  = "Indicele preţurilor de consum la sfîrşitul anului"
COL_NEW_CRED = "Credite noi acordate"
COL_NEW_DEP  = "Depozite noi"

COL_BASE = "Baza monetară, mil. lei"
COL_DEP  = "Depozite"

if USE_FAKE_DATA:
    years = list(range(2014, 2026))
    df_mon = pd.DataFrame({
        COL_YEAR: years,
        COL_GDP:  [170000, 178000, 185000, 193000, 205000, 212000, 220000, 235000, 250000, 265000, 280000, 295000],
        COL_INFL: [4.6, 6.4, 2.4, 6.6, 0.5, 4.8, 3.8, 5.1, 13.9, 4.2, 4.8, 5.6],
        COL_RES:  [2200, 2400, 2550, 2700, 2900, 3050, 3300, 3400, 3700, 4100, 4500, 4800],
        COL_CPI:  [104.6, 106.4, 102.4, 106.6, 100.5, 104.8, 103.8, 105.1, 113.9, 104.2, 104.8, 105.6],
        COL_NEW_CRED: [18000, 19000, 20000, 21500, 23000, 24500, 26000, 27500, 29500, 31000, 33000, 35000],
        COL_NEW_DEP:  [16000, 17000, 18000, 19500, 21000, 22500, 24000, 25500, 28000, 29500, 31500, 33500],
        COL_BASE: [24000, 25500, 26500, 28000, 29500, 31000, 33000, 34500, 36000, 38000, 40000, 42000],
        COL_DEP:  [52000, 54500, 56500, 59000, 61500, 64000, 67000, 70000, 73000, 77000, 81000, 85000],
    })
else:
    # =====================================================
    # 2) ÎNCĂRCARE DIN EXCEL (CÂND VEI FI GATA)
    # =====================================================
    file_path = os.path.join("data", "Test_Data_Sector_Monetar.xlsx")
    try:
        df_mon = pd.read_excel(file_path, sheet_name="Monetar")
    except FileNotFoundError:
        st.error(
            f"Fișierul nu a fost găsit: `{file_path}`.\n"
            f"Verifică să fie în folderul `data/` sau actualizează calea / numele fișierului."
        )
        st.stop()

    # aici vei ajusta numele coloanelor exact cum sunt în Excel și conversiile numerice

# =====================================================
# 3) FILTRU: AN
# =====================================================
years_available = sorted(df_mon[COL_YEAR].unique())
st.sidebar.header("Filtre")

selected_year = st.sidebar.selectbox(
    "Selectează anul:",
    options=years_available,
    index=len(years_available) - 1
)

row_sel = df_mon[df_mon[COL_YEAR] == selected_year].iloc[0]
st.caption(f"Anul selectat: **{selected_year}**")

# =====================================================
# 4) KPI
# =====================================================
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("PIB", f"{row_sel[COL_GDP]:,.0f} mil. lei")
c2.metric("Inflație", f"{row_sel[COL_INFL]:,.1f} %")
c3.metric("Rezerve BNM", f"{row_sel[COL_RES]:,.0f} mil. USD")
c4.metric("Baza monetară", f"{row_sel[COL_BASE]:,.0f} mil. lei")
c5.metric("Depozite (stoc)", f"{row_sel[COL_DEP]:,.0f} mil. lei")

st.markdown("---")

# =====================================================
# 5) DIAGRAMA 1: INFLAȚIA (SUS, FULL WIDTH)
# =====================================================
# st.markdown("### Rata inflației (%)")
# fig_infl = px.line(df_mon, x=COL_YEAR, y=COL_INFL, template="simple_white",
#                    labels={COL_YEAR: "An", COL_INFL: "%"})
# fig_infl.update_traces(mode="lines+markers", line=dict(width=3))
# fig_infl.update_layout(margin=dict(l=40, r=20, t=40, b=60))
# st.plotly_chart(fig_infl, use_container_width=True)

# st.markdown("---")

# =====================================================
# 6) REZERVE (STÂNGA) + IPC (DREAPTA)
# =====================================================
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Rezerve valutare brute ale BNM (mil. USD)")
    fig_res = px.line(df_mon, x=COL_YEAR, y=COL_RES, template="simple_white",
                      labels={COL_YEAR: "An", COL_RES: "mil. USD"})
    fig_res.update_traces(mode="lines+markers", line=dict(width=3))
    fig_res.update_layout(margin=dict(l=40, r=20, t=40, b=60))
    st.plotly_chart(fig_res, use_container_width=True)

with col_right:
    st.markdown("#### IPC la sfârșitul anului (%)")
    fig_cpi = px.line(df_mon, x=COL_YEAR, y=COL_CPI, template="simple_white",
                      labels={COL_YEAR: "An", COL_CPI: "%"})
    fig_cpi.update_traces(mode="lines+markers", line=dict(width=3))
    fig_cpi.update_layout(margin=dict(l=40, r=20, t=40, b=60))
    st.plotly_chart(fig_cpi, use_container_width=True)

st.markdown("---")

# =====================================================
# 7) CREDITE NOI (STÂNGA) + DEPOZITE NOI (DREAPTA)
# =====================================================
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.markdown("#### Credite noi acordate")
    fig_new_cred = px.line(df_mon, x=COL_YEAR, y=COL_NEW_CRED, template="simple_white",
                           labels={COL_YEAR: "An", COL_NEW_CRED: "valoare"})
    fig_new_cred.update_traces(mode="lines+markers", line=dict(width=3))
    fig_new_cred.update_layout(margin=dict(l=40, r=20, t=40, b=60))
    st.plotly_chart(fig_new_cred, use_container_width=True)

with col_right2:
    st.markdown("#### Depozite noi")
    fig_new_dep = px.line(df_mon, x=COL_YEAR, y=COL_NEW_DEP, template="simple_white",
                          labels={COL_YEAR: "An", COL_NEW_DEP: "valoare"})
    fig_new_dep.update_traces(mode="lines+markers", line=dict(width=3))
    fig_new_dep.update_layout(margin=dict(l=40, r=20, t=40, b=60))
    st.plotly_chart(fig_new_dep, use_container_width=True)
