"""
page_overview.py — Indicatorii MacroEconomici
Surse:
  (1) statistica.gov.md — 8 indicatori cheie (scraping live, ttl=3600)
  (2) BNS TNA01 — PIB mii USD, PIB/locuitor, IPC mediu anual
      saved query: cc6bdb68-c935-4396-a7cc-c78470fe8d0c
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils.state import page_header, kpi_card, kpi_row
from utils.data_loader import sursa_badge
from utils.api_bns import get_pib_sinteza
from utils.api_bns_scraper import get_indicatori_cheie
from data.demo_data import (
    YEARS_STR, export_vals, import_vals,
    pib_real_growth, prog_years, prog_medd, prog_imf, prog_wb,
)


def render():
    page_header(
        "Indicatorii MacroEconomici",
        "Sumarul principalilor indicatori · Republica Moldova · 2019–2025",
        "BNS · BNM · Ministerul Finanțelor",
        "blue"
    )

    # ── Date BNS TNA01 ────────────────────────────────────────────────────────
    result_tna = get_pib_sinteza()
    df         = result_tna["data"]
    is_live    = result_tna["live"]
    sursa_lbl  = "BNS TNA01 — live" if is_live else "BNS TNA01 — date de referinta"

    # ── Indicatori cheie — scraping statistica.gov.md ─────────────────────────
    result_kpi = get_indicatori_cheie()
    kpi_live   = result_kpi["live"]
    indicatori = result_kpi["data"]   # lista de 8 indicatori

    # Badge sursa scraper + timestamp
    st.markdown(sursa_badge(result_kpi), unsafe_allow_html=True)
    if result_kpi.get("eroare"):
        st.caption(f" {result_kpi['eroare']}")
    st.markdown("")

    # ── KPI rows 1 & 2 — cei 8 indicatori de pe statistica.gov.md ────────────
    # Impartiti in 2 randuri de cate 4
    rand1 = indicatori[:4]
    rand2 = indicatori[4:8]

    kpi_row([
        kpi_card(ind["titlu"], ind["valoare"], "", ind["perioada"],
                 ind["pozitiv"], ind["color"])
        for ind in rand1
    ])

    if rand2:
        kpi_row([
            kpi_card(ind["titlu"], ind["valoare"], "", ind["perioada"],
                     ind["pozitiv"], ind["color"])
            for ind in rand2
        ])
    if df.empty:
        st.warning("Date BNS  indisponibile.")
        return

    YEARS_BNS = [str(int(a)) for a in df["an"]]

    # # Badge sursa TNA01
    # st.markdown(sursa_badge(result_tna), unsafe_allow_html=True)
    # st.markdown("")

    def _layout(h=280):
        return dict(
            height=h, paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
            margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
            yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
        )

    col1, col2 = st.columns(2)
    with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">PIB preturi curente (mld. USD)</div>', unsafe_allow_html=True)
            pib_mld_vals = (df["pib_mii_usd"] / 1_000_000).round(3).tolist()
            colors_pib   = ["#185FA5"] * (len(pib_mld_vals) - 1) + ["#378ADD"]
            fig1 = go.Figure(go.Bar(
                x=YEARS_BNS, y=pib_mld_vals,
                marker_color=colors_pib, opacity=0.88,
                text=[f"{v:.2f}" for v in pib_mld_vals],
                textposition="outside",
                textfont=dict(size=9, color="#444441"),
                hovertemplate="<b>%{x}</b>: %{y:.3f} mld. USD<extra></extra>",
            ))
            fig1.update_layout(**{**_layout(), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mld. USD"
            )})
            st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: {sursa_lbl} · saved query cc6bdb68</div></div>', unsafe_allow_html=True)

    with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">PIB pe locuitor, preturi curente (USD)</div>', unsafe_allow_html=True)
            pc_vals = df["pib_pc_usd"].tolist()
            fig2 = go.Figure(go.Scatter(
                x=YEARS_BNS, y=pc_vals,
                mode="lines+markers",
                line=dict(color="#185FA5", width=2.5),
                marker=dict(size=6, color="#185FA5"),
                fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                hovertemplate="<b>%{x}</b>: %{y:,.0f} USD<extra></extra>",
            ))
            fig2.update_layout(**{**_layout(), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="USD"
            )})
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: {sursa_lbl}</div></div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
            st.markdown('<div class="chart-card"><div class="chart-card-title">IPC mediu anual (%)</div>', unsafe_allow_html=True)
            ipc_vals   = df["ipc_mediu"].tolist()
            colors_ipc = [
                "#A32D2D" if v > 120 else
                "#E24B4A" if v > 110 else
                "#BA7517" if v > 105 else
                "#1D9E75"
                for v in ipc_vals
            ]
            fig3 = go.Figure(go.Bar(
                x=YEARS_BNS, y=ipc_vals,
                marker_color=colors_ipc, opacity=0.88,
                text=[f"{v:.1f}%" for v in ipc_vals],
                textposition="outside",
                textfont=dict(size=9, color="#444441"),
                hovertemplate="<b>%{x}</b>: IPC %{y:.1f}%<extra></extra>",
            ))
            fig3.update_layout(**{**_layout(), "yaxis": dict(
                gridcolor="#f1efe8", tickfont=dict(size=10),
                title="%", range=[95, max(ipc_vals) * 1.08]
            )})
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: {sursa_lbl}</div></div>', unsafe_allow_html=True)

    with col4:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Export vs Import (mil. USD)</div>', unsafe_allow_html=True)
                fig5 = go.Figure()
                fig5.add_trace(go.Bar(
                    name="Export", x=YEARS_STR, y=export_vals,
                    marker_color="#1D9E75", opacity=0.85,
                    hovertemplate="Export <b>%{x}</b>: %{y:,.0f} mil. USD<extra></extra>",
                ))
                fig5.add_trace(go.Bar(
                    name="Import", x=YEARS_STR, y=import_vals,
                    marker_color="#E24B4A", opacity=0.70,
                    hovertemplate="Import <b>%{x}</b>: %{y:,.0f} mil. USD<extra></extra>",
                ))
                fig5.update_layout(**{
                    **_layout(),
                    "barmode": "group",
                    "showlegend": True,
                    "legend": dict(orientation="h", y=1.05, x=0,
                                font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                })
                st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: BNM — Balanta de plati</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    ts_scraper = result_kpi.get("ts", "")
    live_str   = "live" if kpi_live else "fallback"
    st.markdown(
        f'<p style="font-size:10px;color:#b4b2a9;font-family:IBM Plex Mono,monospace">'
        f'Indicatori : ({live_str}) · actualizat: {ts_scraper} · '
        f'BNS, BNM, MinFin · '
        f'Platforma MEDD — Directia Analiza si Prognoza Macroeconomica.</p>',
        unsafe_allow_html=True
    )