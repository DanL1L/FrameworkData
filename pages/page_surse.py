import streamlit as st
import pandas as pd
from utils.state import page_header
from utils.api_bns import test_bns, bns_list, BNS_TABLES
from utils.api_bnm import test_bnm, get_rata_bnm, get_rezerve, get_curs_oficial
from utils.api_imf import (
    test_imf, test_wb, get_imf_prognoze,
    imf_weo_multi, wb_multi, imf_regional_compare,
    get_imf_overview, get_wb_social,
)
from utils.api_upload import parse_uploaded_file, auto_map_columns, generate_bns_export, generate_data_export
from utils.charts import line_chart


def render():
    page_header(
        "Surse de date & API",
        "Conexiuni API, upload fisiere, status date",
        "BNS · BNM · IMF · World Bank",
        "gray"
    )

    tab1, tab3, tab4 = st.tabs(["Status API", "Upload fisiere", "IMF & World Bank"])

    # ── Tab 1: Status API ──────────────────────────────────────────────────────
    with tab1:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Conexiuni API active</div>', unsafe_allow_html=True)

        col_test1, col_test2, col_test3, col_test4 = st.columns(4)
        with col_test1:
            if st.button("Test BNS", use_container_width=True):
                with st.spinner("..."):
                    res = test_bns()
                    st.session_state["bns_status"] = res
        with col_test2:
            if st.button("Test BNM", use_container_width=True):
                with st.spinner("..."):
                    res = test_bnm()
                    st.session_state["bnm_status"] = res
        with col_test3:
            if st.button("Test IMF", use_container_width=True):
                with st.spinner("..."):
                    res = test_imf()
                    st.session_state["imf_status"] = res
        with col_test4:
            if st.button("Test World Bank", use_container_width=True):
                with st.spinner("..."):
                    res = test_wb()
                    st.session_state["wb_status"] = res

        st.markdown("<br>", unsafe_allow_html=True)

        sources = [
            {
                "name":     "BNS — statistica.gov.md",
                "endpoint": "PX-Web API v1",
                "desc":     "PIB, preturi, comert exterior, piata muncii, agricultura",
                "key":      "bns_status",
                "docs":     "https://statistica.gov.md/api/v1/ro",
            },
            {
                "name":     "BNM — bnm.md",
                "endpoint": "REST API JSON",
                "desc":     "Curs valutar, rata politicii monetare, rezerve, agregate M3",
                "key":      "bnm_status",
                "docs":     "https://www.bnm.md/ro/content/date-statistice-json",
            },
            {
                "name":     "IMF DataMapper",
                "endpoint": "DataMapper API v1",
                "desc":     "WEO — prognoze PIB, inflatie, cont curent, datorie publica",
                "key":      "imf_status",
                "docs":     "https://data.imf.org/en/Resource-Pages/IMF-API",
            },
            {
                "name":     "World Bank Open Data",
                "endpoint": "WB API v2",
                "desc":     "Indicatori sociali: saracie, sanatate, educatie, remitente",
                "key":      "wb_status",
                "docs":     "https://data360.worldbank.org/en/api",
            },
        ]

        for src in sources:
            status_data = st.session_state.get(src["key"])
            if status_data:
                is_ok = status_data.get("status") == "ok"
                badge = "✓ Conectat" if is_ok else "✗ Eroare"
                badge_style = "background:#E1F5EE;color:#0F6E56;padding:2px 8px;border-radius:3px;font-size:11px;" if is_ok else \
                              "background:#FCEBEB;color:#A32D2D;padding:2px 8px;border-radius:3px;font-size:11px;"
                ms_info = f" · {status_data.get('ms','')}ms" if is_ok else ""
                status_html = f'<span style="{badge_style}">{badge}{ms_info}</span>'
            else:
                status_html = '<span style="background:#F1EFE8;color:#888780;padding:2px 8px;border-radius:3px;font-size:11px;">Netestat</span>'

            st.markdown(f"""
            <div style="border:1px solid #e8e4dc;border-radius:6px;padding:12px 16px;
                        margin-bottom:8px;display:flex;align-items:center;
                        justify-content:space-between;background:white">
                <div>
                    <div style="font-size:13px;font-weight:500;color:#0C1929">{src['name']}</div>
                    <div style="font-size:11px;color:#888780;margin-top:2px;
                                font-family:'IBM Plex Mono',monospace">{src['endpoint']}
                         &nbsp;·&nbsp; <a href="{src['docs']}" target="_blank"
                         style="color:#185FA5">docs</a></div>
                    <div style="font-size:11px;color:#5F5E5A;margin-top:3px">{src['desc']}</div>
                </div>
                <div>{status_html}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Tabele BNS disponibile
        st.markdown('<div class="chart-card"><div class="chart-card-title">Tabele BNS disponibile</div>', unsafe_allow_html=True)
        tbl_df = pd.DataFrame([
            {"Sector": "PIB & conturi nationale", "Tabel": "TNA01", "Path": "SocEc/NA/TNA01/"},
            {"Sector": "PIB trimestrial",          "Tabel": "TNA04", "Path": "SocEc/NA/TNA04/"},
            {"Sector": "Indici preturi consum",    "Tabel": "TPR01", "Path": "SocEc/Pr/TPR01/"},
            {"Sector": "IPC componente",           "Tabel": "TPR02", "Path": "SocEc/Pr/TPR02/"},
            {"Sector": "Comert exterior export",   "Tabel": "TCE01", "Path": "SocEc/CE/TCE01/"},
            {"Sector": "Comert exterior import",   "Tabel": "TCE02", "Path": "SocEc/CE/TCE02/"},
            {"Sector": "Piata muncii — somaj",     "Tabel": "TFM01", "Path": "SocEc/FM/TFM01/"},
            {"Sector": "Salarii pe activitati",    "Tabel": "TFM08", "Path": "SocEc/FM/TFM08/"},
        ])
        st.dataframe(tbl_df, use_container_width=True, hide_index=True)
        st.markdown('<div class="chart-source">Sursa: statistica.gov.md/api/v1/ro — PX-Web API</div></div>', unsafe_allow_html=True)

    # # ── Tab 2: Date live BNM ───────────────────────────────────────────────────
    # with tab2:
    #     col_a, col_b = st.columns(2)

    #     with col_a:
    #         valuta = st.selectbox("Valuta", ["EUR", "USD", "RON", "GBP", "UAH"], index=0)
    #         zile   = st.selectbox("Perioada", [30, 90, 180, 365], index=1,
    #                               format_func=lambda x: f"Ultimele {x} zile")

    #     with col_b:
    #         st.markdown("<br>", unsafe_allow_html=True)
    #         if st.button("Incarca date curs valutar", use_container_width=True):
    #             with st.spinner(f"Se extrage cursul {valuta}/MDL din BNM..."):
    #                 df_curs = get_curs_oficial(valuta, zile)
    #                 st.session_state["curs_df"] = df_curs
    #                 st.session_state["curs_valuta"] = valuta

    #     df_curs = st.session_state.get("curs_df")
    #     valuta_sel = st.session_state.get("curs_valuta", valuta)

    #     if df_curs is not None and not df_curs.empty:
    #         st.markdown(f'<div class="chart-card"><div class="chart-card-title">Curs {valuta_sel}/MDL — BNM oficial</div>', unsafe_allow_html=True)
    #         import plotly.graph_objects as go
    #         fig = go.Figure(go.Scatter(
    #             x=df_curs["data"], y=df_curs.iloc[:, 1],
    #             mode="lines", line=dict(color="#185FA5", width=1.5),
    #             fill="tozeroy", fillcolor="rgba(24,95,165,0.05)",
    #             hovertemplate="<b>%{x|%d %b %Y}</b>: %{y:.2f} MDL<extra></extra>",
    #         ))
    #         fig.update_layout(
    #             height=260,
    #             font=dict(family="IBM Plex Sans", size=10, color="#444441"),
    #             paper_bgcolor="white", plot_bgcolor="white",
    #             margin=dict(l=10,r=10,t=10,b=10),
    #             xaxis=dict(showgrid=False, linecolor="#e8e4dc"),
    #             yaxis=dict(gridcolor="#f1efe8", linecolor="#e8e4dc", zeroline=False),
    #         )
    #         st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    #         st.markdown(f'<div class="chart-source">Sursa: BNM — cursuri oficiale de referinta. {len(df_curs)} observatii.</div></div>', unsafe_allow_html=True)

    #         with st.expander("Vizualizeaza date brute"):
    #             df_show = df_curs.copy()
    #             df_show["data"] = df_show["data"].dt.strftime("%d.%m.%Y")
    #             st.dataframe(df_show, use_container_width=True, hide_index=True)
    #     else:
    #         st.info("Apasa 'Incarca date curs valutar' pentru a extrage date live din BNM.")

    #     # Rata BNM
    #     st.markdown('<div class="chart-card"><div class="chart-card-title">Istoricul ratei de baza BNM</div>', unsafe_allow_html=True)
    #     if st.button("Incarca istoricul ratei BNM"):
    #         with st.spinner("Extragere din BNM..."):
    #             df_rata = get_rata_bnm()
    #             st.session_state["rata_bnm_df"] = df_rata

    #     df_rata = st.session_state.get("rata_bnm_df")
    #     if df_rata is not None:
    #         import plotly.graph_objects as go
    #         fig2 = go.Figure(go.Scatter(
    #             x=df_rata["date"], y=df_rata["rate"],
    #             mode="lines+markers",
    #             line=dict(color="#993556", width=2, shape="hv"),
    #             marker=dict(size=6, color="#993556"),
    #             hovertemplate="<b>%{x|%d %b %Y}</b>: %{y:.2f}%<extra></extra>",
    #         ))
    #         fig2.update_layout(
    #             height=220,
    #             font=dict(family="IBM Plex Sans", size=10, color="#444441"),
    #             paper_bgcolor="white", plot_bgcolor="white",
    #             margin=dict(l=10,r=10,t=10,b=10),
    #             xaxis=dict(showgrid=False, linecolor="#e8e4dc"),
    #             yaxis=dict(gridcolor="#f1efe8", title="% p.a.", zeroline=False),
    #         )
    #         st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    #         st.markdown('<div class="chart-source">Sursa: BNM — decizii Consiliu de Administratie</div>', unsafe_allow_html=True)
    #     else:
    #         st.info("Apasa butonul pentru a incarca istoricul ratei BNM.")
    #     st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab 3: Upload fisiere ──────────────────────────────────────────────────
    with tab3:
        col_up, col_tmpl = st.columns([2, 1])

        with col_tmpl:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Export date BNS</div>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:12px;color:#5F5E5A">Descarca datele afisate in dashboard (sursa BNS/BNM) intr-un Excel formatat cu sheet-uri per sector.</p>', unsafe_allow_html=True)
            if st.button("Genereaza Excel BNS", use_container_width=True, key="btn_gen_bns"):
                with st.spinner("Se compileaza datele BNS..."):
                    bns_bytes = generate_bns_export()
                    st.session_state["bns_export_bytes"] = bns_bytes

            if "bns_export_bytes" in st.session_state:
                st.download_button(
                    "Descarca Excel",
                    data=st.session_state["bns_export_bytes"],
                    file_name="MEDD_Date_BNS.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_dl_bns",
                )
            st.markdown("""
            <div style="font-size:11px;color:#888780;margin-top:8px;line-height:1.6">
            Sheet-uri incluse:<br>
            · PIB — Sector Real<br>
            · Export si Import (lunar)<br>
            · Industrie<br>
            · Salarii si Piata Muncii<br>
            · Venituri Bugetare<br>
            · Cheltuieli Bugetare<br>
            · Monetar (BNM)
            </div>
            </div>
            """, unsafe_allow_html=True)

        with col_up:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Incarca fisier date</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "Trage fisierul sau click pentru selectare",
                type=["xlsx", "xls", "csv"],
                label_visibility="collapsed",
                key="page_upload_widget"
            )

            if uploaded:
                with st.spinner(f"Parsez {uploaded.name}..."):
                    sheets = parse_uploaded_file(uploaded)

                if sheets:
                    st.success(f"Fisier procesat: **{uploaded.name}** — {len(sheets)} sheet(uri)")

                    for sheet_name, df in sheets.items():
                        st.markdown(f"**Sheet: {sheet_name}** — {df.shape[0]} randuri × {df.shape[1]} coloane")

                        mapping = auto_map_columns(df)
                        if mapping:
                            mapped_items = ", ".join([f"`{c}` → {t}" for c, t in mapping.items()])
                            st.markdown(f'<div style="font-size:11px;color:#0c141c;margin-bottom:6px">Indicatori detectati: {mapped_items}</div>', unsafe_allow_html=True)

                        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                        st.session_state[f"upload_{sheet_name}"] = df

                    # st.info("Datele incarcate sunt disponibile in sectoarele corespunzatoare din meniul lateral.")
            else:
                st.markdown("""
                <div style="border:1px dashed #b4b2a9;border-radius:6px;padding:32px;
                            text-align:center;color:#888780;font-size:12px;">
                    <div style="font-size:28px;margin-bottom:8px;color:#D3D1C7">+</div>
                    Trage fisierul Excel/CSV sau click pentru selectare<br>
                    <span style="font-size:10px">Max 200MB · .xlsx, .xls, .csv</span>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab 4: IMF & World Bank ────────────────────────────────────────────────
    with tab4:
        import plotly.graph_objects as go

        _COLORS_REG = {"Moldova":"#185FA5","Romania":"#E6553A","Ucraina":"#993556",
                       "Bulgaria":"#0F6E56","Serbia":"#8B6914","Armenia":"#666","Georgia":"#AAA"}

        def _line_layout(h=280):
            return dict(height=h, paper_bgcolor="white", plot_bgcolor="white",
                        font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                        margin=dict(l=10, r=10, t=32, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="left", x=0),
                        xaxis=dict(showgrid=False, linecolor="#e8e4dc", tickformat="d"),
                        yaxis=dict(gridcolor="#f1efe8", zeroline=True, zerolinecolor="#ccc"))

        btn_col, dl_col = st.columns([2, 1])
        with btn_col:
            if st.button("Incarca date IMF & World Bank", use_container_width=True, key="btn_load_imfwb"):
                with st.spinner("Se extrag date din IMF DataMapper si World Bank API..."):
                    st.session_state["imf_weo"]     = imf_weo_multi(
                        ["NGDP_RPCH", "NGDPD", "PCPIPCH", "TX_RPCH", "TM_RPCH",
                         "BCA_NGDPD", "GGXWDG_NGDP", "LUR"],
                        ani_start=2015
                    )
                    st.session_state["wb_ext"]      = wb_multi({
                        "PIB nominal (mld. USD)":  "NY.GDP.MKTP.CD",
                        "PIB/locuitor (USD)":       "NY.GDP.PCAP.CD",
                        "Export (% PIB)":           "NE.EXP.GNFS.ZS",
                        "Import (% PIB)":           "NE.IMP.GNFS.ZS",
                        "Remitente (% PIB)":        "BX.TRF.PWKR.DT.GD.ZS",
                        "Saracie (%)":              "SI.POV.NAHC",
                        "Somaj (%)":                "SL.UEM.TOTL.ZS",
                        "Populatie":                "SP.POP.TOTL",
                        "Datorie publica (% PIB)":  "GC.DOD.TOTL.GD.ZS",
                    }, ani_start=2010)
                    st.session_state["imf_reg_pib"] = imf_regional_compare("NGDP_RPCH")
                    st.session_state["imf_reg_inf"] = imf_regional_compare("PCPIPCH")
        with dl_col:
            if st.button("Genereaza Excel IMF/WB", use_container_width=True, key="btn_gen_imfwb"):
                with st.spinner("Se genereaza Excel..."):
                    st.session_state["imfwb_bytes"] = generate_data_export()
            if "imfwb_bytes" in st.session_state:
                st.download_button(
                    "Descarca Excel IMF/WB",
                    data=st.session_state["imfwb_bytes"],
                    file_name="MEDD_Date_IMF_WorldBank.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_dl_imfwb",
                )

        df_weo   = st.session_state.get("imf_weo")
        df_wb    = st.session_state.get("wb_ext")
        df_reg   = st.session_state.get("imf_reg_pib")
        df_reg_i = st.session_state.get("imf_reg_inf")

        if df_weo is None:
            st.info("Apasa 'Incarca date IMF & World Bank' pentru a vizualiza indicatorii.")
        else:
            # ── IMF WEO: PIB, Export, Import ──────────────────────────────────
            st.markdown('<div class="chart-card"><div class="chart-card-title">IMF WEO — PIB, Export, Import, Inflatie, Moldova</div>', unsafe_allow_html=True)
            if "eroare" not in df_weo.columns and not df_weo.empty:
                col_i1, col_i2 = st.columns([3, 2])
                with col_i1:
                    fig_weo = go.Figure()
                    if "NGDP_RPCH" in df_weo.columns:
                        colors_bar = ["#185FA5" if v >= 0 else "#A32D2D"
                                      for v in df_weo["NGDP_RPCH"].fillna(0)]
                        fig_weo.add_trace(go.Bar(
                            x=df_weo["an"], y=df_weo["NGDP_RPCH"],
                            name="PIB real (%)", marker_color=colors_bar,
                            hovertemplate="<b>%{x}</b> PIB real: %{y:.1f}%<extra></extra>",
                            yaxis="y1",
                        ))
                    for ind, label, color in [
                        ("TX_RPCH", "Export vol. (%)", "#0F6E56"),
                        ("TM_RPCH", "Import vol. (%)", "#E6553A"),
                    ]:
                        if ind in df_weo.columns:
                            fig_weo.add_trace(go.Scatter(
                                x=df_weo["an"], y=df_weo[ind],
                                mode="lines+markers", name=label,
                                line=dict(color=color, width=1.5),
                                marker=dict(size=4),
                                hovertemplate=f"<b>%{{x}}</b> {label}: %{{y:.1f}}%<extra></extra>",
                                yaxis="y1",
                            ))
                    if "NGDPD" in df_weo.columns:
                        fig_weo.add_trace(go.Scatter(
                            x=df_weo["an"], y=df_weo["NGDPD"],
                            name="PIB nominal (mld. USD)", mode="lines+markers",
                            line=dict(color="#888", width=1.2, dash="dot"),
                            marker=dict(size=3),
                            hovertemplate="<b>%{x}</b> PIB nominal: %{y:.1f} mld. USD<extra></extra>",
                            yaxis="y2",
                        ))
                    layout_weo = _line_layout(270)
                    layout_weo["title"] = dict(text="Crestere PIB / Export / Import (%)", font=dict(size=11))
                    layout_weo["yaxis2"] = dict(
                        overlaying="y", side="right",
                        showgrid=False, zeroline=False,
                        title=dict(text="mld. USD", font=dict(size=9)),
                        tickfont=dict(size=9),
                    )
                    fig_weo.update_layout(**layout_weo)
                    st.plotly_chart(fig_weo, use_container_width=True, config={"displayModeBar": False})

                with col_i2:
                    rename_weo = {
                        "an":          "An",
                        "NGDP_RPCH":   "PIB real (%)",
                        "NGDPD":       "PIB (mld.USD)",
                        "PCPIPCH":     "Inflatie (%)",
                        "TX_RPCH":     "Export vol.(%)",
                        "TM_RPCH":     "Import vol.(%)",
                        "BCA_NGDPD":   "Cont cur. (% PIB)",
                        "GGXWDG_NGDP": "Datorie (% PIB)",
                        "LUR":         "Somaj (%)",
                    }
                    df_show = df_weo.rename(columns=rename_weo)
                    show_cols = [c for c in rename_weo.values() if c in df_show.columns]
                    st.dataframe(df_show[show_cols].tail(12).reset_index(drop=True),
                                 use_container_width=True, hide_index=True)

            st.markdown('<div class="chart-source">Sursa: IMF DataMapper API — WEO. Include prognoze IMF.</div></div>', unsafe_allow_html=True)

            # ── World Bank: PIB, Export, Import, Remitente ───────────────────
            if df_wb is not None and "eroare" not in df_wb.columns and not df_wb.empty:
                st.markdown('<div class="chart-card"><div class="chart-card-title">World Bank — PIB, Export, Import, Remitente · Moldova</div>', unsafe_allow_html=True)

                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    # PIB nominal + PIB/locuitor pe axe duale
                    fig_pib_wb = go.Figure()
                    if "PIB nominal (mld. USD)" in df_wb.columns:
                        df_wb_plot = df_wb.copy()
                        df_wb_plot["PIB nominal (mld. USD)"] = df_wb_plot["PIB nominal (mld. USD)"] / 1e9
                        fig_pib_wb.add_trace(go.Bar(
                            x=df_wb_plot["an"], y=df_wb_plot["PIB nominal (mld. USD)"],
                            name="PIB nominal (mld. USD)",
                            marker_color="#185FA5",
                            hovertemplate="<b>%{x}</b> PIB: %{y:.2f} mld. USD<extra></extra>",
                            yaxis="y1",
                        ))
                    if "PIB/locuitor (USD)" in df_wb.columns:
                        fig_pib_wb.add_trace(go.Scatter(
                            x=df_wb["an"], y=df_wb["PIB/locuitor (USD)"],
                            name="PIB/locuitor (USD)", mode="lines+markers",
                            line=dict(color="#E6553A", width=1.5),
                            marker=dict(size=4),
                            hovertemplate="<b>%{x}</b> PIB/loc: %{y:,.0f} USD<extra></extra>",
                            yaxis="y2",
                        ))
                    layout_pib_wb = _line_layout(260)
                    layout_pib_wb["title"] = dict(text="PIB nominal si PIB/locuitor", font=dict(size=11))
                    layout_pib_wb["yaxis2"] = dict(
                        overlaying="y", side="right",
                        showgrid=False, zeroline=False,
                        tickfont=dict(size=9),
                    )
                    fig_pib_wb.update_layout(**layout_pib_wb)
                    st.plotly_chart(fig_pib_wb, use_container_width=True, config={"displayModeBar": False})

                with col_w2:
                    fig_wb = go.Figure()
                    for col, color in [("Export (% PIB)", "#185FA5"), ("Import (% PIB)", "#E6553A"),
                                       ("Remitente (% PIB)", "#0F6E56")]:
                        if col in df_wb.columns:
                            fig_wb.add_trace(go.Scatter(
                                x=df_wb["an"], y=df_wb[col],
                                mode="lines+markers", name=col,
                                line=dict(color=color, width=1.8),
                                marker=dict(size=4),
                                hovertemplate=f"<b>%{{x}}</b> {col}: %{{y:.1f}}%<extra></extra>",
                            ))
                    fig_wb.update_layout(
                        title=dict(text="Export, Import, Remitente (% PIB)", font=dict(size=11)),
                        **_line_layout(260),
                    )
                    st.plotly_chart(fig_wb, use_container_width=True, config={"displayModeBar": False})

                with st.expander("Date brute — World Bank"):
                    df_wb_show = df_wb.rename(columns={"an": "An"})
                    st.dataframe(df_wb_show.reset_index(drop=True),
                                 use_container_width=True, hide_index=True)
                st.markdown('<div class="chart-source">Sursa: World Bank Open Data API v2.</div></div>', unsafe_allow_html=True)

            # ── Comparativ regional PIB ───────────────────────────────────────
            if df_reg is not None and not df_reg.empty:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Comparativ regional — Crestere PIB real (%)</div>', unsafe_allow_html=True)
                fig_reg = go.Figure()
                for col in df_reg.columns:
                    if col == "an":
                        continue
                    fig_reg.add_trace(go.Scatter(
                        x=df_reg["an"], y=df_reg[col], mode="lines+markers", name=col,
                        line=dict(color=_COLORS_REG.get(col, "#999"),
                                  width=2.5 if col == "Moldova" else 1.2),
                        marker=dict(size=5 if col == "Moldova" else 3),
                        hovertemplate=f"<b>{col}</b> %{{x}}: %{{y:.1f}}%<extra></extra>",
                    ))
                fig_reg.update_layout(**_line_layout(300))
                st.plotly_chart(fig_reg, use_container_width=True, config={"displayModeBar": False})
                with st.expander("Date brute — PIB comparativ"):
                    st.dataframe(df_reg.rename(columns={"an": "An"}),
                                 use_container_width=True, hide_index=True)
                st.markdown('<div class="chart-source">Sursa: IMF DataMapper — NGDP_RPCH. Moldova, Romania, Ucraina, Bulgaria, Serbia, Armenia, Georgia.</div></div>', unsafe_allow_html=True)

            # ── Comparativ regional inflatie ──────────────────────────────────
            if df_reg_i is not None and not df_reg_i.empty:
                st.markdown('<div class="chart-card"><div class="chart-card-title">Comparativ regional — Inflatie IPC (%)</div>', unsafe_allow_html=True)
                fig_inf = go.Figure()
                for col in df_reg_i.columns:
                    if col == "an":
                        continue
                    fig_inf.add_trace(go.Scatter(
                        x=df_reg_i["an"], y=df_reg_i[col], mode="lines+markers", name=col,
                        line=dict(color=_COLORS_REG.get(col, "#999"),
                                  width=2.5 if col == "Moldova" else 1.2),
                        marker=dict(size=5 if col == "Moldova" else 3),
                        hovertemplate=f"<b>{col}</b> %{{x}}: %{{y:.1f}}%<extra></extra>",
                    ))
                layout_inf = _line_layout(300)
                layout_inf["yaxis"]["zeroline"] = False
                fig_inf.update_layout(**layout_inf)
                st.plotly_chart(fig_inf, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="chart-source">Sursa: IMF DataMapper — PCPIPCH.</div></div>', unsafe_allow_html=True)
