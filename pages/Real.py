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

COL_YEAR  = "An"
COL_IND   = "Producția industrială, mil. lei"
COL_AGR   = "Producția agricolă, mil. lei"
COL_FDI   = "Investiţiile directe acumulate în Republica Moldova (stoc) (MBP6), mil. USD"
COL_TRADE = "Comerț intern, mil. lei"

df_real[COL_YEAR] = pd.to_numeric(df_real[COL_YEAR], errors="coerce").astype("Int64")
numeric_cols_real = [c for c in [COL_IND, COL_AGR, COL_FDI, COL_TRADE] if c in df_real.columns]
for col in numeric_cols_real:
    df_real[col] = pd.to_numeric(df_real[col], errors="coerce")
df_real = df_real.dropna(subset=[COL_YEAR]).sort_values(COL_YEAR)

# =====================================================
# 1B. TRANSPORT
# =====================================================
df_trans = None
try:
    df_trans = pd.read_excel(file_path, sheet_name="Tranport")
    df_trans["An"] = pd.to_numeric(df_trans["An"], errors="coerce").astype("Int64")
    df_trans["Trimestrul"] = df_trans["Trimestrul"].astype(str)
    df_trans["Perioadă"] = df_trans["An"].astype(str) + " " + df_trans["Trimestrul"].str.replace("Trimestrul ", "T")
except Exception:
    df_trans = None

# =====================================================
# 1C. PIB PE RAMURI
# =====================================================
df_pib = None
try:
    df_pib = pd.read_excel(file_path, sheet_name="PIB")
    df_pib["An"] = pd.to_numeric(df_pib["An"].astype(str).str.replace(",", ""), errors="coerce").astype("Int64")

    # Creștere reală PIB (%): PIB comparabil_t / PIB curent_{t-1} - 1
    df_pib["Creștere reală (%)"] = (
        df_pib["PIB comparabil"] / df_pib["PIB curent"].shift(1) - 1
    ) * 100
except Exception:
    df_pib = None

# =====================================================
# 1D. PIB PE UTILIZĂRI
# =====================================================
df_pib_use = None
try:
    df_pib_use = pd.read_excel(file_path, sheet_name="PIB_utilizari")
    df_pib_use["An"] = pd.to_numeric(df_pib_use["An"].astype(str).str.replace(",", ""), errors="coerce").astype("Int64")
except Exception:
    df_pib_use = None

# =====================================================
# 1E. INDUSTRIE – INDICI (% față de anul precedent)
# =====================================================
df_ind = None
try:
    df_ind = pd.read_excel(file_path, sheet_name="Industrie")
    df_ind["An"] = pd.to_numeric(df_ind["An"], errors="coerce").astype("Int64")
    for col in df_ind.columns:
        if col != "An":
            df_ind[col] = pd.to_numeric(df_ind[col], errors="coerce")
    df_ind = df_ind.dropna(subset=["An"]).sort_values("An")
except Exception:
    df_ind = None

# =====================================================
# 1F. INDUSTRIE PRELUCRĂTOARE – SUBRAMURI (pentru contribuții)
# =====================================================
df_ind_prel = None
try:
    df_ind_prel = pd.read_excel(file_path, sheet_name="Industrie_Prel")
    df_ind_prel["An"] = pd.to_numeric(df_ind_prel["An"], errors="coerce").astype("Int64")

    # conversie numerică pentru toate coloanele, în afară de "An"
    for col in df_ind_prel.columns:
        if col != "An":
            df_ind_prel[col] = pd.to_numeric(df_ind_prel[col], errors="coerce")

    df_ind_prel = df_ind_prel.dropna(subset=["An"]).sort_values("An")

    # contribuții la creșterea industriei prelucrătoare:
    # (subramură_t - subramură_{t-1}) / Industria prelucratoare_{t-1} * 100
    BASE_INDUSTRY_COL = "Industria prelucratoare"
    if BASE_INDUSTRY_COL in df_ind_prel.columns:
        denom_ind = df_ind_prel[BASE_INDUSTRY_COL].shift(1).replace(0, pd.NA)
        sub_cols = [c for c in df_ind_prel.columns if c not in ["An", BASE_INDUSTRY_COL]]

        for c in sub_cols:
            new_col = c + " (p.p.)"
            df_ind_prel[new_col] = (df_ind_prel[c] - df_ind_prel[c].shift(1)) / denom_ind * 100
except Exception:
    df_ind_prel = None

# =====================================================
# FILTRU AN
# =====================================================
years_available = sorted(df_real[COL_YEAR].unique())
st.sidebar.header("Filtru")
selected_year = st.sidebar.selectbox(
    "Selectează anul:",
    options=years_available,
    index=len(years_available) - 1
)
st.caption(f"An selectat: **{selected_year}**")

# =====================================================
# PRIVIRE DE ANSAMBLU – TEXT + KPI
# =====================================================

row_real_cur = df_real[df_real[COL_YEAR] == selected_year]
row_real_cur = row_real_cur.iloc[0] if not row_real_cur.empty else None

row_pib_cur = None
if df_pib is not None:
    tmp = df_pib[df_pib["An"] == selected_year]
    if not tmp.empty:
        row_pib_cur = tmp.iloc[0]

prev_year = selected_year - 1
row_real_prev = df_real[df_real[COL_YEAR] == prev_year]
row_real_prev = row_real_prev.iloc[0] if not row_real_prev.empty else None

row_pib_prev = None
if df_pib is not None:
    tmp_prev = df_pib[df_pib["An"] == prev_year]
    if not tmp_prev.empty:
        row_pib_prev = tmp_prev.iloc[0]

def yoy(curr, prev):
    if curr is None or prev is None:
        return None
    try:
        if pd.isna(curr) or pd.isna(prev) or prev == 0:
            return None
    except Exception:
        return None
    return (curr / prev - 1) * 100

ind_val  = row_real_cur[COL_IND] if row_real_cur is not None and COL_IND in row_real_cur else None
agr_val  = row_real_cur[COL_AGR] if row_real_cur is not None and COL_AGR in row_real_cur else None
fdi_val  = row_real_cur[COL_FDI] if row_real_cur is not None and COL_FDI in row_real_cur else None
pib_cur  = row_pib_cur["PIB curent"] if row_pib_cur is not None and "PIB curent" in row_pib_cur else None
pib_gr   = row_pib_cur["Creștere reală (%)"] if row_pib_cur is not None and "Creștere reală (%)" in row_pib_cur else None

ind_chg = yoy(ind_val, row_real_prev[COL_IND]) if row_real_prev is not None and COL_IND in row_real_prev else None
agr_chg = yoy(agr_val, row_real_prev[COL_AGR]) if row_real_prev is not None and COL_AGR in row_real_prev else None
fdi_chg = yoy(fdi_val, row_real_prev[COL_FDI]) if row_real_prev is not None and COL_FDI in row_real_prev else None
pib_chg = yoy(pib_cur, row_pib_prev["PIB curent"]) if row_pib_prev is not None and "PIB curent" in row_pib_prev else None

st.markdown("### Indicatori cheie")

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "PIB, mil. lei",
    f"{pib_cur:,.0f}".replace(",", " ") if pib_cur is not None else "n/d",
    (f"{pib_chg:.1f} %" if pib_chg is not None else None)
)
k2.metric(
    "Creștere reală a PIB",
    f"{pib_gr:.1f} %".replace(".", ",") if pib_gr is not None else "n/d",
    None
)
k3.metric(
    "Producția industrială",
    f"{ind_val:,.1f} mil. lei".replace(",", " ") if ind_val is not None else "n/d",
    (f"{ind_chg:.1f} %" if ind_chg is not None else None)
)
k4.metric(
    "Producția agricolă",
    f"{agr_val:,.1f} mil. lei".replace(",", " ") if agr_val is not None else "n/d",
    (f"{agr_chg:.1f} %" if agr_chg is not None else None)
)
k5.metric(
    "Investiții directe (stoc)",
    f"{fdi_val:,.1f} mil. USD".replace(",", " ") if fdi_val is not None else "n/d",
    (f"{fdi_chg:.1f} %" if fdi_chg is not None else None)
)

text_intro = []

if pib_cur is not None:
    text_intro.append(
        f"În **{selected_year}**, PIB la prețuri curente a fost de "
        f"**{pib_cur:,.0f}** lei.".replace(",", " ")
    )

if ind_val is not None or agr_val is not None or fdi_val is not None:
    frag = "Sectorul real al economiei a înregistrat "
    parts = []
    if ind_val is not None:
        parts.append(f"producție industrială de **{ind_val:,.1f} mil. lei**".replace(",", " "))
    if agr_val is not None:
        parts.append(f"producție agricolă de **{agr_val:,.1f} mil. lei**".replace(",", " "))
    if fdi_val is not None:
        parts.append(f"stoc al investițiilor directe de **{fdi_val:,.1f} mil. USD**".replace(",", " "))
    if parts:
        frag += ", ".join(parts) + "."
        text_intro.append(frag)

if pib_gr is not None:
    text_intro.append(
        f"Ritmul de **creștere reală** față de anul precedent a fost de "
        f"**{pib_gr:.1f}%**.".replace(".", ",")
    )

if prev_year in years_available and (ind_chg is not None or agr_chg is not None or fdi_chg is not None or pib_chg is not None):
    comp_frag = f"Comparativ cu **{prev_year}**, "
    comp_parts = []
    if pib_chg is not None:
        comp_parts.append(
            f"PIB la prețuri curente este "
            f"{'mai mare' if pib_chg > 0 else 'mai mic'} cu **{abs(pib_chg):.1f}%**"
        )
    if ind_chg is not None:
        comp_parts.append(
            f"producția industrială este "
            f"{'mai mare' if ind_chg > 0 else 'mai mică'} cu **{abs(ind_chg):.1f}%**"
        )
    if agr_chg is not None:
        comp_parts.append(
            f"producția agricolă este "
            f"{'mai mare' if agr_chg > 0 else 'mai mică'} cu **{abs(agr_chg):.1f}%**"
        )
    if fdi_chg is not None:
        comp_parts.append(
            f"stocul de investiții directe este "
            f"{'mai ridicat' if fdi_chg > 0 else 'mai redus'} cu **{abs(fdi_chg):.1f}%**"
        )
    if comp_parts:
        comp_frag += ", ".join(comp_parts) + "."
        text_intro.append(comp_frag)

if text_intro:
    st.markdown("\n\n".join(text_intro))

# =====================================================
# TAB-URI (PIB primul)
# =====================================================
st.subheader("Componentele sectorului real")

tab_pib, tab_ind_tab, tab_agr, tab_trade, tab_trans_tab, tab_inv = st.tabs([
    "PIB",
    "Producția industrială",
    "Producția agricolă",
    "Comerț intern",
    "Transport",
    "Investiții directe",
])

# =====================================================
# TAB: PIB
# =====================================================
with tab_pib:

    if df_pib is not None and not df_pib.empty:
        # ---------------- PIB nivel + creștere reală ----------------
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### PIB (mil. lei)")
            fig_pib_cur = px.line(
                df_pib,
                x="An",
                y="PIB curent",
                markers=True,
                template="simple_white"
            )
            st.plotly_chart(fig_pib_cur, use_container_width=True)

        with col_right:
            st.markdown("#### Creștere reală a PIB (%)")

            df_gr = df_pib.dropna(subset=["Creștere reală (%)"]).copy()
            df_gr["label_gr"] = df_gr["Creștere reală (%)"].map(
                lambda v: f"{v:.1f}".replace(".", ",")
            )

            fig_pib_real = px.line(
                df_gr,
                x="An",
                y="Creștere reală (%)",
                text="label_gr",
                markers=True,
                template="simple_white",
                labels={
                    "An": "An",
                    "Creștere reală (%)": "% față de anul precedent"
                }
            )

            fig_pib_real.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_pib_real.update_traces(
                textposition="top center",
                textfont=dict(size=11)
            )
            fig_pib_real.update_layout(
                margin=dict(l=40, r=20, t=40, b=60)
            )

            st.plotly_chart(fig_pib_real, use_container_width=True)

        # ---------------- Structură PIB pe ramuri (% din PIB) ----------------
        st.markdown("#### Structura PIB pe ramuri (pondere în PIB, %)")

        ramuri_cols = [
            "Agricultura, silvicultura si pescuit curent",
            "Industrie curent",
            "Constructii curent",
            "Servicii curent",
            "Impozite nete pe produse curent",
        ]

        if all(c in df_pib.columns for c in ramuri_cols):
            df_share = df_pib.dropna(subset=["PIB curent"] + ramuri_cols).copy()
            for c in ramuri_cols:
                df_share[c + "_share"] = df_share[c] / df_share["PIB curent"] * 100

            df_share_long = df_share.melt(
                id_vars=["An"],
                value_vars=[c + "_share" for c in ramuri_cols],
                var_name="Resurse",
                value_name="Pondere (%)",
            )
            df_share_long["Resurse"] = (
                df_share_long["Resurse"]
                .str.replace("_share", "")
                .str.replace(" curent", "")
            )

            fig_stack = px.bar(
                df_share_long,
                x="An",
                y="Pondere (%)",
                color="Resurse",
                template="simple_white",
                barmode="stack",
            )
            fig_stack.update_layout(yaxis=dict(range=[0, 100]))
            st.plotly_chart(fig_stack, use_container_width=True)
        else:
            st.info("Nu există toate coloanele necesare pentru structura pe ramuri.")

        # =====================================================
        # CREȘTERI ANUALE ALE COMPONENTELOR
        # =====================================================
        st.markdown("---")

        g_left, g_right = st.columns(2)

        # ---- Creștere anuală pe RAMURI (resurse) ----
        with g_left:
            st.markdown("#### Creștere anuală – resurse")

            ramuri_def = [
                {
                    "cur": "Agricultura, silvicultura si pescuit curent",
                    "comp": "Agricultura, silvicultura si pescuit comparabil",
                    "name": "Agricultură",
                },
                {
                    "cur": "Industrie curent",
                    "comp": "Industrie comparabil",
                    "name": "Industrie",
                },
                {
                    "cur": "Constructii curent",
                    "comp": "Constructii comparabil",
                    "name": "Construcții",
                },
                {
                    "cur": "Servicii curent",
                    "comp": "Servicii comparabil",
                    "name": "Servicii",
                },
                {
                    "cur": "Impozite nete pe produse curent",
                    "comp": "Impozite nete pe produse comparabil",
                    "name": "Impozite nete",
                },
            ]

            df_g_ram = df_pib.copy()
            series_ram = []

            for cfg in ramuri_def:
                cur_col = cfg["cur"]
                comp_col = cfg["comp"]
                nice_name = cfg["name"]

                if cur_col in df_g_ram.columns and comp_col in df_g_ram.columns:
                    denom = df_g_ram[cur_col].shift(1).replace(0, pd.NA)
                    df_g_ram[nice_name] = (df_g_ram[comp_col] / denom) * 100 - 100
                    series_ram.append(nice_name)

            if series_ram:
                df_long_ram = df_g_ram.dropna(subset=series_ram, how="all").melt(
                    id_vars=["An"],
                    value_vars=series_ram,
                    var_name="Resurse",
                    value_name="Creștere (%)",
                )

                fig_gr_ram = px.line(
                    df_long_ram,
                    x="An",
                    y="Creștere (%)",
                    color="Resurse",
                    markers=True,
                    template="simple_white",
                )
                fig_gr_ram.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_gr_ram, use_container_width=True)
            else:
                st.info("Nu există date suficiente pentru creșterile anuale pe ramuri.")

        # ---- Creștere anuală pe UTILIZĂRI ----
        with g_right:
            st.markdown("#### Creștere anuală – utilizări")

            if df_pib_use is not None and not df_pib_use.empty:
                utiliz_def = [
                    {
                        "cur": "Consumul final al gospodariilor populatiei curent",
                        "comp": "Consumul final al gospodariilor populatiei comparabil",
                        "name": "Consum gospodării",
                    },
                    {
                        "cur": "Consumul final al administratiei publice curent",
                        "comp": "Consumul final al administratiei publice comparabil",
                        "name": "Consum public",
                    },
                    {
                        "cur": "Formarea bruta de capital curent",
                        "comp": "Formarea bruta de capital comparabil",
                        "name": "Formare capital",
                    },
                    {
                        "cur": "Export curent",
                        "comp": "Export comparabil",
                        "name": "Export",
                    },
                    {
                        "cur": "Import curent",
                        "comp": "Import comparabil",
                        "name": "Import",
                    },
                ]

                df_g_use = df_pib_use.copy()
                series_use = []

                for cfg in utiliz_def:
                    cur_col = cfg["cur"]
                    comp_col = cfg["comp"]
                    nice_name = cfg["name"]

                    if cur_col in df_g_use.columns and comp_col in df_g_use.columns:
                        denom = df_g_use[cur_col].shift(1).replace(0, pd.NA)
                        df_g_use[nice_name] = (df_g_use[comp_col] / denom) * 100 - 100
                        series_use.append(nice_name)

                if series_use:
                    df_long_use = df_g_use.dropna(subset=series_use, how="all").melt(
                        id_vars=["An"],
                        value_vars=series_use,
                        var_name="Utilizare",
                        value_name="Creștere (%)",
                    )
                    fig_gr_use = px.line(
                        df_long_use,
                        x="An",
                        y="Creștere (%)",
                        color="Utilizare",
                        markers=True,
                        template="simple_white",
                    )
                    fig_gr_use.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig_gr_use, use_container_width=True)
                else:
                    st.info("Nu există date suficiente pentru creșterile anuale pe utilizări.")
            else:
                st.info("Nu s-au încărcat datele pentru PIB_utilizari.")

        # =====================================================
        # CONTRIBUȚII LA CREȘTERE – RAMURI & UTILIZĂRI
        # =====================================================
        st.markdown("---")
        st.markdown("### Contribuția la creșterea PIB (p.p.)")

        # 1) Contribuții RAMURI
        if all(
            c in df_pib.columns for c in [
                "Agricultura, silvicultura si pescuit curent",
                "Industrie curent",
                "Constructii curent",
                "Servicii curent",
                "Impozite nete pe produse curent",
                "Agricultura, silvicultura si pescuit comparabil",
                "Industrie comparabil",
                "Constructii comparabil",
                "Servicii comparabil",
                "Impozite nete pe produse comparabil",
            ]
        ):
            denom_pp = df_pib["PIB curent"].shift(1).replace(0, pd.NA)
            df_pib["Agricultură (p.p.)"] = (
                df_pib["Agricultura, silvicultura si pescuit comparabil"]
                - df_pib["Agricultura, silvicultura si pescuit curent"].shift(1)
            ) / denom_pp * 100
            df_pib["Industrie (p.p.)"] = (
                df_pib["Industrie comparabil"]
                - df_pib["Industrie curent"].shift(1)
            ) / denom_pp * 100
            df_pib["Construcții (p.p.)"] = (
                df_pib["Constructii comparabil"]
                - df_pib["Constructii curent"].shift(1)
            ) / denom_pp * 100
            df_pib["Servicii (p.p.)"] = (
                df_pib["Servicii comparabil"] - df_pib["Servicii curent"].shift(1)
            ) / denom_pp * 100
            df_pib["Impozite nete (p.p.)"] = (
                df_pib["Impozite nete pe produse comparabil"]
                - df_pib["Impozite nete pe produse curent"].shift(1)
            ) / denom_pp * 100

        # 2) Contribuții UTILIZĂRI
        if df_pib_use is not None and not df_pib_use.empty:
            if all(
                c in df_pib_use.columns for c in [
                    "Consumul final al gospodariilor populatiei curent",
                    "Consumul final al administratiei publice curent",
                    "Formarea bruta de capital curent",
                    "Export curent",
                    "Import curent",
                    "Consumul final al gospodariilor populatiei comparabil",
                    "Consumul final al administratiei publice comparabil",
                    "Formarea bruta de capital comparabil",
                    "Export comparabil",
                    "Import comparabil",
                    "PIB curent",
                ]
            ):
                denom_u = df_pib_use["PIB curent"].shift(1).replace(0, pd.NA)
                df_pib_use["Consum gospodării (p.p.)"] = (
                    df_pib_use["Consumul final al gospodariilor populatiei comparabil"]
                    - df_pib_use["Consumul final al gospodariilor populatiei curent"].shift(1)
                ) / denom_u * 100
                df_pib_use["Consum public (p.p.)"] = (
                    df_pib_use["Consumul final al administratiei publice comparabil"]
                    - df_pib_use["Consumul final al administratiei publice curent"].shift(1)
                ) / denom_u * 100
                df_pib_use["Formare capital (p.p.)"] = (
                    df_pib_use["Formarea bruta de capital comparabil"]
                    - df_pib_use["Formarea bruta de capital curent"].shift(1)
                ) / denom_u * 100
                df_pib_use["Export (p.p.)"] = (
                    df_pib_use["Export comparabil"] - df_pib_use["Export curent"].shift(1)
                ) / denom_u * 100
                df_pib_use["Import (p.p.)"] = (
                    df_pib_use["Import comparabil"] - df_pib_use["Import curent"].shift(1)
                ) / denom_u * 100

        # selectbox an pentru contribuții
        all_years = sorted(
            set(df_pib["An"].dropna().tolist())
            | (set(df_pib_use["An"].dropna().tolist()) if df_pib_use is not None else set())
        )
        selected_contrib_year = st.selectbox(
            "Alege anul pentru analiza contribuțiilor:",
            options=all_years,
            index=len(all_years) - 1,
        )

        c_left, c_right = st.columns(2)

        # --- stânga: contribuții RAMURI ---
        with c_left:
            st.markdown("#### Contribuția resurselor (p.p.)")
            row_r = df_pib[df_pib["An"] == selected_contrib_year]
            if not row_r.empty and "Agricultură (p.p.)" in row_r.columns:
                r = row_r.iloc[0]
                data_r = pd.DataFrame({
                    "Resurse": ["Agricultură", "Industrie", "Construcții", "Servicii", "Impozite nete"],
                    "Contribuție (p.p.)": [
                        r["Agricultură (p.p.)"],
                        r["Industrie (p.p.)"],
                        r["Construcții (p.p.)"],
                        r["Servicii (p.p.)"],
                        r["Impozite nete (p.p.)"],
                    ]
                }).dropna()

                data_r = data_r.sort_values("Contribuție (p.p.)", ascending=False)
                data_r["Etichetă"] = data_r["Contribuție (p.p.)"].map(lambda x: f"{x:.1f}")

                fig_r = px.bar(
                    data_r,
                    x="Resurse",
                    y="Contribuție (p.p.)",
                    text="Etichetă",
                    template="simple_white",
                )
                fig_r.update_traces(textposition="outside", textfont=dict(size=11))
                fig_r.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_r.update_layout(
                    margin=dict(l=20, r=20, t=40, b=40),
                    yaxis_title="p.p.",
                )
                st.plotly_chart(fig_r, use_container_width=True)
            else:
                st.info("Nu există date suficiente pentru contribuțiile pe ramuri.")

        # --- dreapta: contribuții UTILIZĂRI ---
        with c_right:
            st.markdown("#### Contribuția utilizărilor (p.p.)")
            if df_pib_use is not None and not df_pib_use.empty and "Consum gospodării (p.p.)" in df_pib_use.columns:
                row_u = df_pib_use[df_pib_use["An"] == selected_contrib_year]
                if not row_u.empty:
                    u = row_u.iloc[0]
                    data_u = pd.DataFrame({
                        "Utilizare": [
                            "Consum gospodării",
                            "Consum public",
                            "Formare capital",
                            "Export",
                            "Import",
                        ],
                        "Contribuție (p.p.)": [
                            u["Consum gospodării (p.p.)"],
                            u["Consum public (p.p.)"],
                            u["Formare capital (p.p.)"],
                            u["Export (p.p.)"],
                            u["Import (p.p.)"],
                        ],
                    }).dropna()

                    data_u = data_u.sort_values("Contribuție (p.p.)", ascending=False)
                    data_u["Etichetă"] = data_u["Contribuție (p.p.)"].map(lambda x: f"{x:.1f}")

                    fig_u = px.bar(
                        data_u,
                        x="Utilizare",
                        y="Contribuție (p.p.)",
                        text="Etichetă",
                        template="simple_white",
                    )
                    fig_u.update_traces(textposition="outside", textfont=dict(size=11))
                    fig_u.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig_u.update_layout(
                        margin=dict(l=20, r=20, t=40, b=40),
                        yaxis_title="p.p.",
                    )
                    st.plotly_chart(fig_u, use_container_width=True)
                else:
                    st.info("Nu există date pentru anul selectat (utilizări).")
            else:
                st.info("Nu s-au calculat contribuțiile pe utilizări.")
    else:
        st.warning("Nu s-au putut încărca datele de PIB.")

# =====================================================
# TAB: PRODUCȚIA INDUSTRIALĂ
# =====================================================
with tab_ind_tab:

    c1, c2 = st.columns(2)

    # stânga – nivelul producției industriale (mil. lei)
    with c1:
        st.markdown("#### Producția industrială (mil. lei)")
        fig_ind_level = px.line(
            df_real,
            x=COL_YEAR,
            y=COL_IND,
            markers=True,
            template="simple_white",
        )
        st.plotly_chart(fig_ind_level, use_container_width=True)

    # dreapta – indici pe ramuri (Industrie)
    with c2:
        st.markdown("#### Indicii volumului producției industriale")

        if df_ind is not None and not df_ind.empty:
            cols_idx = [c for c in df_ind.columns if c != "An"]
            fig_ind_idx = px.line(
                df_ind,
                x="An",
                y=cols_idx,
                markers=True,
                template="simple_white",
            )

            # linia pentru "Industria total,%" întreruptă
            for trace in fig_ind_idx.data:
                if trace.name.strip().lower().startswith("industria total"):
                    trace.line["dash"] = "dash"
                    trace.line["width"] = 3
                else:
                    trace.line["width"] = 3

            fig_ind_idx.add_hline(y=100, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_ind_idx, use_container_width=True)
        else:
            st.info("Nu s-au putut încărca indicii de industrie (foaia 'Industrie').")

    # ===== Contribuția subramurilor industriei prelucrătoare =====
    st.markdown("---")
    st.markdown("#### Contribuția subramurilor industriei prelucrătoare la creșterea industriei prelucrătoare (p.p.)")

    if df_ind_prel is not None and not df_ind_prel.empty:
        years_prel = sorted(df_ind_prel["An"].dropna().unique())
        selected_ind_year = st.selectbox(
            "Alege anul pentru contribuțiile industriei prelucrătoare:",
            options=years_prel,
            index=len(years_prel) - 1,
        )

        row_prel = df_ind_prel[df_ind_prel["An"] == selected_ind_year]
        if not row_prel.empty:
            r = row_prel.iloc[0]

            pp_cols = [c for c in df_ind_prel.columns if c.endswith(" (p.p.)")]
            rows = []
            for col in pp_cols:
                val = r[col]
                if pd.notna(val):
                    name_clean = col.replace(" (p.p.)", "")
                    rows.append((name_clean, val))

            if rows:
                data_prel = pd.DataFrame(rows, columns=["Subramură", "Contribuție (p.p.)"])
                data_prel = data_prel.sort_values("Contribuție (p.p.)", ascending=False)
                data_prel["Etichetă"] = data_prel["Contribuție (p.p.)"].map(lambda x: f"{x:.1f}")

                fig_prel = px.bar(
                    data_prel,
                    x="Contribuție (p.p.)",
                    y="Subramură",
                    orientation="h",
                    text="Etichetă",
                    template="simple_white",
                )
                fig_prel.update_traces(textposition="outside", textfont=dict(size=9))
                fig_prel.add_vline(x=0, line_dash="dash", line_color="gray")
                fig_prel.update_layout(
                    margin=dict(l=20, r=20, t=40, b=40),
                    xaxis_title="p.p.",
                )
                st.plotly_chart(fig_prel, use_container_width=True)
            else:
                st.info("Nu s-au putut calcula contribuțiile pe subramuri pentru anul selectat.")
        else:
            st.info("Nu există date pentru anul selectat în foaia 'Industrie_Prel'.")
    else:
        st.info("Nu s-au putut încărca datele din foaia 'Industrie_Prel'.")

# =====================================================
# TAB: PRODUCȚIA AGRICOLĂ
# =====================================================
with tab_agr:
    st.markdown("#### Evoluția producției agricole (mil. lei)")
    fig_agr = px.line(df_real, x=COL_YEAR, y=COL_AGR, markers=True, template="simple_white")
    st.plotly_chart(fig_agr, use_container_width=True)

# =====================================================
# TAB: COMERȚ INTERN
# =====================================================
with tab_trade:
    st.markdown("#### Comerț intern (mil. lei)")
    if COL_TRADE in df_real.columns:
        fig_trade = px.line(df_real, x=COL_YEAR, y=COL_TRADE, markers=True, template="simple_white")
        st.plotly_chart(fig_trade, use_container_width=True)
    else:
        st.info("Nu sunt date.")

# =====================================================
# TAB: TRANSPORT
# =====================================================
with tab_trans_tab:
    if df_trans is not None:
        st.markdown("#### Transport – mărfuri și pasageri")
        c1, c2 = st.columns(2)
        with c1:
            fig_marf = px.line(
                df_trans,
                x="Perioadă",
                y="Total mărfuri transportate, mii tone",
                markers=True,
                template="simple_white",
            )
            st.plotly_chart(fig_marf, use_container_width=True)
        with c2:
            fig_pas = px.line(
                df_trans,
                x="Perioadă",
                y="Total, mii pasageri",
                markers=True,
                template="simple_white",
            )
            st.plotly_chart(fig_pas, use_container_width=True)
    else:
        st.info("Nu s-au putut încărca datele pentru transport.")

# =====================================================
# TAB: INVESTIȚII DIRECTE
# =====================================================
with tab_inv:
    st.markdown("#### Investiții directe acumulate (mil. USD)")
    fig_fdi = px.line(df_real, x=COL_YEAR, y=COL_FDI, markers=True, template="simple_white")
    st.plotly_chart(fig_fdi, use_container_width=True)
