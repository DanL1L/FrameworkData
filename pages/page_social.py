"""
sector_social.py  ·  Macroscope Moldova
──────────────────────────────────────────────────────────────────────────────
Pagina redesenată a Sectorului Social: Piața Muncii, Șomaj, Salarii
Date live din BNS API (PxWeb) cu fallback Excel și date demonstrative.
──────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime


# ── Import cu fallback elegant ────────────────────────────────────────────────
try:
    from data.social_loader import load_social_data
    HAS_LOADER = True
except ImportError:
    HAS_LOADER = False

try:
    from utils.state import page_header, kpi_card, kpi_row
    HAS_UTILS = True
except ImportError:
    HAS_UTILS = False


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS & HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

BRAND = {
    "primary":    "#0C6E52",   # teal Moldova
    "primary_lt": "#E8F5F1",
    "accent":     "#F5A623",   # portocaliu accent
    "blue":       "#1A6FA8",
    "red":        "#D94040",
    "text":       "#1C1C1E",
    "subtext":    "#6B7280",
    "border":     "#E5E7EB",
    "bg":         "#F9FAFB",
    "card_bg":    "#FFFFFF",
    "success":    "#10B981",
    "warning":    "#F59E0B",
}

FONT = "IBM Plex Sans, 'Segoe UI', system-ui, sans-serif"


def _plotly_base_layout(height: int = 300, show_legend: bool = False) -> dict:
    """Layout de bază Plotly consistent în toată pagina."""
    return dict(
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=FONT, size=11, color=BRAND["text"]),
        margin=dict(l=12, r=12, t=8, b=8),
        showlegend=show_legend,
        legend=dict(
            orientation="h", y=-0.15, x=0.5, xanchor="center",
            font=dict(size=10)
        ),
        xaxis=dict(
            showgrid=False,
            linecolor=BRAND["border"],
            linewidth=1,
            tickfont=dict(size=9, color=BRAND["subtext"]),
            tickangle=-40,
        ),
        yaxis=dict(
            gridcolor="#F3F4F6",
            gridwidth=1,
            tickfont=dict(size=10, color=BRAND["subtext"]),
            zeroline=False,
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor=BRAND["border"],
            font_family=FONT,
            font_size=12,
        )
    )


def _status_badge(tip_sursa: str, api_ok: bool, ultima_actualizare: str) -> str:
    """Generează badge-ul de stare al sursei de date."""
    if api_ok:
        color = BRAND["success"]
        icon = "🟢"
        label = "Live BNS API"
    elif tip_sursa == "excel":
        color = BRAND["warning"]
        icon = "🟡"
        label = "Fișier Excel local"
    else:
        color = BRAND["subtext"]
        icon = "⚪"
        label = "Date demonstrative"
    
    return f"""
    <div style="display:flex; align-items:center; gap:10px; 
                padding:8px 14px; background:{BRAND['bg']}; 
                border:1px solid {BRAND['border']}; border-radius:8px;
                font-family:{FONT}; font-size:12px; color:{BRAND['subtext']};
                margin-bottom:16px;">
        <span style="font-size:14px;">{icon}</span>
        <span>
            <strong style="color:{color};">{label}</strong>
            &nbsp;·&nbsp; Ultima actualizare: <strong>{ultima_actualizare}</strong>
            &nbsp;·&nbsp; Sursă: Ancheta Forței de Muncă (AFM/BIM), BNS Moldova
        </span>
    </div>
    """


def _metric_card(
    label: str,
    value: str,
    unit: str,
    delta_text: str = "",
    is_positive: bool = True,
    note: str = "",
    color: str = None
) -> str:
    """Renders a KPI metric card as HTML."""
    col = color or BRAND["primary"]
    delta_color = BRAND["success"] if is_positive else BRAND["red"]
    delta_arrow = "▲" if is_positive else "▼"
    
    delta_html = ""
    if delta_text:
        delta_html = f"""
        <div style="font-size:11px; color:{delta_color}; font-weight:600; margin-top:2px;">
            {delta_arrow} {delta_text}
        </div>
        """
    
    note_html = f'<div style="font-size:10px; color:{BRAND["subtext"]}; margin-top:4px;">{note}</div>' if note else ""
    
    return f"""
    <div style="
        background:{BRAND['card_bg']}; 
        border:1px solid {BRAND['border']}; 
        border-top:3px solid {col};
        border-radius:10px; 
        padding:16px 18px; 
        box-shadow:0 1px 4px rgba(0,0,0,0.06);
        font-family:{FONT};
        height:100%;
    ">
        <div style="font-size:11px; color:{BRAND['subtext']}; font-weight:600; 
                    text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px;">
            {label}
        </div>
        <div style="display:flex; align-items:baseline; gap:5px;">
            <span style="font-size:26px; font-weight:700; color:{BRAND['text']};">{value}</span>
            <span style="font-size:13px; color:{BRAND['subtext']}; font-weight:500;">{unit}</span>
        </div>
        {delta_html}
        {note_html}
    </div>
    """


def _section_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Afișează un header de secțiune stilizat."""
    st.markdown(f"""
    <div style="margin: 20px 0 12px 0; font-family:{FONT};">
        <div style="font-size:16px; font-weight:700; color:{BRAND['text']};">
            {icon} {title}
        </div>
        {f'<div style="font-size:12px; color:{BRAND["subtext"]}; margin-top:2px;">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def _chart_container(title: str, source: str = "") -> None:
    """Deschide un container de grafic stilizat."""
    st.markdown(f"""
    <div style="font-family:{FONT}; margin-bottom:4px;">
        <span style="font-size:13px; font-weight:600; color:{BRAND['text']};">{title}</span>
        {f'<span style="font-size:11px; color:{BRAND["subtext"]}; float:right;">{source}</span>' if source else ''}
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCȚII DE CALCUL INDICATORI
# ═══════════════════════════════════════════════════════════════════════════════

def _calc_yoy(df: pd.DataFrame, col: str) -> pd.Series:
    """
    Calculează variația an/an față de același trimestru din anul anterior.
    Metodologie corectă: groupby trimestru → pct_change().
    """
    if col not in df.columns or "trimestru" not in df.columns:
        return pd.Series([np.nan] * len(df))
    
    result = df.copy()
    result = result.sort_values(["an", "trimestru"])
    result["_yoy"] = (
        result.groupby("trimestru")[col]
        .pct_change() * 100
    )
    return result["_yoy"]


def _get_last_and_prev(df: pd.DataFrame):
    """Returnează ultimul rând și rândul din același trimestru al anului anterior."""
    if df.empty:
        return None, None
    
    last = df.iloc[-1]
    
    if "trimestru" in df.columns:
        prev_mask = (
            (df["an"] == int(last["an"]) - 1) &
            (df["trimestru"] == last["trimestru"])
        )
        prev_df = df[prev_mask]
        prev = prev_df.iloc[-1] if not prev_df.empty else (df.iloc[-2] if len(df) >= 2 else last)
    else:
        prev = df.iloc[-2] if len(df) >= 2 else last
    
    return last, prev


# ═══════════════════════════════════════════════════════════════════════════════
# RENDERER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    """Funcția principală de randare a paginii Sector Social."""

    # ── CSS custom injectat ──────────────────────────────────────────────────
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background-color: {BRAND['bg']};
        padding: 4px;
        border-radius: 10px;
        border: 1px solid {BRAND['border']};
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 6px 16px;
        font-size: 13px;
        font-weight: 500;
        font-family: {FONT};
        color: {BRAND['subtext']};
        background: transparent;
        border: none;
    }}
    .stTabs [aria-selected="true"] {{
        background: white !important;
        color: {BRAND['primary']} !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .stDataFrame {{ border-radius: 8px; overflow: hidden; }}
    div[data-testid="metric-container"] {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)

    # ── Header pagină ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        padding: 20px 24px; 
        background: linear-gradient(135deg, {BRAND['primary']} 0%, #0A8A65 100%);
        border-radius: 12px; 
        margin-bottom: 20px;
        font-family: {FONT};
    ">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
            <div>
                <h2 style="color:white; margin:0; font-size:22px; font-weight:700; letter-spacing:-0.02em;">
                    👥 Sectorul Social · Piața Muncii
                </h2>
                <p style="color:rgba(255,255,255,0.8); margin:4px 0 0 0; font-size:13px;">
                    Șomaj · Ocupare · Salarii — date trimestriale, Ancheta Forței de Muncă (AFM/BIM)
                </p>
            </div>
            <div style="text-align:right;">
                <div style="color:rgba(255,255,255,0.7); font-size:11px;">Actualizat</div>
                <div style="color:white; font-weight:600; font-size:13px;">
                    {datetime.now().strftime('%d %b %Y')}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Încărcare date ────────────────────────────────────────────────────────
    if HAS_LOADER:
        result = load_social_data(prefer_api=True)
        df = result["data"]
        tip_sursa = result.get("tip_sursa", "demo")
        api_ok = result.get("api_ok", False)
        ultima_actualizare = result.get("ultima_actualizare", datetime.now().strftime("%d.%m.%Y %H:%M"))
        sursa_text = result.get("sursa", "BNS Moldova")
    else:
        # Dacă modulele nu sunt disponibile, generăm date demo inline
        from data.social_loader import _generate_demo_data
        df = _generate_demo_data()
        tip_sursa = "demo"
        api_ok = False
        ultima_actualizare = datetime.now().strftime("%d.%m.%Y %H:%M")
        sursa_text = "Date demonstrative"

    # Status badge sursa de date
    st.markdown(_status_badge(tip_sursa, api_ok, ultima_actualizare), unsafe_allow_html=True)

    if df is None or df.empty:
        st.error("⚠️ Nu s-au putut încărca datele. Verificați conexiunea la BNS API sau fișierul Excel.")
        return

    # Sortăm și pregătim datele
    if "trimestru" in df.columns:
        df = df.sort_values(["an", "trimestru"]).reset_index(drop=True)
    
    LABELS = (
        df["trim_label"].tolist() if "trim_label" in df.columns
        else df["an"].astype(str).tolist()
    )
    
    last, prev = _get_last_and_prev(df)
    trim_label_last = last.get("trim_label", str(int(last["an"]))) if last is not None else "N/A"

    # ── KPI Cards ────────────────────────────────────────────────────────────
    _section_header("Indicatori principali", f"Ultimul trimestru disponibil: {trim_label_last}", "📊")

    def safe_get(row, col):
        if row is None: return None
        val = row.get(col, None)
        return float(val) if val is not None and not (isinstance(val, float) and np.isnan(val)) else None

    somaj_val  = safe_get(last, "rata_somaj_pct")
    somaj_prev = safe_get(prev, "rata_somaj_pct")
    sal_val    = safe_get(last, "salariu_mediu_mdl")
    sal_prev   = safe_get(prev, "salariu_mediu_mdl")
    pop_val    = safe_get(last, "populatie_ocupata_mii")
    someri_val = safe_get(last, "nr_someri_mii")
    ocu_val    = safe_get(last, "rata_ocupare_pct")

    somaj_delta = round(somaj_val - somaj_prev, 1) if somaj_val and somaj_prev else None
    sal_delta   = ((sal_val - sal_prev) / sal_prev * 100) if sal_val and sal_prev else None

    cols_kpi = st.columns(4)
    kpis = [
        (
            "Rata Șomajului",
            f"{somaj_val:.1f}" if somaj_val else "N/A", "%",
            f"{somaj_delta:+.1f} pp vs an anterior" if somaj_delta is not None else "",
            somaj_delta is not None and somaj_delta <= 0,
            "Față de același trimestru an anterior",
            BRAND["primary"]
        ),
        (
            "Salariu Mediu",
            f"{sal_val:,.0f}" if sal_val else "N/A", "MDL",
            f"{sal_delta:+.1f}% vs an anterior" if sal_delta is not None else "",
            sal_delta is not None and sal_delta > 0,
            "Câștigul salarial mediu brut lunar",
            BRAND["blue"]
        ),
        (
            "Populație Ocupată",
            f"{pop_val:,.1f}" if pop_val else "N/A", "mii pers.",
            "",
            True,
            f"Trimestrul {trim_label_last}",
            "#7C3AED"
        ),
        (
            "Nr. Șomeri",
            f"{someri_val:.1f}" if someri_val else "N/A", "mii pers.",
            "",
            someri_val is not None and someri_val < 50,
            f"Trimestrul {trim_label_last}",
            BRAND["accent"]
        ),
    ]

    for col, (label, val, unit, delta, is_pos, note, color) in zip(cols_kpi, kpis):
        with col:
            st.markdown(_metric_card(label, val, unit, delta, is_pos, note, color), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── Tabs principale ───────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📉 Șomaj & Ocupare",
        "💰 Salarii",
        "📊 Analiză comparativă",
        "🗂️ Date tabelare"
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1: Șomaj & Ocupare
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        col1, col2 = st.columns([3, 2])

        with col1:
            _chart_container("Rata șomajului BIM — evoluție trimestrială (%)", sursa_text)
            if "rata_somaj_pct" in df.columns:
                vals = df["rata_somaj_pct"].tolist()
                media = df["rata_somaj_pct"].mean()

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=LABELS, y=vals,
                    mode="lines+markers",
                    name="Rata șomajului",
                    line=dict(color=BRAND["primary"], width=2.5),
                    marker=dict(size=5, color=BRAND["primary"],
                                line=dict(color="white", width=1.5)),
                    fill="tozeroy",
                    fillcolor=f"rgba(12,110,82,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>",
                ))
                fig.add_hline(
                    y=media, line_dash="dot",
                    line_color=BRAND["subtext"], line_width=1,
                    annotation_text=f"Medie: {media:.1f}%",
                    annotation_font_size=10,
                    annotation_font_color=BRAND["subtext"],
                )
                lay = _plotly_base_layout(310)
                lay["yaxis"]["title"] = dict(text="%", font=dict(size=11, color=BRAND["subtext"]))
                fig.update_layout(**lay)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col2:
            _chart_container("Distribuție an/sezon — rata șomajului", "AFM/BIM, BNS")
            if "rata_somaj_pct" in df.columns and "trimestru" in df.columns:
                # Heatmap trim vs an
                pivot = df.pivot_table(
                    index="trimestru", columns="an",
                    values="rata_somaj_pct", aggfunc="mean"
                )
                fig_heat = go.Figure(go.Heatmap(
                    z=pivot.values.tolist(),
                    x=[str(c) for c in pivot.columns],
                    y=[f"T{r}" for r in pivot.index],
                    colorscale=[[0, BRAND["primary_lt"]], [0.5, "#80C8B0"], [1, BRAND["primary"]]],
                    hoverongaps=False,
                    hovertemplate="An %{x}, %{y}: <b>%{z:.1f}%</b><extra></extra>",
                    showscale=True,
                    colorbar=dict(thickness=12, len=0.7, tickfont=dict(size=9)),
                ))
                fig_heat.update_layout(
                    height=310, margin=dict(l=40, r=10, t=8, b=8),
                    paper_bgcolor="white", plot_bgcolor="white",
                    font=dict(family=FONT, size=10),
                    xaxis=dict(tickfont=dict(size=9)),
                    yaxis=dict(tickfont=dict(size=10)),
                )
                st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

        # Grafice secundare full-width
        col3, col4 = st.columns(2)

        with col3:
            _chart_container("Populația ocupată trimestrial (mii persoane)", sursa_text)
            if "populatie_ocupata_mii" in df.columns:
                vals2 = df["populatie_ocupata_mii"].fillna(0).tolist()
                fig2 = go.Figure(go.Bar(
                    x=LABELS, y=vals2,
                    marker_color=BRAND["primary"],
                    opacity=0.80,
                    hovertemplate="<b>%{x}</b>: %{y:,.1f} mii pers.<extra></extra>",
                ))
                # Adăugăm linia de trend
                if len(vals2) > 3:
                    z = np.polyfit(range(len(vals2)), vals2, 1)
                    p = np.poly1d(z)
                    fig2.add_trace(go.Scatter(
                        x=LABELS, y=[p(i) for i in range(len(vals2))],
                        mode="lines", name="Trend",
                        line=dict(color=BRAND["accent"], width=1.5, dash="dot"),
                        hoverinfo="skip",
                    ))
                lay2 = _plotly_base_layout(280, show_legend=True)
                lay2["yaxis"]["title"] = dict(text="mii pers.", font=dict(size=11))
                lay2["xaxis"]["tickangle"] = -40
                fig2.update_layout(**lay2)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        with col4:
            _chart_container("Numărul șomerilor BIM trimestrial (mii persoane)", sursa_text)
            if "nr_someri_mii" in df.columns:
                vals3 = df["nr_someri_mii"].fillna(0).tolist()
                media3 = np.nanmean(vals3)
                colors3 = [BRAND["red"] if v > media3 else BRAND["primary"] for v in vals3]
                fig3 = go.Figure(go.Bar(
                    x=LABELS, y=vals3,
                    marker_color=colors3,
                    opacity=0.80,
                    hovertemplate="<b>%{x}</b>: %{y:.1f} mii șomeri<extra></extra>",
                ))
                fig3.add_hline(
                    y=media3, line_dash="dot",
                    line_color=BRAND["subtext"], line_width=1,
                    annotation_text=f"Medie: {media3:.1f} mii",
                    annotation_font_size=10,
                )
                lay3 = _plotly_base_layout(280)
                lay3["yaxis"]["title"] = dict(text="mii pers.", font=dict(size=11))
                fig3.update_layout(**lay3)
                st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

        # Notă metodologică
        st.markdown(f"""
        <div style="background:{BRAND['bg']}; border-left:3px solid {BRAND['primary']}; 
                    padding:10px 14px; border-radius:0 6px 6px 0; margin-top:8px;
                    font-family:{FONT}; font-size:11px; color:{BRAND['subtext']};">
            <strong>📎 Notă metodologică:</strong> Datele privind șomajul sunt conform definiției BIM (Biroul 
            Internațional al Muncii), colectate prin Ancheta Forței de Muncă (AFM) realizată de BNS Moldova. 
            Datele sunt trimestriale și acoperă populația cu reședința obișnuită în RM.
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2: Salarii
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            _chart_container("Câștigul salarial mediu trimestrial (MDL)", sursa_text)
            if "salariu_mediu_mdl" in df.columns and df["salariu_mediu_mdl"].notna().any():
                sal_vals = df["salariu_mediu_mdl"].tolist()
                fig4 = go.Figure(go.Scatter(
                    x=LABELS, y=sal_vals,
                    mode="lines+markers",
                    line=dict(color=BRAND["blue"], width=2.5),
                    marker=dict(size=5, color=BRAND["blue"],
                                line=dict(color="white", width=1.5)),
                    fill="tozeroy",
                    fillcolor="rgba(26,111,168,0.08)",
                    hovertemplate="<b>%{x}</b>: %{y:,.0f} MDL<extra></extra>",
                ))
                lay4 = _plotly_base_layout(310)
                lay4["yaxis"]["title"] = dict(text="MDL", font=dict(size=11))
                lay4["yaxis"]["tickformat"] = ",.0f"
                fig4.update_layout(**lay4)
                st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("ℹ️ Datele salariale nu sunt disponibile. Verificați sursa de date.")

        with col2:
            _chart_container("Variație salariu an/an, același trimestru (%)", "Calcul propriu pe baza BNS")
            if "salariu_mediu_mdl" in df.columns and df["salariu_mediu_mdl"].notna().any():
                df["sal_yoy"] = _calc_yoy(df, "salariu_mediu_mdl")
                yoy_vals = df["sal_yoy"].tolist()
                colors5 = [BRAND["success"] if (v >= 0 if not np.isnan(v) else True) else BRAND["red"]
                           for v in yoy_vals]
                fig5 = go.Figure(go.Bar(
                    x=LABELS, y=yoy_vals,
                    marker_color=colors5,
                    opacity=0.85,
                    hovertemplate="<b>%{x}</b>: %{y:+.1f}%<extra></extra>",
                ))
                fig5.add_hline(y=0, line_color=BRAND["border"], line_width=1.5)
                lay5 = _plotly_base_layout(310)
                lay5["yaxis"]["title"] = dict(text="%", font=dict(size=11))
                fig5.update_layout(**lay5)
                st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})

        # Salariu real (ajustat cu inflația dacă e disponibil)
        st.markdown(f"""
        <div style="background:#EFF6FF; border-left:3px solid {BRAND['blue']}; 
                    padding:10px 14px; border-radius:0 6px 6px 0; margin-top:8px;
                    font-family:{FONT}; font-size:11px; color:{BRAND['subtext']};">
            <strong>💡 Sugestie:</strong> Conectați modulul de inflație (IPC) pentru a calcula 
            <em>câștigul salarial real</em> (deflat cu IPC). Aceasta permite o analiză mai precisă 
            a evoluției puterii de cumpărare.
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3: Analiză comparativă
    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        _section_header("Analiză comparativă multi-indicator", "Selectați indicatorii pentru comparație")

        available_indicators = {
            "rata_somaj_pct": "Rata șomajului (%)",
            "salariu_mediu_mdl": "Salariu mediu (MDL)",
            "populatie_ocupata_mii": "Populație ocupată (mii pers.)",
            "nr_someri_mii": "Număr șomeri (mii pers.)",
            "rata_ocupare_pct": "Rata de ocupare (%)",
        }
        avail_cols = {k: v for k, v in available_indicators.items() if k in df.columns and df[k].notna().any()}

        if len(avail_cols) >= 2:
            col_sel1, col_sel2, col_options = st.columns([2, 2, 2])

            with col_sel1:
                ind1 = st.selectbox(
                    "Indicator principal (axa stângă)",
                    options=list(avail_cols.keys()),
                    format_func=lambda x: avail_cols[x],
                    index=0,
                    key="comp_ind1"
                )
            with col_sel2:
                remaining = [k for k in avail_cols.keys() if k != ind1]
                ind2 = st.selectbox(
                    "Indicator secundar (axa dreaptă)",
                    options=remaining,
                    format_func=lambda x: avail_cols[x],
                    index=0,
                    key="comp_ind2"
                )
            with col_options:
                chart_type = st.radio(
                    "Tip grafic",
                    ["Linie + Linie", "Bare + Linie"],
                    horizontal=True,
                    key="comp_type"
                )

            fig_comp = go.Figure()

            # Trace 1 (axa stângă)
            trace1_vals = df[ind1].tolist()
            if "Bare" in chart_type:
                fig_comp.add_trace(go.Bar(
                    x=LABELS, y=trace1_vals,
                    name=avail_cols[ind1],
                    marker_color=BRAND["primary"],
                    opacity=0.75,
                    hovertemplate=f"<b>%{{x}}</b>: %{{y:.2f}}<extra>{avail_cols[ind1]}</extra>",
                    yaxis="y1",
                ))
            else:
                fig_comp.add_trace(go.Scatter(
                    x=LABELS, y=trace1_vals,
                    name=avail_cols[ind1],
                    mode="lines+markers",
                    line=dict(color=BRAND["primary"], width=2.5),
                    marker=dict(size=5),
                    hovertemplate=f"<b>%{{x}}</b>: %{{y:.2f}}<extra>{avail_cols[ind1]}</extra>",
                    yaxis="y1",
                ))

            # Trace 2 (axa dreaptă)
            trace2_vals = df[ind2].tolist()
            fig_comp.add_trace(go.Scatter(
                x=LABELS, y=trace2_vals,
                name=avail_cols[ind2],
                mode="lines+markers",
                line=dict(color=BRAND["accent"], width=2.5, dash="dot"),
                marker=dict(size=5, color=BRAND["accent"]),
                hovertemplate=f"<b>%{{x}}</b>: %{{y:.2f}}<extra>{avail_cols[ind2]}</extra>",
                yaxis="y2",
            ))

            lay_comp = _plotly_base_layout(380, show_legend=True)
            lay_comp.update({
                "yaxis": dict(
                    title=avail_cols[ind1],
                    gridcolor="#F3F4F6",
                    tickfont=dict(size=10, color=BRAND["primary"]),
                    titlefont=dict(color=BRAND["primary"], size=11),
                ),
                "yaxis2": dict(
                    title=avail_cols[ind2],
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickfont=dict(size=10, color=BRAND["accent"]),
                    titlefont=dict(color=BRAND["accent"], size=11),
                ),
                "legend": dict(
                    orientation="h", y=1.08, x=0.5, xanchor="center",
                    font=dict(size=11)
                ),
                "margin": dict(l=60, r=60, t=30, b=8),
            })
            fig_comp.update_layout(**lay_comp)
            st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})

            # Statistici descriptive
            st.markdown("<br>", unsafe_allow_html=True)
            _section_header("Statistici descriptive", "")
            cols_stats = st.columns(2)
            for col_stat, ind_key in zip(cols_stats, [ind1, ind2]):
                with col_stat:
                    series = df[ind_key].dropna()
                    if not series.empty:
                        stats_data = {
                            "Indicator": avail_cols[ind_key],
                            "Observații": len(series),
                            "Medie": f"{series.mean():.2f}",
                            "Std. Dev.": f"{series.std():.2f}",
                            "Minim": f"{series.min():.2f}",
                            "Maxim": f"{series.max():.2f}",
                            "Ultimul": f"{series.iloc[-1]:.2f}",
                        }
                        st.dataframe(
                            pd.DataFrame.from_dict(stats_data, orient="index", columns=["Valoare"]),
                            use_container_width=True,
                            height=280,
                        )
        else:
            st.info("ℹ️ Sunt necesari cel puțin doi indicatori pentru analiza comparativă.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4: Date tabelare
    # ════════════════════════════════════════════════════════════════════════
    with tab4:
        _section_header("Tabel de date — serie trimestrială completă", sursa_text)

        col_rename = {
            "an": "An",
            "trimestru": "Trim.",
            "trim_label": "Perioadă",
            "populatie_ocupata_mii": "Pop. ocupată (mii)",
            "nr_someri_mii": "Șomeri (mii)",
            "rata_somaj_pct": "Rata șomaj (%)",
            "rata_ocupare_pct": "Rata ocupare (%)",
            "salariu_mediu_mdl": "Salariu mediu (MDL)",
        }
        show_cols = [c for c in col_rename if c in df.columns]
        show_df = df[show_cols].rename(columns=col_rename).copy()

        # Formatăm coloanele numerice
        for col in show_df.columns:
            if "MDL" in col:
                show_df[col] = show_df[col].apply(
                    lambda x: f"{x:,.0f}" if pd.notna(x) and x != "" else "—"
                )
            elif any(k in col for k in ["%", "mii", "Trim.", "An"]):
                try:
                    show_df[col] = show_df[col].apply(
                        lambda x: f"{float(x):.1f}" if pd.notna(x) and str(x) not in ["", "—"] else "—"
                    )
                except (ValueError, TypeError):
                    pass

        # Stil tabel: highlight ultimul rând
        def highlight_last(s):
            return ['background-color: #E8F5F1; font-weight: 600' 
                    if i == len(s) - 1 else '' for i in range(len(s))]

        st.dataframe(
            show_df,
            use_container_width=True,
            hide_index=True,
            height=450,
        )

        # Buton de descărcare
        csv_data = df[show_cols].rename(columns=col_rename).to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="⬇️ Descarcă date CSV",
            data=csv_data,
            file_name=f"Moldova_PiataMuncii_{datetime.now().strftime('%Y%m')}.csv",
            mime="text/csv",
            use_container_width=False,
        )

        # Info despre sursa de date
        st.markdown(f"""
        <div style="background:{BRAND['bg']}; border:1px solid {BRAND['border']}; 
                    padding:12px 16px; border-radius:8px; margin-top:12px;
                    font-family:{FONT}; font-size:11px; color:{BRAND['subtext']};">
            <strong>Sursa datelor:</strong> {sursa_text}<br>
            <strong>Acoperire:</strong> Date trimestriale, afișate conform Anchetei Forței de Muncă (AFM/BIM), BNS Moldova.<br>
            <strong>Ultimă actualizare:</strong> {ultima_actualizare}
        </div>
        """, unsafe_allow_html=True)