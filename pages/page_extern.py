import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.state import page_header, kpi_card, kpi_row
from utils.charts import bar_chart, line_chart
from data.excel_loader import load_extern_lunar, load_extern_reexport, load_extern_influenta, load_extern_tari, load_servicii
from utils.data_loader import sursa_badge


def render():
    page_header(
        "Sectorul Extern",
        "Comert exterior, export, import, servicii · 2015–2025",
        "BNS · BNM",
        "purple"
    )

    res_lunar   = load_extern_lunar()
    res_reexp   = load_extern_reexport()
    res_inf_exp = load_extern_influenta("Export")
    res_inf_imp = load_extern_influenta("Import")
    res_tari    = load_extern_tari()
    res_serv    = load_servicii()

    df_lunar = res_lunar["data"]
    df_reexp = res_reexp["data"]
    df_tari  = res_tari["data"]


    if df_lunar.empty:
        st.warning("Fisierul Data.xlsx nu a putut fi citit.")
        return

    # ── KPI din ultimele date disponibile ────────────────────────────────────
    last = df_lunar.iloc[-1]
    # Cautam acelasi luna din anul anterior
    try:
        prev_same = df_lunar[
            (df_lunar["luna_nr"] == last["luna_nr"]) &
            (df_lunar["an"] == int(last["an"]) - 1)
        ]
        prev = prev_same.iloc[-1] if not prev_same.empty else df_lunar.iloc[-2]
    except Exception:
        prev = df_lunar.iloc[-2] if len(df_lunar) >= 2 else last

    exp_val  = last.get("export_mil_usd"); exp_prev = prev.get("export_mil_usd")
    imp_val  = last.get("import_mil_usd"); imp_prev = prev.get("import_mil_usd")
    sold_val = last.get("sold_mil_usd")
    exp_var  = ((exp_val - exp_prev) / exp_prev * 100) if exp_val and exp_prev and exp_prev != 0 else None
    imp_var  = ((imp_val - imp_prev) / imp_prev * 100) if imp_val and imp_prev and imp_prev != 0 else None
    label    = last.get("label", "")

    kpi_row([
        kpi_card("Export", f"{exp_val:,.1f}" if exp_val else "N/A", "mil. USD",
                 f"{exp_var:+.1f}% vs luna an ant." if exp_var else label,
                 exp_var is not None and exp_var > 0, "purple"),
        kpi_card("Import", f"{imp_val:,.1f}" if imp_val else "N/A", "mil. USD",
                 f"{imp_var:+.1f}% vs luna an ant." if imp_var else "",
                 imp_var is not None and imp_var < 0, "purple"),
        kpi_card("Sold comercial", f"{sold_val:,.1f}" if sold_val else "N/A", "mil. USD",
                 label, sold_val is not None and sold_val > 0, "purple"),
        kpi_card("Grad acoperire", f"{exp_val/imp_val*100:.1f}" if exp_val and imp_val else "N/A", "%",
                 "export / import", exp_val and imp_val and exp_val/imp_val > 0.45, "purple"),
    ])

    tab1, tab4, tab5 = st.tabs([
        "Export / Import lunar", "Comerț grupe țări", "Servicii"
    ])

    LABELS = df_lunar["label"].tolist()

    def _layout(h=300):
        return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10,r=10,t=10,b=10),
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=9),
                               tickangle=-45 if len(LABELS) > 16 else 0),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False))

    # ── TAB 1: Export & Import lunar ──────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Export si Import lunar (mil. USD)</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Import", x=LABELS, y=df_lunar["import_mil_usd"].tolist(),
                marker_color="#E24B4A", opacity=0.75,
                hovertemplate="<b>%{x}</b> Import: %{y:,.1f} mil.<extra></extra>"))
            fig.add_trace(go.Bar(name="Export", x=LABELS, y=df_lunar["export_mil_usd"].tolist(),
                marker_color="#534AB7", opacity=0.90,
                hovertemplate="<b>%{x}</b> Export: %{y:,.1f} mil.<extra></extra>"))
            fig.update_layout(**{**_layout(), "barmode": "group",
                "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)")})
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: Data.xlsx — foaia Exp_Lunar</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Sold comercial lunar (mil. USD)</div>', unsafe_allow_html=True)
            if "sold_mil_usd" in df_lunar.columns:
                vals_sold = df_lunar["sold_mil_usd"].tolist()
                colors_sold = ["#1D9E75" if v >= 0 else "#E24B4A" for v in vals_sold]
                fig2 = go.Figure(go.Bar(x=LABELS, y=vals_sold,
                    marker_color=colors_sold, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:,.1f} mil. USD<extra></extra>"))
                fig2.add_hline(y=0, line_color="#444441", line_width=1)
                fig2.update_layout(**{**_layout(), "showlegend": False})
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: Data.xlsx — foaia Exp_Lunar</div></div>', unsafe_allow_html=True)

        # Selectie an pentru comparatie
        ani_disponibili = sorted(df_lunar["an"].dropna().unique().tolist(), reverse=True)
        ani_disponibili = [int(a) for a in ani_disponibili]
        col_sel1, col_sel2, _ = st.columns([1,1,3])
        with col_sel1:
            an1 = st.selectbox("An 1", ani_disponibili, index=0, key="ext_an1")
        with col_sel2:
            an2 = st.selectbox("An 2", ani_disponibili, index=min(1, len(ani_disponibili)-1), key="ext_an2")

        st.markdown('<div class="chart-card"><div class="chart-card-title">Comparatie Export lunar</div>', unsafe_allow_html=True)
        fig3 = go.Figure()
        LUNI_SCURTE = ["Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Nov","Dec"]
        colors_ani = ["#534AB7","#185FA5","#1D9E75","#854F0B"]
        for idx, an in enumerate([an1, an2]):
            df_an = df_lunar[df_lunar["an"] == an].sort_values("luna_nr")
            if not df_an.empty:
                luni_labels = [LUNI_SCURTE[int(n)-1] for n in df_an["luna_nr"] if 1 <= int(n) <= 12]
                fig3.add_trace(go.Scatter(
                    x=luni_labels, y=df_an["export_mil_usd"].tolist(),
                    name=str(an), mode="lines+markers",
                    line=dict(color=colors_ani[idx % 4], width=2.5),
                    marker=dict(size=6),
                    hovertemplate=f"<b>%{{x}} {an}</b>: %{{y:,.1f}} mil.<extra></extra>"))
        fig3.update_layout(**{**_layout(260), "showlegend": True,
            "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)")})
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="chart-source">Sursa: Data.xlsx — foaia Exp_Lunar</div></div>', unsafe_allow_html=True)
        
        if not df_reexp.empty:
            labels_r = df_reexp["label"].tolist()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Exporturi autohtone vs Reexporturi (mil. USD)</div>', unsafe_allow_html=True)
                fig4 = go.Figure()
                fig4.add_trace(go.Bar(name="Exporturi autohtone", x=labels_r,
                    y=df_reexp["export_autohton"].tolist(),
                    marker_color="#1D9E75", opacity=0.85,
                    hovertemplate="<b>%{x}</b> Autohton: %{y:,.1f}<extra></extra>"))
                fig4.add_trace(go.Bar(name="Reexporturi", x=labels_r,
                    y=df_reexp["reexport"].tolist(),
                    marker_color="#854F0B", opacity=0.75,
                    hovertemplate="<b>%{x}</b> Reexport: %{y:,.1f}<extra></extra>"))
                fig4.update_layout(**{**_layout(), "barmode": "stack",
                    "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)")})
                st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: Data.xlsx — foaia Exp_Reexp</div></div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Pondere reexporturi in total export (%)</div>', unsafe_allow_html=True)
                df_reexp["total_exp"] = df_reexp["export_autohton"] + df_reexp["reexport"]
                df_reexp["pondere_reexp"] = df_reexp["reexport"] / df_reexp["total_exp"] * 100
                fig5 = go.Figure(go.Scatter(x=labels_r, y=df_reexp["pondere_reexp"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#854F0B", width=2.5), marker=dict(size=5),
                    fill="tozeroy", fillcolor="rgba(133,79,11,0.07)",
                    hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>"))
                fig5.update_layout(**{**_layout(), "showlegend": False,
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="%")})
                st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Calcule pe baza Data.xlsx — Exp_Reexp</div></div>', unsafe_allow_html=True)
        else:
            st.info("Date Exp_Reexp indisponibile.")

        col1, col2 = st.columns(2)
        for col_ui, tip, res_inf in [(col1, "Export", res_inf_exp), (col2, "Import", res_inf_imp)]:
            with col_ui:
                df_inf = res_inf["data"]
                st.markdown(f'<div class="chart-card"><div class="chart-card-title">Contributia grupelor de mărfuri la dinamica {tip} (%)</div>', unsafe_allow_html=True)
                if not df_inf.empty:
                    ani_inf = sorted(df_inf["an"].dropna().unique().tolist(), reverse=True)
                    ani_inf = [int(a) for a in ani_inf]
                    an_sel = st.selectbox(f"An {tip}", ani_inf, key=f"inf_{tip}")
                    luni_inf = sorted(df_inf[df_inf["an"] == an_sel]["luna"].unique().tolist())
                    luna_sel = st.selectbox(f"Luna {tip}", luni_inf, key=f"luna_{tip}")

                    df_slice = df_inf[
                        (df_inf["an"] == an_sel) & (df_inf["luna"] == luna_sel)
                    ].sort_values("grad_pct")
                    df_slice = df_slice[df_slice["denumire"].str.strip() != tip]  # exclude total

                    if not df_slice.empty:
                        colors_inf = ["#E24B4A" if v < 0 else "#1D9E75" for v in df_slice["grad_pct"].tolist()]
                        fig6 = go.Figure(go.Bar(
                            x=df_slice["grad_pct"].tolist(),
                            y=df_slice["denumire"].str[:30].tolist(),
                            orientation="h",
                            marker_color=colors_inf,
                            opacity=0.85,
                            hovertemplate="<b>%{y}</b>: %{x:+.2f}%<extra></extra>",
                        ))
                        fig6.add_vline(x=0, line_color="#444441", line_width=1)
                        fig6.update_layout(
                            height=350, paper_bgcolor="white", plot_bgcolor="white",
                            font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                            margin=dict(l=10,r=10,t=10,b=10), showlegend=False,
                            xaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9), zeroline=False, title="%"),
                            yaxis=dict(showgrid=False, tickfont=dict(size=9)),
                        )
                        st.plotly_chart(fig6, use_container_width=True, config={"displayModeBar": False})
                st.markdown(f'<div class="chart-source">Sursa: BNS/ Data.xlsx — foaia Influenta_{tip}</div></div>', unsafe_allow_html=True)
    # ── TAB 4: Per tara ───────────────────────────────────────────────────────
    with tab4:
        st.write("DEBUG df_tari:", df_tari.shape)
        st.dataframe(df_tari.head())
        if not df_tari.empty:
            ani_t = sorted(df_tari["an"].dropna().unique().tolist(), reverse=True)
            ani_t = [int(a) for a in ani_t]

            col_f1, col_f2, col_f3, _ = st.columns([1,1,1,2])
            with col_f1:
                an_t = st.selectbox("An", ani_t, key="tari_an")
            with col_f2:
                luni_t = ["Toate"] + sorted(df_tari[df_tari["an"] == an_t]["luna"].str.strip().unique().tolist())
                luna_t = st.selectbox("Luna", luni_t, key="tari_luna")
            with col_f3:
                tip_t = st.selectbox("Flux", ["Export","Import"], key="tari_tip")

            df_t = df_tari[df_tari["an"] == an_t].copy()
            if luna_t != "Toate":
                df_t = df_t[df_t["luna"].str.strip() == luna_t]

            val_col = "export_mil_usd" if tip_t == "Export" else "import_mil_usd"
            if val_col in df_t.columns and "tara" in df_t.columns:
                agg = df_t.groupby("tara")[val_col].sum().reset_index()
                agg = agg[agg[val_col] > 0].sort_values(val_col, ascending=False).head(20)

                col1, col2 = st.columns([1.6, 1])
                with col1:
                    st.markdown(f'<div class="chart-card"><div class="chart-card-title">Top 20 tari — {tip_t} {an_t}{" " + luna_t if luna_t != "Toate" else ""} (mil. USD)</div>', unsafe_allow_html=True)
                    color_bar = "#534AB7" if tip_t == "Export" else "#E24B4A"
                    fig7 = go.Figure(go.Bar(
                        x=agg[val_col].tolist(),
                        y=agg["tara"].tolist(),
                        orientation="h",
                        marker_color=color_bar, opacity=0.85,
                        text=[f"{v/1000:,.2f}" if v > 999 else f"{v:,.3f}" for v in agg[val_col]],
                        textposition="outside", textfont=dict(size=9),
                        hovertemplate="<b>%{y}</b>: %{x:,.3f} mil.<extra></extra>",
                    ))
                    fig7.update_layout(
                        height=450, paper_bgcolor="white", plot_bgcolor="white",
                        font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                        margin=dict(l=10,r=60,t=10,b=10), showlegend=False,
                        xaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9), zeroline=False),
                        yaxis=dict(showgrid=False, tickfont=dict(size=10), autorange="reversed"),
                    )
                    st.plotly_chart(fig7, use_container_width=True, config={"displayModeBar": False})
                    st.markdown('<div class="chart-source">Sursa: Data.xlsx — foaia Start_Data</div></div>', unsafe_allow_html=True)

                with col2:
                    st.markdown(f'<div class="chart-card"><div class="chart-card-title">Structura pe grupe tari (%)</div>', unsafe_allow_html=True)
                    if "grupa_tari" in df_t.columns:
                        grupe = df_t.groupby("grupa_tari")[val_col].sum().reset_index()
                        grupe = grupe[grupe[val_col] > 0].sort_values(val_col, ascending=False)
                        fig8 = go.Figure(go.Pie(
                            labels=grupe["grupa_tari"].tolist(),
                            values=grupe[val_col].tolist(),
                            hole=0.40,
                            marker_colors=["#185FA5","#1D9E75","#534AB7","#854F0B","#993556","#888780"],
                            textfont_size=10,
                            hovertemplate="<b>%{label}</b>: %{value:,.2f} mil. (%{percent})<extra></extra>",
                        ))
                        fig8.update_layout(
                            height=300, paper_bgcolor="white",
                            font=dict(family="IBM Plex Sans", size=10),
                            margin=dict(l=0,r=0,t=0,b=0),
                            legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                        )
                        st.plotly_chart(fig8, use_container_width=True, config={"displayModeBar": False})
                    st.markdown('<div class="chart-source">Sursa: Data.xlsx — Start_Data</div></div>', unsafe_allow_html=True)
        else:
            st.info("Date per tara indisponibile.")
    # ── TAB 5: Servicii ───────────────────────────────────────────────────────
    with tab5:
        df_serv = res_serv["data"]
        st.markdown(sursa_badge(res_serv), unsafe_allow_html=True)
        st.markdown("")

        if df_serv.empty:
            st.warning("Fisierul Date_Servicii.xlsx nu a putut fi citit.")
        else:
            LABELS_S = df_serv["trim_label"].tolist()

            def _layout_s(h=300):
                return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                            margin=dict(l=10,r=10,t=10,b=10),
                            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=9),
                                       tickangle=-45 if len(LABELS_S) > 16 else 0),
                            yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False))

            # ── KPI servicii ──────────────────────────────────────────────────
            last_s = df_serv.iloc[-1]
            prev_s = df_serv[df_serv["an"] == int(last_s["an"]) - 1]
            prev_s = prev_s[prev_s["trim_nr"] == last_s["trim_nr"]]
            prev_s = prev_s.iloc[-1] if not prev_s.empty else df_serv.iloc[-2]

            exp_s  = last_s["export_servicii_mil_usd"]
            imp_s  = last_s["import_servicii_mil_usd"]
            sold_s = last_s["sold_servicii_mil_usd"]
            exp_s_prev = prev_s["export_servicii_mil_usd"]
            imp_s_prev = prev_s["import_servicii_mil_usd"]
            exp_var_s  = (exp_s - exp_s_prev) / exp_s_prev * 100 if exp_s_prev else None
            imp_var_s  = (imp_s - imp_s_prev) / imp_s_prev * 100 if imp_s_prev else None

            kpi_row([
                kpi_card("Export servicii", f"{exp_s:,.1f}", "mil. USD",
                         f"{exp_var_s:+.1f}% vs trim. an ant." if exp_var_s else last_s["trim_label"],
                         exp_var_s is not None and exp_var_s > 0, "purple"),
                kpi_card("Import servicii", f"{imp_s:,.1f}", "mil. USD",
                         f"{imp_var_s:+.1f}% vs trim. an ant." if imp_var_s else "",
                         imp_var_s is not None and imp_var_s < 0, "purple"),
                kpi_card("Sold servicii", f"{sold_s:,.1f}", "mil. USD",
                         "excedent = pozitiv" if sold_s > 0 else "deficit",
                         sold_s > 0, "purple"),
                kpi_card("Grad acoperire", f"{exp_s/imp_s*100:.1f}", "%",
                         "export / import servicii", exp_s/imp_s > 1, "purple"),
            ])

            # ── Grafice principale ─────────────────────────────────────────────
            col1, col2 = st.columns(2)

            with col1:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Export si Import servicii trimestrial (mil. USD)</div>', unsafe_allow_html=True)
                fig_s1 = go.Figure()
                fig_s1.add_trace(go.Bar(
                    name="Import servicii", x=LABELS_S,
                    y=df_serv["import_servicii_mil_usd"].tolist(),
                    marker_color="#993556", opacity=0.75,
                    hovertemplate="<b>%{x}</b> Import: %{y:,.2f} mil.<extra></extra>"))
                fig_s1.add_trace(go.Bar(
                    name="Export servicii", x=LABELS_S,
                    y=df_serv["export_servicii_mil_usd"].tolist(),
                    marker_color="#534AB7", opacity=0.90,
                    hovertemplate="<b>%{x}</b> Export: %{y:,.2f} mil.<extra></extra>"))
                fig_s1.update_layout(**{**_layout_s(), "barmode": "group",
                    "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)")})
                st.plotly_chart(fig_s1, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: Date_Servicii.xlsx — Imp_Exp_Servicii</div></div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Sold comercial servicii trimestrial (mil. USD)</div>', unsafe_allow_html=True)
                sold_vals = df_serv["sold_servicii_mil_usd"].tolist()
                colors_sold_s = ["#1D9E75" if v >= 0 else "#E24B4A" for v in sold_vals]
                fig_s2 = go.Figure(go.Bar(
                    x=LABELS_S, y=sold_vals,
                    marker_color=colors_sold_s, opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+,.2f} mil. USD<extra></extra>"))
                fig_s2.add_hline(y=0, line_color="#444441", line_width=1)
                fig_s2.update_layout(**{**_layout_s(), "showlegend": False})
                st.plotly_chart(fig_s2, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: Date_Servicii.xlsx — Imp_Exp_Servicii</div></div>', unsafe_allow_html=True)

            # ── Evolutie anuala agregata ───────────────────────────────────────
            st.markdown('<div class="chart-card"><div class="chart-card-title">Export si Import servicii — total anual (mil. USD)</div>', unsafe_allow_html=True)
            df_anual = df_serv.groupby("an").agg(
                export_total=("export_servicii_mil_usd","sum"),
                import_total=("import_servicii_mil_usd","sum"),
                sold_total=("sold_servicii_mil_usd","sum"),
            ).reset_index()
            ani_str = [str(int(a)) for a in df_anual["an"]]

            fig_s3 = go.Figure()
            fig_s3.add_trace(go.Bar(name="Import servicii", x=ani_str,
                y=df_anual["import_total"].tolist(),
                marker_color="#993556", opacity=0.75,
                hovertemplate="<b>%{x}</b> Import: %{y:,.1f} mil.<extra></extra>"))
            fig_s3.add_trace(go.Bar(name="Export servicii", x=ani_str,
                y=df_anual["export_total"].tolist(),
                marker_color="#534AB7", opacity=0.90,
                hovertemplate="<b>%{x}</b> Export: %{y:,.1f} mil.<extra></extra>"))
            fig_s3.add_trace(go.Scatter(name="Sold", x=ani_str,
                y=df_anual["sold_total"].tolist(),
                mode="lines+markers",
                line=dict(color="#1D9E75", width=2.5, dash="dot"),
                marker=dict(size=7),
                hovertemplate="<b>%{x}</b> Sold: %{y:+,.1f} mil.<extra></extra>",
                yaxis="y2"))
            fig_s3.update_layout(
                height=300, paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                margin=dict(l=10,r=50,t=10,b=10), barmode="group",
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. USD"),
                yaxis2=dict(overlaying="y", side="right", tickfont=dict(size=9),
                            title="Sold (mil. USD)", showgrid=False, zeroline=True,
                            zerolinecolor="#e8e4dc", zerolinewidth=1),
            )
            st.plotly_chart(fig_s3, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: Date_Servicii.xlsx — agregat anual calcule MEDD</div></div>', unsafe_allow_html=True)

            # ── Comparatie bunuri vs servicii ─────────────────────────────────
            if not df_lunar.empty and "an" in df_lunar.columns:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Structura export: Bunuri vs Servicii — total anual (mil. USD)</div>', unsafe_allow_html=True)

                # Agregam bunuri lunar pe an
                bunuri_anual = df_lunar.groupby("an").agg(
                    export_bunuri=("export_mil_usd","sum"),
                    import_bunuri=("import_mil_usd","sum"),
                ).reset_index()
                bunuri_anual["an"] = bunuri_anual["an"].astype(int)
                df_anual["an_int"] = df_anual["an"].astype(int)

                merged = bunuri_anual.merge(
                    df_anual[["an_int","export_total","import_total"]].rename(columns={"an_int":"an"}),
                    on="an", how="inner"
                )
                ani_m = [str(a) for a in merged["an"]]

                fig_s4 = go.Figure()
                fig_s4.add_trace(go.Bar(name="Export bunuri", x=ani_m,
                    y=merged["export_bunuri"].tolist(),
                    marker_color="#185FA5", opacity=0.85,
                    hovertemplate="<b>%{x}</b> Bunuri: %{y:,.1f} mil.<extra></extra>"))
                fig_s4.add_trace(go.Bar(name="Export servicii", x=ani_m,
                    y=merged["export_total"].tolist(),
                    marker_color="#534AB7", opacity=0.85,
                    hovertemplate="<b>%{x}</b> Servicii: %{y:,.1f} mil.<extra></extra>"))
                fig_s4.update_layout(
                    height=280, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10,r=10,t=10,b=10), barmode="stack",
                    legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False, title="mil. USD"),
                )
                st.plotly_chart(fig_s4, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: Data.xlsx (bunuri) + Date_Servicii.xlsx (servicii)</div></div>', unsafe_allow_html=True)

            # ── Tabel date complete ────────────────────────────────────────────
            st.markdown('<div class="chart-card"><div class="chart-card-title">Date trimestriale complete</div>', unsafe_allow_html=True)
            show_s = df_serv[["an","trimestru","export_servicii_mil_usd","import_servicii_mil_usd","sold_servicii_mil_usd"]].copy()
            show_s.columns = ["An","Trimestru","Export servicii (mil. USD)","Import servicii (mil. USD)","Sold (mil. USD)"]
            for col in ["Export servicii (mil. USD)","Import servicii (mil. USD)","Sold (mil. USD)"]:
                show_s[col] = show_s[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
            st.dataframe(show_s, use_container_width=True, hide_index=True, height=350)
            st.markdown('<div class="chart-source">Sursa: Date_Servicii.xlsx — Imp_Exp_Servicii</div></div>', unsafe_allow_html=True)
