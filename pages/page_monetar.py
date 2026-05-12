import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.state import page_header, kpi_card, kpi_row
from utils.charts import bar_chart, line_chart
from data.excel_loader import load_monetar
from utils.data_loader import sursa_badge


def render():
    page_header(
        "Sectorul Monetar",
        "PIB, rezerve valutare, baza monetara, depozite · 2000–2024",
        "BNM",
        "pink"
    )

    result = load_monetar()
    df     = result["data"]

    if df.empty:
        st.warning(" Fisierul Date_Sector_Monetar.xlsx nu a putut fi citit.")
        return

    YEARS_STR = [str(int(a)) for a in df["an"]]
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    def _safe(col): return last.get(col, None) if col in df.columns else None
    def _prev(col): return prev.get(col, None) if col in df.columns else None
    def _var(col):
        v, p = _safe(col), _prev(col)
        return ((v - p) / p * 100) if v and p and p != 0 else None

    pib_val  = _safe("pib_mil_lei");   pib_var  = _var("pib_mil_lei")
    rez_val  = _safe("rezerve_mln_usd"); rez_var = _var("rezerve_mln_usd")
    ipc_val  = _safe("ipc_sfarsit_an")
    baza_val = _safe("baza_monetara_mil_lei")
    dep_val  = _safe("depozite_mil_lei")
    an_last  = int(last["an"]); an_prev = int(prev["an"])

    kpi_row([
        kpi_card("PIB nominal", f"{pib_val:,.0f}" if pib_val else "N/A", "mil. lei",
                 f"{pib_var:+.1f}% vs {an_prev}" if pib_var else str(an_last), pib_var and pib_var > 0, "pink"),
        kpi_card("Rezerve BNM", f"{rez_val:,.1f}" if rez_val else "N/A", "mil. USD",
                 f"{rez_var:+.1f}% vs {an_prev}" if rez_var else "", rez_var and rez_var > 0, "pink"),
        kpi_card("IPC sfarsit an", f"{ipc_val:.1f}" if ipc_val else "N/A", "%",
                 f"inflatie la sfarsit de an {an_last}", ipc_val and ipc_val < 10, "pink"),
        kpi_card("Baza monetara", f"{baza_val:,.0f}" if baza_val else "N/A", "mil. lei",
                 f"depozite: {dep_val:,.0f} mil. lei" if dep_val else "", True, "pink"),
    ])

    tab1, tab2, tab3 = st.tabs(["PIB / Inflație", "Rezerve valutare", "Baza monetară / Depozite"])

    def _layout(h=280):
        return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10,r=10,t=10,b=10), showlegend=False,
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False))

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">PIB nominal (mil. lei)</div>', unsafe_allow_html=True)
            fig = go.Figure(go.Bar(x=YEARS_STR, y=df["pib_mil_lei"].tolist(),
                marker_color="#993556", opacity=0.85,
                hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>"))
            fig.update_layout(**_layout())
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Indicele Preturilor de Consum — sfarsit de an (%)</div>', unsafe_allow_html=True)
            if "ipc_sfarsit_an" in df.columns:
                vals_ipc = df["ipc_sfarsit_an"].tolist()
                colors_ipc = ["#E24B4A" if v > 10 else "#993556" if v > 5 else "#1D9E75" for v in vals_ipc]
                fig2 = go.Figure(go.Bar(x=YEARS_STR, y=vals_ipc, marker_color=colors_ipc, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>"))
                fig2.add_hline(y=5.0, line_dash="dot", line_color="#1D9E75", line_width=1,
                    annotation_text="Tinta 5%", annotation_font_size=9)
                fig2.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), title="%")})
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Date anuale — sinteza</div>', unsafe_allow_html=True)
        st.dataframe(df[["an","pib_mil_lei","ipc_sfarsit_an"]].rename(columns={
            "an":"An","pib_mil_lei":"PIB (mil. lei)","ipc_sfarsit_an":"IPC sfarsit an (%)"}),
            use_container_width=True, hide_index=True)
        st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Rezerve valutare brute BNM (mil. USD)</div>', unsafe_allow_html=True)
            if "rezerve_mln_usd" in df.columns:
                fig3 = go.Figure(go.Scatter(x=YEARS_STR, y=df["rezerve_mln_usd"].tolist(),
                    mode="lines+markers", line=dict(color="#185FA5", width=2.5), marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(24,95,165,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.1f} mil. USD<extra></extra>"))
                fig3.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. USD")})
                st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNMx</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Rezerve — variatie anuala (%)</div>', unsafe_allow_html=True)
            if "rezerve_mln_usd" in df.columns:
                rez_pct = df["rezerve_mln_usd"].pct_change() * 100
                colors_rez = ["#1D9E75" if v >= 0 else "#E24B4A" for v in rez_pct.fillna(0)]
                fig4 = go.Figure(go.Bar(x=YEARS_STR, y=rez_pct.tolist(),
                    marker_color=colors_rez, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>"))
                fig4.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig4.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), title="%")})
                st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Calcule pe baza date BNM</div></div>', unsafe_allow_html=True)

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Baza monetara (mil. lei)</div>', unsafe_allow_html=True)
            if "baza_monetara_mil_lei" in df.columns:
                fig5 = go.Figure(go.Scatter(x=YEARS_STR, y=df["baza_monetara_mil_lei"].tolist(),
                    mode="lines+markers", line=dict(color="#854F0B", width=2.5), marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(133,79,11,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>"))
                fig5.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. lei")})
                st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Depozite (mil. lei)</div>', unsafe_allow_html=True)
            if "depozite_mil_lei" in df.columns:
                fig6 = go.Figure(go.Scatter(x=YEARS_STR, y=df["depozite_mil_lei"].tolist(),
                    mode="lines+markers", line=dict(color="#534AB7", width=2.5), marker=dict(size=6),
                    fill="tozeroy", fillcolor="rgba(83,74,183,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} mil. lei<extra></extra>"))
                fig6.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. lei")})
                st.plotly_chart(fig6, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Tabel — Baza monetara & Depozite</div>', unsafe_allow_html=True)
        cols_b = {c: c for c in ["an","baza_monetara_mil_lei","depozite_mil_lei"] if c in df.columns}
        st.dataframe(df[list(cols_b)].rename(columns={
            "an":"An","baza_monetara_mil_lei":"Baza monetara (mil. lei)","depozite_mil_lei":"Depozite (mil. lei)"}),
            use_container_width=True, hide_index=True)
        st.markdown('<div class="chart-source">Sursa: BNM</div></div>', unsafe_allow_html=True)
