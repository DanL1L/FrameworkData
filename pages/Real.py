# pages/Sector_Real.py

import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Sector real", layout="wide")

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

st.title("Sectorul real")

# =====================================================
# 1. ÎNCĂRCAREA DATELOR
# =====================================================
# Ajustează numele fișierului / foii de calcul după cum ai datele salvate
file_path = os.path.join("data", "Real.xlsx")

try:
    df_real = pd.read_excel(file_path, sheet_name="Real")
except FileNotFoundError:
    st.error(
        f"Fișierul nu a fost găsit: `{file_path}`.\n"
        f"Verifică să fie în folderul `data/` sau actualizează calea / numele fișierului."
    )
    st.stop()

# Denumiri coloane – adaptează dacă în Excel sunt puțin diferite
COL_YEAR = "An"
COL_IND  = "Producția industrială, mil. lei"
COL_AGR  = "Producția agricolă, mil. lei"
COL_FDI  = "Investiţiile directe acumulate în Republica Moldova (stoc) (MBP6), mil. USD"

# Curățări de bază
df_real[COL_YEAR] = pd.to_numeric(df_real[COL_YEAR], errors="coerce").astype("Int64")

for col in [COL_IND, COL_AGR, COL_FDI]:
    df_real[col] = pd.to_numeric(df_real[col], errors="coerce")

df_real = df_real.dropna(subset=[COL_YEAR]).sort_values(COL_YEAR)

# =====================================================
# 2. FILTRU: AN
# =====================================================
years_available = sorted(df_real[COL_YEAR].unique())
st.sidebar.header("Filtre")

selected_year = st.sidebar.selectbox(
    "Selectează anul:",
    options=years_available,
    index=len(years_available) - 1
)

row_sel = df_real[df_real[COL_YEAR] == selected_year]
if row_sel.empty:
    st.error("Nu există date pentru anul selectat.")
    st.stop()

row_sel = row_sel.iloc[0]
st.caption(f"Anul selectat: **{selected_year}**")

# =====================================================
# 3. CARDURI KPI – NIVELUL INDICATORILOR
# =====================================================
col1, col2, col3 = st.columns(3)

col1.metric(
    "Producția industrială",
    f"{row_sel[COL_IND]:,.1f} mil. lei" if pd.notna(row_sel[COL_IND]) else "n/d"
)
col2.metric(
    "Producția agricolă",
    f"{row_sel[COL_AGR]:,.1f} mil. lei" if pd.notna(row_sel[COL_AGR]) else "n/d"
)
col3.metric(
    "Investiții directe acumulate (stoc)",
    f"{row_sel[COL_FDI]:,.1f} mil. USD" if pd.notna(row_sel[COL_FDI]) else "n/d"
)

# =====================================================
# 4. TEXT DESCRIPTIV + COMPARAȚIE CU ANUL PRECEDENT
# =====================================================
prev_year = selected_year - 1
prev_row = df_real[df_real[COL_YEAR] == prev_year]

text_parts = []

def pct_change(curr, prev):
    return (curr - prev) / prev * 100 if (pd.notna(prev) and prev != 0) else None

if not prev_row.empty:
    prev_row = prev_row.iloc[0]

    ind_chg = pct_change(row_sel[COL_IND], prev_row[COL_IND])
    agr_chg = pct_change(row_sel[COL_AGR], prev_row[COL_AGR])
    fdi_chg = pct_change(row_sel[COL_FDI], prev_row[COL_FDI])

    text_parts.append(
        f"În **{selected_year}**, producția industrială a constituit "
        f"**{row_sel[COL_IND]:,.1f} mil. lei**, iar producția agricolă "
        f"**{row_sel[COL_AGR]:,.1f} mil. lei**. "
        f"Stocul investițiilor directe acumulate în Republica Moldova (MBP6) "
        f"a atins **{row_sel[COL_FDI]:,.1f} mil. USD**."
    )

    text_parts.append(
        f"Comparativ cu **{prev_year}**, producția industrială este "
        f"{'mai mare' if ind_chg and ind_chg > 0 else 'mai mică'} cu "
        f"**{abs(ind_chg):.1f}%**, iar producția agricolă "
        f"{'a crescut' if agr_chg and agr_chg > 0 else 'a scăzut'} cu "
        f"**{abs(agr_chg):.1f}%**. Stocul investițiilor directe "
        f"{'este mai ridicat' if fdi_chg and fdi_chg > 0 else 'este mai redus'} "
        f"cu **{abs(fdi_chg):.1f}%** față de anul precedent."
    )
else:
    text_parts.append(
        f"În **{selected_year}**, producția industrială a constituit "
        f"**{row_sel[COL_IND]:,.1f} mil. lei**, producția agricolă "
        f"**{row_sel[COL_AGR]:,.1f} mil. lei**, iar stocul investițiilor directe "
        f"acumulate **{row_sel[COL_FDI]:,.1f} mil. USD**."
    )
    text_parts.append(
        "Nu există date pentru anul precedent pentru a calcula variațiile anuale."
    )

st.markdown("\n\n".join(text_parts))

# =====================================================
# 5. EVOLUȚIA INDICATORILOR – LAYOUT PE DOUĂ COLOANE
# =====================================================
st.markdown("---")
st.subheader("Evoluția principalilor indicatori ai sectorului real")

df_plot = df_real.copy()

col_left, col_right = st.columns(2)

# 5.1 Producția industrială vs agricolă
with col_left:
    st.markdown("#### Producția industrială și agricolă (mil. lei)")
    fig_prod = px.line(
        df_plot,
        x=COL_YEAR,
        y=[COL_IND, COL_AGR],
        labels={
            COL_YEAR: "An",
            "value": "mil. lei",
            "variable": "Indicator"
        },
        template="simple_white",
    )
    fig_prod.update_traces(mode="lines+markers", line=dict(width=3))
    fig_prod.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(l=40, r=20, t=40, b=60),
    )
    st.plotly_chart(fig_prod, use_container_width=True)

# 5.2 Investiții directe acumulate
with col_right:
    st.markdown("#### Investiții directe acumulate (stoc, MBP6) – mil. USD")
    fig_fdi = px.line(
        df_plot,
        x=COL_YEAR,
        y=COL_FDI,
        labels={COL_YEAR: "An", COL_FDI: "mil. USD"},
        template="simple_white",
    )
    fig_fdi.update_traces(mode="lines+markers", line=dict(width=3))
    fig_fdi.update_layout(
        margin=dict(l=40, r=20, t=40, b=60),
    )
    st.plotly_chart(fig_fdi, use_container_width=True)
