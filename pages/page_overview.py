import streamlit as st
import plotly.graph_objects as go
from utils.state import page_header, kpi_card, kpi_row
from utils.charts import bar_chart, line_chart
from data.demo_data import *

def render():
    page_header(
        "Indicatorii MacroEconomici",
        "Sinteza indicatorilor principali · Republica Moldova · 2025",
        "BNS · BNM · Ministerul Finantelor",
        "blue"
    )

    # KPI row 1
    kpi_row([
        kpi_card("PIB nominal 2024", "16.4", "mld USD", "+2.1% fata de 2023", True, "blue"),
        kpi_card("Crestere PIB real", "+2.1", "%", "revenire dupa -5.9% in 2023", True, "blue"),
        kpi_card("Inflatie IPC (feb 25)", "5.2", "%", "-0.8pp fata de ian 2025", True, "blue"),
        kpi_card("Rata de baza BNM", "3.6", "%", "neschimbata — feb 2025", True, "blue"),
    ])
    kpi_row([
        kpi_card("Deficit CA (% PIB)", "-8.4", "%", "imbunatatit fata de -13.1%", True, "blue"),
        kpi_card("Deficit bugetar", "-3.4", "% PIB", "+0.6pp fata de plan", False, "blue"),
        kpi_card("Datorie publica", "31.2", "% PIB", "sub pragul UE de 60%", True, "blue"),
        kpi_card("Rezerve BNM", "4.8", "luni imp.", "+0.3 luni fata de an anterior", True, "blue"),
    ])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Crestere PIB real (%, an/an)</div>', unsafe_allow_html=True)
        fig = bar_chart(YEARS_STR, pib_real_growth, "blue", ylabel="% an/an")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Surse: BNS — Conturi nationale</div></div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Export vs Import (mil. USD)</div>', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="Export", x=YEARS_STR, y=export_vals, marker_color="#1D9E75", opacity=0.85))
        fig2.add_trace(go.Bar(name="Import", x=YEARS_STR, y=import_vals, marker_color="#E24B4A", opacity=0.70))
        fig2.update_layout(
            barmode="group", height=280,
            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=10,r=10,t=10,b=10),
            legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
            yaxis=dict(gridcolor="#f1efe8", linecolor="#e8e4dc", tickfont=dict(size=10), zeroline=False),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Sursa: BNM — Balanta de plati</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card"><div class="chart-card-title">Prognoze crestere PIB real 2024–2028 (%)</div>', unsafe_allow_html=True)
    fig3 = line_chart(
        {"MEDD (scenariu de baza)": prog_medd, "FMI WEO": prog_imf, "Banca Mondiala": prog_wb},
        prog_years, ylabel="% an/an", dashes=["FMI WEO", "Banca Mondiala"]
    )
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    st.markdown('<div class="chart-source">Sursa: MEDD, IMF World Economic Outlook oct 2024, World Bank Moldova Economic Update</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p style="font-size:10px;color:#b4b2a9;font-family:IBM Plex Mono,monospace">Actualizate: martie 2025. Platforma MEDD — Directia Analiza si Prognoza Macroeconomica.</p>', unsafe_allow_html=True)
