import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.state import page_header, kpi_card, kpi_row
from data.excel_loader import load_monetar
from utils.data_loader import sursa_badge
from utils.api_bns import get_pib_sinteza


def render():
    page_header(
        "Sectorul Monetar",
        "Inflatie, rezerve, credite, depozite · 2007–2025",
        "BNM",
        "pink"
    )

    result = load_monetar()
    df     = result["data"]

    if df.empty:
        st.warning(f"Date indisponibile: {result.get('sursa', 'eroare')}")
        return

    YEARS_STR = [str(int(a)) for a in df["an"]]
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    def _safe(col): return last.get(col, None) if col in df.columns else None
    def _prev(col): return prev.get(col, None) if col in df.columns else None
    def _var(col):
        v, p = _safe(col), _prev(col)
        return ((v - p) / p * 100) if v and p and p != 0 else None

    # Coloane disponibile — suporta ambele versiuni Excel
    rez_col  = "rezerve_mil_eur" if "rezerve_mil_eur" in df.columns else "rezerve_mln_usd"
    dep_col  = "depozite_total_mil_lei" if "depozite_total_mil_lei" in df.columns else "depozite_mil_lei"

    rez_val  = _safe(rez_col);          rez_var  = _var(rez_col)
    ipc_val  = _safe("ipc_sfarsit_an")
    baza_val = _safe("baza_monetara_mil_lei")
    dep_val  = _safe(dep_col)
    an_last  = int(last["an"]); an_prev = int(prev["an"])
    rez_unit = "mil. EUR" if rez_col == "rezerve_mil_eur" else "mil. USD"

    # IPC medie anuala din BNS API
    res_tna = get_pib_sinteza()
    df_tna  = res_tna["data"]
    has_ipc_mediu   = not df_tna.empty and "ipc_mediu" in df_tna.columns
    ipc_mediu_last  = None
    if has_ipc_mediu:
        ipc_mediu_last = df_tna.iloc[-1].get("ipc_mediu", None)

    kpi_row([
        kpi_card("Rezerve BNM",
                 f"{rez_val:,.1f}" if rez_val else "N/A", rez_unit,
                 f"{rez_var:+.1f}% vs {an_prev}" if rez_var else "",
                 rez_var and rez_var > 0, "pink"),
        kpi_card("IPC sfarsit an",
                 f"{ipc_val:.1f}" if ipc_val else "N/A", "%",
                 f"inflatie la sfarsit de an {an_last}",
                 ipc_val and ipc_val < 10, "pink"),
        kpi_card("IPC medie anuala (BNS)",
                 f"{ipc_mediu_last:.1f}" if ipc_mediu_last else "N/A", "%",
                 f"medie {int(df_tna.iloc[-1]['an']) if has_ipc_mediu else ''}",
                 ipc_mediu_last and ipc_mediu_last < 105, "pink"),
        kpi_card("Baza monetara (MO)",
                 f"{baza_val:,.0f}" if baza_val else "N/A", "mil. lei",
                 f"depozite totale: {dep_val/1000:,.1f} mld." if dep_val else "",
                 True, "pink"),
    ])

    def _layout(h=280, legend=False):
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

    tab2, tab1, tab3, tab4 = st.tabs([
        "Date sector monetar",
        "Baza monetară",
        "Credite",
        "Structura depozitelor",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Date sector monetar (COD VECHI)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">IPC medie anuala (%)</div>', unsafe_allow_html=True)
            if has_ipc_mediu:
                ani_tna     = df_tna["an"].astype(str).tolist()
                ipc_vals_an = (df_tna["ipc_mediu"] - 100).tolist()
                colors_m = [
                    "#A32D2D" if v > 20 else
                    "#E24B4A" if v > 10 else
                    "#BA7517" if v > 5  else
                    "#1D9E75"
                    for v in ipc_vals_an
                ]
                fig_ipc_m = go.Figure(go.Bar(
                    x=ani_tna, y=ipc_vals_an,
                    marker_color=colors_m, opacity=0.88,
                    text=[f"{v:.1f}%" for v in ipc_vals_an],
                    textposition="outside",
                    textfont=dict(size=9, color="#444441"),
                    hovertemplate="<b>%{x}</b>: IPC mediu %{y:.1f}%<extra></extra>",
                ))
                fig_ipc_m.add_hline(y=5.0, line_dash="dot", line_color="#1D9E75",
                                    line_width=1.2, annotation_text="Tinta 5%",
                                    annotation_font_size=9)
                fig_ipc_m.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10),
                    title="%", range=[0, max(ipc_vals_an) * 1.15],
                )})
                st.plotly_chart(fig_ipc_m, use_container_width=True,
                                config={"displayModeBar": False})
                ts_tna   = res_tna.get("ts","")
                live_lbl = "live" if res_tna.get("live") else "date referinta"
                st.markdown(
                    f'<div class="chart-source">Sursa: BNS TNA01 ({live_lbl}) · '
                    f'saved query cc6bdb68 · {ts_tna}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info("IPC medie anuala indisponibila — API BNS offline.")
                # st.markdown('<div class="chart-source">Sursa: BNS TNA01</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">IPC la sfarsit de an (%)</div>', unsafe_allow_html=True)
            if "ipc_sfarsit_an" in df.columns:
                df_ipc    = df[df["an"] >= 2019].copy()
                years_ipc = df_ipc["an"].astype(str).tolist()
                vals_ipc  = df_ipc["ipc_sfarsit_an"].tolist()
                colors_ipc = [
                    "#A32D2D" if v > 20 else
                    "#E24B4A" if v > 10 else
                    "#BA7517" if v > 5  else
                    "#1D9E75"
                    for v in vals_ipc
                ]
                fig2 = go.Figure(go.Bar(
                    x=years_ipc, y=vals_ipc,
                    marker_color=colors_ipc, opacity=0.85,
                    text=[f"{v:.1f}%" for v in vals_ipc],
                    textposition="outside",
                    textfont=dict(size=9, color="#444441"),
                    hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>",
                ))
                fig2.add_hline(y=5.0, line_dash="dot", line_color="#1D9E75",
                               line_width=1.2, annotation_text="Tinta 5%",
                               annotation_font_size=9)
                fig2.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="%"
                )})
                st.plotly_chart(fig2, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f'<div class="chart-card"><div class="chart-card-title">Active oficiale de rezerva ({rez_unit})</div>', unsafe_allow_html=True)
            if rez_col in df.columns:
                fig3 = go.Figure(go.Scatter(
                    x=YEARS_STR, y=df[rez_col].tolist(),
                    mode="lines+markers",
                    line=dict(color="#185FA5", width=2.5), marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                    hovertemplate=f"<b>%{{x}}</b>: %{{y:,.0f}} {rez_unit}<extra></extra>",
                ))
                fig3.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10),
                    zeroline=False, title=rez_unit
                )})
                st.plotly_chart(fig3, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        with col4:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Rezerve — variatie anuala (%)</div>', unsafe_allow_html=True)
            if rez_col in df.columns:
                rez_pct    = df[rez_col].pct_change() * 100
                colors_rez = ["#1D9E75" if v >= 0 else "#E24B4A"
                              for v in rez_pct.fillna(0)]
                fig4 = go.Figure(go.Bar(
                    x=YEARS_STR, y=rez_pct.tolist(),
                    marker_color=colors_rez, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
                ))
                fig4.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig4.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="%"
                )})
                st.plotly_chart(fig4, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Calcule: BNM</div></div>', unsafe_allow_html=True)

        # Tabel sinteza
        st.markdown('<div class="chart-card"><div class="chart-card-title">Tabel sinteza — indicatori monetari</div>', unsafe_allow_html=True)
        cols_tbl = {
            "an":                    "An",
            "ipc_sfarsit_an":        "IPC sfarsit an (%)",
            "ipc_medie_an":          "IPC medie anuala (%)",
            "rezerve_mil_eur":       "Rezerve BNM (mil. EUR)",
            "rezerve_mln_usd":       "Rezerve BNM (mil. USD)",
            "rata_baza_pct":         "Rata de baza (%)",
            "baza_monetara_mil_lei": "MO — Bani lichizi (mil. lei)",
            "depozite_total_mil_lei":"Depozite totale (mil. lei)",
        }
        show_cols = [c for c in cols_tbl if c in df.columns]
        tbl = df[show_cols].rename(columns=cols_tbl).copy()
        tbl["An"] = tbl["An"].astype(int)
        for col in tbl.columns:
            if col == "An": continue
            if "%" in col:
                tbl[col] = tbl[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")
            else:
                tbl[col] = tbl[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        st.dataframe(tbl, use_container_width=True, hide_index=True, height=360)
        # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Baza monetara / Depozite (COD VECHI)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Bani lichizi in circulatie — MO (mil. lei)</div>', unsafe_allow_html=True)
            if "baza_monetara_mil_lei" in df.columns:
                fig5 = go.Figure(go.Scatter(
                    x=YEARS_STR, y=df["baza_monetara_mil_lei"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#854F0B", width=2.5), marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(133,79,11,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>",
                ))
                fig5.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10),
                    zeroline=False, title="mil. lei"
                )})
                st.plotly_chart(fig5, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Depozite totale (mil. lei)</div>', unsafe_allow_html=True)
            if dep_col in df.columns:
                fig6 = go.Figure(go.Scatter(
                    x=YEARS_STR, y=df[dep_col].tolist(),
                    mode="lines+markers",
                    line=dict(color="#534AB7", width=2.5), marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(83,74,183,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>",
                ))
                fig6.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10),
                    zeroline=False, title="mil. lei"
                )})
                st.plotly_chart(fig6, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Tabel — MO & Depozite totale</div>', unsafe_allow_html=True)
        cols_b = {c: c for c in ["an", "baza_monetara_mil_lei", dep_col] if c in df.columns}
        tbl_b = df[list(cols_b)].rename(columns={
            "an": "An",
            "baza_monetara_mil_lei":  "MO — Bani lichizi (mil. lei)",
            "depozite_total_mil_lei": "Depozite totale (mil. lei)",
            "depozite_mil_lei":       "Depozite (mil. lei)",
        }).copy()
        tbl_b["An"] = tbl_b["An"].astype(int)
        for col in tbl_b.columns:
            if col != "An":
                tbl_b[col] = tbl_b[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        st.dataframe(tbl_b, use_container_width=True, hide_index=True)
        # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3 — CREDITE (NOU)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Credite noi acordate — juridice si fizice (mil. lei)</div>', unsafe_allow_html=True)
            fig_cr = go.Figure()
            if "credite_juridice_mil_lei" in df.columns:
                fig_cr.add_trace(go.Bar(
                    name="Pers. juridice", x=YEARS_STR,
                    y=df["credite_juridice_mil_lei"].tolist(),
                    marker_color="#185FA5", opacity=0.88,
                    hovertemplate="<b>%{x}</b> Juridice: %{y:,.0f}<extra></extra>",
                ))
            if "credite_fizice_mil_lei" in df.columns:
                fig_cr.add_trace(go.Bar(
                    name="Pers. fizice", x=YEARS_STR,
                    y=df["credite_fizice_mil_lei"].tolist(),
                    marker_color="#534AB7", opacity=0.85,
                    hovertemplate="<b>%{x}</b> Fizice: %{y:,.0f}<extra></extra>",
                ))
            if "credite_total_mil_lei" in df.columns:
                fig_cr.add_trace(go.Scatter(
                    name="Total", x=YEARS_STR,
                    y=df["credite_total_mil_lei"].tolist(),
                    mode="lines+markers+text",
                    line=dict(color="#0D1F3C", width=2.5),
                    marker=dict(size=5),
                    text=[f"{v/1000:.1f}" for v in df["credite_total_mil_lei"]],
                    textposition="top center",
                    textfont=dict(size=8, color="#0D1F3C"),
                    hovertemplate="<b>%{x}</b> Total: %{y:,.0f}<extra></extra>",
                ))
            fig_cr.update_layout(**{
                **_layout(320, legend=True), "barmode": "stack",
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mil. lei"),
            })
            st.plotly_chart(fig_cr, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura creditelor noi persoane fizice (mil. lei)</div>', unsafe_allow_html=True)
            fig_crf = go.Figure()
            for col_k, name, color in [
                ("credite_consum_mil_lei",  "Consum",       "#534AB7"),
                ("credite_imobil_mil_lei",  "Imobil",       "#185FA5"),
                ("credite_alte_mil_lei",    "Alte scopuri", "#888780"),
            ]:
                if col_k in df.columns:
                    fig_crf.add_trace(go.Bar(
                        name=name, x=YEARS_STR,
                        y=df[col_k].tolist(),
                        marker_color=color, opacity=0.88,
                        hovertemplate=f"<b>%{{x}}</b> {name}: %{{y:,.0f}}<extra></extra>",
                    ))
            fig_crf.update_layout(**{
                **_layout(320, legend=True), "barmode": "stack",
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mil. lei"),
            })
            st.plotly_chart(fig_crf, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Credite juridice — variatie anuala (%)</div>', unsafe_allow_html=True)
            if "credite_juridice_mil_lei" in df.columns:
                var_j = df["credite_juridice_mil_lei"].pct_change() * 100
                c_j   = ["#1D9E75" if v >= 0 else "#E24B4A" for v in var_j.fillna(0)]
                fig_vj = go.Figure(go.Bar(
                    x=YEARS_STR, y=var_j.tolist(),
                    marker_color=c_j, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
                ))
                fig_vj.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig_vj.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="%"
                )})
                st.plotly_chart(fig_vj, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Calcule: BNM</div></div>', unsafe_allow_html=True)

        with col4:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Credite fizice — variatie anuala (%)</div>', unsafe_allow_html=True)
            if "credite_fizice_mil_lei" in df.columns:
                var_f = df["credite_fizice_mil_lei"].pct_change() * 100
                c_f   = ["#1D9E75" if v >= 0 else "#E24B4A" for v in var_f.fillna(0)]
                fig_vf = go.Figure(go.Bar(
                    x=YEARS_STR, y=var_f.tolist(),
                    marker_color=c_f, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
                ))
                fig_vf.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig_vf.update_layout(**{**_layout(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="%"
                )})
                st.plotly_chart(fig_vf, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Calcule: BNM</div></div>', unsafe_allow_html=True)

        # Depozite noi la termen
        st.markdown('<div class="chart-card"><div class="chart-card-title">Depozite noi la termen atrase — juridice si fizice (mil. lei)</div>', unsafe_allow_html=True)
        fig_dt = go.Figure()
        if "depozite_termen_juridice_mil_lei" in df.columns:
            fig_dt.add_trace(go.Bar(
                name="De la juridice", x=YEARS_STR,
                y=df["depozite_termen_juridice_mil_lei"].tolist(),
                marker_color="#1D9E75", opacity=0.88,
                hovertemplate="<b>%{x}</b> Juridice: %{y:,.0f}<extra></extra>",
            ))
        if "depozite_termen_fizice_mil_lei" in df.columns:
            fig_dt.add_trace(go.Bar(
                name="De la fizice", x=YEARS_STR,
                y=df["depozite_termen_fizice_mil_lei"].tolist(),
                marker_color="#0F6E56", opacity=0.80,
                hovertemplate="<b>%{x}</b> Fizice: %{y:,.0f}<extra></extra>",
            ))
        fig_dt.update_layout(**{
            **_layout(280, legend=True), "barmode": "stack",
            "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                          zeroline=False, title="mil. lei"),
        })
        st.plotly_chart(fig_dt, use_container_width=True, config={"displayModeBar": False})
        # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        # Tabel credite
        st.markdown('<div class="chart-card"><div class="chart-card-title">Date complete — Credite (mil. lei)</div>', unsafe_allow_html=True)
        cr_rename = {
            "an": "An",
            "credite_juridice_mil_lei":          "Credite juridice",
            "credite_fizice_mil_lei":            "Credite fizice",
            "credite_total_mil_lei":             "Total credite",
            "credite_consum_mil_lei":            "din care: Consum",
            "credite_imobil_mil_lei":            "din care: Imobil",
            "credite_alte_mil_lei":              "din care: Alte",
            "depozite_termen_juridice_mil_lei":  "Dep. termen jur.",
            "depozite_termen_fizice_mil_lei":    "Dep. termen fiz.",
        }
        tbl_cr = df[[c for c in cr_rename if c in df.columns]].rename(columns=cr_rename).copy()
        tbl_cr["An"] = tbl_cr["An"].astype(int)
        for col in tbl_cr.columns:
            if col != "An":
                tbl_cr[col] = tbl_cr[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        st.dataframe(tbl_cr, use_container_width=True, hide_index=True)
        # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4 — DEPOZITE STRUCTURA (NOU)
    # ═══════════════════════════════════════════════════════════════════════════
    with tab4:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura depozitelor bancare (mil. lei)</div>', unsafe_allow_html=True)
            fig_dep = go.Figure()
            for col_k, name, color in [
                ("depozite_vedere_mn_mil_lei", "La vedere MN",  "#185FA5"),
                ("depozite_termen_mn_mil_lei", "La termen MN",  "#534AB7"),
                ("depozite_valuta_mil_lei",    "In valuta",     "#854F0B"),
            ]:
                if col_k in df.columns:
                    fig_dep.add_trace(go.Bar(
                        name=name, x=YEARS_STR,
                        y=df[col_k].tolist(),
                        marker_color=color, opacity=0.88,
                        hovertemplate=f"<b>%{{x}}</b> {name}: %{{y:,.0f}}<extra></extra>",
                    ))
            if "depozite_total_mil_lei" in df.columns:
                fig_dep.add_trace(go.Scatter(
                    name="Total", x=YEARS_STR,
                    y=df["depozite_total_mil_lei"].tolist(),
                    mode="lines+markers+text",
                    line=dict(color="#0D1F3C", width=2.5),
                    marker=dict(size=5),
                    text=[f"{v/1000:.1f}" for v in df["depozite_total_mil_lei"]],
                    textposition="top center",
                    textfont=dict(size=8, color="#0D1F3C"),
                    hovertemplate="<b>%{x}</b> Total: %{y:,.0f}<extra></extra>",
                ))
            fig_dep.update_layout(**{
                **_layout(320, legend=True), "barmode": "stack",
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                              zeroline=False, title="mil. lei"),
            })
            st.plotly_chart(fig_dep, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Depozite totale — variatie anuala (%)</div>', unsafe_allow_html=True)
            if "depozite_total_mil_lei" in df.columns:
                var_dep = df["depozite_total_mil_lei"].pct_change() * 100
                c_dep   = ["#1D9E75" if v >= 0 else "#E24B4A" for v in var_dep.fillna(0)]
                fig_vd  = go.Figure(go.Bar(
                    x=YEARS_STR, y=var_dep.tolist(),
                    marker_color=c_dep, opacity=0.85,
                    text=[f"{v:+.1f}%" for v in var_dep.fillna(0)],
                    textposition="outside",
                    textfont=dict(size=9, color="#444441"),
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
                ))
                fig_vd.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig_vd.update_layout(**{**_layout(320), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="%"
                )})
                st.plotly_chart(fig_vd, use_container_width=True, config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Calcule: BNM</div></div>', unsafe_allow_html=True)

        # Structura procentuala 100%
        st.markdown('<div class="chart-card"><div class="chart-card-title">Structura depozitelor (%) — vedere MN / termen MN / valuta</div>', unsafe_allow_html=True)
        dep_struct = ["depozite_vedere_mn_mil_lei", "depozite_termen_mn_mil_lei", "depozite_valuta_mil_lei"]
        if all(c in df.columns for c in dep_struct) and "depozite_total_mil_lei" in df.columns:
            fig_dpct = go.Figure()
            for col_k, name, color in [
                ("depozite_vedere_mn_mil_lei", "La vedere MN",  "#185FA5"),
                ("depozite_termen_mn_mil_lei", "La termen MN",  "#534AB7"),
                ("depozite_valuta_mil_lei",    "In valuta",     "#854F0B"),
            ]:
                pct = (df[col_k] / df["depozite_total_mil_lei"] * 100).round(1).tolist()
                fig_dpct.add_trace(go.Bar(
                    name=name, x=YEARS_STR, y=pct,
                    marker_color=color, opacity=0.88,
                    text=[f"{v:.0f}%" for v in pct],
                    textposition="inside",
                    textfont=dict(size=9, color="white"),
                    hovertemplate=f"<b>%{{x}}</b> {name}: %{{y:.1f}}%<extra></extra>",
                ))
                fig_dpct.update_layout(**{
                    **_layout(300, legend=True),
                    "barmode": "stack",

                    "legend": dict(
                        orientation="h",
                        y=-0.22,
                        x=0.5,
                        xanchor="center",
                        yanchor="top",
                        font=dict(size=10),
                        bgcolor="rgba(0,0,0,0)"
                    ),

                    "margin": dict(
                        l=10,
                        r=10,
                        t=10,
                        b=70
                    ),

                    "yaxis": dict(
                        gridcolor="#f1efe8",
                        tickfont=dict(size=10),
                        title="%",
                        ticksuffix="%",
                        range=[0, 100]
                    ),
                })
            st.plotly_chart(fig_dpct, use_container_width=True, config={"displayModeBar": False})
        # st.markdown('<div class="chart-source">Calcule: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        # Tabel depozite
        st.markdown('<div class="chart-card"><div class="chart-card-title">Date complete — Depozite (mil. lei)</div>', unsafe_allow_html=True)
        dep_rename = {
            "an":                         "An",
            "depozite_vedere_mn_mil_lei":  "La vedere MN",
            "depozite_termen_mn_mil_lei":  "La termen MN",
            "depozite_valuta_mil_lei":     "In valuta",
            "depozite_total_mil_lei":      "Total",
            "baza_monetara_mil_lei":       "Bani lichizi MO",
        }
        tbl_dep = df[[c for c in dep_rename if c in df.columns]].rename(columns=dep_rename).copy()
        tbl_dep["An"] = tbl_dep["An"].astype(int)
        for col in tbl_dep.columns:
            if col != "An":
                tbl_dep[col] = tbl_dep[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        st.dataframe(tbl_dep, use_container_width=True, hide_index=True)
        # st.markdown('<div class="chart-source">Sursa: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    ts_tna   = res_tna.get("ts","")
    live_lbl = "live" if res_tna.get("live") else "date referinta"
    st.markdown(
        f'<p style="font-size:10px;color:#b4b2a9;font-family:IBM Plex Mono,monospace">'
        f'Sursa datelor: BNS / BNM ·'
        f'Platforma MEDD — Directia Analiza si Prognoza Macroeconomica.</p>',
        unsafe_allow_html=True,
    )