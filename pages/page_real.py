"""
pages/page_real.py — Sectorul Real
Date din: data/Real.xlsx
Sheets: Real | PIB | PIB_utilizari | Industrie | Industrie_Prel |
        Agricultura | Tranport | Comert_Intern
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import os

from utils.state import page_header, kpi_card, kpi_row


def _find(filename: str) -> str | None:
    base = os.path.dirname(__file__)
    for p in [f"data/{filename}", filename,
              os.path.join(base, f"../data/{filename}")]:
        if os.path.exists(p):
            return p
    return None


@st.cache_data(ttl=300, show_spinner=False)
def _load_real() -> dict:
    path = _find("Real.xlsx")
    if path is None:
        return {"ok": False, "eroare": "Real.xlsx negasit in /data"}
    try:
        def _int_an(df):
            df["An"] = pd.to_numeric(df["An"], errors="coerce").astype("Int64")
            return df.dropna(subset=["An"]).sort_values("An").reset_index(drop=True)

        df_real   = _int_an(pd.read_excel(path, sheet_name="Real"))
        df_pib    = _int_an(pd.read_excel(path, sheet_name="PIB"))
        df_use    = _int_an(pd.read_excel(path, sheet_name="PIB_utilizari"))
        df_ind    = _int_an(pd.read_excel(path, sheet_name="Industrie"))
        df_prel   = _int_an(pd.read_excel(path, sheet_name="Industrie_Prel"))
        df_agr    = pd.read_excel(path, sheet_name="Agricultura")
        df_trans  = pd.read_excel(path, sheet_name="Tranport")
        df_comert = pd.read_excel(path, sheet_name="Comert_Intern")

        for col in df_ind.columns:
            if col != "An":
                df_ind[col] = pd.to_numeric(df_ind[col], errors="coerce")

        df_pib["PIB curent"]     = pd.to_numeric(df_pib["PIB curent"],     errors="coerce")
        df_pib["PIB comparabil"] = pd.to_numeric(df_pib["PIB comparabil"], errors="coerce")
        df_pib["Crestere reala (%)"] = (
            df_pib["PIB comparabil"] / df_pib["PIB curent"].shift(1) - 1
        ) * 100

        denom_pp = df_pib["PIB curent"].shift(1).replace(0, pd.NA)
        for ram, col_cur, col_comp in [
            ("Agricultura (p.p.)",   "Agricultura, silvicultura si pescuit curent",  "Agricultura, silvicultura si pescuit comparabil"),
            ("Industrie (p.p.)",     "Industrie curent",    "Industrie comparabil"),
            ("Constructii (p.p.)",   "Constructii curent",  "Constructii comparabil"),
            ("Servicii (p.p.)",      "Servicii curent",     "Servicii comparabil"),
            ("Impozite nete (p.p.)", "Impozite nete pe produse curent", "Impozite nete pe produse comparabil"),
        ]:
            if col_cur in df_pib.columns and col_comp in df_pib.columns:
                df_pib[ram] = (df_pib[col_comp] - df_pib[col_cur].shift(1)) / denom_pp * 100

        denom_u = df_use["PIB curent"].shift(1).replace(0, pd.NA)
        for label, col_cur, col_comp in [
            ("Consum gospodarii (p.p.)", "Consumul final al gospodariilor populatiei curent", "Consumul final al gospodariilor populatiei comparabil"),
            ("Consum public (p.p.)",     "Consumul final al administratiei publice curent",   "Consumul final al administratiei publice comparabil"),
            ("Formare capital (p.p.)",   "Formarea bruta de capital curent",                  "Formarea bruta de capital comparabil"),
            ("Export (p.p.)",            "Export curent",  "Export comparabil"),
            ("Import (p.p.)",            "Import curent",  "Import comparabil"),
        ]:
            if col_cur in df_use.columns and col_comp in df_use.columns:
                df_use[label] = (df_use[col_comp] - df_use[col_cur].shift(1)) / denom_u * 100

        if "Industria prelucratoare" in df_prel.columns:
            denom_i = df_prel["Industria prelucratoare"].shift(1).replace(0, pd.NA)
            for c in [x for x in df_prel.columns if x not in ["An", "Industria prelucratoare"]]:
                df_prel[c + " (p.p.)"] = (df_prel[c] - df_prel[c].shift(1)) / denom_i * 100

        df_agr["An"] = pd.to_numeric(df_agr["An"], errors="coerce").astype("Int64")
        df_agr["Trimestrul"] = df_agr["Trimestrul"].astype(str)
        df_agr["Perioada"] = (df_agr["An"].astype(str) + " "
                              + df_agr["Trimestrul"].str.replace("Trimestrul ", "T"))
        df_agr.columns = [c.replace("ș","s").replace("ă","a").replace("î","i")
                           .replace("â","a").replace("ț","t") for c in df_agr.columns]
        df_agr = df_agr.dropna(subset=["An"]).sort_values(["An", "Trimestrul"])

        df_trans["An"] = pd.to_numeric(df_trans["An"], errors="coerce").astype("Int64")
        df_trans["Trimestrul"] = df_trans["Trimestrul"].astype(str)
        df_trans["Perioada"] = (df_trans["An"].astype(str) + " "
                                + df_trans["Trimestrul"].str.replace("Trimestrul ", "T"))

        df_comert["An"] = pd.to_numeric(df_comert["An"], errors="coerce").astype("Int64")
        df_comert["Trimestrul"] = df_comert["Trimestrul"].astype(str)
        df_comert["Perioada"] = (df_comert["An"].astype(str) + " "
                                 + df_comert["Trimestrul"].str.replace("Trimestrul ", "T"))
        for col in df_comert.columns:
            if col not in ["An", "Trimestrul", "Perioada"]:
                df_comert[col] = pd.to_numeric(df_comert[col], errors="coerce")
        df_comert = df_comert.dropna(subset=["An"]).sort_values(["An", "Trimestrul"])

        return {
            "ok": True,
            "real": df_real, "pib": df_pib, "use": df_use,
            "ind": df_ind, "prel": df_prel,
            "agr": df_agr, "trans": df_trans, "comert": df_comert,
        }
    except Exception as e:
        return {"ok": False, "eroare": str(e)}


def _layout(h=300, legend=False):
    d = dict(
        height=h, paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="IBM Plex Sans", size=11, color="#444441"),
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=legend,
        xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
    )
    if legend:
        d["legend"] = dict(orientation="h", y=1.05, x=0,
                           font=dict(size=10), bgcolor="rgba(0,0,0,0)")
    return d


PALETTE = ["#185FA5","#1D9E75","#854F0B","#534AB7","#993556",
           "#0F6E56","#378ADD","#5DCAA5","#EF9F27","#888780"]


def render():
    page_header(
        "Sectorul Real",
        "PIB, industrie, agricultura, comert, transport · 2010–2024",
        "BNS — Conturi nationale · Real.xlsx",
        "green"
    )

    data = _load_real()
    if not data["ok"]:
        st.error(f"Eroare la incarcarea datelor: {data['eroare']}")
        return

    df_real  = data["real"]
    df_pib   = data["pib"]
    df_use   = data["use"]
    df_ind   = data["ind"]
    df_prel  = data["prel"]
    df_agr   = data["agr"]
    df_trans = data["trans"]
    df_com   = data["comert"]

    last_pib  = df_pib.iloc[-1]
    last_real = df_real.iloc[-1]
    prev_real = df_real.iloc[-2] if len(df_real) >= 2 else last_real
    an_last   = int(last_pib["An"])

    pib_gr  = last_pib.get("Crestere reala (%)", None)
    ind_val = last_real.get("Producția industrială, mil. lei", None)
    agr_val = last_real.get("Producția agricolă, mil. lei", None)

    def _chg(cur, prev_row, col):
        v = prev_row.get(col, None)
        return (cur / v - 1) * 100 if cur and v and v != 0 else None

    ind_chg = _chg(ind_val, prev_real, "Producția industrială, mil. lei")
    agr_chg = _chg(agr_val, prev_real, "Producția agricolă, mil. lei")

    kpi_row([
        kpi_card(f"PIB real {an_last}", f"{pib_gr:+.1f}" if pib_gr else "N/A", "%",
                 f"crestere vs {an_last-1}", pib_gr and pib_gr > 0, "green"),
        kpi_card("Productia industriala",
                 f"{ind_val/1e3:,.1f}" if ind_val else "N/A", "mld. lei",
                 f"{ind_chg:+.1f}% vs {an_last-1}" if ind_chg else "", ind_chg and ind_chg > 0, "green"),
        kpi_card("Productia agricola",
                 f"{agr_val/1e3:,.1f}" if agr_val else "N/A", "mld. lei",
                 f"{agr_chg:+.1f}% vs {an_last-1}" if agr_chg else "", agr_chg and agr_chg > 0, "green"),
        kpi_card("Comert interior", "+6.6", "%",
                 "trim. IV 2024 / trim. IV 2023", True, "green"),
    ])

    tab_pib, tab_ind, tab_agr, tab_com, tab_trans = st.tabs([
        "PIB", "Industrie", "Agricultura", "Comert intern", "Transport"
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB PIB
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_pib:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">PIB nominal (mil. lei)</div>', unsafe_allow_html=True)
            fig = go.Figure(go.Scatter(
                x=df_pib["An"].astype(str), y=df_pib["PIB curent"],
                mode="lines+markers",
                line=dict(color="#1D9E75", width=2.5),
                marker=dict(size=6, color="#1D9E75"),
                fill="tozeroy", fillcolor="rgba(29,158,117,0.08)",
                hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>",
            ))
            fig.update_layout(**{**_layout(280), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. lei"
            )})
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet PIB</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Crestere reala a PIB (%, fata de anul precedent)</div>', unsafe_allow_html=True)
            df_gr = df_pib.dropna(subset=["Crestere reala (%)"]).copy()
            colors_gr = ["#1D9E75" if v >= 0 else "#E24B4A" for v in df_gr["Crestere reala (%)"]]
            fig2 = go.Figure(go.Bar(
                x=df_gr["An"].astype(str), y=df_gr["Crestere reala (%)"].round(1),
                marker_color=colors_gr, opacity=0.88,
                text=[f"{v:.1f}%" for v in df_gr["Crestere reala (%)"]],
                textposition="outside",
                textfont=dict(size=9, color="#444441"),
                hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
            ))
            fig2.add_hline(y=0, line_color="#e8e4dc", line_width=1)
            fig2.update_layout(**{**_layout(280), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10), title="% an/an"
            )})
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet PIB (calcule)</div></div>', unsafe_allow_html=True)

        ramuri_cols = [
            ("Agricultura, silvicultura si pescuit curent", "Agricultura"),
            ("Industrie curent", "Industrie"),
            ("Constructii curent", "Constructii"),
            ("Servicii curent", "Servicii"),
            ("Impozite nete pe produse curent", "Impozite nete"),
        ]
        ramuri_prezente = [(c, n) for c, n in ramuri_cols if c in df_pib.columns]

        if ramuri_prezente:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura PIB pe ramuri (% din PIB)</div>', unsafe_allow_html=True)
            df_share = df_pib.dropna(subset=["PIB curent"]).copy()
            fig3 = go.Figure()
            for i, (col, name) in enumerate(ramuri_prezente):
                share = df_share[col] / df_share["PIB curent"] * 100
                fig3.add_trace(go.Bar(
                    name=name,
                    x=df_share["An"].astype(str), y=share.round(1),
                    marker_color=PALETTE[i], opacity=0.9,
                    hovertemplate=f"<b>{name}</b> %{{x}}: %{{y:.1f}}%<extra></extra>",
                ))
            fig3.update_layout(**{
                **_layout(320, legend=True),
                "barmode": "stack",
                "margin": dict(l=10, r=10, t=10, b=70),
                "legend": dict(orientation="h", y=-0.22, x=0, xanchor="left",
                               yanchor="top", font=dict(size=9),
                               bgcolor="rgba(0,0,0,0)", itemwidth=40),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="% PIB",
                              ticksuffix="%", range=[0, 100]),
            })
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet PIB</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Contributia la cresterea PIB (p.p.) — selecteaza anul</div>', unsafe_allow_html=True)
        all_years = sorted(df_pib["An"].dropna().unique())
        sel_yr = st.selectbox("An pentru contributii:", all_years,
                              index=len(all_years)-1, key="pib_contrib_yr")

        col5, col6 = st.columns(2)
        with col5:
            st.markdown('<div class="chart-card-title">Contributia resurselor (p.p.)</div>', unsafe_allow_html=True)
            pp_ram = ["Agricultura (p.p.)","Industrie (p.p.)","Constructii (p.p.)",
                      "Servicii (p.p.)","Impozite nete (p.p.)"]
            row_r  = df_pib[df_pib["An"] == sel_yr]
            if not row_r.empty and pp_ram[0] in row_r.columns:
                r = row_r.iloc[0]
                data_r = pd.DataFrame({
                    "Ramura": [c.replace(" (p.p.)","") for c in pp_ram],
                    "pp": [r[c] for c in pp_ram if c in r.index],
                }).dropna()
                colors_r = ["#1D9E75" if v >= 0 else "#E24B4A" for v in data_r["pp"]]
                fig6 = go.Figure(go.Bar(
                    x=data_r["Ramura"], y=data_r["pp"].round(2),
                    marker_color=colors_r, opacity=0.88,
                    text=[f"{v:.2f}" for v in data_r["pp"]],
                    textposition="outside", textfont=dict(size=9),
                    hovertemplate="<b>%{x}</b>: %{y:+.2f} p.p.<extra></extra>",
                ))
                fig6.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig6.update_layout(**{**_layout(300), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="p.p."
                )})
                st.plotly_chart(fig6, use_container_width=True, config={"displayModeBar": False})

        with col6:
            st.markdown('<div class="chart-card-title">Contributia utilizarilor (p.p.)</div>', unsafe_allow_html=True)
            pp_use = ["Consum gospodarii (p.p.)","Consum public (p.p.)",
                      "Formare capital (p.p.)","Export (p.p.)","Import (p.p.)"]
            row_u  = df_use[df_use["An"] == sel_yr]
            if not row_u.empty and pp_use[0] in row_u.columns:
                u = row_u.iloc[0]
                data_u = pd.DataFrame({
                    "Utilizare": [c.replace(" (p.p.)","") for c in pp_use],
                    "pp": [u[c] for c in pp_use if c in u.index],
                }).dropna()
                colors_u = ["#1D9E75" if v >= 0 else "#E24B4A" for v in data_u["pp"]]
                fig7 = go.Figure(go.Bar(
                    x=data_u["Utilizare"], y=data_u["pp"].round(2),
                    marker_color=colors_u, opacity=0.88,
                    text=[f"{v:.2f}" for v in data_u["pp"]],
                    textposition="outside", textfont=dict(size=9),
                    hovertemplate="<b>%{x}</b>: %{y:+.2f} p.p.<extra></extra>",
                ))
                fig7.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig7.update_layout(**{**_layout(300), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="p.p."
                )})
                st.plotly_chart(fig7, use_container_width=True, config={"displayModeBar": False})
        # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet PIB / PIB_utilizari (calcule)</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB INDUSTRIE
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_ind:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Productia industriala (mil. lei)</div>', unsafe_allow_html=True)
            col_ind = "Producția industrială, mil. lei"
            df_real_plot = df_real[df_real["An"] >= 2019].copy()
            fig_il = go.Figure(go.Scatter(
                x=df_real_plot["An"].astype(str), y=df_real_plot[col_ind],
                mode="lines+markers",
                line=dict(color="#185FA5", width=2.5),
                marker=dict(size=6),
                fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>",
            ))
            fig_il.update_layout(**{**_layout(280), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. lei"
            )})
            st.plotly_chart(fig_il, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Real</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Indicii volumului productiei industriale (% fata de an precedent)</div>', unsafe_allow_html=True)
            tbl_ind = df_ind.copy()
            tbl_ind["An"] = tbl_ind["An"].astype(int)
            tbl_ind = tbl_ind[tbl_ind["An"] >= 2019]
            rename_ind = {
                "Industria total,%":       "Total (%)",
                "Industria prelucratoare": "Prelucratoare (%)",
                "Industria extractivă":    "Extractiva (%)",
                "Industria energetică":    "Energetica (%)",
            }
            tbl_ind = tbl_ind.rename(columns={k: v for k, v in rename_ind.items()
                                               if k in tbl_ind.columns})
            cols_num = [c for c in tbl_ind.columns if c != "An"]
            tbl_disp = tbl_ind.copy()
            for col in cols_num:
                tbl_disp[col] = tbl_disp[col].apply(
                    lambda x: f"{x:.1f}" if pd.notna(x) else "—"
                )

            def _color_ind(val):
                try:
                    v = float(val)
                    if v > 100:   return "color: #0F6E56; font-weight: 500"
                    elif v < 100: return "color: #A32D2D; font-weight: 500"
                    return "color: #888780"
                except Exception:
                    return ""

            st.dataframe(
                tbl_disp.style.map(_color_ind, subset=cols_num),
                use_container_width=True,
                hide_index=True,
                height=min(430, 36 * (len(tbl_ind) + 1)),
            )
            st.markdown("""
            <div style="font-size:10px;color:#888780;font-family:IBM Plex Mono,monospace;
                        margin-top:4px;display:flex;gap:16px">
                <span><span style="color:#0F6E56;font-weight:500">▲</span> &gt;100% — crestere</span>
                <span><span style="color:#A32D2D;font-weight:500">▼</span> &lt;100% — scadere</span>
            </div>
            """, unsafe_allow_html=True)
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Industrie</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Contributia subramurilor la cresterea industriei prelucrătoare (p.p.) — selecteaza anul</div>', unsafe_allow_html=True)
        years_prel = sorted(df_prel["An"].dropna().unique())
        sel_ind_yr = st.selectbox("An:", years_prel, index=len(years_prel)-1, key="ind_prel_yr")
        row_prel = df_prel[df_prel["An"] == sel_ind_yr]
        if not row_prel.empty:
            r = row_prel.iloc[0]
            pp_cols = [c for c in df_prel.columns if c.endswith(" (p.p.)")]
            rows = [(c.replace(" (p.p.)",""), float(r[c]))
                    for c in pp_cols if pd.notna(r[c]) and round(r[c],1) != 0]
            if rows:
                df_pp = pd.DataFrame(rows, columns=["Subramura","pp"]).sort_values("pp")
                colors_pp = ["#1D9E75" if v >= 0 else "#E24B4A" for v in df_pp["pp"]]
                fig_pp = go.Figure(go.Bar(
                    x=df_pp["pp"].round(2), y=df_pp["Subramura"],
                    orientation="h", marker_color=colors_pp, opacity=0.85,
                    text=[f"{v:.2f}" for v in df_pp["pp"]],
                    textposition="outside", textfont=dict(size=8),
                    hovertemplate="<b>%{y}</b>: %{x:+.2f} p.p.<extra></extra>",
                ))
                fig_pp.add_vline(x=0, line_color="#e8e4dc", line_width=1)
                fig_pp.update_layout(
                    height=max(300, len(df_pp)*22),
                    paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                    margin=dict(l=10, r=60, t=10, b=10), showlegend=False,
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc",
                               tickfont=dict(size=9), title="p.p."),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9)),
                )
                st.plotly_chart(fig_pp, use_container_width=True, config={"displayModeBar": False})
        # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Industrie_Prel (calcule)</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB AGRICULTURA
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_agr:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Productia agricola anuala (mil. lei)</div>', unsafe_allow_html=True)
            fig_agr = go.Figure(go.Scatter(
                x=df_real["An"].astype(str),
                y=df_real["Producția agricolă, mil. lei"],
                mode="lines+markers",
                line=dict(color="#1D9E75", width=2.5),
                marker=dict(size=6),
                fill="tozeroy", fillcolor="rgba(29,158,117,0.08)",
                hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>",
            ))
            fig_agr.update_layout(**{**_layout(280), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. lei"
            )})
            st.plotly_chart(fig_agr, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Real</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Indici trimestriali volum productie agricola (%)</div>', unsafe_allow_html=True)
            col_tot  = next((c for c in df_agr.columns if "total" in c.lower() and "%" in c), None)
            col_veg  = next((c for c in df_agr.columns if "vegetal" in c.lower()), None)
            col_anim = next((c for c in df_agr.columns if "animal" in c.lower()), None)
            fig_aqt = go.Figure()
            for col, name, color, dash in [
                (col_tot,  "Total",      "#0F6E56", "dash"),
                (col_veg,  "Vegetala",   "#1D9E75", "solid"),
                (col_anim, "Animaliera", "#5DCAA5", "solid"),
            ]:
                if col and col in df_agr.columns:
                    df_agr[col] = pd.to_numeric(df_agr[col], errors="coerce")
                    fig_aqt.add_trace(go.Scatter(
                        x=df_agr["Perioada"], y=df_agr[col],
                        name=name, mode="lines+markers",
                        line=dict(color=color, width=2.5 if dash=="dash" else 1.8, dash=dash),
                        marker=dict(size=4),
                        hovertemplate=f"<b>{name}</b> %{{x}}: %{{y:.1f}}%<extra></extra>",
                    ))
            fig_aqt.add_hline(y=100, line_dash="dot", line_color="#888780", line_width=1,
                              annotation_text="100%", annotation_font_size=9)
            fig_aqt.update_layout(**{
                **_layout(280, legend=True),
                "xaxis": dict(showgrid=False, linecolor="#e8e4dc",
                              tickfont=dict(size=9), tickangle=-45),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), title="%"),
            })
            st.plotly_chart(fig_aqt, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Agricultura</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB COMERT INTERN
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_com:
        # Coloane exacte (cu spatiu trailing la Total)
        col_am   = "Comert cu amanuntul"
        col_rid  = "Comert cu ridicata"
        col_tot  = next((c for c in df_com.columns if "total comert" in c.lower()), None)

        # Convertim din lei în mld. lei pentru lizibilitate
        SCALE    = 1e9   # lei → mld. lei
        UNIT_LBL = "mld. lei"

        col1, col2 = st.columns(2)

        with col1:
            # ── Stacked bar: Amanuntul + Ridicata + linie Total ───────────────
            st.markdown(
                '<div class="chart-card"><div class="chart-card-title">'
                'Comert intern trimestrial — structura (mld. lei)'
                '</div>',
                unsafe_allow_html=True
            )

            fig_cs = go.Figure()

            # Bara 1: Comert cu amanuntul (albastru)
            if col_am in df_com.columns:
                am_vals = (df_com[col_am] / SCALE).round(3).tolist()
                fig_cs.add_trace(go.Bar(
                    name="Cu amănuntul",
                    x=df_com["Perioada"],
                    y=am_vals,
                    marker_color="#185FA5",
                    opacity=0.88,
                    hovertemplate="Amănuntul <b>%{x}</b>: %{y:,.2f} mld. lei<extra></extra>",
                ))

            # Bara 2: Comert cu ridicata (teal)
            if col_rid in df_com.columns:
                rid_vals = (df_com[col_rid] / SCALE).round(3).tolist()
                fig_cs.add_trace(go.Bar(
                    name="Cu ridicata",
                    x=df_com["Perioada"],
                    y=rid_vals,
                    marker_color="#1D9E75",
                    opacity=0.85,
                    hovertemplate="Ridicata <b>%{x}</b>: %{y:,.2f} mld. lei<extra></extra>",
                ))

            # Linie Total deasupra
            # if col_tot and col_tot in df_com.columns:
            #     tot_vals = (df_com[col_tot] / SCALE).round(3).tolist()
            #     fig_cs.add_trace(go.Scatter(
            #         name="Total comert",
            #         x=df_com["Perioada"],
            #         y=tot_vals,
            #         mode="lines+markers+text",
            #         line=dict(color="#0D1F3C", width=2.5),
            #         marker=dict(size=5, color="#0D1F3C"),
            #         text=[f"{v:.2f}" for v in tot_vals],
            #         textposition="top center",
            #         textfont=dict(size=8, color="#0D1F3C"),
            #         hovertemplate="Total <b>%{x}</b>: %{y:,.2f} mld. lei<extra></extra>",
            #     ))

            fig_cs.update_layout(**{
                **_layout(320, legend=True),
                "barmode": "stack",
                "legend": dict(orientation="h", y=1.05, x=0,
                               font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                "xaxis": dict(showgrid=False, linecolor="#e8e4dc",
                              tickfont=dict(size=9), tickangle=-45),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title=UNIT_LBL),
            })
            st.plotly_chart(fig_cs, use_container_width=True, config={"displayModeBar": False})
            # st.markdown(
            #     '<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Comert_Intern</div></div>',
            #     unsafe_allow_html=True
            # )

        with col2:
            # ── Crestere reala comert ─────────────────────────────────────────
            cols_gr = [c for c in [
                "Creștere reala comert",
                "Crestere reala comert cu amanuntul",
                "Crestere reala comert cu ridicata",
            ] if c in df_com.columns]

            st.markdown(
                '<div class="chart-card"><div class="chart-card-title">'
                'Crestere reala comert intern (% trimestrial)'
                '</div>',
                unsafe_allow_html=True
            )
            fig_cg = go.Figure()
            color_gr = ["#0D1F3C", "#185FA5", "#1D9E75"]
            dash_gr  = ["dash", "solid", "solid"]
            for i, col in enumerate(cols_gr):
                label = (col.replace("Creștere reala comert","Total")
                            .replace("Crestere reala comert cu ","")
                            .strip().capitalize()
                         or "Total")
                fig_cg.add_trace(go.Scatter(
                    x=df_com["Perioada"],
                    y=df_com[col],
                    name=label,
                    mode="lines+markers",
                    line=dict(color=color_gr[i % len(color_gr)],
                              width=2.5 if i == 0 else 1.8,
                              dash=dash_gr[i % len(dash_gr)]),
                    marker=dict(size=4),
                    hovertemplate=f"{label} <b>%{{x}}</b>: %{{y:+.1f}}%<extra></extra>",
                ))
            fig_cg.add_hline(y=0, line_dash="dot", line_color="#e8e4dc", line_width=1)
            fig_cg.update_layout(**{
                **_layout(320, legend=True),
                "legend": dict(orientation="h", y=1.05, x=0,
                               font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                "xaxis": dict(showgrid=False, linecolor="#e8e4dc",
                              tickfont=dict(size=9), tickangle=-45),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), title="%"),
            })
            st.plotly_chart(fig_cg, use_container_width=True, config={"displayModeBar": False})
            # st.markdown(
            #     '<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Comert_Intern</div></div>',
            #     unsafe_allow_html=True
            # )
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB TRANSPORT
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_trans:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Marfuri transportate total (mii tone)</div>', unsafe_allow_html=True)
            fig_tm = go.Figure(go.Scatter(
                x=df_trans["Perioada"],
                y=df_trans["Total mărfuri transportate, mii tone"],
                mode="lines+markers",
                line=dict(color="#534AB7", width=2),
                marker=dict(size=4),
                fill="tozeroy", fillcolor="rgba(83,74,183,0.08)",
                hovertemplate="<b>%{x}</b>: %{y:,.0f} mii tone<extra></extra>",
            ))
            fig_tm.update_layout(**{
                **_layout(260),
                "xaxis": dict(showgrid=False, linecolor="#e8e4dc",
                              tickfont=dict(size=9), tickangle=-45),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mii tone"),
            })
            st.plotly_chart(fig_tm, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Tranport</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Pasageri transportati total (mii)</div>', unsafe_allow_html=True)
            fig_tp = go.Figure(go.Scatter(
                x=df_trans["Perioada"],
                y=df_trans["Total, mii pasageri"],
                mode="lines+markers",
                line=dict(color="#185FA5", width=2),
                marker=dict(size=4),
                fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                hovertemplate="<b>%{x}</b>: %{y:,.0f} mii pasageri<extra></extra>",
            ))
            fig_tp.update_layout(**{
                **_layout(260),
                "xaxis": dict(showgrid=False, linecolor="#e8e4dc",
                              tickfont=dict(size=9), tickangle=-45),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mii pasageri"),
            })
            st.plotly_chart(fig_tp, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Tranport</div></div>', unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        cols_marf = [c for c in df_trans.columns
                     if "mărfuri" in c.lower() and "total" not in c.lower()]
        cols_pas  = [c for c in df_trans.columns
                     if "pasager" in c.lower() and "total" not in c.lower()]

        with col3:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura transport marfuri pe tip (mii tone)</div>', unsafe_allow_html=True)
            fig_sm = go.Figure()
            for i, col in enumerate(cols_marf):
                fig_sm.add_trace(go.Bar(
                    x=df_trans["Perioada"], y=df_trans[col],
                    name=col.replace(" mărfuri","").replace(", mii tone","").strip(),
                    marker_color=PALETTE[i], opacity=0.88,
                ))
            fig_sm.update_layout(**{
                **_layout(260, legend=True),
                "barmode": "stack",
                "xaxis": dict(showgrid=False, linecolor="#e8e4dc",
                              tickfont=dict(size=9), tickangle=-45),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mii tone"),
            })
            st.plotly_chart(fig_sm, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Tranport</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura transport pasageri pe tip (mii)</div>', unsafe_allow_html=True)
            fig_sp = go.Figure()
            for i, col in enumerate(cols_pas):
                fig_sp.add_trace(go.Bar(
                    x=df_trans["Perioada"], y=df_trans[col],
                    name=col.replace(" pasageri","").strip(),
                    marker_color=PALETTE[i], opacity=0.88,
                ))
            fig_sp.update_layout(**{
                **_layout(260, legend=True),
                "barmode": "stack",
                "xaxis": dict(showgrid=False, linecolor="#e8e4dc",
                              tickfont=dict(size=9), tickangle=-45),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mii pasageri"),
            })
            st.plotly_chart(fig_sp, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNS — Real.xlsx · sheet Tranport</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(
        '<p style="font-size:10px;color:#b4b2a9;font-family:IBM Plex Mono,monospace">'
        'Sursa: BNS statistica.gov.md · '
        'Platforma MEDD — Directia Analiza si Prognoza Macroeconomica.</p>',
        unsafe_allow_html=True
    )