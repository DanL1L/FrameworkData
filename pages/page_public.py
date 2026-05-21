import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import os
from utils.state import page_header, kpi_card, kpi_row
from utils.charts import line_chart, bar_chart
from data.demo_data import YEARS_STR, sold_pib
from utils.api_public import get_buget_trim_bns


# ── Loaders ───────────────────────────────────────────────────────────────────

def _find(filename: str, extra_dirs: list = None) -> str | None:
    """Cauta un fisier in locatiile standard ale proiectului."""
    base = os.path.dirname(__file__)
    candidates = [
        f"data/{filename}",
        filename,
        os.path.join(base, f"../data/{filename}"),
        os.path.join(base, filename),
    ] + (extra_dirs or [])
    return next((p for p in candidates if os.path.exists(p)), None)


@st.cache_data(ttl=300, show_spinner=False)
def _load_bpn() -> dict:
    """
    Date_Public_BPN.xlsx — sheets: Venituri, Cheltuieli, Deficit BPN
    DataFrame indexat pe indicatori, coloane = ani (int).
    """
    path = _find("Date_Public_BPN.xlsx")
    if path is None:
        return {"ok": False, "eroare": "Date_Public_BPN.xlsx negasit in /data"}
    try:
        df_v = pd.read_excel(path, sheet_name="Venituri",    index_col=0)
        df_c = pd.read_excel(path, sheet_name="Cheltuieli",  index_col=0)
        df_d = pd.read_excel(path, sheet_name="Deficit BPN", index_col=0)
        return {"ok": True, "venituri": df_v, "cheltuieli": df_c, "deficit": df_d}
    except Exception as e:
        return {"ok": False, "eroare": str(e)}


@st.cache_data(ttl=300, show_spinner=False)
def _load_vc() -> dict:
    """
    Data_Venituri_Cheltuieli.xlsx — date lunare agregate anual.
    Sheets: Venituri | Cheltuieli_F | Cheltuieli_CE
    Returneaza DataFrames anuale cu coloane per componenta (mil. lei).
    2025 are 11 luni — marcat ca partial.
    """
    path = _find("Data_Venituri_Cheltuieli.xlsx")
    if path is None:
        return {"ok": False, "eroare": "Data_Venituri_Cheltuieli.xlsx negasit in /data"}
    try:
        xl = pd.ExcelFile(path)

        # ── Venituri ─────────────────────────────────────────────────────────
        df_v = pd.read_excel(xl, sheet_name="Venituri")
        df_v["Date"] = pd.to_datetime(df_v["Date"], errors="coerce")
        df_v["An"]   = df_v["Date"].dt.year
        # Numar luni per an → marcheaza partial
        luni_per_an  = df_v.groupby("An")["Date"].count()
        df_van = df_v.groupby("An").sum(numeric_only=True)
        df_van["luni"] = luni_per_an

        # Redenumire coloane scurte pentru grafic
        rename_v = {
            "Impozit pe venitul persoanelor fizice":              "Imp. venit fizic",
            "Impozit pe venitul persoanelor juridice":            "Imp. venit juridic",
            "Imp. pe proprietate":                                "Proprietate",
            "TVA local":                                          "TVA local",
            "TVA la marfurile importate":                         "TVA import",
            "Accize total":                                       "Accize",
            "Contribuţii de asigurări sociale de stat obligatorii": "Contrib. sociale",
            "Prime de asigurare obligatorie de asistenţă medicală": "Prime asig. med.",
            "Granturi":                                           "Granturi",
            "Alte venituri":                                      "Alte venituri",
            "TOTAL VENITURI":                                     "Total venituri",
        }
        df_van = df_van.rename(columns=rename_v)

        # ── Cheltuieli_CE (pe clasificatie economica) ─────────────────────────
        df_ce = pd.read_excel(xl, sheet_name="Cheltuieli_CE", header=1)
        df_ce.columns = [str(c).strip() for c in df_ce.columns]
        df_ce["Date"] = pd.to_datetime(df_ce["Date"], errors="coerce")
        df_ce = df_ce.dropna(subset=["Date"])
        df_ce["An"]   = df_ce["Date"].dt.year
        df_cean = df_ce.groupby("An").sum(numeric_only=True)

        # ── Cheltuieli_F (pe clasificatie functionala) ─────────────────────────
        df_f = pd.read_excel(xl, sheet_name="Cheltuieli_F")
        df_f["Date"] = pd.to_datetime(df_f["Date"], errors="coerce")
        df_f = df_f.dropna(subset=["Date"])
        df_f["An"]   = df_f["Date"].dt.year
        df_fan = df_f.groupby("An").sum(numeric_only=True)

        # Ani disponibili cu date complete (>= 10 luni)
        ani_ok  = sorted([a for a, l in luni_per_an.items() if l >= 10])
        an_max  = max(ani_ok)
        partial = luni_per_an.get(an_max, 12) < 12

        return {
            "ok": True,
            "venituri": df_van,
            "chelt_ec": df_cean,
            "chelt_fc": df_fan,
            "ani": ani_ok,
            "an_max": an_max,
            "partial": partial,
            "luni_max": int(luni_per_an.get(an_max, 12)),
        }
    except Exception as e:
        return {"ok": False, "eroare": str(e)}


@st.cache_data(ttl=300, show_spinner=False)
def _load_datorie() -> dict:
    """
    Date_Sector_Public.xlsx — sheet: Public
    Coloane: An, Datorie totală (% PIB), Datorie externa (% PIB), Sold bugetar etc.
    """
    path = _find("Date_Sector_Public.xlsx")
    if path is None:
        return {"ok": False, "eroare": "Date_Sector_Public.xlsx negasit in /data"}
    try:
        df = pd.read_excel(path, sheet_name="Public")
        df.columns = [str(c).strip() for c in df.columns]
        # Normalizeaza coloana An
        df["An"] = pd.to_numeric(df["An"], errors="coerce").astype("Int64")
        df = df.dropna(subset=["An"]).sort_values("An").reset_index(drop=True)
        return {"ok": True, "data": df}
    except Exception as e:
        return {"ok": False, "eroare": str(e)}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct_pib(df: pd.DataFrame, indicator: str, ani: list) -> list:
    pib = df.loc["PIB"]
    return [round(df.loc[indicator, a] / pib[a] * 100, 2) for a in ani if a in df.columns]


def _ani_comuni(df: pd.DataFrame, ani_ref: list) -> list:
    return [a for a in ani_ref if a in df.columns]


def _col(df: pd.DataFrame, pattern: str) -> str | None:
    """Gaseste prima coloana care contine pattern (case-insensitive)."""
    pattern_low = pattern.lower()
    return next((c for c in df.columns if pattern_low in c.lower()), None)


# ── Paleta culori — albastru gradient ────────────────────────────────────────
CULORI_VEN = ["#0D2B6B","#1A4FA0","#2D6EC8","#5B9BD5","#8CB4E1","#B8D4EE","#D9E8F7"]
CULORI_CHELT = ["#0D2B6B","#1A4FA0","#2D6EC8","#5B9BD5","#8CB4E1","#B8D4EE","#D9E8F7"]


def render():
    page_header(
        "Sectorul Public",
        "Finante publice, executie bugetara BPN, datorie publică· 2019–2025",
        "Ministerul Finantelor — Executie bugetara",
        "amber"
    )

    # ── Incarca date ──────────────────────────────────────────────────────────
    bpn      = _load_bpn()
    dat_res  = _load_datorie()
    vc       = _load_vc()
    res_bns  = get_buget_trim_bns()
    df_bns   = res_bns["data"]
    bpn_ok   = bpn["ok"]
    dat_ok   = dat_res["ok"]
    vc_ok    = vc["ok"]

    # Date BPN
    if bpn_ok:
        df_v  = bpn["venituri"]
        df_c  = bpn["cheltuieli"]
        df_d  = bpn["deficit"]
        ANI_V = _ani_comuni(df_v, [2019,2020,2021,2022,2023,2024,2025])
        ANI_C = _ani_comuni(df_c, [2019,2020,2021,2022,2023,2024,2025])
        ANI_VS = [str(a) for a in ANI_V]
        ANI_CS = [str(a) for a in ANI_C]
        tot_ven_pib   = _pct_pib(df_v, "Total venituri",   ANI_V)
        tot_chelt_pib = _pct_pib(df_c, "Cheltuieli total", ANI_C)
        ven_last   = tot_ven_pib[-1]
        chelt_last = tot_chelt_pib[-1]
        sold_last  = round(
            df_d.loc["Deficitul general", ANI_C[-1]] / df_d.loc["PIB", ANI_C[-1]] * 100, 1
        ) if "Deficitul general" in df_d.index else -3.4
    else:
        ANI_VS = YEARS_STR; ANI_CS = YEARS_STR
        ven_last = 34.2; chelt_last = 38.3; sold_last = -4.1

    # Date datorie — din Date_Sector_Public.xlsx
    if dat_ok:
        df_pub   = dat_res["data"]
        col_dat  = _col(df_pub, "datorie total")      # "Datorie totală (% PIB)"
        col_dext = _col(df_pub, "datorie extern")     # "Datorie externa (% PIB)"
        col_sold = _col(df_pub, "sold bugetar")       # "Sold bugetar (% PIB)"

        # Filtrare ani cu date complete pentru datorie
        df_dat = df_pub.dropna(subset=[col_dat]).copy() if col_dat else df_pub.copy()
        ani_dat_int = df_dat["An"].tolist()
        ani_dat_str = [str(a) for a in ani_dat_int]
        dat_tot  = df_dat[col_dat].round(2).tolist()  if col_dat  else []
        dat_ext  = df_dat[col_dext].round(2).tolist() if col_dext else []
        dat_int  = [round(t - e, 2) for t, e in zip(dat_tot, dat_ext)] if (dat_tot and dat_ext) else []
        dat_last = dat_tot[-1] if dat_tot else 37.6
    else:
        ani_dat_str = YEARS_STR
        dat_tot     = [26.2, 34.8, 34.2, 33.6, 32.1, 31.2]
        dat_ext     = []
        dat_int     = []
        dat_last    = 31.2

    kpi_row([
        kpi_card("Venituri BPN", f"{ven_last:.1f}", "% PIB",
                 f"an {ANI_VS[-1] if bpn_ok else '2025'}", True, "amber"),
        kpi_card("Cheltuieli BPN", f"{chelt_last:.1f}", "% PIB",
                 "presiune bugetara", False, "amber"),
        kpi_card("Sold BPN", f"{sold_last:.1f}", "% PIB",
                 "deficit bugetar", False, "amber"),
        kpi_card("Datorie publica", f"{dat_last:.1f}", "% PIB",
                 "sub pragul UE de 60%", dat_last < 60, "amber"),
    ])

    tab1, tab2, tab3 = st.tabs([
        "Executie bugetara", "Structura BPN", "Datorie publică"
    ])

    def _layout(h=300):
        return dict(
            height=h, paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
            yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
            legend=dict(orientation="h", y=1.05, x=0,
                        font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
        )

    # ── Tab 1: Executie bugetara — date din Data_Venituri_Cheltuieli.xlsx ──────
    with tab1:
        if vc_ok:
            df_van  = vc["venituri"]
            df_cean = vc["chelt_ec"]
            ani_vc  = [a for a in vc["ani"] if a >= 2018]
            ani_str = [str(a) + ("*" if a == vc["an_max"] and vc["partial"] else "") for a in ani_vc]
            partial_note = f"* {vc['an_max']}: date pentru {vc['luni_max']} luni" if vc["partial"] else ""

            # ── Grafic 1: Evolutia venituri si cheltuieli absolute (mil. lei) ─
            st.markdown('<div class="chart-card"><div class="chart-card-title">Evolutia venituri si cheltuieli bugetare (mil. lei) · 2018–2025</div>', unsafe_allow_html=True)

            col_tot_ven   = "Total venituri"
            col_tot_chelt = "Total" if "Total" in df_cean.columns else next(
                (c for c in df_cean.columns if "total" in c.lower()), None)

            fig_ev = go.Figure()
            if col_tot_ven in df_van.columns:
                ven_vals = [df_van.loc[a, col_tot_ven] / 1000 for a in ani_vc if a in df_van.index]
                fig_ev.add_trace(go.Scatter(
                    x=ani_str, y=[round(v, 1) for v in ven_vals],
                    name="Venituri totale",
                    mode="lines+markers",
                    line=dict(color="#1D9E75", width=2.5),
                    marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(29,158,117,0.06)",
                    hovertemplate="Venituri <b>%{x}</b>: %{y:,.2f} mld. lei<extra></extra>",
                ))
            if col_tot_chelt:
                chelt_vals = [df_cean.loc[a, col_tot_chelt] / 1000 for a in ani_vc if a in df_cean.index]
                fig_ev.add_trace(go.Scatter(
                    x=ani_str[:len(chelt_vals)], y=[round(v, 1) for v in chelt_vals],
                    name="Cheltuieli totale",
                    mode="lines+markers",
                    line=dict(color="#E24B4A", width=2.5),
                    marker=dict(size=6),
                    hovertemplate="Cheltuieli <b>%{x}</b>: %{y:,.2f} mld. lei<extra></extra>",
                ))

            fig_ev.update_layout(**{
                **_layout(300),
                "showlegend": True,
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mld. lei"),
            })
            st.plotly_chart(fig_ev, use_container_width=True, config={"displayModeBar": False})
            if partial_note:
                st.caption(partial_note)
            # ── Grafic 2: Stacked bar venituri pe componente ──────────────────
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura veniturilor bugetare (mil. lei) · componente</div>', unsafe_allow_html=True)

            COL_VEN = [
                ("Imp. venit fizic",   "#0D2B6B"),
                ("Imp. venit juridic", "#1A4FA0"),
                ("TVA local",          "#2D6EC8"),
                ("TVA import",         "#4A87D4"),
                ("Accize",             "#5B9BD5"),
                ("Contrib. sociale",   "#7BB0E0"),
                ("Prime asig. med.",   "#8CB4E1"),
                ("Granturi",           "#B8D4EE"),
                ("Alte venituri",      "#D9E8F7"),
            ]

            fig_vstr = go.Figure()
            for col, color in COL_VEN:
                if col in df_van.columns:
                    vals = [df_van.loc[a, col] / 1000 if a in df_van.index else 0
                            for a in ani_vc]
                    fig_vstr.add_trace(go.Bar(
                        name=col, x=ani_str, y=[round(v, 2) for v in vals],
                        marker_color=color, opacity=0.92,
                        hovertemplate=f"<b>{col}</b> %{{x}}: %{{y:,.2f}} mld. lei<extra></extra>",
                    ))

            # Linie total
            if col_tot_ven in df_van.columns:
                tot_v = [df_van.loc[a, col_tot_ven] / 1000 if a in df_van.index else 0
                         for a in ani_vc]
                fig_vstr.add_trace(go.Scatter(
                    name="Total venituri", x=ani_str, y=[round(v, 1) for v in tot_v],
                    mode="lines+markers+text",
                    line=dict(color="#0D1F3C", width=2.5),
                    marker=dict(size=5, color="#0D1F3C"),
                    text=[f"{v:.1f}" for v in tot_v],
                    textposition="top center",
                    textfont=dict(size=9, color="#0D1F3C"),
                    hovertemplate="Total <b>%{x}</b>: %{y:,.2f} mld. lei<extra></extra>",
                ))

            fig_vstr.update_layout(**{
                **_layout(380),
                "barmode": "stack",
                "showlegend": True,
                "legend": dict(orientation="h", y=-0.22, x=0,
                               font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mld. lei"),
            })
            st.plotly_chart(fig_vstr, use_container_width=True, config={"displayModeBar": False})
            if partial_note:
                st.caption(partial_note)
            # ── Grafic 3: Stacked bar cheltuieli pe clasificatia economica ────
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura cheltuielilor bugetare, clasificatie economica (mil. lei)</div>', unsafe_allow_html=True)

            COL_CHELT_EC = [
                ("Cheltuieli de personal", "#0D2B6B"),
                ("Bunuri și servicii",     "#1A4FA0"),
                ("Dobânzi",                "#2D6EC8"),
                ("Subvenții",              "#4A87D4"),
                ("Granturi acordate",      "#5B9BD5"),
                ("Prestații sociale",      "#7BB0E0"),
                ("Alte cheltuieli",        "#8CB4E1"),
                ("Mijloace fixe",          "#B8D4EE"),
                ("Stocuri de materiale",   "#CADAED"),
            ]

            fig_cstr = go.Figure()
            for col, color in COL_CHELT_EC:
                if col in df_cean.columns:
                    ani_ce_ok = [a for a in ani_vc if a in df_cean.index]
                    ani_ce_str = [str(a) + ("*" if a == vc["an_max"] and vc["partial"] else "")
                                  for a in ani_ce_ok]
                    vals = [max(0, df_cean.loc[a, col] / 1000) for a in ani_ce_ok]
                    fig_cstr.add_trace(go.Bar(
                        name=col, x=ani_ce_str, y=[round(v, 2) for v in vals],
                        marker_color=color, opacity=0.92,
                        hovertemplate=f"<b>{col}</b> %{{x}}: %{{y:,.2f}} mld. lei<extra></extra>",
                    ))

            # Linie total cheltuieli
            if col_tot_chelt:
                ani_ce_ok = [a for a in ani_vc if a in df_cean.index]
                ani_ce_str = [str(a) + ("*" if a == vc["an_max"] and vc["partial"] else "")
                              for a in ani_ce_ok]
                tot_c = [df_cean.loc[a, col_tot_chelt] / 1000 for a in ani_ce_ok]
                fig_cstr.add_trace(go.Scatter(
                    name="Total cheltuieli", x=ani_ce_str, y=[round(v, 1) for v in tot_c],
                    mode="lines+markers+text",
                    line=dict(color="#0D1F3C", width=2.5),
                    marker=dict(size=5, color="#0D1F3C"),
                    text=[f"{v:.1f}" for v in tot_c],
                    textposition="top center",
                    textfont=dict(size=9, color="#0D1F3C"),
                    hovertemplate="Total <b>%{x}</b>: %{y:,.2f} mld. lei<extra></extra>",
                ))

            fig_cstr.update_layout(**{
                **_layout(380),
                "barmode": "stack",
                "showlegend": True,
                "legend": dict(orientation="h", y=-0.22, x=0,
                               font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mld. lei"),
            })
            st.plotly_chart(fig_cstr, use_container_width=True, config={"displayModeBar": False})
            if partial_note:
                st.caption(partial_note)
            # ── Grafic 4: Cheltuieli clasificatie functionala ─────────────────
            df_fan = vc["chelt_fc"]
            col_fn = [c for c in df_fan.columns
                      if c not in ["Total Cheltuieli și active nefinanciare",
                                   "Total cheltuieli conf. raportului Min Fin",
                                   "(ocrotirea muncii)* inclusiv transferuri între instituțiile  BS "]
                      and df_fan[c].sum() > 0]

            if col_fn:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Structura cheltuielilor, clasificatie functionala (mil. lei)</div>', unsafe_allow_html=True)
                PALETTE_FC = ["#0D2B6B","#185FA5","#2D6EC8","#1D9E75","#0F6E56",
                              "#854F0B","#534AB7","#993556","#888780","#E24B4A"]
                ani_fc_ok  = [a for a in ani_vc if a in df_fan.index]
                ani_fc_str = [str(a) + ("*" if a == vc["an_max"] and vc["partial"] else "")
                              for a in ani_fc_ok]
                fig_fc = go.Figure()
                for i, col in enumerate(col_fn):
                    vals = [max(0, df_fan.loc[a, col] / 1000) if a in df_fan.index else 0
                            for a in ani_fc_ok]
                    fig_fc.add_trace(go.Bar(
                        name=col[:30], x=ani_fc_str, y=[round(v, 2) for v in vals],
                        marker_color=PALETTE_FC[i % len(PALETTE_FC)], opacity=0.88,
                        hovertemplate=f"<b>{col[:40]}</b> %{{x}}: %{{y:,.2f}} mld. lei<extra></extra>",
                    ))
                fig_fc.update_layout(**{
                    **_layout(380),
                    "barmode": "stack",
                    "showlegend": True,
                    "legend": dict(orientation="h", y=-0.30, x=0,
                                   font=dict(size=8), bgcolor="rgba(0,0,0,0)"),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                                  zeroline=False, title="mld. lei"),
                })
                st.plotly_chart(fig_fc, use_container_width=True, config={"displayModeBar": False})
                if partial_note:
                    st.caption(partial_note)
            # ── Sold bugetar ──────────────────────────────────────────────────
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Sold bugetar (Venituri − Cheltuieli, mld. lei)</div>', unsafe_allow_html=True)
                if col_tot_ven in df_van.columns and col_tot_chelt:
                    ani_sold = [a for a in ani_vc if a in df_van.index and a in df_cean.index]
                    ani_sold_str = [str(a) + ("*" if a == vc["an_max"] and vc["partial"] else "")
                                    for a in ani_sold]
                    sold_vals_vc = [
                        round((df_van.loc[a, col_tot_ven] - df_cean.loc[a, col_tot_chelt]) / 1000, 2)
                        for a in ani_sold
                    ]
                    c_sold = ["#1D9E75" if v >= 0 else "#E24B4A" for v in sold_vals_vc]
                    fig_sold = go.Figure(go.Bar(
                        x=ani_sold_str, y=sold_vals_vc,
                        marker_color=c_sold, opacity=0.88,
                        text=[f"{v:+.2f}" for v in sold_vals_vc],
                        textposition="outside",
                        textfont=dict(size=9, color="#444441"),
                        hovertemplate="<b>%{x}</b>: %{y:+.2f} mld. lei<extra></extra>",
                    ))
                    fig_sold.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                    fig_sold.update_layout(**{**_layout(260), "yaxis": dict(
                        gridcolor="#f1efe8", tickfont=dict(size=10), title="mld. lei"
                    )})
                    st.plotly_chart(fig_sold, use_container_width=True, config={"displayModeBar": False})
            with col2:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Variatie anuala venituri si cheltuieli (%)</div>', unsafe_allow_html=True)
                if col_tot_ven in df_van.columns and col_tot_chelt:
                    ven_ser = pd.Series(
                        [df_van.loc[a, col_tot_ven] for a in ani_vc if a in df_van.index],
                        index=[a for a in ani_vc if a in df_van.index]
                    )
                    chelt_ser = pd.Series(
                        [df_cean.loc[a, col_tot_chelt] for a in ani_vc if a in df_cean.index],
                        index=[a for a in ani_vc if a in df_cean.index]
                    )
                    var_v = ven_ser.pct_change().fillna(0) * 100
                    var_c = chelt_ser.pct_change().fillna(0) * 100

                    fig_var = go.Figure()
                    fig_var.add_trace(go.Bar(
                        name="Venituri", x=ani_str[:len(var_v)],
                        y=var_v.round(1).tolist(),
                        marker_color="#1D9E75", opacity=0.80,
                        hovertemplate="Venituri <b>%{x}</b>: %{y:+.2f}%<extra></extra>",
                    ))
                    fig_var.add_trace(go.Bar(
                        name="Cheltuieli", x=ani_str[:len(var_c)],
                        y=var_c.round(1).tolist(),
                        marker_color="#E24B4A", opacity=0.70,
                        hovertemplate="Cheltuieli <b>%{x}</b>: %{y:+.2f}%<extra></extra>",
                    ))
                    fig_var.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                    fig_var.update_layout(**{
                        **_layout(260),
                        "barmode": "group",
                        "showlegend": True,
                        "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), title="%"),
                    })
                    st.plotly_chart(fig_var, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: MinFin</div></div>', unsafe_allow_html=True)

        else:
            st.warning(f"Data_Venituri_Cheltuieli.xlsx indisponibil: {vc.get('eroare','')}") 

    # ── Tab 2: Structura BPN ──────────────────────────────────────────────────
    with tab2:
        if not bpn_ok:
            st.warning(f"Date_Public_BPN.xlsx indisponibil: {bpn.get('eroare','')}")
        else:
            # ── Grafic 1: Venituri BPN in PIB ────────────────────────────────
            st.markdown('<div class="chart-card"><div class="chart-card-title">Raportul veniturilor BPN în PIB, 2019–2025 (%)</div>', unsafe_allow_html=True)

            IND_VEN = [
                "Impozite venit fizic",
                "Impozite venit juridic",
                "TVA",
                "Accize",
                "Contribuții salariale",
                "Granturi ",
                "Altele",
            ]

            fig_v = go.Figure()
            for i, ind in enumerate(IND_VEN):
                if ind not in df_v.index:
                    continue
                vals  = _pct_pib(df_v, ind, ANI_V)
                label = ind.strip()
                fig_v.add_trace(go.Bar(
                    name=label, x=ANI_VS, y=vals,
                    marker_color=CULORI_VEN[i], opacity=0.92,
                    hovertemplate=f"<b>{label}</b> %{{x}}: %{{y:.2f}}% PIB<extra></extra>",
                ))

            fig_v.add_trace(go.Scatter(
                name="Total venituri", x=ANI_VS, y=tot_ven_pib,
                mode="lines+markers+text",
                line=dict(color="#0D1F3C", width=2.5),
                marker=dict(size=5, color="#0D1F3C"),
                text=[f"{v:.1f}%" for v in tot_ven_pib],
                textposition="top center",
                textfont=dict(size=9, color="#0D1F3C"),
                hovertemplate="Total venituri <b>%{x}</b>: %{y:.2f}% PIB<extra></extra>",
            ))
            fig_v.update_layout(**{
                **_layout(380),
                "barmode": "stack",
                "showlegend": True,
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="% PIB",
                              tickformat=".0f", ticksuffix="%",
                              range=[0, max(tot_ven_pib) * 1.15]),
            })
            st.plotly_chart(fig_v, use_container_width=True, config={"displayModeBar": False})

            tbl_v = pd.DataFrame(
                {ind.strip(): _pct_pib(df_v, ind, ANI_V) for ind in IND_VEN if ind in df_v.index},
                index=ANI_VS
            )
            tbl_v["Total venituri"] = tot_ven_pib
            tbl_v.index.name = "An"
            st.dataframe(
                tbl_v.map(lambda x: f"{x:.1f}%").reset_index(),
                use_container_width=True, hide_index=True,
            )
            st.markdown('<div class="chart-source">Sursa: MinFin </div></div>', unsafe_allow_html=True)

            st.markdown("")

            # ── Grafic 2: Cheltuieli BPN in PIB ──────────────────────────────
            st.markdown('<div class="chart-card"><div class="chart-card-title">Raportul cheltuielilor BPN în PIB, 2019–2025 (%)</div>', unsafe_allow_html=True)

            IND_CHELT = [
                "Cheltuieli de personal",
                "Bunuri și servicii",
                "Dobânzi",
                "Prestații sociale",
                "Alte active nefinanciare",
                "Investiții capitale",
                "Alte cheltuieli",
            ]

            fig_c = go.Figure()
            for i, ind in enumerate(IND_CHELT):
                if ind not in df_c.index:
                    continue
                vals = _pct_pib(df_c, ind, ANI_C)
                fig_c.add_trace(go.Bar(
                    name=ind, x=ANI_CS, y=vals,
                    marker_color=CULORI_CHELT[i], opacity=0.92,
                    hovertemplate=f"<b>{ind}</b> %{{x}}: %{{y:.2f}}% PIB<extra></extra>",
                ))

            fig_c.add_trace(go.Scatter(
                name="Cheltuieli total", x=ANI_CS, y=tot_chelt_pib,
                mode="lines+markers+text",
                line=dict(color="#0D1F3C", width=2.5),
                marker=dict(size=5, color="#0D1F3C"),
                text=[f"{v:.1f}%" for v in tot_chelt_pib],
                textposition="top center",
                textfont=dict(size=9, color="#0D1F3C"),
                hovertemplate="Cheltuieli total <b>%{x}</b>: %{y:.2f}% PIB<extra></extra>",
            ))
            fig_c.update_layout(**{
                **_layout(380),
                "barmode": "stack",
                "showlegend": True,
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="% PIB",
                              tickformat=".0f", ticksuffix="%",
                              range=[0, max(tot_chelt_pib) * 1.15]),
            })
            st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})

            tbl_c = pd.DataFrame(
                {ind: _pct_pib(df_c, ind, ANI_C) for ind in IND_CHELT if ind in df_c.index},
                index=ANI_CS
            )
            tbl_c["Cheltuieli total"] = tot_chelt_pib
            tbl_c.index.name = "An"
            st.dataframe(
                tbl_c.map(lambda x: f"{x:.1f}%").reset_index(),
                use_container_width=True, hide_index=True,
            )
            st.markdown('<div class="chart-source">Sursa: MinFin</div></div>', unsafe_allow_html=True)

    # ── Tab 3: Datorie publica ────────────────────────────────────────────────
    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            # Datorie totala vs externa din Date_Sector_Public.xlsx
            st.markdown('<div class="chart-card"><div class="chart-card-title">Datorie publica totala si externa (% PIB)</div>', unsafe_allow_html=True)
            fig_dat = go.Figure()

            if dat_tot:
                fig_dat.add_trace(go.Scatter(
                    name="Datorie totala", x=ani_dat_str, y=dat_tot,
                    mode="lines+markers",
                    line=dict(color="#854F0B", width=2.5),
                    marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(133,79,11,0.07)",
                    hovertemplate="Totala <b>%{x}</b>: %{y:.2f}%<extra></extra>",
                ))
            if dat_ext:
                fig_dat.add_trace(go.Scatter(
                    name="Datorie externa", x=ani_dat_str, y=dat_ext,
                    mode="lines+markers",
                    line=dict(color="#534AB7", width=2, dash="dash"),
                    marker=dict(size=5),
                    hovertemplate="Externa <b>%{x}</b>: %{y:.2f}%<extra></extra>",
                ))
            if dat_int:
                fig_dat.add_trace(go.Scatter(
                    name="Datorie interna", x=ani_dat_str, y=dat_int,
                    mode="lines+markers",
                    line=dict(color="#185FA5", width=2, dash="dot"),
                    marker=dict(size=5),
                    hovertemplate="Interna <b>%{x}</b>: %{y:.2f}%<extra></extra>",
                ))

            # fig_dat.add_hline(y=60, line_dash="dot", line_color="#E24B4A", line_width=1,
            #                   annotation_text="Prag UE 60%", annotation_font_size=9)
            fig_dat.update_layout(
                height=280, paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                           zeroline=False, title="% PIB"),
            )
            st.plotly_chart(fig_dat, use_container_width=True, config={"displayModeBar": False})
            sursa_dat = "Date_Sector_Public.xlsx · col. Datorie totală" if dat_ok else "date demo"
            st.markdown(f'<div class="chart-source">Sursa: MinFin </div></div>', unsafe_allow_html=True)

        with col2:
            # Deficit BPN din Date_Public_BPN.xlsx
            st.markdown('<div class="chart-card"><div class="chart-card-title">Deficit BPN (% PIB)</div>', unsafe_allow_html=True)
            if bpn_ok and "Deficitul general" in df_d.index:
                pib_d    = df_d.loc["PIB"]
                def_vals = [
                    round(df_d.loc["Deficitul general", a] / pib_d[a] * 100, 1)
                    for a in ANI_C if a in df_d.columns
                ]
                colors_def = ["#E24B4A" if v < 0 else "#1D9E75" for v in def_vals]
                fig_def = go.Figure(go.Bar(
                    x=ANI_CS, y=def_vals,
                    marker_color=colors_def, opacity=0.88,
                    text=[f"{v:.1f}%" for v in def_vals],
                    textposition="outside",
                    textfont=dict(size=9, color="#444441"),
                    hovertemplate="<b>%{x}</b>: %{y:.2f}% PIB<extra></extra>",
                ))
                fig_def.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                # fig_def.add_hline(y=-3.0, line_dash="dot", line_color="#BA7517", line_width=1,
                #                   annotation_text="Prag -3% PIB", annotation_font_size=9)
                fig_def.update_layout(
                    height=280, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                               zeroline=False, title="% PIB"),
                )
                st.plotly_chart(fig_def, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: MinFin · Deficit BPN</div></div>', unsafe_allow_html=True)
            else:
                fig_def = bar_chart(YEARS_STR, sold_pib, "amber", ylabel="% PIB", neg_color="amber")
                st.plotly_chart(fig_def, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: Ministerul Finantelor</div></div>', unsafe_allow_html=True)

        # Tabel sinteza datorie + fiscal
        st.markdown('<div class="chart-card"><div class="chart-card-title">Indicatori fiscali si datorie publica 2019–2025</div>', unsafe_allow_html=True)

        if dat_ok and bpn_ok:
            ani_tbl = [a for a in [2019,2020,2021,2022,2023,2024,2025]
                       if a in df_v.columns and a in df_c.columns]
            rows = {"Indicator": ["Venituri (% PIB)", "Cheltuieli (% PIB)", "Deficit (% PIB)",
                                  "Datorie totala (% PIB)", "Datorie externa (% PIB)"]}
            for a in ani_tbl:
                dat_row  = df_pub[df_pub["An"] == a]
                dat_t    = f"{dat_row[col_dat].values[0]:.1f}%"  if col_dat  and not dat_row.empty else "N/A"
                dat_e    = f"{dat_row[col_dext].values[0]:.1f}%" if col_dext and not dat_row.empty else "N/A"
                deficit  = f"{round(df_d.loc['Deficitul general',a]/df_d.loc['PIB',a]*100,1)}%" \
                           if ("Deficitul general" in df_d.index and a in df_d.columns) else "N/A"
                rows[str(a)] = [
                    f"{round(df_v.loc['Total venituri',a]/df_v.loc['PIB',a]*100,1)}%",
                    f"{round(df_c.loc['Cheltuieli total',a]/df_c.loc['PIB',a]*100,1)}%",
                    deficit, dat_t, dat_e,
                ]
            fis_tbl = pd.DataFrame(rows)
        else:
            fis_tbl = pd.DataFrame({
                "Indicator": ["Venituri (% PIB)", "Cheltuieli (% PIB)", "Sold (% PIB)", "Datorie (% PIB)"],
                "2022": ["33.3%", "36.6%", "-3.2%", "34.5%"],
                "2023": ["33.7%", "38.8%", "-5.1%", "34.3%"],
                "2024": ["34.3%", "38.7%", "-4.4%", "37.5%"],
                "2025": ["34.2%", "38.3%", "-4.1%", "37.6%"],
            })
        st.dataframe(fis_tbl, use_container_width=True, hide_index=True)
        st.markdown('<div class="chart-source">Sursa: MinFin</div></div>', unsafe_allow_html=True)
