# pages/Sector_Social.py

import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Sector social", layout="wide")

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

st.title("Sectorul Social")

st.markdown("""
Principalii indicatori ai **pieței muncii**:
populația ocupată, numărul șomerilor, rata șomajului, rata de ocupare și câștigul mediu salarial.  
""")

# =====================================================
# 1. ÎNCĂRCAREA DATELOR
# =====================================================
file_path = os.path.join("data", "Test_Data_Sector_Social.xlsx")

try:
    df_social = pd.read_excel(file_path, sheet_name="Social")
except FileNotFoundError:
    st.error(
        f"Fișierul nu a fost găsit: `{file_path}`.\n"
        f"Verifică să fie în folderul `data/` sau actualizează calea / numele fișierului."
    )
    st.stop()

# Denumirile coloanelor (conform structurii noi)
COL_YEAR  = "An"
COL_QTR   = "Trimestrul"
COL_EMP   = "Populația ocupată"
COL_UNEMP = "Numărul șomerilor"
COL_URATE = "Rata șomajului"
COL_ERATE = "Rata de ocupare"
COL_WAGE  = "Câștigul mediu salarial"

# Curățări de bază
df_social[COL_YEAR] = pd.to_numeric(df_social[COL_YEAR], errors="coerce").astype("Int64")
df_social[COL_QTR] = df_social[COL_QTR].astype(str).str.strip()

# ordinea corectă a trimestrelor
quarter_order = ["Trimestrul I", "Trimestrul II", "Trimestrul III", "Trimestrul IV"]
quarter_rank = {q: i for i, q in enumerate(quarter_order)}

# =====================================================
# 2. FILTRE: AN + TRIMESTRU
# =====================================================
years_available = sorted(df_social[COL_YEAR].dropna().unique())
st.sidebar.header("Filtre")

selected_year = st.sidebar.selectbox(
    "Selectează anul:",
    options=years_available,
    index=len(years_available) - 1
)

quarters_in_year = sorted(
    df_social.loc[df_social[COL_YEAR] == selected_year, COL_QTR].unique(),
    key=lambda q: quarter_rank.get(q, 99)
)

selected_quarter = st.sidebar.selectbox(
    "Selectează trimestrul:",
    options=quarters_in_year,
    index=len(quarters_in_year) - 1
)

matching = df_social[
    (df_social[COL_YEAR] == selected_year) &
    (df_social[COL_QTR] == selected_quarter)
]

if matching.empty:
    st.error("Nu există date pentru combinația selectată de an și trimestru.")
    st.stop()

row_sel = matching.iloc[0]

st.caption(
    f"Perioada selectată: **{selected_quarter} {selected_year}**"
)

# =====================================================
# 3. CARDURI KPI – NIVELUL INDICATORILOR
# =====================================================
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Populația ocupată",
    f"{row_sel[COL_EMP]:,.1f}" if pd.notna(row_sel[COL_EMP]) else "n/d",
)
col2.metric(
    "Numărul șomerilor",
    f"{row_sel[COL_UNEMP]:,.1f}" if pd.notna(row_sel[COL_UNEMP]) else "n/d",
)
col3.metric(
    "Rata șomajului",
    f"{row_sel[COL_URATE]:.1f} %" if pd.notna(row_sel[COL_URATE]) else "n/d",
)
col4.metric(
    "Rata de ocupare",
    f"{row_sel[COL_ERATE]:.1f} %" if pd.notna(row_sel[COL_ERATE]) else "n/d",
)
col5.metric(
    "Câștigul mediu salarial",
    f"{row_sel[COL_WAGE]:,.1f}" if pd.notna(row_sel[COL_WAGE]) else "n/d",
)

# =====================================================
# 4. COMPARAȚIE CU ACELAȘI TRIMESTRU DIN ANUL PRECEDENT
# =====================================================
prev_year = selected_year - 1
prev_row = df_social[
    (df_social[COL_YEAR] == prev_year) &
    (df_social[COL_QTR] == selected_quarter)
]

text_parts = []

if not prev_row.empty:
    prev_row = prev_row.iloc[0]

    def pct_change(curr, prev):
        return (curr - prev) / prev * 100 if (pd.notna(prev) and prev != 0) else None

    emp_chg   = pct_change(row_sel[COL_EMP],   prev_row[COL_EMP])
    une_chg   = pct_change(row_sel[COL_UNEMP], prev_row[COL_UNEMP])
    ur_chg    = pct_change(row_sel[COL_URATE], prev_row[COL_URATE])
    er_chg    = pct_change(row_sel[COL_ERATE], prev_row[COL_ERATE])
    wage_chg  = pct_change(row_sel[COL_WAGE],  prev_row[COL_WAGE])

    text_parts.append(
        f"În **{selected_quarter} {selected_year}**, populația ocupată a fost de "
        f"**{row_sel[COL_EMP]:,.1f} mii persoane**, iar numărul șomerilor "
        f"de **{row_sel[COL_UNEMP]:,.1f} mii persoane**. Rata șomajului a constituit "
        f"**{row_sel[COL_URATE]:.1f}%**, iar rata de ocupare **{row_sel[COL_ERATE]:.1f}%**. "
        f"Câștigul mediu salarial a fost de **{row_sel[COL_WAGE]:,.1f}**."
    )

    text_parts.append(
        f"Comparativ cu **{selected_quarter} {prev_year}**, populația ocupată este "
        f"{'mai mare' if emp_chg and emp_chg > 0 else 'mai mică'} cu **{abs(emp_chg):.1f}%**, "
        f"iar numărul șomerilor este "
        f"{'mai mare' if une_chg and une_chg > 0 else 'mai mic'} cu **{abs(une_chg):.1f}%**. "
        f"Rata șomajului s-a modificat cu **{ur_chg:+.1f} p.p.**, rata de ocupare cu "
        f"**{er_chg:+.1f} p.p.**, iar câștigul mediu salarial cu **{wage_chg:+.1f}%**."
    )
else:
    text_parts.append(
        f"În **{selected_quarter} {selected_year}**, populația ocupată a fost de "
        f"**{row_sel[COL_EMP]:,.1f} mii persoane**, iar numărul șomerilor de "
        f"**{row_sel[COL_UNEMP]:,.1f} mii persoane**. Rata șomajului a constituit "
        f"**{row_sel[COL_URATE]:.1f}%**, rata de ocupare **{row_sel[COL_ERATE]:.1f}%**, "
        f"iar câștigul mediu salarial a fost de **{row_sel[COL_WAGE]:,.1f}**."
    )
    text_parts.append(
        "Nu există date pentru același trimestru din anul precedent pentru a calcula variațiile anuale."
    )

st.markdown("\n\n".join(text_parts))

# =====================================================
# 5–6. EVOLUȚIA INDICATORILOR PIEȚEI MUNCII (Trimestrial / Anual)
# =====================================================
st.markdown("---")
st.subheader("Evoluția indicatorilor pieței muncii")

# Selector de frecvență
freq_option = st.radio(
    "Selectează frecvența datelor:",
    options=["Trimestrial", "Anual"],
    index=0,
    horizontal=True
)

df_plot = df_social.copy()
df_plot["Perioadă"] = (
    df_plot[COL_YEAR].astype(str) + " " + df_plot[COL_QTR].str.replace("Trimestrul ", "T")
)

# ======== AGREGARE ANUALĂ (media valorilor trimestriale) ========
if freq_option == "Anual":
    df_plot = (
        df_plot.groupby(COL_YEAR, as_index=False)
        [[COL_EMP, COL_UNEMP, COL_URATE, COL_ERATE, COL_WAGE]]
        .mean(numeric_only=True)
    )
    df_plot["Perioadă"] = df_plot[COL_YEAR].astype(str)

# ======== Layout pe două coloane ========
col_left, col_right = st.columns(2)

# -----------------------------------------------------
# GRAFIC 1 – Populația ocupată și numărul șomerilor
# -----------------------------------------------------
with col_left:
    st.markdown("#### Populația ocupată și numărul șomerilor")
    fig_emp = px.line(
        df_plot,
        x="Perioadă",
        y=[COL_EMP, COL_UNEMP],
        labels={
            "value": "Persoane (mii)",
            "variable": "Indicator",
        },
        template="simple_white",
    )
    fig_emp.update_traces(line=dict(width=3))
    fig_emp.update_layout(
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
    st.plotly_chart(fig_emp, use_container_width=True)

# -----------------------------------------------------
# GRAFIC 2 – Rata șomajului și rata de ocupare
# -----------------------------------------------------
with col_right:
    st.markdown("#### Rata șomajului și rata de ocupare (%)")
    fig_rates = px.line(
        df_plot,
        x="Perioadă",
        y=[COL_URATE, COL_ERATE],
        labels={
            "value": "%",
            "variable": "Indicator",
        },
        template="simple_white",
    )
    fig_rates.update_traces(line=dict(width=3))
    fig_rates.update_layout(
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
    st.plotly_chart(fig_rates, use_container_width=True)


# =====================================================
# 7. EVOLUȚIA CÂȘTIGULUI MEDIU SALARIAL
# =====================================================
st.subheader("Evoluția câștigului mediu salarial (mii lei)")

fig_wage = px.line(
    df_plot,
    x="Perioadă",
    y=COL_WAGE,
    labels={"Perioadă": "Perioadă (an / trimestru)", COL_WAGE: "Câștig mediu"},
    template="simple_white",
)
fig_wage.update_traces(mode="lines+markers", line=dict(width=3))
fig_wage.update_layout(
    margin=dict(l=40, r=20, t=40, b=80),
)
st.plotly_chart(fig_wage, use_container_width=True)
