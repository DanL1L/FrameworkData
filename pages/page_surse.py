import streamlit as st
import pandas as pd
from utils.state import page_header
from utils.api_bns import test_bns, bns_list, BNS_TABLES
from utils.api_bnm import test_bnm, get_rata_bnm, get_rezerve, get_curs_oficial
from utils.api_imf import test_imf, test_wb, get_imf_prognoze
from utils.api_upload import parse_uploaded_file, auto_map_columns, generate_template
from utils.charts import line_chart


def render():
    page_header(
        "Surse de date & API",
        "Conexiuni API, upload fisiere, status date",
        "BNS · BNM · IMF · World Bank",
        "gray"
    )

    tab1, tab2, tab3 = st.tabs(["Status API", "Date live BNM", "Upload fisiere"])

    # ── Tab 1: Status API ──────────────────────────────────────────────────────
    with tab1:
        st.markdown('<div class="chart-card"><div class="chart-card-title">Conexiuni API active</div>', unsafe_allow_html=True)

        col_test1, col_test2, col_test3, col_test4 = st.columns(4)
        with col_test1:
            if st.button("Testeaza BNS", use_container_width=True):
                with st.spinner("..."):
                    res = test_bns()
                    st.session_state["bns_status"] = res
        with col_test2:
            if st.button("Testeaza BNM", use_container_width=True):
                with st.spinner("..."):
                    res = test_bnm()
                    st.session_state["bnm_status"] = res
        with col_test3:
            if st.button("Testeaza IMF", use_container_width=True):
                with st.spinner("..."):
                    res = test_imf()
                    st.session_state["imf_status"] = res
        with col_test4:
            if st.button("Testeaza World Bank", use_container_width=True):
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
                "docs":     "https://www.imf.org/external/datamapper/api/v1",
            },
            {
                "name":     "World Bank Open Data",
                "endpoint": "WB API v2",
                "desc":     "Indicatori sociali: saracie, sanatate, educatie, remitente",
                "key":      "wb_status",
                "docs":     "https://api.worldbank.org/v2",
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

    # ── Tab 2: Date live BNM ───────────────────────────────────────────────────
    with tab2:
        col_a, col_b = st.columns(2)

        with col_a:
            valuta = st.selectbox("Valuta", ["EUR", "USD", "RON", "GBP", "UAH"], index=0)
            zile   = st.selectbox("Perioada", [30, 90, 180, 365], index=1,
                                  format_func=lambda x: f"Ultimele {x} zile")

        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Incarca date curs valutar", use_container_width=True):
                with st.spinner(f"Se extrage cursul {valuta}/MDL din BNM..."):
                    df_curs = get_curs_oficial(valuta, zile)
                    st.session_state["curs_df"] = df_curs
                    st.session_state["curs_valuta"] = valuta

        df_curs = st.session_state.get("curs_df")
        valuta_sel = st.session_state.get("curs_valuta", valuta)

        if df_curs is not None and not df_curs.empty:
            st.markdown(f'<div class="chart-card"><div class="chart-card-title">Curs {valuta_sel}/MDL — BNM oficial</div>', unsafe_allow_html=True)
            import plotly.graph_objects as go
            fig = go.Figure(go.Scatter(
                x=df_curs["data"], y=df_curs.iloc[:, 1],
                mode="lines", line=dict(color="#185FA5", width=1.5),
                fill="tozeroy", fillcolor="rgba(24,95,165,0.05)",
                hovertemplate="<b>%{x|%d %b %Y}</b>: %{y:.4f} MDL<extra></extra>",
            ))
            fig.update_layout(
                height=260,
                font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=False, linecolor="#e8e4dc"),
                yaxis=dict(gridcolor="#f1efe8", linecolor="#e8e4dc", zeroline=False),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown(f'<div class="chart-source">Sursa: BNM — cursuri oficiale de referinta. {len(df_curs)} observatii.</div></div>', unsafe_allow_html=True)

            with st.expander("Vizualizeaza date brute"):
                df_show = df_curs.copy()
                df_show["data"] = df_show["data"].dt.strftime("%d.%m.%Y")
                st.dataframe(df_show, use_container_width=True, hide_index=True)
        else:
            st.info("Apasa 'Incarca date curs valutar' pentru a extrage date live din BNM.")

        # Rata BNM
        st.markdown('<div class="chart-card"><div class="chart-card-title">Istoricul ratei de baza BNM</div>', unsafe_allow_html=True)
        if st.button("Incarca istoricul ratei BNM"):
            with st.spinner("Extragere din BNM..."):
                df_rata = get_rata_bnm()
                st.session_state["rata_bnm_df"] = df_rata

        df_rata = st.session_state.get("rata_bnm_df")
        if df_rata is not None:
            import plotly.graph_objects as go
            fig2 = go.Figure(go.Scatter(
                x=df_rata["date"], y=df_rata["rate"],
                mode="lines+markers",
                line=dict(color="#993556", width=2, shape="hv"),
                marker=dict(size=6, color="#993556"),
                hovertemplate="<b>%{x|%d %b %Y}</b>: %{y:.2f}%<extra></extra>",
            ))
            fig2.update_layout(
                height=220,
                font=dict(family="IBM Plex Sans", size=10, color="#444441"),
                paper_bgcolor="white", plot_bgcolor="white",
                margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(showgrid=False, linecolor="#e8e4dc"),
                yaxis=dict(gridcolor="#f1efe8", title="% p.a.", zeroline=False),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="chart-source">Sursa: BNM — decizii Consiliu de Administratie</div>', unsafe_allow_html=True)
        else:
            st.info("Apasa butonul pentru a incarca istoricul ratei BNM.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Tab 3: Upload fisiere ──────────────────────────────────────────────────
    with tab3:
        col_up, col_tmpl = st.columns([2, 1])

        with col_tmpl:
            st.markdown('<div class="chart-card"><div class="chart-card-title">Template import</div>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:12px;color:#5F5E5A">Descarca template-ul Excel standardizat cu toate cele 6 sectoare pre-formatate.</p>', unsafe_allow_html=True)
            tmpl_bytes = generate_template()
            st.download_button(
                "Descarca template Excel",
                data=tmpl_bytes,
                file_name="MEDD_Template_Import.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.markdown("""
            <div style="font-size:11px;color:#888780;margin-top:8px;line-height:1.6">
            Formate acceptate:<br>
            · Excel (.xlsx, .xls)<br>
            · CSV cu separator , sau ;<br>
            · Encoding UTF-8 sau ANSI<br>
            · Virgula sau punct decimal
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
                            st.markdown(f'<div style="font-size:11px;color:#185FA5;margin-bottom:6px">Indicatori detectati: {mapped_items}</div>', unsafe_allow_html=True)

                        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
                        st.session_state[f"upload_{sheet_name}"] = df

                    st.info("Datele incarcate sunt disponibile in sectoarele corespunzatoare din meniul lateral.")
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
