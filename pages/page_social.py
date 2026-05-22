"""
pages/page_social.py — Sectorul Social
Date trimestriale: data/Date_Sector_Social.xlsx  (excel_loader.load_social)
Date anuale:       BNS API via utils/api_social.py
  - Castig salarial mediu: saved query 61bba808-4c00-4a35-9c0d-946caaa33cb8
  - Rata activitate/ocupare/somaj: saved query 08546b68-0d6b-4746-9623-1c5c50916b8f
  - Populatie ocupata pe gen (barbati/femei/total): saved query ef9f71d7-a859-4d5d-9c03-1cf128ff9616
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils.state import page_header, kpi_card, kpi_row
from utils.data_loader import sursa_badge
from data.excel_loader import load_social
from utils.api_social import (
    get_salarii_anual,
    get_piata_muncii_anual,
    get_populatie_someri_anual,
    get_populatie_gen_anual,
    get_salarii_trim_bns,
    get_ocupare_trim_bns,
)


def render():
    page_header(
        "Sectorul Social",
        "Piata muncii, somaj, ocupare, salarii · trimestrial / anual",
        "BNS",
        "teal"
    )

    # ── Date trimestriale: BNS (primar) → Excel (fallback) ───────────────────
    result_sal_trim = get_salarii_trim_bns()
    result_occ_trim = get_ocupare_trim_bns()
    df_sal_trim = result_sal_trim["data"]
    df_occ_trim = result_occ_trim["data"]
    bns_trim_live = result_sal_trim["live"] or result_occ_trim["live"]

    # Construim df_q unificat din BNS sau Excel
    result_q = load_social()
    df_q_excel = result_q["data"]

    if bns_trim_live and not df_sal_trim.empty:
        # Combina sal_trim + occ_trim pe (an, trim)
        merge_keys = ["an"] + (["trim"] if "trim" in df_sal_trim.columns else [])
        if "trim" in df_sal_trim.columns and "trim" in df_occ_trim.columns:
            df_q = df_sal_trim.merge(df_occ_trim, on=merge_keys, how="outer", suffixes=("", "_occ"))
            if "trim_label_occ" in df_q.columns:
                df_q["trim_label"] = df_q["trim_label"].fillna(df_q["trim_label_occ"])
                df_q = df_q.drop(columns=["trim_label_occ"])
        else:
            df_q = df_sal_trim.copy()
        # Normalizeaza coloane BNS la conventia Excel
        df_q = df_q.rename(columns={
            "rata_somaj":      "rata_somaj_pct",
            "rata_ocupare":    "rata_ocupare_pct",
            "pop_ocupata_mii": "populatie_ocupata_mii",
        })
        df_q = df_q.sort_values(merge_keys).reset_index(drop=True)
        sursa_trim = "BNS SAL010 + SAL020 (live)"
    else:
        df_q = df_q_excel
        sursa_trim = "Date_Sector_Social.xlsx"

    # ── Date anuale din BNS API ───────────────────────────────────────────────
    result_sal = get_salarii_anual()
    result_pm  = get_piata_muncii_anual()
    result_pop = get_populatie_someri_anual()
    result_gen = get_populatie_gen_anual()
    df_sal     = result_sal["data"]
    df_pm      = result_pm["data"]
    df_pop     = result_pop["data"]
    df_gen     = result_gen["data"]

    # # ── Badge surse ───────────────────────────────────────────────────────────
    # col_b1, col_b2 = st.columns(2)
    # with col_b1:
    #     st.markdown(sursa_badge(result_q), unsafe_allow_html=True)
    # with col_b2:
    #     sal_live = result_sal["live"] or result_pm["live"]
    #     badge_api = {
    #         "live":  sal_live,
    #         "sursa": "BNS PX-Web API — date anuale",
    #     }
    #     st.markdown(sursa_badge(badge_api), unsafe_allow_html=True)
    # st.markdown("")

    # ── KPI — din trimestrale (ultimul trimestru disponibil) ──────────────────
    if not df_q.empty:
        last = df_q.iloc[-1]
        prev_yr = df_q[df_q["an"] == (int(last["an"]) - 1)]
        prev = prev_yr.iloc[-1] if not prev_yr.empty else (
            df_q.iloc[-2] if len(df_q) >= 2 else last
        )

        somaj_val  = last.get("rata_somaj_pct",   None)
        somaj_prev = prev.get("rata_somaj_pct",   None)
        somaj_var  = round(somaj_val - somaj_prev, 1) if somaj_val and somaj_prev else None

        sal_val    = last.get("salariu_mediu_mdl", None)
        sal_prev   = prev.get("salariu_mediu_mdl", None)
        sal_var    = ((sal_val - sal_prev) / sal_prev * 100) if sal_val and sal_prev and sal_prev != 0 else None

        pop_val    = last.get("populatie_ocupata_mii", None)
        ocupare_val= last.get("rata_ocupare_pct",      None)
        trim_label = last.get("trim_label", str(int(last["an"])))
    else:
        somaj_val = somaj_var = sal_val = sal_var = pop_val = ocupare_val = None
        trim_label = "N/A"

    # KPI din anuale pentru castig salarial (ultimul an BNS)
    if not df_sal.empty and "total" in df_sal.columns:
        sal_an_last = df_sal.iloc[-1]["total"]
        sal_an_prev = df_sal.iloc[-2]["total"] if len(df_sal) >= 2 else None
        sal_an_var  = ((sal_an_last - sal_an_prev) / sal_an_prev * 100) if sal_an_prev else None
        an_sal      = int(df_sal.iloc[-1]["an"])
    else:
        sal_an_last = sal_an_var = None; an_sal = 2024

    kpi_row([
        kpi_card("Rata somajului",
                 f"{somaj_val:.1f}" if somaj_val else "N/A", "%",
                 f"{somaj_var:+.1f}pp vs an anterior" if somaj_var else trim_label,
                 somaj_var is not None and somaj_var <= 0, "teal"),
        kpi_card("Salariu mediu (trim.)",
                 f"{sal_val:,.0f}" if sal_val else "N/A", "MDL",
                 f"{sal_var:+.1f}% vs an anterior" if sal_var else trim_label,
                 sal_var is not None and sal_var > 0, "teal"),
        kpi_card(f"Castig salarial {an_sal} (BNS)",
                 f"{sal_an_last:,.0f}" if sal_an_last else "N/A", "MDL",
                 f"{sal_an_var:+.1f}% vs {an_sal-1}" if sal_an_var else "",
                 sal_an_var is not None and sal_an_var > 0, "teal"),
        kpi_card("Populatie ocupata",
                 f"{pop_val:,.1f}" if pop_val else "N/A", "mii pers.",
                 f"trim. {trim_label}", True, "teal"),
    ])

    # ── Tabs ──────────────────────────────────────────────────────────────────
    trim_tab_label = "Date trimestriale (BNS)" if bns_trim_live else "Date trimestriale"
    tab_an, tab_trim, tab_tbl = st.tabs([
        "Date anuale", trim_tab_label, "Tabel date"
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — DATE ANUALE DIN BNS API
    # ─────────────────────────────────────────────────────────────────────────
    with tab_an:

        def _layout_an(h=280):
            return dict(
                height=h, paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
            )

        # ── Salarii anuale ────────────────────────────────────────────────────
        st.markdown('<div class="chart-card"><div class="chart-card-title">Castigul salarial mediu lunar brut (MDL)</div>', unsafe_allow_html=True)

        if not df_sal.empty and "total" in df_sal.columns:
            ani_sal = df_sal["an"].astype(str).tolist()
            sal_tot = df_sal["total"].tolist()

            col1, col2 = st.columns(2)

            with col1:
                # Line + fill nivel
                fig_sl = go.Figure(go.Scatter(
                    x=ani_sal, y=sal_tot,
                    mode="lines+markers",
                    line=dict(color="#185FA5", width=2.5),
                    marker=dict(size=6, color="#185FA5"),
                    fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} MDL<extra></extra>",
                ))
                fig_sl.update_layout(**{**_layout_an(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10),
                    zeroline=False, title="MDL"
                )})
                st.plotly_chart(fig_sl, use_container_width=True, config={"displayModeBar": False})

            with col2:
                # Bar variatie % an/an
                sal_series = pd.Series(sal_tot)
                var_yoy    = sal_series.pct_change().fillna(0) * 100
                colors_sal = ["#1D9E75" if v >= 0 else "#E24B4A" for v in var_yoy]
                fig_sv = go.Figure(go.Bar(
                    x=ani_sal, y=var_yoy.round(1).tolist(),
                    marker_color=colors_sal, opacity=0.88,
                    text=[f"{v:+.2f}%" for v in var_yoy],
                    textposition="outside",
                    textfont=dict(size=9, color="#444441"),
                    hovertemplate="<b>%{x}</b>: %{y:+.2f}%<extra></extra>",
                ))
                fig_sv.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig_sv.update_layout(**{**_layout_an(), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10), title="% an/an"
                )})
                st.plotly_chart(fig_sv, use_container_width=True, config={"displayModeBar": False})

            # Sectoare salariale (coloane extra in afara de 'an' si 'total')
            cols_sectoare = [c for c in df_sal.columns if c not in ["an","total"]]
            if cols_sectoare:
                st.markdown("**Castig salarial pe sectoare (MDL)**")
                PALETTE = ["#185FA5","#1D9E75","#854F0B","#534AB7",
                           "#993556","#0F6E56","#378ADD","#5DCAA5"]
                fig_ss = go.Figure()
                for i, sec in enumerate(cols_sectoare[:8]):
                    fig_ss.add_trace(go.Scatter(
                        x=ani_sal, y=df_sal[sec].tolist(),
                        name=sec, mode="lines+markers",
                        line=dict(color=PALETTE[i % len(PALETTE)], width=1.8),
                        marker=dict(size=4),
                        hovertemplate=f"<b>{sec}</b> %{{x}}: %{{y:,.0f}} MDL<extra></extra>",
                    ))
                fig_ss.update_layout(**{
                    **_layout_an(300),
                    "showlegend": True,
                    "legend": dict(orientation="h", y=-0.25, x=0,
                                   font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                                  zeroline=False, title="MDL"),
                })
                st.plotly_chart(fig_ss, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Date salariale BNS indisponibile — se afiseaza fallback.")

        ts_sal = result_sal.get("ts","")
        live_sal = "live" if result_sal["live"] else " "
       

        st.markdown("")

        # ── Piata muncii anuala ───────────────────────────────────────────────
        if not df_pm.empty:
            ani_pm = df_pm["an"].astype(str).tolist()

            col3, col4 = st.columns(2)

            with col3:

                st.markdown(
                    '<div class="chart-card-title">Rata de activitate și ocupare (%)</div>',
                    unsafe_allow_html=True
                )
                # ── Rate activitate + ocupare ──────────────────────────────────────
                fig_pm1 = go.Figure()
                for col, name, color in [

                    ("rata_activitate", "Rata activitate", "#185FA5"),
                    ("rata_ocupare",    "Rata ocupare",    "#1D9E75"),
                ]:
                    if col in df_pm.columns:
                        fig_pm1.add_trace(go.Scatter(
                            x=ani_pm,
                            y=df_pm[col].tolist(),
                            name=name,
                            mode="lines+markers",
                            line=dict(
                                color=color,
                                width=2.5
                            ),
                            marker=dict(
                                size=6
                            ),
                            hovertemplate=f"<b>{name}</b> %{{x}}: %{{y:.2f}}%<extra></extra>",
                        ))

                fig_pm1.update_layout(

                    **{
                        **_layout_an(340),

                        "margin": dict(
                            l=10,
                            r=10,
                            t=10,
                            b=70
                        ),
                        "showlegend": True,
                        "legend": dict(
                            orientation="h",
                            y=-0.22,
                            x=0,
                            xanchor="left",
                            yanchor="top",
                            font=dict(size=10),
                            bgcolor="rgba(0,0,0,0)",
                        ),

                        "xaxis": dict(
                            showgrid=False,
                            linecolor="#e8e4dc",
                            tickfont=dict(size=10),
                        ),
                        "yaxis": dict(

                            gridcolor="#f1efe8",
                            tickfont=dict(size=10),
                            zeroline=False,
                            title="%",
                            ticksuffix="%"
                        ),
                    }
                )
                st.plotly_chart(
                    fig_pm1,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )
            with col4:
                st.markdown(
                    '<div class="chart-card-title">Rata șomajului (%)</div>',
                    unsafe_allow_html=True
                )
                # ── Rata somaj ─────────────────────────────────────────────────────
                if "rata_somaj" in df_pm.columns:
                    somaj_vals = df_pm["rata_somaj"].tolist()
                    media_somaj = sum(somaj_vals) / len(somaj_vals)
                    colors_som = [
                        "#E24B4A" if v > media_somaj else "#0F6E56"
                        for v in somaj_vals
                    ]
                    fig_pm2 = go.Figure(go.Bar(
                        x=ani_pm,
                        y=somaj_vals,
                        marker_color=colors_som,
                        opacity=0.88,
                        text=[f"{v:.2f}%" for v in somaj_vals],
                        textposition="outside",
                        textfont=dict(
                            size=9,
                            color="#444441"
                        ),
                        hovertemplate="<b>%{x}</b>: rata șomaj %{y:.2f}%<extra></extra>",
                    ))
                    # ── Linie medie ────────────────────────────────────────────────
                    fig_pm2.add_hline(
                        y=media_somaj,
                        line_dash="dot",
                        line_color="#888780",
                        line_width=1,
                        annotation_text=f"Media: {media_somaj:.1f}%",
                        annotation_font_size=9,
                    )
                    # ── Layout ─────────────────────────────────────────────────────
                    fig_pm2.update_layout(

                        **{
                            **_layout_an(340),
                            "margin": dict(
                                l=10,
                                r=10,
                                t=10,
                                b=70
                            ),
                            "xaxis": dict(
                                showgrid=False,
                                linecolor="#e8e4dc",
                                tickfont=dict(size=10),
                            ),

                            "yaxis": dict(
                                gridcolor="#f1efe8",
                                tickfont=dict(size=10),
                                zeroline=False,
                                title="%",
                                ticksuffix="%"
                            ),
                        }
                    )
                    st.plotly_chart(
                        fig_pm2,
                        use_container_width=True,
                        config={"displayModeBar": False}
                    )

            # Tabel anual piata muncii
            cols_show_pm = {
                "an": "An", "rata_activitate": "Rata activitate (%)",
                "rata_ocupare": "Rata ocupare (%)", "rata_somaj": "Rata somaj (%)",
            }
            show_pm = df_pm[[c for c in cols_show_pm if c in df_pm.columns]].copy()
            show_pm = show_pm.rename(columns=cols_show_pm)
            for col in show_pm.columns:
                if col != "An":
                    show_pm[col] = show_pm[col].apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else ""
                    )
            st.dataframe(show_pm, use_container_width=True, hide_index=True)

        else:
            st.info("Date piata muncii BNS indisponibile.")

        ts_pm = result_pm.get("ts","")
        live_pm = "live" if result_pm["live"] else "fallback"
        # st.markdown(f'<div class="chart-source">Sursa: {result_pm["sursa"]} ({live_pm}) · actualizat: {ts_pm}</div></div>', unsafe_allow_html=True)

        st.markdown("")

        # ── Populatie ocupata pe gen — stacked bar barbati/femei + linie total ─
        # Folosim df_gen (barbati/femei/total) daca e disponibil, altfel df_pop
        df_occ = df_gen if not df_gen.empty and "barbati" in df_gen.columns else df_pop
        sursa_gen = result_gen if not df_gen.empty else result_pop

        if not df_occ.empty:
            ani_occ  = df_occ["an"].astype(str).tolist()
            has_b    = "barbati" in df_occ.columns
            has_f    = "femei"   in df_occ.columns
            has_tot  = "total"   in df_occ.columns
            # fallback total daca lipseste
            if not has_tot and has_b and has_f:
                df_occ = df_occ.copy()
                df_occ["total"] = df_occ["barbati"] + df_occ["femei"]
                has_tot = True
            col5, col6 = st.columns(2)
            with col5:
                st.markdown(
                    '<div class="chart-card-title">Populația ocupată (mii persoane)</div>',
                    unsafe_allow_html=True
                )
                # ── Stacked bar Barbati + Femei + linie Total ─────────────────────
                fig_gen = go.Figure()
                if has_b:
                    fig_gen.add_trace(go.Bar(
                        name="Bărbați",
                        x=ani_occ,
                        y=df_occ["barbati"].round(1).tolist(),
                        marker_color="#185FA5",
                        opacity=0.88,
                        hovertemplate="Bărbați <b>%{x}</b>: %{y:,.2f} mii<extra></extra>",
                    ))
                if has_f:
                    fig_gen.add_trace(go.Bar(
                        name="Femei",
                        x=ani_occ,
                        y=df_occ["femei"].round(1).tolist(),
                        marker_color="#993556",
                        opacity=0.88,
                        hovertemplate="Femei <b>%{x}</b>: %{y:,.2f} mii<extra></extra>",
                    ))
                if has_tot:
                    tot_vals = df_occ["total"].round(1).tolist()
                    fig_gen.add_trace(go.Scatter(
                        name="Total",
                        x=ani_occ,
                        y=tot_vals,
                        mode="lines+markers+text",
                        line=dict(
                            color="#0D1F3C",
                            width=2.5
                        ),
                        marker=dict(
                            size=5,
                            color="#0D1F3C"
                        ),
                        text=[f"{v:,.2f}" for v in tot_vals],
                        textposition="top center",
                        textfont=dict(
                            size=8,
                            color="#0D1F3C"
                        ),
                        hovertemplate="Total <b>%{x}</b>: %{y:,.2f} mii<extra></extra>",
                    ))
                y_max = max(df_occ["total"].tolist()) if has_tot else (
                    max(df_occ.get("barbati", pd.Series([900])).tolist()) * 2
                )
                fig_gen.update_layout(
                    **{
                        **_layout_an(340),
                        "margin": dict(
                            l=10,
                            r=10,
                            t=10,
                            b=70
                        ),
                        "barmode": "stack",
                        "showlegend": True,
                        "legend": dict(
                            orientation="h",
                            y=-0.22,
                            x=0,
                            xanchor="left",
                            yanchor="top",
                            font=dict(size=10),
                            bgcolor="rgba(0,0,0,0)",
                        ),
                        "xaxis": dict(
                            showgrid=False,
                            linecolor="#e8e4dc",
                            tickfont=dict(size=10),
                        ),
                        "yaxis": dict(
                            gridcolor="#f1efe8",
                            tickfont=dict(size=10),
                            zeroline=False,
                            title="mii persoane",
                            range=[0, y_max * 1.18],
                        ),
                    }
                )
                st.plotly_chart(
                    fig_gen,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )
            with col6:
                st.markdown(
                    '<div class="chart-card-title">Structura populației ocupate pe sex (%)</div>',
                    unsafe_allow_html=True
                )
                # ── Structura procentuala barbati vs femei ────────────────────────
                if has_b and has_f:

                    b_vals = df_occ["barbati"].tolist()
                    f_vals = df_occ["femei"].tolist()

                    tot_bf = [b + f for b, f in zip(b_vals, f_vals)]

                    b_pct = [
                        b / t * 100 if t else 0
                        for b, t in zip(b_vals, tot_bf)
                    ]
                    f_pct = [
                        f / t * 100 if t else 0
                        for f, t in zip(f_vals, tot_bf)
                    ]
                    fig_pct = go.Figure()
                    fig_pct.add_trace(go.Bar(
                        name="Bărbați (%)",
                        x=ani_occ,
                        y=[round(v, 1) for v in b_pct],
                        marker_color="#185FA5",
                        opacity=0.88,
                        text=[f"{v:.2f}%" for v in b_pct],
                        textposition="inside",
                        textfont=dict(
                            size=9,
                            color="white"
                        ),
                        hovertemplate="Bărbați <b>%{x}</b>: %{y:.2f}%<extra></extra>",
                    ))

                    fig_pct.add_trace(go.Bar(
                        name="Femei (%)",
                        x=ani_occ,
                        y=[round(v, 1) for v in f_pct],
                        marker_color="#993556",
                        opacity=0.88,
                        text=[f"{v:.2f}%" for v in f_pct],
                        textposition="inside",
                        textfont=dict(
                            size=9,
                            color="white"
                        ),
                        hovertemplate="Femei <b>%{x}</b>: %{y:.2f}%<extra></extra>",
                    ))
                    fig_pct.update_layout(
                        **{
                            **_layout_an(340),
                            "margin": dict(
                                l=10,
                                r=10,
                                t=10,
                                b=70
                            ),
                            "barmode": "stack",
                            "showlegend": True,
                            "legend": dict(
                                orientation="h",
                                y=-0.22,
                                x=0,
                                xanchor="left",
                                yanchor="top",
                                font=dict(size=10),
                                bgcolor="rgba(0,0,0,0)",
                            ),
                            "xaxis": dict(
                                showgrid=False,
                                linecolor="#e8e4dc",
                                tickfont=dict(size=10),
                            ),
                            "yaxis": dict(
                                gridcolor="#f1efe8",
                                tickfont=dict(size=10),
                                zeroline=False,
                                title="%",
                                ticksuffix="%",
                                range=[0, 100],
                            ),
                        }
                    )
                    st.plotly_chart(
                        fig_pct,
                        use_container_width=True,
                        config={"displayModeBar": False}
                    )
                else:
                    st.info("Date pe gen indisponibile pentru structura procentuală.")
        #     # ── Tabel sinteza barbati / femei / total ─────────────────────────
        #     tbl_cols = {c: c for c in ["an","barbati","femei","total"]
        #                 if c in df_occ.columns}
        #     tbl_gen = df_occ[list(tbl_cols)].copy()
        #     tbl_gen = tbl_gen.rename(columns={
        #         "an": "An", "barbati": "Bărbați (mii)",
        #         "femei": "Femei (mii)", "total": "Total (mii)",
        #     })
        #     tbl_gen["An"] = tbl_gen["An"].astype(int)
        #     for col in tbl_gen.columns:
        #         if col != "An":
        #             tbl_gen[col] = tbl_gen[col].apply(
        #                 lambda x: f"{x:,.1f}" if pd.notna(x) else ""
        #             )
        #     st.dataframe(tbl_gen, use_container_width=True, hide_index=True)

        # else:
        #     st.info("Date populatie ocupata pe gen BNS indisponibile.")

        # ts_gen  = sursa_gen.get("ts","") if not df_gen.empty else result_pop.get("ts","")
        # live_g  = "live" if sursa_gen.get("live") else "fallback"
        # st.markdown(f'<div class="chart-source">Sursa: {sursa_gen.get("sursa","")} ({live_g}) · actualizat: {ts_gen} · saved query ef9f71d7</div></div>', unsafe_allow_html=True)

        # st.markdown("")

        # ── Someri — bar bicolor fata de medie ───────────────────────────────
        st.markdown('<div class="chart-card"><div class="chart-card-title">Numarul somerilor (mii persoane), date anuale</div>', unsafe_allow_html=True)
        if not df_pop.empty and "someri_mii" in df_pop.columns:
            ani_som   = df_pop["an"].astype(str).tolist()
            som_vals  = df_pop["someri_mii"].tolist()
            media_som = sum(som_vals) / len(som_vals)
            colors_sm = ["#E24B4A" if v > media_som else "#0F6E56" for v in som_vals]
            fig_som = go.Figure(go.Bar(
                x=ani_som, y=som_vals,
                marker_color=colors_sm, opacity=0.85,
                text=[f"{v:,.2f}" for v in som_vals],
                textposition="outside",
                textfont=dict(size=9, color="#444441"),
                hovertemplate="<b>%{x}</b>: %{y:,.2f} mii someri<extra></extra>",
            ))
            fig_som.add_hline(
                y=media_som, line_dash="dot",
                line_color="#888780", line_width=1,
                annotation_text=f"Media: {media_som:.1f} mii",
                annotation_font_size=9,
            )
            fig_som.update_layout(**{**_layout_an(260), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10),
                zeroline=False, title="mii persoane",
                range=[0, max(som_vals) * 1.18],
            )})
            st.plotly_chart(fig_som, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Date someri BNS indisponibile.")
        ts_pop  = result_pop.get("ts","")
        live_pop = "live" if result_pop["live"] else "fallback"
        # st.markdown(f'<div class="chart-source">Sursa: {result_pop["sursa"]} ({live_pop}) · actualizat: {ts_pop}</div></div>', unsafe_allow_html=True)
    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — DATE TRIMESTRIALE DIN EXCEL
    # ─────────────────────────────────────────────────────────────────────────
    with tab_trim:
        if df_q.empty:
            st.warning("Date_Sector_Social.xlsx nu a putut fi citit.")
        else:
            LABELS = (df_q["trim_label"].tolist() if "trim_label" in df_q.columns
                      else [str(int(a)) for a in df_q["an"]])
            def _layout_q(h=280):
                return dict(
                    height=h, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc",
                               tickfont=dict(size=9),
                               tickangle=-45 if len(LABELS) > 12 else 0),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
                )
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Rata somajului trimestrial (%)</div>', unsafe_allow_html=True)
                if "rata_somaj_pct" in df_q.columns:
                    vals = df_q["rata_somaj_pct"].tolist()
                    fig = go.Figure(go.Scatter(
                        x=LABELS, y=vals,
                        mode="lines+markers",
                        line=dict(color="#0F6E56", width=2.5),
                        marker=dict(size=5, color="#0F6E56"),
                        fill="tozeroy", fillcolor="rgba(15,110,86,0.07)",
                        hovertemplate="<b>%{x}</b>: %{y:.2f}%<extra></extra>",
                    ))
                    fig.add_hline(
                        y=df_q["rata_somaj_pct"].mean(), line_dash="dot",
                        line_color="#888780", line_width=1,
                        annotation_text=f"Media: {df_q['rata_somaj_pct'].mean():.1f}%",
                        annotation_font_size=9,
                    )
                    fig.update_layout(**{**_layout_q(), "yaxis": dict(
                        gridcolor="#f1efe8", tickfont=dict(size=10),
                        zeroline=False, title="%"
                    )})
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with col2:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Populatia ocupata trimestrial (mii persoane)</div>', unsafe_allow_html=True)
                if "populatie_ocupata_mii" in df_q.columns:
                    vals2 = df_q["populatie_ocupata_mii"].tolist()
                    fig2 = go.Figure(go.Bar(
                        x=LABELS, y=vals2,
                        marker_color="#0F6E56", opacity=0.80,
                        hovertemplate="<b>%{x}</b>: %{y:,.2f} mii pers.<extra></extra>",
                    ))
                    fig2.update_layout(**{**_layout_q(), "yaxis": dict(
                        gridcolor="#f1efe8", tickfont=dict(size=10),
                        zeroline=False, title="mii pers."
                    )})
                    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-card"><div class="chart-card-title">Numarul somerilor trimestrial (mii persoane)</div>', unsafe_allow_html=True)
            if "nr_someri_mii" in df_q.columns:
                vals3 = df_q["nr_someri_mii"].tolist()
                media_s = df_q["nr_someri_mii"].mean()
                colors3 = ["#E24B4A" if v > media_s else "#0F6E56" for v in vals3]
                fig3 = go.Figure(go.Bar(
                    x=LABELS, y=vals3,
                    marker_color=colors3, opacity=0.80,
                    hovertemplate="<b>%{x}</b>: %{y:.2f} mii someri<extra></extra>",
                ))
                fig3.add_hline(
                    y=media_s, line_dash="dot",
                    line_color="#888780", line_width=1,
                    annotation_text=f"Media: {media_s:.1f} mii",
                    annotation_font_size=9,
                )
                fig3.update_layout(**{**_layout_q(240), "yaxis": dict(
                    gridcolor="#f1efe8", tickfont=dict(size=10),
                    zeroline=False, title="mii pers."
                )})
                st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
            col3, col4 = st.columns(2)
            with col3:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Castigul mediu salarial trimestrial (MDL)</div>', unsafe_allow_html=True)
                if "salariu_mediu_mdl" in df_q.columns:
                    fig4 = go.Figure(go.Scatter(
                        x=LABELS, y=df_q["salariu_mediu_mdl"].tolist(),
                        mode="lines+markers",
                        line=dict(color="#185FA5", width=2.5),
                        marker=dict(size=5),
                        fill="tozeroy", fillcolor="rgba(24,95,165,0.07)",
                        hovertemplate="<b>%{x}</b>: %{y:,.0f} MDL<extra></extra>",
                    ))
                    fig4.update_layout(**{**_layout_q(), "yaxis": dict(
                        gridcolor="#f1efe8", tickfont=dict(size=10),
                        zeroline=False, title="MDL"
                    )})
                    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
            with col4:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Salariu mediu, variatie an/an (%)</div>', unsafe_allow_html=True)
                if "salariu_mediu_mdl" in df_q.columns:
                    df_copy = df_q.copy()
                    df_copy["sal_var_yoy"] = df_copy.groupby(
                        df_copy["trimestru"] if "trimestru" in df_copy.columns else df_copy.index
                    )["salariu_mediu_mdl"].pct_change() * 100
                    if df_copy["sal_var_yoy"].isna().all():
                        df_copy["sal_var_yoy"] = (df_copy["salariu_mediu_mdl"].pct_change(4) * 100).round(2)
                    colors4 = ["#1D9E75" if v >= 0 else "#E24B4A"
                               for v in df_copy["sal_var_yoy"].fillna(0)]
                    fig5 = go.Figure(go.Bar(
                        x=LABELS, y=df_copy["sal_var_yoy"].tolist(),
                        marker_color=colors4, opacity=0.85,
                        hovertemplate="<b>%{x}</b>: %{y:+.2f}%<extra></extra>",
                    ))
                    fig5.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                    fig5.update_layout(**{**_layout_q(), "yaxis": dict(
                        gridcolor="#f1efe8", tickfont=dict(size=10), title="%"
                    )})
                    st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})

            # st.caption(f"Sursa date trimestriale: {sursa_trim}")
            if bns_trim_live:
                if st.button("Reincarca date trimestriale", key="reload_trim_bns"):
                    get_salarii_trim_bns.clear()
                    get_ocupare_trim_bns.clear()
                    st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3 — TABEL DATE COMPLETE
    # ─────────────────────────────────────────────────────────────────────────
    with tab_tbl:
        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Date trimestriale</div>', unsafe_allow_html=True)
            if not df_q.empty:
                col_rename = {
                    "an": "An", "trimestru": "Trim.",
                    "populatie_ocupata_mii": "Pop. ocupata (mii)",
                    "nr_someri_mii": "Someri (mii)",
                    "rata_somaj_pct": "Rata somaj (%)",
                    "rata_ocupare_pct": "Rata ocupare (%)",
                    "salariu_mediu_mdl": "Salariu mediu (MDL)",
                }
                show_cols = [c for c in col_rename if c in df_q.columns]
                show_q = df_q[show_cols].rename(columns=col_rename).copy()
                for col in show_q.columns:
                    if "MDL" in col:
                        show_q[col] = show_q[col].apply(
                            lambda x: f"{x:,.0f}" if pd.notna(x) else "")
                    elif "%" in col or "mii" in col.lower():
                        show_q[col] = show_q[col].apply(
                            lambda x: f"{x:.1f}" if pd.notna(x) else "")
                st.dataframe(show_q, use_container_width=True, hide_index=True, height=380)
            # st.markdown('<div class="chart-source">Sursa: BNS</div></div>', unsafe_allow_html=True)

        with col_t2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Date anuale</div>', unsafe_allow_html=True)

            # Combinam salarii + piata muncii pe an
            dfs_an = []
            if not df_sal.empty and "total" in df_sal.columns:
                dfs_an.append(df_sal[["an","total"]].rename(columns={"total":"Salariu mediu (MDL)"}))
            if not df_pm.empty:
                pm_cols = {c: c.replace("rata_","Rata ").replace("_"," ").title()
                           for c in ["rata_activitate","rata_ocupare","rata_somaj"]
                           if c in df_pm.columns}
                dfs_an.append(df_pm[["an"] + list(pm_cols.keys())].rename(columns=pm_cols))

            if dfs_an:
                from functools import reduce
                df_an_tbl = reduce(lambda l, r: pd.merge(l, r, on="an", how="outer"), dfs_an)
                df_an_tbl = df_an_tbl.sort_values("an").reset_index(drop=True)
                df_an_tbl["an"] = df_an_tbl["an"].astype(int)
                df_an_tbl = df_an_tbl.rename(columns={"an": "An"})

                # Formateaza
                for col in df_an_tbl.columns:
                    if col == "An":
                        continue
                    if "MDL" in col or "Salariu" in col:
                        df_an_tbl[col] = df_an_tbl[col].apply(
                            lambda x: f"{x:,.0f}" if pd.notna(x) else "")
                    else:
                        df_an_tbl[col] = df_an_tbl[col].apply(
                            lambda x: f"{x:.1f}%" if pd.notna(x) else "")

                st.dataframe(df_an_tbl, use_container_width=True, hide_index=True, height=380)
            else:
                st.info("Date anuale indisponibile.")

            live_str = "live" if (result_sal["live"] or result_pm["live"]) else "fallback"
            # st.markdown(f'<div class="chart-source">Sursa: BNS </div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        '<p style="font-size:10px;color:#b4b2a9;font-family:IBM Plex Mono,monospace">'
        f'Sursa date : BNS · actualizat: {ts_sal} ·'
        'Platforma MEDD — Directia Analiza si Prognoza Macroeconomica.</p>',
        unsafe_allow_html=True
    )