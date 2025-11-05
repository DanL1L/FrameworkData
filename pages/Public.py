# pages/Sector_Public.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os

st.set_page_config(page_title="Finanțe publice – Structura bugetului", layout="wide")

# ====== Stil general mai modern și font clar ======
st.markdown("""
<style>
    html, body, [class*="css"]  {
        font-family: 'Segoe UI', 'Roboto', 'Open Sans', sans-serif;
        color: #1a1a1a;
    }
    h1, h2, h3, h4 {
        font-family: 'Segoe UI Semibold', 'Roboto', sans-serif;
    }
    .stMarkdown p {
        font-size: 15px;
        line-height: 1.5;
    }
    .js-plotly-plot text,
    .js-plotly-plot tspan {
    text-shadow: none !important;
    fill: #111111 !important;      /* culoare text SVG */
    color: #111111 !important;     /* fallback */
    font-weight: 600 !important;   /* puțin mai bold */
}
</style>
""", unsafe_allow_html=True)

st.title("Sectorul Public")

st.markdown("""
Analiza **veniturilor și cheltuielilor bugetului public național**.
""")

# =====================================================
# 1. ÎNCĂRCAREA DATELOR DIN EXCEL
# =====================================================
file_path = os.path.join("data", "Test_Data_Venituri_Cheltuieli.xlsx")

try:
    xls = pd.ExcelFile(file_path)
except FileNotFoundError:
    st.error(f"Fișierul nu a fost găsit: `{file_path}`.\n"
             f"Verifică să fie în folderul `data/` sau actualizează calea în cod.")
    st.stop()

df_venituri = pd.read_excel(xls, sheet_name="Venituri")
df_chelt_f = pd.read_excel(xls, sheet_name="Cheltuieli_F")
df_debt = pd.read_excel(xls, sheet_name="Datoria")   # <<< NOU

df_venituri["Date"] = pd.to_datetime(df_venituri["Date"])
df_chelt_f["Date"] = pd.to_datetime(df_chelt_f["Date"])
df_debt["Date"] = pd.to_datetime(df_debt["Date"])
df_debt.columns = df_debt.columns.str.strip()        # eliminăm eventualele spații

# =====================================================
# 2. PERIOADE DISPONIBILE + FILTRE (AN + LUNĂ)
# =====================================================
common_dates = sorted(set(df_venituri["Date"]).intersection(df_chelt_f["Date"]))
if not common_dates:
    st.error("Nu există nicio perioadă comună între foile 'Venituri' și 'Cheltuieli_F'.")
    st.stop()

month_names_ro = {
    1: "ianuarie", 2: "februarie", 3: "martie", 4: "aprilie",
    5: "mai", 6: "iunie", 7: "iulie", 8: "august",
    9: "septembrie", 10: "octombrie", 11: "noiembrie", 12: "decembrie"
}

years_available = sorted({d.year for d in common_dates})
st.sidebar.header("Filtre")

selected_year = st.sidebar.selectbox(
    "Selectează anul:",
    options=years_available,
    index=len(years_available) - 1
)

months_in_year = sorted({d.month for d in common_dates if d.year == selected_year})
month_labels = [month_names_ro[m].capitalize() for m in months_in_year]
month_label_to_num = {month_names_ro[m].capitalize(): m for m in months_in_year}

selected_month_label = st.sidebar.selectbox(
    "Selectează luna:",
    options=month_labels,
    index=len(month_labels) - 1
)
selected_month = month_label_to_num[selected_month_label]

matching = [d for d in common_dates if d.year == selected_year and d.month == selected_month]
if not matching:
    st.error("Nu există date pentru combinația selectată de lună și an.")
    st.stop()

selected_date = matching[0]
st.caption(
    f"Perioada selectată: **{month_names_ro[selected_date.month].capitalize()} {selected_date.year}**"
)

# =====================================================
# 3. CREARE STRUCTURI VENITURI / CHELTUIELI PENTRU PERIOADA ALEASĂ
# =====================================================
row_v = df_venituri[df_venituri["Date"] == selected_date].iloc[0]
row_c = df_chelt_f[df_chelt_f["Date"] == selected_date].iloc[0]

# Venituri: toate coloanele între 'Date' și 'TOTAL VENITURI'
revenues = {col: float(row_v[col]) for col in df_venituri.columns[1:-1]}
total_rev = float(row_v["TOTAL VENITURI"])

# Cheltuieli: funcțiile bugetare principale
expense_cols = [
    "Servicii de stat cu destinație generală",
    "Apărare națională",
    "Ordine publică și securitate națională",
    "Servicii în domeniul economiei",
    "Protecția mediului",
    "Gospodăria de locuințe și gospodăria serviciilor comunale",
    "Ocrotirea sănătății",
    "Cultură, sport, tineret, culte și odihnă",
    "Învățămînt",
    "Protecție socială",
]
expenses = {col: float(row_c[col]) for col in expense_cols}
total_exp = float(row_c["Total cheltuieli conf. raportului Min Fin"])
deficit = round(total_exp - total_rev, 1)

# =====================================================
# 4. STRUCTURA PENTRU SANKEY
# =====================================================
nodes = (
    list(revenues.keys())
    + ["Total venituri", "Deficit", "Total cheltuieli"]
    + list(expenses.keys())
)
idx = {name: i for i, name in enumerate(nodes)}

sources, targets, values = [], [], []

# Venituri → Total venituri
for name, val in revenues.items():
    sources.append(idx[name])
    targets.append(idx["Total venituri"])
    values.append(val)

# Total venituri + Deficit → Total cheltuieli
sources += [idx["Total venituri"], idx["Deficit"]]
targets += [idx["Total cheltuieli"], idx["Total cheltuieli"]]
values += [total_rev, deficit]

# Total cheltuieli → Funcții bugetare
for name, val in expenses.items():
    sources.append(idx["Total cheltuieli"])
    targets.append(idx[name])
    values.append(val)

# =====================================================
# 5. DIAGRAMA SANKEY
# =====================================================
fig = go.Figure(
    data=[
        go.Sankey(
            node=dict(
                pad=22,
                thickness=18,
                line=dict(color="rgba(0,0,0,0.2)", width=0.5),
                label=nodes,
                color="#5BB2FA",
                hoverlabel=dict(font=dict(size=15, family="Times New Roman", color="black", shadow="none")),
            ),
            link=dict(
                source=sources,
                target=targets, 
                value=values,
                color="rgba(91, 178, 250, 0.6)",
            ),
        )
    ]
)

fig.update_layout(
    title={
        "text": f"<b>Structura veniturilor și cheltuielilor bugetare – "
                f"{month_names_ro[selected_date.month].capitalize()} {selected_date.year}</b>",
        "x": 0.5,
        "xanchor": "center",
        "font": dict(family="Times New Roman", size=20, color="#0f172a"),
    },
    font=dict(
        family="Times New Roman",
        size=16,
        color="#000000",
        
    ),
    height=680,
    margin=dict(l=40, r=40, t=80, b=40),
    paper_bgcolor="white",
    plot_bgcolor="white",
)

st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 7. DIAGRAME CIRCULARE – STRUCTURA VENITURILOR / CHELTUIELILOR
# =====================================================
st.markdown("---")
st.subheader("Structura pe componente a veniturilor și cheltuielilor")

col_pie1, col_pie2 = st.columns(2)

rev_df = pd.DataFrame({
    "Categorie": list(revenues.keys()),
    "Valoare": list(revenues.values()),
})

exp_df = pd.DataFrame({
    "Categorie": list(expenses.keys()),
    "Valoare": list(expenses.values()),
})

with col_pie1:
    st.markdown("#### Venituri după surse")
    fig_rev_pie = px.pie(
        rev_df,
        names="Categorie",
        values="Valoare",
        hole=0.4,
    )
    fig_rev_pie.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Pondere: %{percent}<br>Valoare: %{value:,.1f} mil. lei<extra></extra>",
    )
    fig_rev_pie.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_rev_pie, use_container_width=True)

with col_pie2:
    st.markdown("#### Cheltuieli după funcții bugetare")
    fig_exp_pie = px.pie(
        exp_df,
        names="Categorie",
        values="Valoare",
        hole=0.4,
    )
    fig_exp_pie.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Pondere: %{percent}<br>Valoare: %{value:,.1f} mil. lei<extra></extra>",
    )
    fig_exp_pie.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_exp_pie, use_container_width=True)


# ---- comparație cu aceeași lună din anul precedent (dacă există) ----
prev_year = selected_year - 1
prev_date_candidates = df_venituri[
    (df_venituri["Date"].dt.year == prev_year) &
    (df_venituri["Date"].dt.month == selected_month)
]

if not prev_date_candidates.empty:
    prev_date = prev_date_candidates["Date"].iloc[0]
    row_v_prev = df_venituri[df_venituri["Date"] == prev_date].iloc[0]
    row_c_prev = df_chelt_f[df_chelt_f["Date"] == prev_date].iloc[0]

    prev_rev = float(row_v_prev["TOTAL VENITURI"])
    prev_exp = float(row_c_prev["Total cheltuieli conf. raportului Min Fin"])
    prev_def = prev_exp - prev_rev

    chg_rev_pct = (total_rev - prev_rev) / prev_rev * 100 if prev_rev else 0
    chg_exp_pct = (total_exp - prev_exp) / prev_exp * 100 if prev_exp else 0
    chg_def_pct = (deficit - prev_def) / prev_def * 100 if prev_def else 0
else:
    prev_rev = prev_exp = prev_def = None
    chg_rev_pct = chg_exp_pct = chg_def_pct = None

# ---- cele mai mari surse de venit / categorii de cheltuieli ----
rev_df = pd.DataFrame({
    "Categorie": list(revenues.keys()),
    "Valoare": list(revenues.values()),
})
exp_df = pd.DataFrame({
    "Categorie": list(expenses.keys()),
    "Valoare": list(expenses.values()),
})

top_rev = rev_df.sort_values("Valoare", ascending=False).head(2)
top_exp = exp_df.sort_values("Valoare", ascending=False).head(2)

top_rev_1 = top_rev.iloc[0]
top_rev_2 = top_rev.iloc[1]
top_exp_1 = top_exp.iloc[0]
top_exp_2 = top_exp.iloc[1]

share_rev_1 = top_rev_1["Valoare"] / total_rev * 100 if total_rev else 0
share_rev_2 = top_rev_2["Valoare"] / total_rev * 100 if total_rev else 0
share_exp_1 = top_exp_1["Valoare"] / total_exp * 100 if total_exp else 0
share_exp_2 = top_exp_2["Valoare"] / total_exp * 100 if total_exp else 0

# ---- text descriptiv ----
text_parts = []

# baza – nivelul agregat
text_parts.append(
    f"În **{month_names_ro[selected_date.month].capitalize()} {selected_date.year}**, "
    f"veniturile totale ale bugetului public național au constituit "
    f"**{total_rev:,.1f} mil. lei**, iar cheltuielile totale **{total_exp:,.1f} mil. lei**, "
    f"ceea ce a generat un **deficit bugetar de {deficit:,.1f} mil. lei** "
    f"(*{abs(deficit) / total_rev * 100:,.1f}% din venituri*)."
)

# comparație cu anul precedent – doar dacă avem date
if prev_rev is not None:
    semn_def = "majorat" if chg_def_pct and chg_def_pct > 0 else "micșorat"
    text_parts.append(
        f"Comparativ cu **aceeași perioadă din {prev_year}**, "
        f"veniturile au fost "
        f"{'mai mari' if chg_rev_pct > 0 else 'mai mici'} cu "
        f"**{abs(chg_rev_pct):.1f}%**, iar cheltuielile "
        f"{'au crescut' if chg_exp_pct > 0 else 'au scăzut'} cu "
        f"**{abs(chg_exp_pct):.1f}%**. "
        f"Deficitul bugetar s-a **{semn_def}** cu aproximativ "
        f"**{abs(chg_def_pct):.1f}%**."
    )

# structură – principalele categorii
text_parts.append(
    f"Cele mai importante surse de venit au fost:\n"
    f"- **{top_rev_1['Categorie']}**, cu **{top_rev_1['Valoare']:,.1f} mil. lei** "
    f"(*{share_rev_1:.1f}% din venituri*);\n"
    f"- **{top_rev_2['Categorie']}**, cu **{top_rev_2['Valoare']:,.1f} mil. lei** "
    f"(*{share_rev_2:.1f}% din venituri*).\n\n"
    f"La capitolul cheltuieli, cele mai mari alocări au revenit pentru:\n"
    f"- **{top_exp_1['Categorie']}**, în sumă de **{top_exp_1['Valoare']:,.1f} mil. lei** "
    f"(*{share_exp_1:.1f}% din totalul cheltuielilor*);\n"
    f"- **{top_exp_2['Categorie']}**, în sumă de **{top_exp_2['Valoare']:,.1f} mil. lei** "
    f"(*{share_exp_2:.1f}% din total*)."
)

st.markdown("\n\n".join(text_parts))
# =====================================================
# 8. DIAGRAMĂ DE EVOLUȚIE VENITURI vs. CHELTUIELI
# =====================================================
st.markdown("---")
st.subheader("Evoluția în timp a veniturilor și cheltuielilor bugetare")

df_all = pd.merge(
    df_venituri[["Date", "TOTAL VENITURI"]],
    df_chelt_f[["Date", "Total cheltuieli conf. raportului Min Fin"]],
    on="Date",
    how="inner"
).sort_values("Date")

df_all = df_all.rename(columns={
    "TOTAL VENITURI": "Venituri totale",
    "Total cheltuieli conf. raportului Min Fin": "Cheltuieli totale",
})

freq = st.radio(
    "Frecvența datelor pentru evoluție:",
    ["Lunar", "Anual"],
    horizontal=True,
)

if freq == "Anual":
    df_plot = df_all.copy()
    df_plot["An"] = df_plot["Date"].dt.year
    df_plot = df_plot.groupby("An", as_index=False)[["Venituri totale", "Cheltuieli totale"]].sum()
    x_col = "An"
else:
    df_plot = df_all.copy()
    df_plot["Perioadă"] = df_plot["Date"].dt.to_period("M").astype(str)
    df_plot = df_plot.groupby("Perioadă", as_index=False)[["Venituri totale", "Cheltuieli totale"]].sum()
    x_col = "Perioadă"

fig_line = px.line(
    df_plot,
    x=x_col,
    y=["Venituri totale", "Cheltuieli totale"],
    labels={
        x_col: "Perioadă",
        "value": "mil. lei",
        "variable": "Indicator",
    },
    template="simple_white",
)

fig_line.update_traces(line=dict(width=3))
fig_line.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.25,
        xanchor="center",
        x=0.5,
        font=dict(size=12),
    ),
    yaxis_title="mil. lei",
    xaxis_title="",
    margin=dict(l=40, r=20, t=40, b=80),
)

st.plotly_chart(fig_line, use_container_width=True)


# =====================================================
# 9. DATORIA PUBLICĂ – NIVEL ȘI STRUCTURĂ
# =====================================================
st.markdown("---")
st.subheader("Datoria publică (cumulativă)")

df_debt_sorted = df_debt.sort_values("Date").copy()

# denumirile trebuie să fie exact ca în fișierul Excel
col_int = "Datoria internă"
col_ext = "Datoria externă"
col_ext_usd = "Datoria externă USD"
col_fx = "Curs"
col_gdp = "PIB"

# rândul de datorie pentru perioada selectată (aceeași selected_date ca la buget)
row_debt = df_debt_sorted[df_debt_sorted["Date"] == selected_date]

if row_debt.empty:
    # dacă nu găsim perioada exactă, folosim ultima observație și afișăm un mesaj
    row_debt = df_debt_sorted.iloc[[-1]]
    st.warning(
        "Nu există date de datorie pentru perioada selectată; "
        "se afișează ultima observație disponibilă."
    )

row_debt = row_debt.iloc[0]

total_debt = float(row_debt[col_int]) + float(row_debt[col_ext])
share_int = row_debt[col_int] / total_debt * 100 if total_debt else 0
share_ext = row_debt[col_ext] / total_debt * 100 if total_debt else 0

# KPI–uri pentru perioada selectată
col_k1, col_k2, col_k3 = st.columns(3)
col_k1.metric(
    "Datorie internă",
    f"{row_debt[col_int]:,.1f} mil. lei",
    f"{share_int:.1f}% din total"
)
col_k2.metric(
    "Datorie externă",
    f"{row_debt[col_ext]:,.1f} mil. lei",
    f"{share_ext:.1f}% din total"
)
col_k3.metric(
    "Total datorie publică",
    f"{total_debt:,.1f} mil. lei"
)

# ===== Text explicativ pentru perioada selectată =====
ext_usd = row_debt.get(col_ext_usd, None)
fx = row_debt.get(col_fx, None)
gdp_val = row_debt.get(col_gdp, None)

text = f"""
În **Ianuarie - {month_names_ro[selected_date.month].capitalize()} {selected_date.year}**, datoria publică totală
a constituit **{total_debt:,.1f} mil. lei**, din care:
- datoria **internă**: **{row_debt[col_int]:,.1f} mil. lei** (*{share_int:.1f}%* din total),
- datoria **externă**: **{row_debt[col_ext]:,.1f} mil. lei** (*{share_ext:.1f}%* din total).
"""

if pd.notna(ext_usd) and pd.notna(fx):
    text += (
        f"\nDatoria externă corespunde la aproximativ **{ext_usd:,.1f} mil. USD**, "
        f"la un curs mediu de **{fx:,.2f} MDL/USD**."
    )

if pd.notna(gdp_val):
    ratio = total_debt / gdp_val * 100 if gdp_val else 0
    text += (
        f"\nRaportul datoriei publice la PIB a fost de **{ratio:.1f}%**, "
        f"pe baza unui PIB de **{gdp_val:,.1f} mil. lei**."
    )

st.markdown(text)


# =====================================================
# 9. Structura datoriei și cursul MDL/USD – pe același rând
# =====================================================
st.markdown("#### Structura datoriei publice și rata de schimb MDL/USD în anul selectat")

df_debt_year = df_debt_sorted[df_debt_sorted["Date"].dt.year == selected_year].copy()

if df_debt_year.empty:
    st.info("Nu există date de datorie pentru anul selectat.")
else:
    # --- valori pentru Donut ---
    last_year_row = df_debt_year.iloc[-1]  # de ex. decembrie 2024
    d_int_year = float(last_year_row[col_int])
    d_ext_year = float(last_year_row[col_ext])
    total_year = d_int_year + d_ext_year

    # --- structura layout pe 2 coloane ---
    col_left, col_right = st.columns([1, 1])

    # ===============================
    # 1️⃣ Donut în stânga
    # ===============================
    with col_left:
        df_donut = pd.DataFrame({
            "Componentă": ["Datoria internă", "Datoria externă"],
            "Valoare": [d_int_year, d_ext_year],
        })
        fig_donut = px.pie(
            df_donut,
            names="Componentă",
            values="Valoare",
            hole=0.7,
            template="simple_white",
        )
        fig_donut.update_traces(
            textposition="inside",
            texttemplate="%{label}<br>%{value:,.1f} mil. lei<br>%{percent:.1%}",
            showlegend=True
        )
        fig_donut.update_layout(
            margin=dict(l=40, r=40, t=40, b=40),
            legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
            font=dict(family="Times New Roman", size=14),
        )

        # Donut + anul mare în colțul din dreapta sus
        st.plotly_chart(fig_donut, use_container_width=True)
        st.markdown(
            f"<div style='font-size:50px; font-weight:700; text-align:right; margin-top:-80px;'>{selected_year}</div>",
            unsafe_allow_html=True,
        )

    # ===============================
    # 2️⃣ Rata de schimb în dreapta
    # ===============================
    with col_right:
        df_fx = df_debt_year.copy()
        df_fx["Lună"] = df_fx["Date"].dt.month.map(
            lambda m: month_names_ro[m].capitalize()
        )

        fig_fx = px.line(
            df_fx,
            x="Lună",
            y=col_fx,
            template="plotly_white",
            labels={"Lună": "Lună", col_fx: "MDL / USD"},
        )
        fig_fx.update_traces(
            mode="lines+markers+text",
            line=dict(width=3),
            text=df_fx[col_fx].round(2),
            textposition="top center",
        )
        fig_fx.update_layout(
            title=dict(
                text="Rata de schimb MDL / USD",
                x=0.5,
                font=dict(family="Times New Roman", size=16, color="#1a1a1a")
            ),
            margin=dict(l=40, r=40, t=60, b=60),
            xaxis=dict(showgrid=False),
            yaxis=dict(title="MDL / USD"),
            font=dict(family="Times New Roman", size=14),
        )

        st.plotly_chart(fig_fx, use_container_width=True)

# ===== Grafic de evoluție a datoriei (internă vs. externă) =====
st.markdown("#### Evoluția în timp a datoriei interne și externe")

fig_debt = px.line(
    df_debt_sorted,
    x="Date",
    y=[col_int, col_ext],
    labels={
        "Date": "Perioadă",
        "value": "mil. lei",
        "variable": "Componentă",
    },
    template="simple_white",
)

fig_debt.update_traces(line=dict(width=3))
fig_debt.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.25,
        xanchor="center",
        x=0.5,
        font=dict(size=12),
    ),
    margin=dict(l=40, r=20, t=40, b=80),
)

st.plotly_chart(fig_debt, use_container_width=True)