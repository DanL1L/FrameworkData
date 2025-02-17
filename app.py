import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_data

# Configurarea paginii
st.set_page_config(page_title='Macroeconomic', layout='wide')

# Titlul aplicației
# st.title('Indicatorii macroeconomici')

# Adăugare Header
# st.markdown("""
#     <h1 style='text-align: center; color: #1a498d;'>Indicatorii macroeconomici</h1>
#     <hr style='border: 1px solid #ddd;'>
# """, unsafe_allow_html=True)

# Creare layout cu logo și titlu pe același rând
col1, col2 = st.columns([1, 4])  # Prima coloană mai mică pentru logo, a doua mai mare pentru text

with col1:
    st.image("data/logo.svg", width=200  )  # Ajustează calea dacă este necesar


with col2:
    st.markdown("""
        <h1 style='color: #1f4e79;'> Principalii Indicatorii macroeconomici</h1>
        <p><strong>Analiza și Prognozare Macroeconomică</strong></p>
         <p style='text-align: justify;'>Această pagină oferă o <strong>monitorizare și analiză</strong> a situației macroeconomice din Republica Moldova, prezentând informații despre <strong>importuri, 
         exporturi și balanța comercială</strong>. Scopul principal este <strong>informarea factorilor de decizie</strong> - conducerea ministerului, instituțiile de stat, organizațiile internaționale și publicul larg.
          Prin analiza datelor comerciale și prognozele economice pe termen mediu, contribuim la eficientizarea procesului de luare a deciziilor, inclusiv la <strong>elaborarea Cadrului Bugetar pe 
          Termen Mediu și a Legii bugetului de stat</strong>.</p>
    """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# Încărcarea datelor
df, df_exports = load_data()

month_mapping = {
    "Ianuarie": 1, "Februarie": 2, "Martie": 3, "Aprilie": 4,
    "Mai": 5, "Iunie": 6, "Iulie": 7, "August": 8,
    "Septembrie": 9, "Octombrie": 10, "Noiembrie": 11, "Decembrie": 12
}

# Verificăm dacă există date    
if df.empty:
    st.warning("Nu există date disponibile. Verificați fișierul sursă.")
    st.stop()

# Convertim toate coloanele relevante în string pentru a evita erorile de concatenare
df = df.astype({"An": "int", "Trimestru": "Int64", "Semestru": "Int64"})
df = df.astype({"An": "str", "Lună": "str", "Trimestru": "str", "Semestru": "str"})

# Sidebar pentru selecții
st.sidebar.header("Filtre")
selected_period = st.sidebar.selectbox("Selectează perioada:", ["Lunar", "Trimestrial", "Anual"])
selected_indicator = st.sidebar.selectbox("Selectează indicatorul:", ["Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"])
selected_country = st.sidebar.selectbox("Selectează țara:", ["Toate"] + list(df["Țară"].unique()))
selected_group = st.sidebar.selectbox("Selectează grupul de țări:", ["Toate", "UE", "CSI", "Restul lumii"])
selected_month = st.sidebar.selectbox("Selectează perioada:", df["Lună"].unique())

# Filtrare după țară dacă este selectată una
if selected_country != "Toate":
    df = df[df["Țară"] == selected_country]

# Filtrare după grup de țări
if selected_group != "Toate":
    df = df[df["Grupă Țări"] == selected_group]

# Grupare în funcție de perioada selectată
if selected_period == "Trimestrial":
    df["Perioadă"] = df["An"] + "-Q" + df["Trimestru"]
elif selected_period == "Semestrial":
    df["Perioadă"] = df["An"] + "-S" + df["Semestru"]
elif selected_period == "Anual":
    df["Perioadă"] = df["An"]
else:
    df["Perioadă"] = df["Lună"]

# Asigurăm că indicatorii sunt numerici înainte de agregare
for col in ["Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Agregare
df_grouped = df.groupby(["Perioadă", "Țară"])[selected_indicator].sum().reset_index()
df_total = df.groupby(["Perioadă"])[["Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]].sum().reset_index()

df_total = df_total.sort_values(by=["Perioadă"], ascending=True)


# Afișare grafic principal - Total agregat fără divizări
st.subheader(f"Evoluția {selected_indicator} ({selected_period})")
fig = px.bar(df_total, x="Perioadă", y=selected_indicator, title=f"{selected_indicator} în timp", 
             labels={selected_indicator: "Valoare (mil. $)"}, barmode='relative')
             
st.plotly_chart(fig, use_container_width=True)

# Filtrare pentru luna selectată
df_month = df[df["Lună"] == selected_month]

# Crearea layout-ului cu două coloane
col1, col2 = st.columns(2)

# Top 10 țări pentru importuri în coloana stângă
with col1:
    st.subheader("Top 10 Țări - Importuri")
    df_top_import = df_month.sort_values(by="Importuri (mil. $)", ascending=False).head(10)
    other_import_value = df_month["Importuri (mil. $)"].sum() - df_top_import["Importuri (mil. $)"].sum()
    df_top_import = pd.concat([df_top_import, pd.DataFrame([{"Țară": "Altele", "Importuri (mil. $)": other_import_value}])], ignore_index=True)
    total_import = df_top_import["Importuri (mil. $)"].sum()
    df_top_import["Procent"] = (df_top_import["Importuri (mil. $)"] / total_import) * 100
    fig_pie_import = px.pie(df_top_import, names="Țară", values="Procent", title="Ponderea Top 10 Țări - Importuri", hole=0.4)
    st.plotly_chart(fig_pie_import, use_container_width=True)

# Top 10 țări pentru exporturi în coloana dreaptă
with col2:
    st.subheader("Top 10 Țări - Exporturi")
    df_top_export = df_month.sort_values(by="Exporturi (mil. $)", ascending=False).head(10)
    other_export_value = df_month["Exporturi (mil. $)"].sum() - df_top_export["Exporturi (mil. $)"].sum()
    df_top_export = pd.concat([df_top_export, pd.DataFrame([{"Țară": "Altele", "Exporturi (mil. $)": other_export_value}])], ignore_index=True)
    total_export = df_top_export["Exporturi (mil. $)"].sum()
    df_top_export["Procent"] = (df_top_export["Exporturi (mil. $)"] / total_export) * 100
    fig_pie_export = px.pie(df_top_export, names="Țară", values="Procent", title="Ponderea Top 10 Țări - Exporturi", hole=0.4)
    st.plotly_chart(fig_pie_export, use_container_width=True)

df_total = df.groupby("Perioadă")[["Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]].sum().reset_index()

# Selectăm doar ultima perioadă din setul de date pentru calculul valorilor
latest_data = df_total.iloc[-1]
previous_data = df_total.iloc[-2] if len(df_total) > 1 else latest_data

# Calculăm variațiile procentuale
trade_balance_change = ((latest_data["Sold Comercial (mil. $)"] - previous_data["Sold Comercial (mil. $)"]) / abs(previous_data["Sold Comercial (mil. $)"])) * 100 if previous_data["Sold Comercial (mil. $)"] != 0 else 0
export_change = ((latest_data["Exporturi (mil. $)"] - previous_data["Exporturi (mil. $)"]) / abs(previous_data["Exporturi (mil. $)"])) * 100 if previous_data["Exporturi (mil. $)"] != 0 else 0
import_change = ((latest_data["Importuri (mil. $)"] - previous_data["Importuri (mil. $)"]) / abs(previous_data["Importuri (mil. $)"])) * 100 if previous_data["Importuri (mil. $)"] != 0 else 0



# Text start
import locale
locale.setlocale(locale.LC_NUMERIC, "en_US.UTF-8")  # Setăm formatul pentru numere

# Selectăm cea mai recentă perioadă și perioada anterioară
latest_data = df_total.iloc[-1]
previous_data = df_total.iloc[-2] if len(df_total) > 1 else latest_data

# Calculăm variațiile procentuale și absolute
trade_balance_change_abs = latest_data["Sold Comercial (mil. $)"] - previous_data["Sold Comercial (mil. $)"]
export_change_abs = latest_data["Exporturi (mil. $)"] - previous_data["Exporturi (mil. $)"]
import_change_abs = latest_data["Importuri (mil. $)"] - previous_data["Importuri (mil. $)"]

trade_balance_change_pct = (trade_balance_change_abs / abs(previous_data["Sold Comercial (mil. $)"]) * 100) if previous_data["Sold Comercial (mil. $)"] != 0 else 0
export_change_pct = (export_change_abs / abs(previous_data["Exporturi (mil. $)"]) * 100) if previous_data["Exporturi (mil. $)"] != 0 else 0
import_change_pct = (import_change_abs / abs(previous_data["Importuri (mil. $)"]) * 100) if previous_data["Importuri (mil. $)"] != 0 else 0

# Formatarea numerelor
total_trade_value = locale.format_string("%.1f", (latest_data["Exporturi (mil. $)"] + latest_data["Importuri (mil. $)"]) / 1000, grouping=True)
export_change_value = locale.format_string("%.1f", export_change_abs, grouping=True)
import_change_value = locale.format_string("%.1f", import_change_abs, grouping=True)
trade_balance_value = locale.format_string("%.1f", trade_balance_change_abs, grouping=True)

# Generare text descriptiv dinamic
description_text = (
    f"**Valoarea totală a schimburilor comerciale cu mărfuri în {selected_month} a fost de {total_trade_value} mil. dolari**, "
    f"înregistrând o {'creștere' if trade_balance_change_pct > 0 else 'scădere'} de {abs(trade_balance_change_pct):.1f}% față de {previous_data['Perioadă']}. "
    f"Exporturile s-au {'majorat' if export_change_pct > 0 else 'diminuat'} cu {export_change_value} mil. dolari ({export_change_pct:+.1f}%), "
    f"iar importurile s-au {'majorat' if import_change_pct > 0 else 'diminuat'} cu {import_change_value} mil. dolari ({import_change_pct:+.1f}%). "
    f"În rezultat, deficitul balanței comerciale s-a {'majorat' if trade_balance_change_abs > 0 else 'micșorat'} cu {trade_balance_value} mil. dolari."
)

st.markdown(f"**{description_text}**")

# Text finish






# Step 2: Strip any extra whitespace from the strings
df_exports["Lună"] = df_exports["Lună"].str.strip()

# Step 3: Map the month names to numbers
df_exports["Lună"] = df_exports["Lună"].map(month_mapping)

# Step 4: Convert the column to integers
df_exports["Lună"] = df_exports["Lună"].astype(int)

# Convertim coloanele relevante
df_exports["An"] = df_exports["An"].astype(str)

# Convertim valorile la format numeric
for col in ["Exporturi autohtone", "Reexporturi"]:
    df_exports[col] = pd.to_numeric(df_exports[col], errors='coerce').fillna(0)

# Sortăm după An și Lună pentru a păstra ordinea corectă
df_exports["Lună"] = df_exports["Lună"].astype(int)
df_exports = df_exports.sort_values(by=["An", "Lună"])

# Creăm graficul clustered bar chart cu separare pe ani
fig_exp = px.bar(df_exports, x="Lună", y=["Exporturi autohtone", "Reexporturi"],
                 barmode="relative",
                 facet_col="An",  # Separăm anii în coloane distincte
                 title="Exporturile lunare autohtone și reexporturile de mărfuri străine, mil $",
                 labels={"value": "Valoare (mil. $)", "variable": "Tip Export", "Lună": "Luna"},
                 color_discrete_map={"Exporturi autohtone": "#4C8BF5", "Reexporturi": "#A9C9E8"})

# Ajustăm aspectul pentru un stil mai clar și ordonat
fig_exp.update_layout(
    xaxis=dict(tickmode="linear", tickvals=list(range(1, 13))),  # Asigurăm că toate lunile sunt vizibile
    yaxis_title="Mil. $"
)

# Afișarea graficului în aplicație
st.plotly_chart(fig_exp, use_container_width=True)







# Filtrare date în funcție de luna selectată
df_filtered = df[df["Lună"] == selected_month]

# Grupăm datele după grupul de țări
df_countries_grouped = df_filtered.groupby("Grupă Țări")[["Exporturi (mil. $)", "Importuri (mil. $)"]].sum().reset_index()

# Calculăm totalul schimburilor comerciale pentru fiecare grupă
df_countries_grouped["Total Comerț"] = df_countries_grouped["Exporturi (mil. $)"] + df_countries_grouped["Importuri (mil. $)"]

# Calculăm procentele și le rotunjim la cel mai apropiat număr întreg
df_countries_grouped["Procent"] = ((df_countries_grouped["Total Comerț"] / df_countries_grouped["Total Comerț"].sum()) * 100).round(0).astype(int)

# Crearea diagramei tip "donut" cu etichete rotunjite
fig_donut = px.pie(df_countries_grouped, names="Grupă Țări", values="Procent",
                   title=f"Schimburile comerciale pe grupe de țări ({selected_month})",
                   hole=0.4,  # Creează un efect de "donut"
                   labels={"Grupă Țări": "Grupa de Țări"},
                   color_discrete_sequence=["#4C8BF5", "#A9C9E8", "#6C757D"])

# Adăugăm etichete personalizate cu procentaj + valoarea în milioane $, rotunjite
fig_donut.update_traces(
    textinfo="percent+label",
    hovertemplate="<b>%{label}</b><br>Procent: %{value}%<br>Valoare: %{customdata} mil. $",
    customdata=df_countries_grouped["Total Comerț"].round(0).astype(int)  # Rotunjire la număr întreg
)

# Afișarea graficului
st.plotly_chart(fig_donut, use_container_width=True)







# Adăugare diagramă Waterfall pentru balanța comercială totală
# if "Sold Comercial (mil. $)" in df_total.columns and not df_total["Sold Comercial (mil. $)"].isnull().all():
#     st.subheader("Contribuția fiecărei perioade la Balanța Comercială Totală")
#     df_total["Tip"] = df_total["Sold Comercial (mil. $)"].apply(lambda x: "Surplus" if x > 0 else "Deficit")

#     fig_waterfall = px.bar(df_total, x="Perioadă", y="Sold Comercial (mil. $)", 
#                            title="Balanța Comercială Totală - Contribuție pe Perioade",
#                            labels={"Sold Comercial (mil. $)": "Mil. $"},
#                            color="Tip",
#                            color_discrete_map={"Surplus": "green", "Deficit": "red"})
#     st.plotly_chart(fig_waterfall, use_container_width=True)
# else:
#     st.warning("Nu există date pentru Balanța Comercială Totală în perioada selectată.")


# Afișare tabel pe toată lățimea ecranului
st.subheader("Tabel Date")
st.dataframe(df_grouped, use_container_width=True)

# Adăugare Footer
st.markdown("""
    <hr style='border: 1px solid #ddd;'>
    <p style='text-align: center; color: grey;'>© 2024 APM. Toate drepturile rezervate.</p>
""", unsafe_allow_html=True)
