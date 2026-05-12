import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.state import page_header, kpi_card, kpi_row
from utils.charts import bar_chart, line_chart
from data.excel_loader import load_social
from utils.data_loader import sursa_badge


def render():
    page_header(
        "Sectorul Social",
        "Piata muncii, somaj, ocupare, salarii · date trimestriale",
        "BNS",
        "teal"
    )

    result = load_social()
    df     = result["data"]


    if df.empty:
        st.warning(" Fisierul Date_Sector_Social.xlsx nu a putut fi citit.")
        return

    # ── KPI ultimul trimestru ────────────────────────────────────────────────
    last = df.iloc[-1]
    prev_yr = df[df["an"] == (int(last["an"]) - 1)]
    prev = prev_yr.iloc[-1] if not prev_yr.empty else df.iloc[-2] if len(df) >= 2 else last

    somaj_val   = last.get("rata_somaj_pct",   None)
    somaj_prev  = prev.get("rata_somaj_pct",   None)
    somaj_var   = round(somaj_val - somaj_prev, 1) if somaj_val and somaj_prev else None

    sal_val     = last.get("salariu_mediu_mdl", None)
    sal_prev    = prev.get("salariu_mediu_mdl", None)
    sal_var     = ((sal_val - sal_prev) / sal_prev * 100) if sal_val and sal_prev and sal_prev != 0 else None

    pop_val     = last.get("populatie_ocupata_mii", None)
    ocupare_val = last.get("rata_ocupare_pct",       None)
    trim_label  = last.get("trim_label", str(int(last["an"])))

    kpi_row([
        kpi_card("Rata somajului", f"{somaj_val:.1f}" if somaj_val else "N/A", "%",
                 f"{somaj_var:+.1f}pp vs an anterior" if somaj_var else trim_label,
                 somaj_var is not None and somaj_var <= 0, "teal"),
        kpi_card("Salariu mediu", f"{sal_val:,.0f}" if sal_val else "N/A", "MDL",
                 f"{sal_var:+.1f}% vs an anterior" if sal_var else "",
                 sal_var is not None and sal_var > 0, "teal"),
        kpi_card("Populatie ocupata", f"{pop_val:,.1f}" if pop_val else "N/A", "mii pers.",
                 f"trimestrul {trim_label}", True, "teal"),
        kpi_card("Rata de ocupare", f"{ocupare_val:.1f}" if ocupare_val else "N/A", "%",
                 f"trimestrul {trim_label}", True, "teal"),
    ])

    tab1, tab2, tab3 = st.tabs(["Șomaj / Ocupare", "Salarii", "Date tabel"])

    LABELS = df["trim_label"].tolist() if "trim_label" in df.columns else [str(int(a)) for a in df["an"]]

    def _layout(h=280):
        return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10,r=10,t=10,b=10), showlegend=False,
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=9),
                               tickangle=-45 if len(LABELS) > 12 else 0),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False))

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Rata somajului trimestrial (%)</div>', unsafe_allow_html=True)
            if "rata_somaj_pct" in df.columns:
                vals = df["rata_somaj_pct"].tolist()
                fig = go.Figure(go.Scatter(x=LABELS, y=vals,
                    mode="lines+markers",
                    line=dict(color="#0F6E56", width=2.5),
                    marker=dict(size=5, color="#0F6E56"),
                    fill="tozeroy", fillcolor="rgba(15,110,86,0.07)",
                    hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>"))
                fig.add_hline(y=df["rata_somaj_pct"].mean(), line_dash="dot",
                    line_color="#888780", line_width=1,
                    annotation_text=f"Media: {df['rata_somaj_pct'].mean():.1f}%",
                    annotation_font_size=9)
                fig.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="%")})
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNS</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Populatia ocupata trimestrial (mii persoane)</div>', unsafe_allow_html=True)
            if "populatie_ocupata_mii" in df.columns:
                vals2 = df["populatie_ocupata_mii"].tolist()
                fig2 = go.Figure(go.Bar(x=LABELS, y=vals2,
                    marker_color="#0F6E56", opacity=0.80,
                    hovertemplate="<b>%{x}</b>: %{y:,.1f} mii pers.<extra></extra>"))
                fig2.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mii pers.")})
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNS</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-card"><div class="chart-card-title">Numarul somerilor trimestrial (mii persoane)</div>', unsafe_allow_html=True)
        if "nr_someri_mii" in df.columns:
            vals3 = df["nr_someri_mii"].tolist()
            colors3 = ["#E24B4A" if v > df["nr_someri_mii"].mean() else "#0F6E56" for v in vals3]
            fig3 = go.Figure(go.Bar(x=LABELS, y=vals3,
                marker_color=colors3, opacity=0.80,
                hovertemplate="<b>%{x}</b>: %{y:.1f} mii someri<extra></extra>"))
            fig3.add_hline(y=df["nr_someri_mii"].mean(), line_dash="dot",
                line_color="#888780", line_width=1,
                annotation_text=f"Media: {df['nr_someri_mii'].mean():.1f} mii", annotation_font_size=9)
            fig3.update_layout(**{**_layout(240), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mii pers.")})
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Sursa: BNS</div></div>', unsafe_allow_html=True)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Castigul mediu salarial trimestrial (MDL)</div>', unsafe_allow_html=True)
            if "salariu_mediu_mdl" in df.columns:
                fig4 = go.Figure(go.Scatter(x=LABELS, y=df["salariu_mediu_mdl"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#185FA5", width=2.5),
                    marker=dict(size=5),
                    fill="tozeroy", fillcolor="rgba(24,95,165,0.07)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} MDL<extra></extra>"))
                fig4.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="MDL")})
                st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNS</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Salariu mediu — variatie an/an (%)</div>', unsafe_allow_html=True)
            if "salariu_mediu_mdl" in df.columns:
                # variatie fata de acelasi trimestru al anului anterior
                df_copy = df.copy()
                df_copy["sal_var_yoy"] = df_copy.groupby(
                    df_copy["trimestru"] if "trimestru" in df_copy.columns else df_copy.index
                )["salariu_mediu_mdl"].pct_change() * 100

                # fallback simplu daca groupby nu merge
                if df_copy["sal_var_yoy"].isna().all():
                    df_copy["sal_var_yoy"] = df_copy["salariu_mediu_mdl"].pct_change(4) * 100

                colors4 = ["#1D9E75" if v >= 0 else "#E24B4A"
                           for v in df_copy["sal_var_yoy"].fillna(0).tolist()]
                fig5 = go.Figure(go.Bar(x=LABELS, y=df_copy["sal_var_yoy"].tolist(),
                    marker_color=colors4, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>"))
                fig5.add_hline(y=0, line_color="#e8e4dc", line_width=1)
                fig5.update_layout(**{**_layout(), "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), title="%")})
                st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Calcule pe baza datelor BNS</div></div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Date complete — trimestrial</div>', unsafe_allow_html=True)
        col_rename = {
            "an": "An",
            "trimestru": "Trimestru",
            "populatie_ocupata_mii": "Pop. ocupata (mii)",
            "nr_someri_mii": "Someri (mii)",
            "rata_somaj_pct": "Rata somaj (%)",
            "rata_ocupare_pct": "Rata ocupare (%)",
            "salariu_mediu_mdl": "Salariu mediu (MDL)",
        }
        show_cols = [c for c in col_rename if c in df.columns]
        show_df = df[show_cols].rename(columns=col_rename)

        # Formateaza coloane numerice
        for col in show_df.columns:
            if "MDL" in col:
                show_df[col] = show_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
            elif "%" in col or "mii" in col.lower():
                show_df[col] = show_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "")

        st.dataframe(show_df, use_container_width=True, hide_index=True, height=400)
        st.markdown('<div class="chart-source">Sursa: BNS</div></div>', unsafe_allow_html=True)
