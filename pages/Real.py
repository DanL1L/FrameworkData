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
# 1. ÎNCĂRCAREA DATELOR – SECTOR REAL (ANUAL)
# =====================================================
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

# (opțional, pentru viitor)
COL_TRADE = "Comerț intern, mil. lei"  # dacă vei adăuga ulterior în Real.xlsx

# Curățări de bază – sector real
df_real[COL_YEAR] = pd.to_numeric(df_real[COL_YEAR], errors="coerce").astype("Int64")

numeric_cols_real = [c for c in [COL_IND, COL_AGR, COL_FDI, COL_TRADE] if c in df_real.columns]
for col in numeric_cols_real:
    df_real[col] = pd.to_numeric(df_real[col], errors="coerce")

df_real = df_real.dropna(subset=[COL_YEAR]).sort_values(COL_YEAR)

# =====================================================
# 1B. ÎNCĂRCAREA DATELOR – TRANSPORT (FOAIA „Tranport”)
# =====================================================
df_trans = None
trans_load_error = None

# denumiri coloane în foaia Tranport
T_COL_YEAR = "An"
T_COL_QTR  = "Trimestrul"
T_COL_TOT_MARFURI = "Total mărfuri transportate, mii tone"
T_COL_TOT_PAS     = "Total, mii pasageri"

try:
    df_trans = pd.read_excel(file_path, sheet_name="Tranport")  # denumirea foii exact cum ai spus
    df_trans[T_COL_YEAR] = pd.to_numeric(df_trans[T_COL_YEAR], errors="coerce").astype("Int64")
    df_trans[T_COL_QTR] = df_trans[T_COL_QTR].astype(str).str.strip()

    # creăm un label text „Perioadă” (ex: 2021 T1)
    df_trans["Perioadă"] = (
        df_trans[T_COL_YEAR].astype(str) + " " +
        df_trans[T_COL_QTR].str.replace("Trimestrul ", "T")
    )

    # asigurăm numeric pentru total mărfuri și total pasageri
    for col in [T_COL_TOT_MARFURI, T_COL_TOT_PAS]:
        if col in df_trans.columns:
            df_trans[col] = pd.to_numeric(df_trans[col], errors="coerce")

    df_trans = df_trans.dropna(subset=[T_COL_YEAR]).sort_values([T_COL_YEAR, T_COL_QTR])
except Exception as e:
    df_trans = None
    trans_load_error = str(e)


# =====================================================
# 2. FILTRU: AN (PE BAZA SECTORULUI REAL)
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
# 3. CARDURI KPI – NIVELUL INDICATORILOR (ANUAL)
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
# 5. TAB-URI PE COMPONENTE ALE SECTORULUI REAL
# =====================================================
st.markdown("---")
st.subheader("Componentele sectorului real")

df_plot = df_real.copy()

tab_ind, tab_agr, tab_trade, tab_trans_tab, tab_inv = st.tabs([
    "Producția industrială",
    "Producția agricolă",
    "Comerț intern",
    "Transport auto",
    "Investiții directe"
])

# ---- TAB: PRODUCȚIA INDUSTRIALĂ ----
with tab_ind:
    st.markdown("#### Evoluția producției industriale (mil. lei)")
    fig_ind = px.line(
        df_plot,
        x=COL_YEAR,
        y=COL_IND,
        labels={COL_YEAR: "An", COL_IND: "mil. lei"},
        template="simple_white",
    )
    fig_ind.update_traces(mode="lines+markers", line=dict(width=3))
    fig_ind.update_layout(margin=dict(l=40, r=20, t=40, b=60))
    st.plotly_chart(fig_ind, use_container_width=True)

# ---- TAB: PRODUCȚIA AGRICOLĂ ----
with tab_agr:
    st.markdown("#### Evoluția producției agricole (mil. lei)")
    fig_agr = px.line(
        df_plot,
        x=COL_YEAR,
        y=COL_AGR,
        labels={COL_YEAR: "An", COL_AGR: "mil. lei"},
        template="simple_white",
    )
    fig_agr.update_traces(mode="lines+markers", line=dict(width=3))
    fig_agr.update_layout(margin=dict(l=40, r=20, t=40, b=60))
    st.plotly_chart(fig_agr, use_container_width=True)

# ---- TAB: COMERȚ INTERN ----
with tab_trade:
    st.markdown("#### Comerț intern (mil. lei)")

    if COL_TRADE in df_plot.columns:
        fig_trade = px.line(
            df_plot,
            x=COL_YEAR,
            y=COL_TRADE,
            labels={COL_YEAR: "An", COL_TRADE: "mil. lei"},
            template="simple_white",
        )
        fig_trade.update_traces(mode="lines+markers", line=dict(width=3))
        fig_trade.update_layout(margin=dict(l=40, r=20, t=40, b=60))
        st.plotly_chart(fig_trade, use_container_width=True)
    else:
        st.info(
            "Nu există încă o coloană pentru **Comerț intern** în fișierul Excel.\n\n"
            "Adaugă, de exemplu, o coloană numită **'Comerț intern, mil. lei'** "
            "în foaia `Real` și aplicația o va afișa automat aici."
        )

# ---- TAB: TRANSPORT AUTO (din foaia „Tranport”) ----
with tab_trans_tab:
    st.markdown("#### Transport auto și alte moduri de transport")

    if df_trans is None:
        msg = "Nu s-au putut încărca datele de transport (foaia `Tranport`)."
        if trans_load_error:
            msg += f"<br/><span style='font-size:0.8rem;color:#6b7280;'>Detalii: {trans_load_error}</span>"
        st.markdown(msg, unsafe_allow_html=True)
    elif not all(col in df_trans.columns for col in [T_COL_TOT_MARFURI, T_COL_TOT_PAS]):
        st.info(
            "Foaia **`Tranport`** a fost găsită, dar lipsesc coloanele:\n\n"
            f"- `{T_COL_TOT_MARFURI}` sau\n"
            f"- `{T_COL_TOT_PAS}`.\n\n"
            "Verifică denumirile coloanelor în Excel."
        )
    else:
        # KPI pentru ultimul trimestru
        last_row = df_trans.dropna(subset=[T_COL_TOT_MARFURI, T_COL_TOT_PAS]).iloc[-1]
        last_period = last_row["Perioadă"]

        k1, k2 = st.columns(2)
        k1.metric(
            f"Total mărfuri transportate ({last_period})",
            f"{last_row[T_COL_TOT_MARFURI]:,.1f} mii tone".replace(",", " ")
        )
        k2.metric(
            f"Total pasageri transportați ({last_period})",
            f"{last_row[T_COL_TOT_PAS]:,.1f} mii persoane".replace(",", " ")
        )

        col_left, col_right = st.columns(2)

        # Grafic mărfuri
        with col_left:
            st.markdown("##### Total mărfuri transportate (mii tone)")
            fig_marf = px.line(
                df_trans,
                x="Perioadă",
                y=T_COL_TOT_MARFURI,
                labels={"Perioadă": "Perioadă (an / trimestru)", T_COL_TOT_MARFURI: "mii tone"},
                template="simple_white",
            )
            fig_marf.update_traces(mode="lines+markers", line=dict(width=3))
            fig_marf.update_layout(
                margin=dict(l=40, r=20, t=40, b=80),
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig_marf, use_container_width=True)

        # Grafic pasageri
        with col_right:
            st.markdown("##### Total pasageri transportați (mii persoane)")
            fig_pas = px.line(
                df_trans,
                x="Perioadă",
                y=T_COL_TOT_PAS,
                labels={"Perioadă": "Perioadă (an / trimestru)", T_COL_TOT_PAS: "mii pasageri"},
                template="simple_white",
            )
            fig_pas.update_traces(mode="lines+markers", line=dict(width=3))
            fig_pas.update_layout(
                margin=dict(l=40, r=20, t=40, b=80),
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig_pas, use_container_width=True)

# ---- TAB: INVESTIȚII DIRECTE ----
with tab_inv:
    st.markdown("#### Investiții directe acumulate (stoc, MBP6) – mil. USD")
    fig_fdi = px.line(
        df_plot,
        x=COL_YEAR,
        y=COL_FDI,
        labels={COL_YEAR: "An", COL_FDI: "mil. USD"},
        template="simple_white",
    )
    fig_fdi.update_traces(mode="lines+markers", line=dict(width=3))
    fig_fdi.update_layout(margin=dict(l=40, r=20, t=40, b=60))
    st.plotly_chart(fig_fdi, use_container_width=True)
