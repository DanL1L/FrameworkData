import streamlit as st
import plotly.graph_objects as go
from utils.state import page_header, kpi_card, kpi_row
from utils.charts import line_chart, bar_chart, stacked_bar
from data.demo_data import *

def render():
    page_header(
        "Sectorul Public",
        "Finante publice, executie bugetara, datorie publica · 2019–2024",
        "Ministerul Finantelor — Executie bugetara",
        "amber"
    )

    kpi_row([
        kpi_card("Venituri bugetare", "33.1", "% PIB", "+0.4pp fata de 2023", True, "amber"),
        kpi_card("Cheltuieli totale", "36.5", "% PIB", "+1.0pp — presiune", False, "amber"),
        kpi_card("Sold bugetar", "-3.4", "% PIB", "deteriorare fata de plan", False, "amber"),
        kpi_card("Datorie publica", "31.2", "% PIB", "sub pragul UE de 60%", True, "amber"),
    ])

    tab1, tab2, tab3 = st.tabs(["Executie bugetara", "Structura venituri", "Datorie publica"])

    with tab1:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Venituri si cheltuieli (% PIB)</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=YEARS_STR, y=venituri_pib, name="Venituri",
            mode="lines+markers", line=dict(color="#1D9E75", width=2),
            marker=dict(size=5), fill="tozeroy", fillcolor="rgba(29,158,117,0.06)",
        ))
        fig.add_trace(go.Scatter(
            x=YEARS_STR, y=cheltuieli_pib, name="Cheltuieli",
            mode="lines+markers", line=dict(color="#E24B4A", width=2),
            marker=dict(size=5),
        ))
        fig.update_layout(
            height=280,
            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(l=10,r=10,t=10,b=10),
            legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
            yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="% PIB"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Sursa: Ministerul Finantelor — Buget general consolidat</div></div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Sold bugetar (% PIB)</div>', unsafe_allow_html=True)
            fig2 = bar_chart(YEARS_STR, sold_pib, "amber", ylabel="% PIB", neg_color="amber")
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: Ministerul Finantelor</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Datorie publica (% PIB)</div>', unsafe_allow_html=True)
            fig3 = line_chart({"Datorie publica (% PIB)": datorie_pib}, YEARS_STR, ylabel="% PIB")
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: Ministerul Finantelor — Raport datorie</div></div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Structura veniturilor bugetare (% PIB, componente)</div>', unsafe_allow_html=True)
        fig4 = stacked_bar(YEARS_STR, venituri_comp, ylabel="% PIB",
                           colors=["#185FA5","#1D9E75","#BA7517","#534AB7","#888780"])
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Sursa: Ministerul Finantelor — Clasificatie bugetara</div></div>', unsafe_allow_html=True)

        import pandas as pd
        ven_df = pd.DataFrame({
            "Componenta": list(venituri_comp.keys()),
            "2022 (% PIB)": [f"{v:.1f}%" for v in [v[3] for v in venituri_comp.values()]],
            "2023 (% PIB)": [f"{v:.1f}%" for v in [v[4] for v in venituri_comp.values()]],
            "2024p (% PIB)": [f"{v:.1f}%" for v in [v[5] for v in venituri_comp.values()]],
        })
        st.dataframe(ven_df, use_container_width=True, hide_index=True)

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Evolutia datoriei publice (% PIB)</div>', unsafe_allow_html=True)
            fig5 = line_chart({"Datorie publica": datorie_pib}, YEARS_STR, ylabel="% PIB")
            fig5.add_hline(y=60, line_dash="dot", line_color="#E24B4A", line_width=1,
                           annotation_text="Prag UE 60%", annotation_font_size=9)
            st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: MF — Raport privind datoria publica</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Indicatori fiscali sintetici 2019–2024</div>', unsafe_allow_html=True)
            import pandas as pd
            fis_tbl = pd.DataFrame({
                "Indicator": ["Venituri (% PIB)", "Cheltuieli (% PIB)", "Sold (% PIB)", "Datorie (% PIB)"],
                "2022": ["33.2%", "36.2%", "-3.0%", "33.6%"],
                "2023": ["32.7%", "35.5%", "-2.8%", "32.1%"],
                "2024p": ["33.1%", "36.5%", "-3.4%", "31.2%"],
            })
            st.dataframe(fis_tbl, use_container_width=True, hide_index=True, height=210)
            st.markdown('<div class="chart-source">Sursa: Ministerul Finantelor</div></div>', unsafe_allow_html=True)
