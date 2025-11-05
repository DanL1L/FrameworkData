# pages/Sector_Monetar.py

import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Sector monetar", layout="wide")

# ========== STIL GENERAL ==========
st.markdown("""
<style>
    html, body, [class*="css"]  {
        font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
        color: #1a1a1a;
    }
    h1, h2, h3, h4 {
        font-family: 'Segoe UI Semibold', 'Roboto', sans-serif;
    }
    .stMarkdown p {
        font-size: 15px;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

st.title("Sectorul monetar")


# =====================================================
# 1. ÎNCĂRCAREA DATELOR
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

# Denumiri coloane (conform structurii date)
COL_YEAR = "An"
COL_GDP  = "PIB, mil lei"
COL_CPI  = "Indicele preţurilor de consum la sfîrşitul anului"
COL_RES  = "Rezerve valutare brute ale BNM, mil. USD"
COL_BASE = "Baza monetară, mil. lei"
COL_DEP  = "Depozite"

# Curățări de bază
df_mon[COL_YEAR] = pd.to_numeric(df_mon[COL_YEAR], errors="coerce").astype("Int64")

for col in [COL_GDP, COL_CPI, COL_RES, COL_BASE, COL_DEP]:
    df_mon[col] = pd.to_numeric(df_mon[col], errors="coerce")

df_mon = df_mon.dropna(subset=[COL_YEAR]).sort_values(COL_YEAR)

# =====================================================
# 2. FILTRU: AN
# =====================================================
years_available = sorted(df_mon[COL_YEAR].unique())
st.sidebar.header("Filtre")

selected_year = st.sidebar.selectbox(
    "Selectează anul:",
    options=years_available,
    index=len(years_available) - 1
)

row_sel = df_mon[df_mon[COL_YEAR] == selected_year]
if row_sel.empty:
    st.error("Nu există date pentru anul selectat.")
    st.stop()

row_sel = row_sel.iloc[0]

st.caption(f"Anul selectat: **{selected_year}**")

# =====================================================
# 3. CARDURI KPI – NIVELUL INDICATORILOR
# =====================================================
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("PIB", f"{row_sel[COL_GDP]:,.1f} mil. lei")
col2.metric("IPC (sfârșit de an)", f"{row_sel[COL_CPI]:.1f} %")
col3.metric("Rezerve valutare BNM", f"{row_sel[COL_RES]:,.1f} mil. USD")
col4.metric("Baza monetară", f"{row_sel[COL_BASE]:,.1f} mil. lei")
col5.metric("Depozite", f"{row_sel[COL_DEP]:,.1f}")

# =====================================================
# 4. TEXT DESCRIPTIV + COMPARAȚIE CU ANUL PRECEDENT
# =====================================================
prev_year = selected_year - 1
prev_row = df_mon[df_mon[COL_YEAR] == prev_year]

text_parts = []

def pct_change(curr, prev):
    return (curr - prev) / prev * 100 if (pd.notna(prev) and prev != 0) else None

if not prev_row.empty:
    prev_row = prev_row.iloc[0]

    gdp_chg  = pct_change(row_sel[COL_GDP],  prev_row[COL_GDP])
    cpi_chg  = row_sel[COL_CPI] - prev_row[COL_CPI]   # p.p.
    res_chg  = pct_change(row_sel[COL_RES],  prev_row[COL_RES])
    base_chg = pct_change(row_sel[COL_BASE], prev_row[COL_BASE])
    dep_chg  = pct_change(row_sel[COL_DEP],  prev_row[COL_DEP])

    text_parts.append(
        f"În **{selected_year}**, PIB-ul a constituit **{row_sel[COL_GDP]:,.1f} mil. lei**, "
        f"iar indicele prețurilor de consum la sfârșitul anului a fost de "
        f"**{row_sel[COL_CPI]:.1f}%**. Rezervele valutare brute ale BNM au însumat "
        f"**{row_sel[COL_RES]:,.1f} mil. USD**, baza monetară **{row_sel[COL_BASE]:,.1f} mil. lei**, "
        f"iar depozitele în sistemul bancar **{row_sel[COL_DEP]:,.1f}**."
    )

    text_parts.append(
        f"Comparativ cu **{prev_year}**, PIB-ul este "
        f"{'mai mare' if gdp_chg and gdp_chg > 0 else 'mai mic'} cu **{abs(gdp_chg):.1f}%**, "
        f"în timp ce indicele prețurilor de consum s-a modificat cu **{cpi_chg:+.1f} p.p.**. "
        f"Rezervele valutare au fost "
        f"{'mai ridicate' if res_chg and res_chg > 0 else 'mai reduse'} cu **{abs(res_chg):.1f}%**, "
        f"baza monetară cu **{base_chg:+.1f}%**, iar volumul depozitelor cu **{dep_chg:+.1f}%**."
    )
else:
    text_parts.append(
        f"În **{selected_year}**, PIB-ul a constituit **{row_sel[COL_GDP]:,.1f} mil. lei**, "
        f"indicele prețurilor de consum la sfârșitul anului **{row_sel[COL_CPI]:.1f}%**, "
        f"rezervele valutare brute ale BNM **{row_sel[COL_RES]:,.1f} mil. USD**, "
        f"baza monetară **{row_sel[COL_BASE]:,.1f} mil. lei**, iar depozitele "
        f"**{row_sel[COL_DEP]:,.1f}**."
    )
    text_parts.append(
        "Nu există date pentru anul precedent pentru a calcula variațiile anuale."
    )

st.markdown("\n\n".join(text_parts))

# =====================================================
# 5. EVOLUȚIA PIB / REZERVE / BAZA MONETARĂ / DEPOZITE
# =====================================================
st.markdown("---")
st.subheader("Evoluția PIB-ului și a principalelor agregate monetare")

df_plot = df_mon.copy()

# 5.1 PIB + depozite + baza monetară
fig_agg = px.line(
    df_plot,
    x=COL_YEAR,
    y=[COL_GDP, COL_BASE, COL_DEP],
    labels={"value": "mil. lei", "variable": "Indicator", COL_YEAR: "An"},
    template="simple_white",
)
fig_agg.update_traces(line=dict(width=3))
fig_agg.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.25,
        xanchor="center",
        x=0.5,
        font=dict(size=12),
    ),
    margin=dict(l=40, r=20, t=40, b=80),
)
st.plotly_chart(fig_agg, use_container_width=True)

# =====================================================
# 5.2–5.3 Rezerve valutare și Indicele prețurilor de consum (afișate una lângă alta)
# =====================================================

col_left, col_right = st.columns(2)

# --------- 5.2 Rezerve valutare brute ale BNM ----------
with col_left:
    st.markdown("#### Rezerve valutare brute ale BNM (mil. USD)")
    fig_res = px.line(
        df_plot,
        x=COL_YEAR,
        y=COL_RES,
        labels={COL_YEAR: "An", COL_RES: "mil. USD"},
        template="simple_white",
    )
    fig_res.update_traces(mode="lines+markers", line=dict(width=3))
    fig_res.update_layout(
        margin=dict(l=40, r=20, t=40, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
    )
    st.plotly_chart(fig_res, use_container_width=True)

# --------- 5.3 Indicele prețurilor de consum ----------
with col_right:
    st.markdown("#### Indicele prețurilor de consum la sfârșitul anului (%)")
    fig_cpi = px.line(
        df_plot,
        x=COL_YEAR,
        y=COL_CPI,
        labels={COL_YEAR: "An", COL_CPI: "%"},
        template="simple_white",
    )
    fig_cpi.update_traces(mode="lines+markers", line=dict(width=3))
    fig_cpi.update_layout(
        margin=dict(l=40, r=20, t=40, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
    )
    st.plotly_chart(fig_cpi, use_container_width=True)

