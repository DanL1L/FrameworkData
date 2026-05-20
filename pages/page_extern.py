import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils.state import page_header, kpi_card, kpi_row
from utils.api_comert_extern import get_comert_ext_bns, get_comert_produse_bns, get_indici_comert_bns, get_comert_tari_bns
from data.excel_loader import load_servicii


def render():
    page_header(
        "Sectorul Extern",
        "Comert exterior bunuri, export, import, servicii · 2015–2026",
        "BNS · BNM",
        "purple"
    )

    res_ext    = get_comert_ext_bns()
    res_prod   = get_comert_produse_bns()
    res_indici = get_indici_comert_bns()
    res_tari   = get_comert_tari_bns()
    res_serv   = load_servicii()

    df_ext = res_ext["data"]

    if df_ext.empty:
        st.warning(f"Date BNS indisponibile: {res_ext.get('eroare','')}")
        if st.button("Reincarcă date comerț", key="reload_ext_main"):
            get_comert_ext_bns.clear()
            st.rerun()
        return

    # Filtrare date Total (fara defalcare pe grupe)
    df_total = df_ext[df_ext["grupa"] == "Total"].copy()
    df_total = df_total.dropna(subset=["export_mil_usd", "import_mil_usd"])

    if not res_ext["live"]:
        st.warning(f"Date offline · {res_ext.get('eroare','')}")

    # ── KPI din ultima luna disponibila ───────────────────────────────────────
    last = df_total.iloc[-1]
    try:
        prev_same = df_total[
            (df_total["luna_nr"] == last["luna_nr"]) &
            (df_total["an"] == int(last["an"]) - 1)
        ]
        prev = prev_same.iloc[-1] if not prev_same.empty else df_total.iloc[-2]
    except Exception:
        prev = df_total.iloc[-2] if len(df_total) >= 2 else last

    exp_val  = last.get("export_mil_usd")
    imp_val  = last.get("import_mil_usd")
    sold_val = last.get("sold_mil_usd")
    exp_prev = prev.get("export_mil_usd")
    imp_prev = prev.get("import_mil_usd")
    exp_var  = ((exp_val - exp_prev) / exp_prev * 100) if exp_val and exp_prev else None
    imp_var  = ((imp_val - imp_prev) / imp_prev * 100) if imp_val and imp_prev else None
    label    = last.get("label", "")

    kpi_row([
        kpi_card("Export", f"{exp_val:,.1f}" if exp_val else "N/A", "mil. USD",
                 f"{exp_var:+.1f}% vs luna an ant." if exp_var is not None else label,
                 exp_var is not None and exp_var > 0, "purple"),
        kpi_card("Import", f"{imp_val:,.1f}" if imp_val else "N/A", "mil. USD",
                 f"{imp_var:+.1f}% vs luna an ant." if imp_var is not None else "",
                 imp_var is not None and imp_var < 0, "purple"),
        kpi_card("Sold comercial", f"{sold_val:,.1f}" if sold_val is not None else "N/A",
                 "mil. USD", label, sold_val is not None and sold_val > 0, "purple"),
        kpi_card("Grad acoperire",
                 f"{exp_val/imp_val*100:.1f}" if exp_val and imp_val else "N/A", "%",
                 "export / import", bool(exp_val and imp_val and exp_val/imp_val > 0.45), "purple"),
    ])

    tab1, tab4, tab_tari, tab_prod, tab_indici, tab5 = st.tabs([
        "Export / Import lunar", "Comerț grupe țări", "Top Țări", "Categoriile de produse (NCM)", "Indici", "Servicii"
    ])

    LABELS = df_total["label"].tolist()

    def _layout(h=300):
        return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=9),
                               tickangle=-45 if len(LABELS) > 16 else 0),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False))

    # ── TAB 1: Export & Import lunar ─────────────────────────────────────────
    with tab1:
        # Date lunare filtrate 2024+
        df_lunar = df_total[df_total["an"] >= 2025].copy()
        LABELS_L = df_lunar["label"].tolist()

        def _layout_l(h=300):
            return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                        font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                        margin=dict(l=10, r=10, t=10, b=10),
                        xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=9),
                                   tickangle=-45 if len(LABELS_L) > 16 else 0),
                        yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False))

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Export si Import lunar (mil. USD) · 2024–prezent</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Import", x=LABELS_L, y=df_lunar["import_mil_usd"].tolist(),
                marker_color="#E24B4A", opacity=0.75,
                hovertemplate="<b>%{x}</b> Import: %{y:,.1f} mil.<extra></extra>"))
            fig.add_trace(go.Bar(name="Export", x=LABELS_L, y=df_lunar["export_mil_usd"].tolist(),
                marker_color="#534AB7", opacity=0.90,
                hovertemplate="<b>%{x}</b> Export: %{y:,.1f} mil.<extra></extra>"))
            fig.update_layout(**{**_layout_l(), "barmode": "group",
                "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                               bgcolor="rgba(0,0,0,0)")})
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            # st.markdown(f'<div class="chart-source">Sursa: BNS EXT015000 ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Balanta comerciala lunara (mil. USD) · 2024–prezent</div>', unsafe_allow_html=True)
            vals_sold = df_lunar["sold_mil_usd"].tolist()
            colors_sold = ["#1D9E75" if v and v >= 0 else "#E24B4A" for v in vals_sold]
            fig2 = go.Figure(go.Bar(x=LABELS_L, y=vals_sold,
                marker_color=colors_sold, opacity=0.85,
                hovertemplate="<b>%{x}</b>: %{y:,.1f} mil. USD<extra></extra>"))
            fig2.add_hline(y=0, line_color="#444441", line_width=1)
            fig2.update_layout(**{**_layout_l(), "showlegend": False})
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            # st.markdown(f'<div class="chart-source">Sursa: BNS EXT015000 ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

        # ── Comert anual — ultimii 5 ani ──────────────────────────────────────
        df_anual_total = (
            df_total.groupby("an")
            .agg(export=("export_mil_usd","sum"), import_=("import_mil_usd","sum"),
                 n_luni=("luna_nr","count"))
            .reset_index()
        )
        df_anual_total["sold"] = df_anual_total["export"] - df_anual_total["import_"]
        df_5ani = df_anual_total.sort_values("an").tail(5)
        ani_5 = df_5ani["an"].astype(str).tolist()

        st.markdown('<div class="chart-card"><div class="chart-card-title">Comert exterior anual — ultimii 5 ani (mil. USD)</div>', unsafe_allow_html=True)
        fig_a = go.Figure()
        fig_a.add_trace(go.Bar(
            name="Import", x=ani_5, y=df_5ani["import_"].tolist(),
            marker_color="#E24B4A", opacity=0.75,
            hovertemplate="<b>%{x}</b> Import: %{y:,.0f} mil.<extra></extra>",
            text=[f"{v:,.0f}" for v in df_5ani["import_"]],
            textposition="outside", textfont=dict(size=9),
        ))
        fig_a.add_trace(go.Bar(
            name="Export", x=ani_5, y=df_5ani["export"].tolist(),
            marker_color="#534AB7", opacity=0.90,
            hovertemplate="<b>%{x}</b> Export: %{y:,.0f} mil.<extra></extra>",
            text=[f"{v:,.0f}" for v in df_5ani["export"]],
            textposition="outside", textfont=dict(size=9),
        ))
        fig_a.add_trace(go.Scatter(
            name="Balanta", x=ani_5, y=df_5ani["sold"].tolist(),
            mode="lines+markers",
            line=dict(color="#1D9E75", width=2.5, dash="dot"),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b> Balanta: %{y:+,.0f} mil.<extra></extra>",
            yaxis="y2",
        ))
        # Nota pentru anul curent (date partiale)
        an_curent = df_5ani["an"].max()
        n_luni_curent = int(df_5ani[df_5ani["an"] == an_curent]["n_luni"].iloc[0])
        if n_luni_curent < 12:
            fig_a.add_annotation(
                x=str(an_curent), y=0, yref="paper",
                text=f"*{n_luni_curent} luni", showarrow=False,
                font=dict(size=9, color="#888780"), yanchor="bottom",
            )
        fig_a.update_layout(
            height=320, paper_bgcolor="white", plot_bgcolor="white",
            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
            margin=dict(l=10, r=60, t=20, b=10), barmode="group",
            legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                        bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=11)),
            yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                       title="mil. USD"),
            yaxis2=dict(overlaying="y", side="right", tickfont=dict(size=9),
                        title="Balanta (mil. USD)", showgrid=False, zeroline=True,
                        zerolinecolor="#e8e4dc", zerolinewidth=1),
        )
        st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})
        nota = f" · *{an_curent}: date partiale ({n_luni_curent} luni)" if n_luni_curent < 12 else ""
        st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_ext["ts"]}){nota}</div></div>', unsafe_allow_html=True)

        # Comparatie anuala
        ani_disponibili = sorted(df_total["an"].dropna().unique().tolist(), reverse=True)
        ani_disponibili = [int(a) for a in ani_disponibili]
        col_sel1, col_sel2, _ = st.columns([1, 1, 3])
        with col_sel1:
            an1 = st.selectbox("An 1", ani_disponibili, index=0, key="ext_an1")
        with col_sel2:
            an2 = st.selectbox("An 2", ani_disponibili, index=min(1, len(ani_disponibili)-1), key="ext_an2")

        st.markdown('<div class="chart-card"><div class="chart-card-title">Comparatie Export lunar</div>', unsafe_allow_html=True)
        fig3 = go.Figure()
        LUNI_SCURTE = ["Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Nov","Dec"]
        colors_ani = ["#534AB7","#185FA5","#1D9E75","#854F0B"]
        for idx, an in enumerate([an1, an2]):
            df_an = df_total[df_total["an"] == an].sort_values("luna_nr")
            if not df_an.empty:
                luni_labels = [LUNI_SCURTE[int(n)-1] for n in df_an["luna_nr"] if 1 <= int(n) <= 12]
                fig3.add_trace(go.Scatter(
                    x=luni_labels, y=df_an["export_mil_usd"].tolist(),
                    name=str(an), mode="lines+markers",
                    line=dict(color=colors_ani[idx % 4], width=2.5),
                    marker=dict(size=6),
                    hovertemplate=f"<b>%{{x}} {an}</b>: %{{y:,.1f}} mil.<extra></extra>"))
        fig3.update_layout(**{**_layout(260), "showlegend": True,
            "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                           bgcolor="rgba(0,0,0,0)")})
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        # st.markdown(f'<div class="chart-source">Sursa: BNS EXT015000 ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

        # Export pe grupe de tari (luna curenta)
        st.markdown('<div class="chart-card"><div class="chart-card-title">Structura Export pe grupe de tari — ultima luna disponibila (mil. USD)</div>', unsafe_allow_html=True)
        df_grupe_last = df_ext[
            (df_ext["an"] == int(last["an"])) &
            (df_ext["luna_nr"] == int(last["luna_nr"])) &
            (df_ext["grupa"] != "Total")
        ].copy()
        if not df_grupe_last.empty:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_g1 = go.Figure(go.Bar(
                    x=df_grupe_last["grupa"].tolist(),
                    y=df_grupe_last["export_mil_usd"].tolist(),
                    marker_color=["#185FA5","#1D9E75","#854F0B"],
                    opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:,.1f} mil.<extra></extra>",
                    name="Export",
                ))
                fig_g1.add_trace(go.Bar(
                    x=df_grupe_last["grupa"].tolist(),
                    y=df_grupe_last["import_mil_usd"].tolist(),
                    marker_color=["#185FA5","#1D9E75","#854F0B"],
                    opacity=0.45,
                    hovertemplate="<b>%{x}</b>: %{y:,.1f} mil.<extra></extra>",
                    name="Import",
                ))
                fig_g1.update_layout(
                    height=260, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10, r=10, t=10, b=10), barmode="group",
                    legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                                bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(showgrid=False, tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
                )
                st.plotly_chart(fig_g1, use_container_width=True, config={"displayModeBar": False})
            with col_g2:
                fig_g2 = go.Figure(go.Pie(
                    labels=df_grupe_last["grupa"].tolist(),
                    values=df_grupe_last["export_mil_usd"].tolist(),
                    hole=0.40,
                    marker_colors=["#185FA5","#1D9E75","#854F0B"],
                    textfont_size=10,
                    hovertemplate="<b>%{label}</b>: %{value:,.1f} mil. (%{percent})<extra></extra>",
                ))
                fig_g2.update_layout(
                    height=260, paper_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=10),
                    margin=dict(l=0, r=0, t=0, b=0),
                    legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_g2, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<div class="chart-source">Sursa: BNS — {label} ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

    # ── TAB 4: Grupe de tari ─────────────────────────────────────────────────
    with tab4:
        df_grupe = df_ext[df_ext["grupa"] != "Total"].copy()

        col_f1, col_f2, _ = st.columns([1, 1, 3])
        with col_f1:
            ani_g = sorted(df_grupe["an"].dropna().unique().tolist(), reverse=True)
            an_g  = st.selectbox("An", [int(a) for a in ani_g], key="grupe_an")
        with col_f2:
            tip_g = st.selectbox("Flux", ["Export", "Import"], key="grupe_tip")

        val_col_g = "export_mil_usd" if tip_g == "Export" else "import_mil_usd"

        # Trend anual agregat pe grupe
        df_anual_grupe = (
            df_grupe.groupby(["an", "grupa"])[["export_mil_usd","import_mil_usd"]]
            .sum(min_count=1).reset_index()
        )

        col1, col2 = st.columns(2)
        GRUPE_COLORS = {"CSI": "#E24B4A", "UE": "#185FA5", "Alte tari": "#854F0B"}

        with col1:
            st.markdown(f'<div class="chart-card"><div class="chart-card-title">Evolutie anuala {tip_g} pe grupe de tari (mil. USD)</div>', unsafe_allow_html=True)
            fig_t1 = go.Figure()
            for grupa, color in GRUPE_COLORS.items():
                df_g = df_anual_grupe[df_anual_grupe["grupa"] == grupa].sort_values("an")
                if not df_g.empty:
                    fig_t1.add_trace(go.Scatter(
                        x=df_g["an"].astype(str).tolist(),
                        y=df_g[val_col_g].tolist(),
                        name=grupa, mode="lines+markers",
                        line=dict(color=color, width=2.5), marker=dict(size=6),
                        hovertemplate=f"<b>%{{x}} {grupa}</b>: %{{y:,.1f}} mil.<extra></extra>",
                    ))
            fig_t1.update_layout(
                height=320, paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                            bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                           title="mil. USD"),
            )
            st.plotly_chart(fig_t1, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

        with col2:
            st.markdown(f'<div class="chart-card"><div class="chart-card-title">Structura {tip_g} pe grupe tari — {an_g} (%)</div>', unsafe_allow_html=True)
            df_pie = df_anual_grupe[df_anual_grupe["an"] == an_g]
            if not df_pie.empty:
                fig_t2 = go.Figure(go.Pie(
                    labels=df_pie["grupa"].tolist(),
                    values=df_pie[val_col_g].tolist(),
                    hole=0.40,
                    marker_colors=[GRUPE_COLORS.get(g,"#888780") for g in df_pie["grupa"].tolist()],
                    textfont_size=10,
                    hovertemplate="<b>%{label}</b>: %{value:,.1f} mil. (%{percent})<extra></extra>",
                ))
                fig_t2.update_layout(
                    height=320, paper_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=10),
                    margin=dict(l=0, r=0, t=0, b=0),
                    legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_t2, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

        # Comparatie Export vs Import pentru fiecare grupa in anul selectat
        st.markdown(f'<div class="chart-card"><div class="chart-card-title">Export vs Import pe grupe de tari — {an_g} (mil. USD)</div>', unsafe_allow_html=True)
        df_cmp = df_anual_grupe[df_anual_grupe["an"] == an_g].copy()
        if not df_cmp.empty:
            fig_t3 = go.Figure()
            fig_t3.add_trace(go.Bar(
                name="Export", x=df_cmp["grupa"].tolist(),
                y=df_cmp["export_mil_usd"].tolist(),
                marker_color="#534AB7", opacity=0.90,
                hovertemplate="<b>%{x}</b> Export: %{y:,.1f} mil.<extra></extra>",
            ))
            fig_t3.add_trace(go.Bar(
                name="Import", x=df_cmp["grupa"].tolist(),
                y=df_cmp["import_mil_usd"].tolist(),
                marker_color="#E24B4A", opacity=0.75,
                hovertemplate="<b>%{x}</b> Import: %{y:,.1f} mil.<extra></extra>",
            ))
            fig_t3.update_layout(
                height=280, paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                margin=dict(l=10, r=10, t=10, b=10), barmode="group",
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                            bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, tickfont=dict(size=11)),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                           title="mil. USD"),
            )
            st.plotly_chart(fig_t3, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

        # Evolutie lunara in anul selectat, pe grupe
        st.markdown(f'<div class="chart-card"><div class="chart-card-title">Evolutie lunara {tip_g} pe grupe de tari — {an_g} (mil. USD)</div>', unsafe_allow_html=True)
        df_luna_an = df_grupe[df_grupe["an"] == an_g].sort_values("luna_nr")
        LUNI_SCURTE = ["Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Nov","Dec"]
        if not df_luna_an.empty:
            fig_t4 = go.Figure()
            for grupa, color in GRUPE_COLORS.items():
                df_gl = df_luna_an[df_luna_an["grupa"] == grupa]
                if not df_gl.empty:
                    luni_l = [LUNI_SCURTE[int(n)-1] for n in df_gl["luna_nr"] if 1 <= int(n) <= 12]
                    fig_t4.add_trace(go.Scatter(
                        x=luni_l, y=df_gl[val_col_g].tolist(),
                        name=grupa, mode="lines+markers",
                        line=dict(color=color, width=2.5), marker=dict(size=6),
                        hovertemplate=f"<b>%{{x}} {grupa}</b>: %{{y:,.1f}} mil.<extra></extra>",
                    ))
            fig_t4.update_layout(
                height=280, paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                            bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                           title="mil. USD"),
            )
            st.plotly_chart(fig_t4, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_ext["ts"]})</div></div>', unsafe_allow_html=True)

    # ── TAB TOP ȚĂRI ─────────────────────────────────────────────────────────
    with tab_tari:
        df_tari_exp = res_tari["export"]
        df_tari_imp = res_tari["import"]

        if df_tari_exp.empty and df_tari_imp.empty:
            st.warning(f"Date tari indisponibile: {res_tari.get('eroare','')}")
            if st.button(" Reincarcă", key="btn_reload_tari"):
                get_comert_tari_bns.clear()
                st.rerun()
        else:
            if not res_tari["live_exp"] or not res_tari["live_imp"]:
                st.warning(f"Date partial offline · {res_tari.get('eroare','')}")

            # ── Selectori an + trimestru ──────────────────────────────────────
            ani_tari = sorted(
                set(
                    (df_tari_exp["an"].dropna().unique().tolist() if not df_tari_exp.empty else []) +
                    (df_tari_imp["an"].dropna().unique().tolist() if not df_tari_imp.empty else [])
                ),
                reverse=True,
            )
            trim_opts_all = ["Anual", "T1", "T2", "T3", "T4"]
            trim_opts_exp = df_tari_exp["trim_label"].dropna().unique().tolist() if not df_tari_exp.empty else []
            trim_opts_imp = df_tari_imp["trim_label"].dropna().unique().tolist() if not df_tari_imp.empty else []
            trim_avail = [t for t in trim_opts_all if t in trim_opts_exp or t in trim_opts_imp]

            col_ta1, col_ta2, _ = st.columns([1, 1, 3])
            with col_ta1:
                an_t = st.selectbox("An", [int(a) for a in ani_tari], key="tari_an")
            with col_ta2:
                trim_t = st.selectbox("Trimestru", trim_avail or trim_opts_all,
                                      key="tari_trim")

            col1, col2 = st.columns(2)

            # ── Top 10 Export ─────────────────────────────────────────────────
            with col1:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Top 10 destinatii Export (mil. USD)</div>', unsafe_allow_html=True)
                if not df_tari_exp.empty:
                    df_te = df_tari_exp[
                        (df_tari_exp["an"] == an_t) &
                        (df_tari_exp["trim_label"] == trim_t) &
                        (df_tari_exp["tara"] != "Total")
                    ].dropna(subset=["export_mil_usd"]).nlargest(10, "export_mil_usd")

                    if not df_te.empty:
                        df_te = df_te.sort_values("export_mil_usd", ascending=True)
                        colors_exp = ["#378ADD" if i < len(df_te) - 1 else "#185FA5"
                                      for i in range(len(df_te))]
                        fig_te = go.Figure(go.Bar(
                            y=df_te["tara"].tolist(),
                            x=df_te["export_mil_usd"].tolist(),
                            orientation="h",
                            marker_color=colors_exp,
                            opacity=0.88,
                            text=[f"{v:,.1f}" for v in df_te["export_mil_usd"]],
                            textposition="outside",
                            textfont=dict(size=9),
                            hovertemplate="<b>%{y}</b>: %{x:,.1f} mil. USD<extra></extra>",
                        ))
                        fig_te.update_layout(
                            height=360, paper_bgcolor="white", plot_bgcolor="white",
                            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                            margin=dict(l=10, r=60, t=10, b=10), showlegend=False,
                            xaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9), zeroline=False,
                                       title="mil. USD"),
                            yaxis=dict(showgrid=False, tickfont=dict(size=10)),
                        )
                        st.plotly_chart(fig_te, use_container_width=True,
                                        config={"displayModeBar": False})
                    else:
                        st.info(f"Fara date export pentru {trim_t} {an_t}.")
                else:
                    st.info("Date export pe tari indisponibile.")
                st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_tari["ts"]})</div></div>', unsafe_allow_html=True)

            # ── Top 10 Import ─────────────────────────────────────────────────
            with col2:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Top 10 surse Import (mil. USD)</div>', unsafe_allow_html=True)
                if not df_tari_imp.empty:
                    df_ti = df_tari_imp[
                        (df_tari_imp["an"] == an_t) &
                        (df_tari_imp["trim_label"] == trim_t) &
                        (df_tari_imp["tara"] != "Total")
                    ].dropna(subset=["import_mil_usd"]).nlargest(10, "import_mil_usd")

                    if not df_ti.empty:
                        df_ti = df_ti.sort_values("import_mil_usd", ascending=True)
                        colors_imp = ["#E87877" if i < len(df_ti) - 1 else "#E24B4A"
                                      for i in range(len(df_ti))]
                        fig_ti = go.Figure(go.Bar(
                            y=df_ti["tara"].tolist(),
                            x=df_ti["import_mil_usd"].tolist(),
                            orientation="h",
                            marker_color=colors_imp,
                            opacity=0.88,
                            text=[f"{v:,.1f}" for v in df_ti["import_mil_usd"]],
                            textposition="outside",
                            textfont=dict(size=9),
                            hovertemplate="<b>%{y}</b>: %{x:,.1f} mil. USD<extra></extra>",
                        ))
                        fig_ti.update_layout(
                            height=360, paper_bgcolor="white", plot_bgcolor="white",
                            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                            margin=dict(l=10, r=60, t=10, b=10), showlegend=False,
                            xaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9), zeroline=False,
                                       title="mil. USD"),
                            yaxis=dict(showgrid=False, tickfont=dict(size=10)),
                        )
                        st.plotly_chart(fig_ti, use_container_width=True,
                                        config={"displayModeBar": False})
                    else:
                        st.info(f"Fara date import pentru {trim_t} {an_t}.")
                else:
                    st.info("Date import pe tari indisponibile.")
                st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_tari["ts"]})</div></div>', unsafe_allow_html=True)

            # ── Evolutie top 5 tari in timp ───────────────────────────────────
            if not df_tari_exp.empty:
                df_exp_anual = df_tari_exp[
                    (df_tari_exp["trim_label"] == "Anual") &
                    (df_tari_exp["tara"] != "Total")
                ].dropna(subset=["export_mil_usd"])

                if not df_exp_anual.empty:
                    # Top 5 tari dupa ultimul an disponibil
                    an_ref = df_exp_anual["an"].max()
                    top5_exp = (
                        df_exp_anual[df_exp_anual["an"] == an_ref]
                        .nlargest(5, "export_mil_usd")["tara"].tolist()
                    )
                    df_ev = df_exp_anual[df_exp_anual["tara"].isin(top5_exp)].sort_values("an")

                    st.markdown('<div class="chart-card"><div class="chart-card-title">Evolutie anuala Export — Top 5 tari partenere (mil. USD)</div>', unsafe_allow_html=True)
                    fig_ev = go.Figure()
                    EV_COLORS = ["#185FA5","#1D9E75","#854F0B","#534AB7","#E24B4A"]
                    for i, tara in enumerate(top5_exp):
                        df_t = df_ev[df_ev["tara"] == tara]
                        fig_ev.add_trace(go.Scatter(
                            name=tara,
                            x=df_t["an"].astype(str).tolist(),
                            y=df_t["export_mil_usd"].tolist(),
                            mode="lines+markers",
                            line=dict(color=EV_COLORS[i % 5], width=2.5),
                            marker=dict(size=6),
                            hovertemplate=f"<b>%{{x}} {tara}</b>: %{{y:,.1f}} mil.<extra></extra>",
                        ))
                    fig_ev.update_layout(
                        height=300, paper_bgcolor="white", plot_bgcolor="white",
                        font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                        margin=dict(l=10, r=10, t=10, b=10),
                        legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                                    bgcolor="rgba(0,0,0,0)"),
                        xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                        yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                                   title="mil. USD"),
                    )
                    st.plotly_chart(fig_ev, use_container_width=True,
                                    config={"displayModeBar": False})
                    st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_tari["ts"]})</div></div>', unsafe_allow_html=True)

    # ── TAB PRODUSE NCM ───────────────────────────────────────────────────────
    with tab_prod:
        df_prod = res_prod["data"]

        if df_prod.empty:
            st.warning(f"Date produse NCM indisponibile: {res_prod.get('eroare','')}")
            if st.button("Reincarcă", key="btn_reload_prod"):
                get_comert_produse_bns.clear()
                st.rerun()
        else:
            if not res_prod["live"]:
                st.warning(f"Date offline · {res_prod.get('eroare','')}")

            ani_prod = sorted(df_prod["an"].dropna().unique().tolist(), reverse=True)

            # Optiunile de trimestru disponibile in date (trim_nr 0=Anual, 1-4=trimestre)
            _TRIM_OPTS = {0: "Anual (T1-T4)", 1: "Trimestrul I", 2: "Trimestrul II",
                          3: "Trimestrul III", 4: "Trimestrul IV"}
            trim_nrs_avail = sorted(df_prod["trim_nr"].unique().tolist())
            trim_opts_avail = {k: v for k, v in _TRIM_OPTS.items() if k in trim_nrs_avail}

            col_fp1, col_fp2, col_fp3, _ = st.columns([1, 1, 1, 1])
            with col_fp1:
                an_p = st.selectbox("An", [int(a) for a in ani_prod], key="prod_an")
            with col_fp2:
                an_p_prev = st.selectbox("An referinta",
                                         [int(a) for a in ani_prod],
                                         index=min(1, len(ani_prod) - 1),
                                         key="prod_an_prev")
            with col_fp3:
                trim_sel_label = st.selectbox(
                    "Trimestru",
                    options=list(trim_opts_avail.values()),
                    index=0,
                    key="prod_trim",
                )
            trim_sel_nr = next(k for k, v in trim_opts_avail.items() if v == trim_sel_label)

            # Eticheta perioadei pentru titluri
            per_label = f"{trim_sel_label} {an_p}" if trim_sel_nr != 0 else str(an_p)
            per_prev_label = f"{trim_sel_label} {an_p_prev}" if trim_sel_nr != 0 else str(an_p_prev)

            df_cur  = df_prod[(df_prod["an"] == an_p)     & (df_prod["trim_nr"] == trim_sel_nr)].copy()
            df_prev = df_prod[(df_prod["an"] == an_p_prev) & (df_prod["trim_nr"] == trim_sel_nr)].copy()

            # Excludem randul Total din graficele pe sectiuni
            df_cur_sect  = df_cur[df_cur["sectiune"] != "Total"].copy()
            df_prev_sect = df_prev[df_prev["sectiune"] != "Total"].copy()

            # Total pentru calculul gradului de influenta
            total_prev = df_prev[df_prev["sectiune"] == "Total"]
            total_exp_prev = float(total_prev["export_mil_usd"].iloc[0]) if not total_prev.empty else None
            total_imp_prev = float(total_prev["import_mil_usd"].iloc[0]) if not total_prev.empty else None

            # Imbinare cur + prev pentru calcule
            merged = df_cur_sect.merge(
                df_prev_sect[["sectiune", "export_mil_usd", "import_mil_usd"]],
                on="sectiune", suffixes=("", "_prev"), how="left"
            )

            # Rata de crestere (%)
            merged["rata_exp"] = (
                (merged["export_mil_usd"] - merged["export_mil_usd_prev"])
                / merged["export_mil_usd_prev"] * 100
            ).where(merged["export_mil_usd_prev"].notna() & (merged["export_mil_usd_prev"] != 0))

            merged["rata_imp"] = (
                (merged["import_mil_usd"] - merged["import_mil_usd_prev"])
                / merged["import_mil_usd_prev"] * 100
            ).where(merged["import_mil_usd_prev"].notna() & (merged["import_mil_usd_prev"] != 0))

            # Grad de influenta = (val_cur - val_prev) / Total_prev * 100
            merged["influenta_exp"] = (
                (merged["export_mil_usd"] - merged["export_mil_usd_prev"]) / total_exp_prev * 100
                if total_exp_prev else None
            )
            merged["influenta_imp"] = (
                (merged["import_mil_usd"] - merged["import_mil_usd_prev"]) / total_imp_prev * 100
                if total_imp_prev else None
            )

            def _lp(h=360):
                return dict(
                    height=h, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                    margin=dict(l=10, r=60, t=10, b=10),
                    xaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9), zeroline=False),
                    yaxis=dict(showgrid=False, tickfont=dict(size=9), autorange="reversed"),
                )

            sursa_label = f"BNS  ({res_prod['ts']})"

            # ── Structura pe sectiuni ────────────────────────────────────────
            col_exp_str, col_imp_str = st.columns(2)

            df_exp_str = merged.dropna(subset=["export_mil_usd"]).sort_values("export_mil_usd", ascending=True).tail(15)
            lbl_exp_str = df_exp_str["sectiune_label"].str.replace(r"^[IVXLC]+\.\s*", "", regex=True).str[:35]

            df_imp_str = merged.dropna(subset=["import_mil_usd"]).sort_values("import_mil_usd", ascending=True).tail(15)
            lbl_imp_str = df_imp_str["sectiune_label"].str.replace(r"^[IVXLC]+\.\s*", "", regex=True).str[:35]

            with col_exp_str:
                st.markdown(f'<div class="chart-card"><div class="chart-card-title">Export pe sectiuni NCM — {per_label} (mil. USD)</div>', unsafe_allow_html=True)
                fig_exp_str = go.Figure(go.Bar(
                    y=lbl_exp_str.tolist(), x=df_exp_str["export_mil_usd"].tolist(),
                    orientation="h", marker_color="#534AB7", opacity=0.90,
                    hovertemplate="<b>%{y}</b>: %{x:,.1f} mil.<extra></extra>",
                ))
                fig_exp_str.update_layout(**_lp(420))
                st.plotly_chart(fig_exp_str, use_container_width=True, config={"displayModeBar": False})
                st.markdown(f'<div class="chart-source">Sursa: {sursa_label}</div></div>', unsafe_allow_html=True)

            with col_imp_str:
                st.markdown(f'<div class="chart-card"><div class="chart-card-title">Import pe sectiuni NCM — {per_label} (mil. USD)</div>', unsafe_allow_html=True)
                fig_imp_str = go.Figure(go.Bar(
                    y=lbl_imp_str.tolist(), x=df_imp_str["import_mil_usd"].tolist(),
                    orientation="h", marker_color="#E24B4A", opacity=0.85,
                    hovertemplate="<b>%{y}</b>: %{x:,.1f} mil.<extra></extra>",
                ))
                fig_imp_str.update_layout(**_lp(420))
                st.plotly_chart(fig_imp_str, use_container_width=True, config={"displayModeBar": False})
                st.markdown(f'<div class="chart-source">Sursa: {sursa_label}</div></div>', unsafe_allow_html=True)

            # ── Grad de influenta ───────────────────────────────────────────
            col1, col2 = st.columns(2)

            for col_ui, tip, col_inf in [
                (col1, "Export", "influenta_exp"),
                (col2, "Import", "influenta_imp"),
            ]:
                with col_ui:
                    st.markdown(f'<div class="chart-card"><div class="chart-card-title">Grad de influenta {tip} — {per_label} vs {per_prev_label} (pp)</div>', unsafe_allow_html=True)
                    df_inf = merged.dropna(subset=[col_inf]).sort_values(col_inf)
                    df_inf = df_inf[df_inf["sectiune"] != "Total"]
                    lbl_inf = df_inf["sectiune_label"].str.replace(r"^[IVXLC]+\.\s*", "", regex=True).str[:35]
                    colors_inf = ["#1D9E75" if v >= 0 else "#E24B4A" for v in df_inf[col_inf]]
                    fig_inf = go.Figure(go.Bar(
                        x=df_inf[col_inf].tolist(), y=lbl_inf.tolist(),
                        orientation="h", marker_color=colors_inf, opacity=0.85,
                        hovertemplate="<b>%{y}</b>: %{x:+.2f} pp<extra></extra>",
                    ))
                    fig_inf.add_vline(x=0, line_color="#444441", line_width=1)
                    fig_inf.update_layout(
                        height=400, paper_bgcolor="white", plot_bgcolor="white",
                        font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                        margin=dict(l=10, r=20, t=10, b=10), showlegend=False,
                        xaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9),
                                   zeroline=False, title="puncte procentuale"),
                        yaxis=dict(showgrid=False, tickfont=dict(size=9)),
                    )
                    st.plotly_chart(fig_inf, use_container_width=True, config={"displayModeBar": False})
                    st.markdown(f'<div class="chart-source">Sursa: {sursa_label}</div></div>', unsafe_allow_html=True)

            # ── Rata de crestere ────────────────────────────────────────────
            st.markdown(f'<div class="chart-card"><div class="chart-card-title">Rata de crestere pe sectiuni NCM — {per_label} vs {per_prev_label} (%)</div>', unsafe_allow_html=True)
            df_rata = merged.dropna(subset=["rata_exp", "rata_imp"])
            df_rata = df_rata[df_rata["sectiune"] != "Total"].sort_values("rata_exp", ascending=False)
            lbl_rata = df_rata["sectiune_label"].str.replace(r"^[IVXLC]+\.\s*", "", regex=True).str[:35]

            fig_rata = go.Figure()
            fig_rata.add_trace(go.Bar(
                name=f"Export {per_prev_label}→{per_label}",
                x=lbl_rata.tolist(), y=df_rata["rata_exp"].tolist(),
                marker_color="#534AB7", opacity=0.85,
                hovertemplate="<b>%{x}</b> Export: %{y:+.1f}%<extra></extra>",
                text=[f"{v:+.0f}%" for v in df_rata["rata_exp"]],
                textposition="outside", textfont=dict(size=8),
            ))
            fig_rata.add_trace(go.Bar(
                name=f"Import {per_prev_label}→{per_label}",
                x=lbl_rata.tolist(), y=df_rata["rata_imp"].tolist(),
                marker_color="#E24B4A", opacity=0.70,
                hovertemplate="<b>%{x}</b> Import: %{y:+.1f}%<extra></extra>",
            ))
            fig_rata.add_hline(y=0, line_color="#444441", line_width=1)
            fig_rata.update_layout(
                height=320, paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                margin=dict(l=10, r=10, t=20, b=10), barmode="group",
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                            bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, tickfont=dict(size=8), tickangle=-40),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=9), zeroline=False,
                           title="%"),
            )
            st.plotly_chart(fig_rata, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: {sursa_label}</div></div>', unsafe_allow_html=True)

    # ── TAB INDICI ────────────────────────────────────────────────────────────
    with tab_indici:
        df_ind = res_indici["data"]

        if df_ind.empty:
            st.warning(f"Date indici indisponibile: {res_indici.get('eroare','')}")
            if st.button("Reincarcă", key="reload_indici"):
                get_indici_comert_bns.clear()
                st.rerun()
        else:
            if not res_indici["live"]:
                st.warning(f"Date offline · {res_indici.get('eroare','')}")

            ani_ind = sorted(df_ind["an"].unique().tolist(), reverse=True)

            col_i1, col_i2, _ = st.columns([1, 1, 3])
            with col_i1:
                an_ind_start = st.selectbox("An de la", ani_ind,
                                            index=min(4, len(ani_ind) - 1), key="ind_start")
            with col_i2:
                an_ind_end = st.selectbox("An pana la", ani_ind,
                                          index=0, key="ind_end")

            an_lo = min(an_ind_start, an_ind_end)
            an_hi = max(an_ind_start, an_ind_end)
            df_i = df_ind[(df_ind["an"] >= an_lo) & (df_ind["an"] <= an_hi)].copy()

            df_exp = df_i[df_i["indicatori"] == "Export"].sort_values(["an", "trim_nr"])
            df_imp = df_i[df_i["indicatori"] == "Import"].sort_values(["an", "trim_nr"])
            TRIM_L = df_exp["trim_label"].tolist()

            def _li(h=260):
                return dict(
                    height=h, paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=9),
                               tickangle=-45 if len(TRIM_L) > 12 else 0),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False),
                )

            # Linie de referinta la 100
            def _hline100(fig):
                fig.add_hline(y=100, line_color="#888780", line_width=1, line_dash="dot")

            # ── Indici valorici ───────────────────────────────────────────────
            st.markdown('<div class="chart-card"><div class="chart-card-title">Indicii valorici Export si Import (perioada corespunzatoare an precedent = 100)</div>', unsafe_allow_html=True)
            fig_iv = go.Figure()
            fig_iv.add_trace(go.Scatter(
                name="Export — Indice valoric", x=TRIM_L, y=df_exp["ind_valoric"].tolist(),
                mode="lines+markers", line=dict(color="#534AB7", width=2.5), marker=dict(size=5),
                hovertemplate="<b>%{x}</b> Export: %{y:.1f}<extra></extra>",
            ))
            fig_iv.add_trace(go.Scatter(
                name="Import — Indice valoric", x=TRIM_L, y=df_imp["ind_valoric"].tolist(),
                mode="lines+markers", line=dict(color="#E24B4A", width=2.5), marker=dict(size=5),
                hovertemplate="<b>%{x}</b> Import: %{y:.1f}<extra></extra>",
            ))
            _hline100(fig_iv)
            fig_iv.update_layout(**{**_li(280), "showlegend": True,
                "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                               bgcolor="rgba(0,0,0,0)"),
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                              title="indice (an prec. = 100)"),
            })
            st.plotly_chart(fig_iv, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_indici["ts"]})</div></div>', unsafe_allow_html=True)

            # ── Indici valoare unitara + volum fizic ──────────────────────────
            col1, col2 = st.columns(2)

            with col1:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Indicii valorii unitare — preturi (an prec. = 100)</div>', unsafe_allow_html=True)
                fig_vu = go.Figure()
                fig_vu.add_trace(go.Scatter(
                    name="Export", x=TRIM_L, y=df_exp["ind_val_unitara"].tolist(),
                    mode="lines+markers", line=dict(color="#534AB7", width=2.5), marker=dict(size=5),
                    hovertemplate="<b>%{x}</b> Export: %{y:.1f}<extra></extra>",
                ))
                fig_vu.add_trace(go.Scatter(
                    name="Import", x=TRIM_L, y=df_imp["ind_val_unitara"].tolist(),
                    mode="lines+markers", line=dict(color="#E24B4A", width=2.5), marker=dict(size=5),
                    hovertemplate="<b>%{x}</b> Import: %{y:.1f}<extra></extra>",
                ))
                _hline100(fig_vu)
                fig_vu.update_layout(**{**_li(), "showlegend": True,
                    "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                                   bgcolor="rgba(0,0,0,0)"),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                                  title="indice"),
                })
                st.plotly_chart(fig_vu, use_container_width=True, config={"displayModeBar": False})
                st.markdown(f'<div class="chart-source">Sursa: BNS </div></div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Indicii volumului fizic — cantitati (an prec. = 100)</div>', unsafe_allow_html=True)
                fig_vf = go.Figure()
                fig_vf.add_trace(go.Scatter(
                    name="Export", x=TRIM_L, y=df_exp["ind_volum"].tolist(),
                    mode="lines+markers", line=dict(color="#534AB7", width=2.5), marker=dict(size=5),
                    hovertemplate="<b>%{x}</b> Export: %{y:.1f}<extra></extra>",
                ))
                fig_vf.add_trace(go.Scatter(
                    name="Import", x=TRIM_L, y=df_imp["ind_volum"].tolist(),
                    mode="lines+markers", line=dict(color="#E24B4A", width=2.5), marker=dict(size=5),
                    hovertemplate="<b>%{x}</b> Import: %{y:.1f}<extra></extra>",
                ))
                _hline100(fig_vf)
                fig_vf.update_layout(**{**_li(), "showlegend": True,
                    "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                                   bgcolor="rgba(0,0,0,0)"),
                    "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                                  title="indice"),
                })
                st.plotly_chart(fig_vf, use_container_width=True, config={"displayModeBar": False})
                st.markdown(f'<div class="chart-source">Sursa: BNS </div></div>', unsafe_allow_html=True)

            # ── Termenii de schimb (terms of trade) ──────────────────────────
            df_tot = df_exp[["an", "trim_nr", "trim_label", "ind_val_unitara"]].merge(
                df_imp[["an", "trim_nr", "ind_val_unitara"]],
                on=["an", "trim_nr"], suffixes=("_exp", "_imp"),
            )
            df_tot["terms_of_trade"] = (
                df_tot["ind_val_unitara_exp"] / df_tot["ind_val_unitara_imp"] * 100
            ).where(df_tot["ind_val_unitara_imp"].notna() & (df_tot["ind_val_unitara_imp"] != 0))

            st.markdown('<div class="chart-card"><div class="chart-card-title">Termenii de schimb — Ind. val. unitara Export / Import × 100 (>100 = avantaj export)</div>', unsafe_allow_html=True)
            vals_tot = df_tot["terms_of_trade"].tolist()
            colors_tot = ["#1D9E75" if v and v >= 100 else "#E24B4A" for v in vals_tot]
            fig_tot = go.Figure()
            fig_tot.add_trace(go.Bar(
                x=df_tot["trim_label"].tolist(), y=vals_tot,
                marker_color=colors_tot, opacity=0.85,
                hovertemplate="<b>%{x}</b>: %{y:.1f}<extra></extra>",
            ))
            fig_tot.add_hline(y=100, line_color="#444441", line_width=1.5, line_dash="dash")
            fig_tot.update_layout(**{**_li(260), "showlegend": False,
                "yaxis": dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                              title="indice"),
            })
            st.plotly_chart(fig_tot, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: BNS  ({res_indici["ts"]})</div></div>', unsafe_allow_html=True)

    # ── TAB 5: Servicii ──────────────────────────────────────────────────────
    with tab5:
        df_serv = res_serv["data"]

        if df_serv.empty:
            st.warning("Fisierul Date_Servicii.xlsx nu a putut fi citit.")
        else:
            LABELS_S = df_serv["trim_label"].tolist()

            def _layout_s(h=300):
                return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                            font=dict(family="IBM Plex Sans", size=11, color="#444441"),
                            margin=dict(l=10, r=10, t=10, b=10),
                            xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=9),
                                       tickangle=-45 if len(LABELS_S) > 16 else 0),
                            yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False))

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
                    "legend": dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                                   bgcolor="rgba(0,0,0,0)")})
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

            st.markdown('<div class="chart-card"><div class="chart-card-title">Export si Import servicii — total anual (mil. USD)</div>', unsafe_allow_html=True)
            df_anual = df_serv.groupby("an").agg(
                export_total=("export_servicii_mil_usd", "sum"),
                import_total=("import_servicii_mil_usd", "sum"),
                sold_total=("sold_servicii_mil_usd", "sum"),
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
                margin=dict(l=10, r=50, t=10, b=10), barmode="group",
                legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                            bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                           title="mil. USD"),
                yaxis2=dict(overlaying="y", side="right", tickfont=dict(size=9),
                            title="Sold (mil. USD)", showgrid=False, zeroline=True,
                            zerolinecolor="#e8e4dc", zerolinewidth=1),
            )
            st.plotly_chart(fig_s3, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: Date_Servicii.xlsx — agregat anual</div></div>', unsafe_allow_html=True)

            # Comparatie bunuri vs servicii (bunuri din BNS API)
            if not df_total.empty and "an" in df_total.columns:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Structura export: Bunuri vs Servicii — total anual (mil. USD)</div>', unsafe_allow_html=True)
                bunuri_anual = df_total.groupby("an").agg(
                    export_bunuri=("export_mil_usd", "sum"),
                    import_bunuri=("import_mil_usd", "sum"),
                ).reset_index()
                bunuri_anual["an"] = bunuri_anual["an"].astype(int)
                df_anual["an_int"] = df_anual["an"].astype(int)
                merged = bunuri_anual.merge(
                    df_anual[["an_int","export_total","import_total"]].rename(
                        columns={"an_int": "an"}),
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
                    margin=dict(l=10, r=10, t=10, b=10), barmode="stack",
                    legend=dict(orientation="h", y=1.05, x=0, font=dict(size=10),
                                bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#f1efe8", tickfont=dict(size=10), zeroline=False,
                               title="mil. USD"),
                )
                st.plotly_chart(fig_s4, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: BNS (bunuri) + Date_Servicii.xlsx (servicii)</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="chart-card"><div class="chart-card-title">Date trimestriale complete</div>', unsafe_allow_html=True)
            show_s = df_serv[["an","trimestru","export_servicii_mil_usd","import_servicii_mil_usd","sold_servicii_mil_usd"]].copy()
            show_s.columns = ["An","Trimestru","Export servicii (mil. USD)","Import servicii (mil. USD)","Sold (mil. USD)"]
            for col in ["Export servicii (mil. USD)","Import servicii (mil. USD)","Sold (mil. USD)"]:
                show_s[col] = show_s[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
            st.dataframe(show_s, use_container_width=True, hide_index=True, height=350)
            st.markdown('<div class="chart-source">Sursa: Date_Servicii.xlsx — Imp_Exp_Servicii</div></div>', unsafe_allow_html=True)
