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
        "PIB, rezerve valutare, baza monetara, depozite · 2000–2024",
        "BNM",
        "pink"
    )

    # ── Date Excel ────────────────────────────────────────────────────────────
    result = load_monetar()
    df     = result["data"]

    if df.empty:
        st.warning("Fisierul Date_Sector_Monetar.xlsx nu a putut fi citit.")
        return

    YEARS_STR = [str(int(a)) for a in df["an"]]
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    def _safe(col): return last.get(col, None) if col in df.columns else None
    def _prev(col): return prev.get(col, None) if col in df.columns else None
    def _var(col):
        v, p = _safe(col), _prev(col)
        return ((v - p) / p * 100) if v and p and p != 0 else None

    rez_val  = _safe("rezerve_mln_usd");       rez_var  = _var("rezerve_mln_usd")
    ipc_val  = _safe("ipc_sfarsit_an")
    baza_val = _safe("baza_monetara_mil_lei")
    dep_val  = _safe("depozite_mil_lei")
    an_last  = int(last["an"]); an_prev = int(prev["an"])

    # ── IPC medie anuala din BNS API ──────────────────────────────────────────
    res_tna = get_pib_sinteza()
    df_tna  = res_tna["data"]
    has_ipc_mediu = not df_tna.empty and "ipc_mediu" in df_tna.columns

    # KPI ipc_mediu din ultimul an disponibil BNS
    ipc_mediu_last = None
    if has_ipc_mediu:
        row_last = df_tna.iloc[-1]
        ipc_mediu_last = row_last.get("ipc_mediu", None)
        # Convertim din index (ex 113.4 = 13.4%) → afisam direct
        # BNS returneaza deja ca procent fata de 100 (113.4 = inflatie 13.4%)

    kpi_row([
        kpi_card("Rezerve BNM", f"{rez_val:,.1f}" if rez_val else "N/A", "mil. USD",
                 f"{rez_var:+.1f}% vs {an_prev}" if rez_var else "",
                 rez_var and rez_var > 0, "pink"),
        kpi_card("IPC sfarsit an", f"{ipc_val:.1f}" if ipc_val else "N/A", "%",
                 f"inflatie la sfarsit de an {an_last}",
                 ipc_val and ipc_val < 10, "pink"),
        kpi_card("IPC medie anuala (BNS)",
                 f"{ipc_mediu_last:.1f}" if ipc_mediu_last else "N/A", "%",
                 f"medie {int(df_tna.iloc[-1]['an']) if has_ipc_mediu else ''}",
                 ipc_mediu_last and ipc_mediu_last < 105, "pink"),
        kpi_card("Baza monetara", f"{baza_val:,.0f}" if baza_val else "N/A", "mil. lei",
                 f"depozite: {dep_val:,.0f} mil. lei" if dep_val else "",
                 True, "pink"),
    ])

    def _layout(h=280):
        return dict(
            height=h, paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
            margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
            yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
        )

    tab1, tab2 = st.tabs(["Baza monetară / Depozite", "Date sector monetar"])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Date sector monetar
    # ═══════════════════════════════════════════════════════════════════════════
    with tab2:
        col1, col2 = st.columns(2)

        # ── col1: IPC medie anuala (BNS API) ──────────────────────────────────
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">IPC medie anuala (%)</div>', unsafe_allow_html=True)
            if has_ipc_mediu:
                ani_tna  = df_tna["an"].astype(str).tolist()
                ipc_vals_an = (df_tna["ipc_mediu"] - 100).tolist()

              
                colors_m = [
                    "#1D9E75" if v > 20 else
                    "#1D9E75" if v > 10 else
                    "#1D9E75" if v > 5 else
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
                fig_ipc_m.update_layout(**{
                    **_layout(),
                    "yaxis": dict(
                        gridcolor="#f1efe8", tickfont=dict(size=10),
                        title="%", range=[0, max(ipc_vals_an) * 1.15],
                    ),
                })
                st.plotly_chart(fig_ipc_m, use_container_width=True,
                                config={"displayModeBar": False})
                ts_tna  = res_tna.get("ts","")
                live_lbl = "live" if res_tna.get("live") else "date referinta"
                # st.markdown(
                #     f'<div class="chart-source">Sursa: BNS ({live_lbl}) · '
                #     f'saved query cc6bdb68 · {ts_tna}</div></div>',
                #     unsafe_allow_html=True,
                # )
            else:
                st.info("IPC medie anuala indisponibila — API BNS .")

        # ── col2: IPC sfarsit an (Excel) ──────────────────────────────────────
        with col2:
            st.markdown(
                '<div class="chart-card"><div class="chart-card-title">IPC la sfarsit de an (%)</div>',
                unsafe_allow_html=True
            )

            if "ipc_sfarsit_an" in df.columns:

                # Filtrare din 2019
                df_ipc = df[df["an"] >= 2019].copy()

                years_ipc = df_ipc["an"].astype(str).tolist()
                vals_ipc = df_ipc["ipc_sfarsit_an"].tolist()

                colors_ipc = [
                    "#1D9E75" if v > 20 else
                    "#1D9E75" if v > 10 else
                    "#1D9E75" if v > 5 else
                    "#1D9E75"
                    for v in vals_ipc
                ]

                fig2 = go.Figure(go.Bar(
                    x=years_ipc,
                    y=vals_ipc,
                    marker_color=colors_ipc,
                    opacity=0.85,
                    text=[f"{v:.1f}%" for v in vals_ipc],
                    textposition="outside",
                    textfont=dict(size=9, color="#444441"),
                    hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>",
                ))

                fig2.add_hline(
                    y=5.0,
                    line_dash="dot",
                    line_color="#1D9E75",
                    line_width=1.2,
                    annotation_text="Tinta 5%",
                    annotation_font_size=9,
                )

                fig2.update_layout(**{
                    **_layout(),
                    "yaxis": dict(
                        gridcolor="#f1efe8",
                        tickfont=dict(size=10),
                        title="%"
                    ),
                })

                st.plotly_chart(
                    fig2,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )

            # st.markdown(
            #     '<div class="chart-source">Sursa: BNM</div></div>',
            #     unsafe_allow_html=True
            # )

        # ── Rezerve BNM ───────────────────────────────────────────────────────
        col3, col4 = st.columns(2)
        with col3:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Rezerve valutare brute BNM (mil. USD)</div>', unsafe_allow_html=True)
            if "rezerve_mln_usd" in df.columns:
                fig3 = go.Figure(go.Scatter(
                    x=YEARS_STR, y=df["rezerve_mln_usd"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#185FA5", width=2.5),
                    marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.1f} mil. USD<extra></extra>",
                ))
                fig3.update_layout(**{
                    **_layout(),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                                  zeroline=False, title="mil. USD"),
                })
                st.plotly_chart(fig3, use_container_width=True,
                                config={"displayModeBar": False})
        with col4:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Rezerve — variatie anuala (%)</div>', unsafe_allow_html=True)
            if "rezerve_mln_usd" in df.columns:
                rez_pct    = df["rezerve_mln_usd"].pct_change() * 100
                colors_rez = ["#1D9E75" if v >= 0 else "#E24B4A"
                              for v in rez_pct.fillna(0)]
                fig4 = go.Figure(go.Bar(
                    x=YEARS_STR, y=rez_pct.tolist(),
                    marker_color=colors_rez, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
                ))
                fig4.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig4.update_layout(**{
                    **_layout(),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), title="%"),
                })
                st.plotly_chart(fig4, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Calcule: BNM — Date_Sector_Monetar.xlsx</div></div>', unsafe_allow_html=True)

        # ── Tabel sinteza ─────────────────────────────────────────────────────
        st.markdown('<div class="chart-card"><div class="chart-card-title">Tabel sinteza — indicatori monetari</div>', unsafe_allow_html=True)
        cols_tbl = {
            "an":               "An",
            "ipc_sfarsit_an":   "IPC sfarsit an (%)",
            "rezerve_mln_usd":  "Rezerve BNM (mil. USD)",
            "baza_monetara_mil_lei": "Baza monetara (mil. lei)",
            "depozite_mil_lei": "Depozite (mil. lei)",
        }
        show_cols = [c for c in cols_tbl if c in df.columns]
        tbl = df[show_cols].rename(columns=cols_tbl).copy()
        for col in tbl.columns:
            if col == "An":
                continue
            if "%" in col:
                tbl[col] = tbl[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
            else:
                tbl[col] = tbl[col].apply(lambda x: f"{x:,.1f}" if pd.notna(x) else "")
        st.dataframe(tbl, use_container_width=True, hide_index=True, height=360)
        st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Baza monetara / Depozite
    # ═══════════════════════════════════════════════════════════════════════════
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Baza monetara (mil. lei)</div>', unsafe_allow_html=True)
            if "baza_monetara_mil_lei" in df.columns:
                fig5 = go.Figure(go.Scatter(
                    x=YEARS_STR, y=df["baza_monetara_mil_lei"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#854F0B", width=2.5),
                    marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(133,79,11,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>",
                ))
                fig5.update_layout(**{
                    **_layout(),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                                  zeroline=False, title="mil. lei"),
                })
                st.plotly_chart(fig5, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Depozite (mil. lei)</div>', unsafe_allow_html=True)
            if "depozite_mil_lei" in df.columns:
                fig6 = go.Figure(go.Scatter(
                    x=YEARS_STR, y=df["depozite_mil_lei"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#534AB7", width=2.5),
                    marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(83,74,183,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>",
                ))
                fig6.update_layout(**{
                    **_layout(),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10),
                                  zeroline=False, title="mil. lei"),
                })
                st.plotly_chart(fig6, use_container_width=True,
                                config={"displayModeBar": False})
            # st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Tabel — Baza monetara & Depozite</div>', unsafe_allow_html=True)
        cols_b = {c: c for c in ["an","baza_monetara_mil_lei","depozite_mil_lei"] if c in df.columns}
        tbl_b  = df[list(cols_b)].rename(columns={
            "an": "An",
            "baza_monetara_mil_lei": "Baza monetara (mil. lei)",
            "depozite_mil_lei": "Depozite (mil. lei)",
        }).copy()
        for col in ["Baza monetara (mil. lei)", "Depozite (mil. lei)"]:
            if col in tbl_b.columns:
                tbl_b[col] = tbl_b[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        st.dataframe(tbl_b, use_container_width=True, hide_index=True)
        st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    ts_tna  = res_tna.get("ts","")
    live_lbl = "live" if res_tna.get("live") else "date referinta"
    st.markdown(
        f'<p style="font-size:10px;color:#b4b2a9;font-family:IBM Plex Mono,monospace">'
        f'Date: BNM · '
        f'IPC medie anuala: BNS ({live_lbl}) · {ts_tna} '
        f'Platforma MEDD — Directia Analiza si Prognoza Macroeconomica.</p>',
        unsafe_allow_html=True,
    )