import streamlit as st
from utils.state import page_header, kpi_card, kpi_row
from utils.charts import bar_chart, line_chart, stacked_bar
from data.demo_data import *

def render():
    page_header(
        "Sectorul Real",
        "PIB, crestere economica, structura productiei · 2019–2024",
        "BNS — Conturi nationale",
        "green"
    )

    kpi_row([
        kpi_card("Crestere PIB 2024", "+2.1", "%", "revenire dupa 3 ani negativi", True, "green"),
        kpi_card("PIB nominal", "388.6", "mld MDL", "+4.8% nominal", True, "green"),
        kpi_card("PIB/locuitor (PPP)", "18,200", "USD", "+12.3% fata de 2023", True, "green"),
        kpi_card("FBCF (% PIB)", "21.3", "%", "-1.1pp fata de 2023", False, "green"),
    ])

    tab1, tab2, tab3 = st.tabs(["Crestere & componente", "Structura pe sectoare", "Prognoze"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Crestere PIB real (%, an/an)</div>', unsafe_allow_html=True)
            fig = bar_chart(YEARS_STR, pib_real_growth, "teal", ylabel="% an/an")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNS — Conturi nationale trimestriale</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Contributia componentelor la crestere (pp)</div>', unsafe_allow_html=True)
            fig2 = stacked_bar(YEARS_STR, pib_components, ylabel="pp contributie",
                               colors=["#1D9E75","#5DCAA5","#378ADD","#BA7517"])
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNS — Conturi nationale, calcule MEDD</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Activitati economice — crestere anuala (%)</div>', unsafe_allow_html=True)
        fig3 = line_chart({
            "Industrie": industrie_growth,
            "Agricultura": agricultura_growth,
            "Constructii": constructii_growth,
            "Servicii": servicii_growth,
        }, YEARS_STR, ylabel="% an/an")
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Sursa: BNS — Conturi nationale pe activitati CAEM</div></div>', unsafe_allow_html=True)

    with tab2:
        col1, col2 = st.columns([1.4, 1])
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Structura PIB pe sectoare (% PIB, 2024)</div>', unsafe_allow_html=True)
            import plotly.graph_objects as go
            fig_pie = go.Figure(go.Pie(
                labels=pib_sector_df["Sector"],
                values=pib_sector_df["Pondere (% PIB)"],
                hole=0.45,
                marker_colors=["#1D9E75","#185FA5","#BA7517","#534AB7","#888780"],
                textfont_size=10,
                hovertemplate="<b>%{label}</b><br>%{value:.1f}% din PIB<extra></extra>",
            ))
            fig_pie.update_layout(
                height=260, paper_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=10),
                margin=dict(l=0,r=0,t=0,b=0),
                legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                showlegend=True,
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNS — Conturi nationale 2024 (date preliminare)</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Pondere si dinamica pe sectoare</div>', unsafe_allow_html=True)
            st.dataframe(
                pib_sector_df,
                use_container_width=True,
                hide_index=True,
                height=220,
            )
            st.markdown('<div class="chart-source">Sursa: BNS — 2024p</div></div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Scenarii crestere PIB real 2024–2028 (%)</div>', unsafe_allow_html=True)
        fig_prog = line_chart(
            {"MEDD (baza)": prog_medd, "FMI WEO": prog_imf, "Banca Mondiala": prog_wb},
            prog_years, ylabel="% an/an", dashes=["FMI WEO", "Banca Mondiala"]
        )
        st.plotly_chart(fig_prog, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Sursa: MEDD, IMF WEO oct 2024, World Bank Moldova Economic Update</div></div>', unsafe_allow_html=True)

        import pandas as pd
        prog_df = pd.DataFrame({
            "Institutie": ["MEDD", "FMI WEO", "Banca Mondiala"],
            "2024": ["2.1%", "2.1%", "2.1%"],
            "2025p": ["3.5%", "3.2%", "3.0%"],
            "2026p": ["4.2%", "3.9%", "3.7%"],
            "2027p": ["4.8%", "4.4%", "4.2%"],
            "2028p": ["5.0%", "4.7%", "4.6%"],
        })
        st.dataframe(prog_df, use_container_width=True, hide_index=True)
