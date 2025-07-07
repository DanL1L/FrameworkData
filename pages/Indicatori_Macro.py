import streamlit as st
import pandas as pd
import re
import plotly.express as px
import statsmodels.api as sm
from utils.data_loader import load_data
# from utils.comert_scraper import fetch_comert_data

import os
# os.system('pip install PyPDF2')
# os.system('pip install langchain langchain-community')
# os.system('pip install sentence-transformers transformers torch')
import locale
import PyPDF2

# from PyPDF2 import PdfReader
# from langchain.text_splitter import CharacterTextSplitter
# from langchain_community.vectorstores import FAISS
# from langchain_community.document_loaders import PyPDFLoader
# from langchain_community.embeddings import HuggingFaceEmbeddings

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
     logo_path = os.path.join(os.getcwd(), "data", "logo.svg")
     st.image(logo_path, width=200)

with col2:
    st.markdown("""
        <h1 style='color: #1f4e79;'> Principalii Indicatori macroeconomici</h1>
        <p><strong>Analiza și Prognozare Macroeconomică</strong></p>
         <p style='text-align: justify;'>Această pagină oferă o <strong>monitorizare și analiză</strong> a situației macroeconomice din Republica Moldova, prezentând informații despre <strong>importuri, 
         exporturi și balanța comercială</strong>. Scopul principal este <strong>informarea factorilor de decizie</strong> - conducerea ministerului, instituțiile de stat, organizațiile internaționale și publicul larg.
          Prin analiza datelor comerciale și prognozele economice pe termen mediu, contribuim la eficientizarea procesului de luare a deciziilor, inclusiv la <strong>elaborarea Cadrului Bugetar pe 
          Termen Mediu și a Legii bugetului de stat</strong>.</p>
    """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# Încărcarea datelor
df, df_exports, df_influenta, df_influenta_Import, df_exp_lunar, df_exp_imp_total, df_import_ncm_all  = load_data()

month_mapping = {
    "Ianuarie": 1, "Februarie": 2, "Martie": 3, "Aprilie": 4,
    "Mai": 5, "Iunie": 6, "Iulie": 7, "August": 8,
    "Septembrie": 9, "Octombrie": 10, "Noiembrie": 11, "Decembrie": 12
}

# Dicționar de mapare a lunilor la valori numerice
month_order = {
    "Ianuarie": 0,  # Facem "Ianuarie" prima
    "Ianuarie - Februarie": 11, "Ianuarie - Martie": 10, "Ianuarie - Aprilie": 9,
    "Ianuarie - Mai": 8, "Ianuarie - Iunie": 7, "Ianuarie - Iulie": 6, "Ianuarie - August": 5,
    "Ianuarie - Septembrie": 4, "Ianuarie - Octombrie": 3, "Ianuarie - Noiembrie": 2, "Ianuarie - Decembrie": 1
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
# Adăugare FILTRU pentru selecția anului
selected_year = st.sidebar.selectbox("Selectează anul:",sorted(df["An"].unique(), reverse=True))
selected_period = st.sidebar.selectbox("Selectează perioada:", ["Lunară"])
selected_indicator = st.sidebar.selectbox("Selectează indicatorul:", ["Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"])
selected_country = st.sidebar.selectbox("Selectează țara:", ["Toate"] + list(df["Țară"].unique()))
selected_group = st.sidebar.selectbox("Selectează grupul de țări:", ["Toate", "UE", "CSI", "Restul lumii"])
selected_month = st.sidebar.selectbox("Selectează intervalul:", df["Lună"].unique())

# assistant_active = st.sidebar.checkbox("Activare Asistent MDED")

# st.sidebar.markdown(
#     """
#     <style>
#         .back-button {
#             display: block;
#             text-align: center;
#             background-color: #ffffff;
#             color: white;
#             padding: 10px;
#             text-decoration: none;
#             border-radius: 8px;
#             width: 100%; 
#             height: 45px; 
#             transition: 0.3s;
#         }
#         .back-button:hover {
#             filter: blur(0px); 
#             background-color: #dadfe5; 
#         }
#     </style>
#     <a href='/page/forecast.py' target='_self' class='back-button'>Prognoza</a>
#     """,
#     unsafe_allow_html=True
# )

#Adaugare de delimitator pentru a separa secțiunile
st.sidebar.markdown("<hr>", unsafe_allow_html=True)


st.sidebar.markdown(
    """
    <style>
        .back-button {
            display: block;
            text-align: center;
            background-color: #ffffff;
            color: white;
            padding: 10px;
            text-decoration: none;
            border-radius: 8px;
            width: 100%; 
            height: 45px; 
            transition: 0.3s;
        }
        .back-button:hover {
            filter: blur(0px); 
            background-color: #dadfe5; 
        }
    </style>
    <a href='https://danl1l.github.io/macro/index.html' target='_self' class='back-button'>Înapoi</a>
    """,
    unsafe_allow_html=True
)

# Filtrare după țară dacă este selectată una
if selected_year != "Toți":
    df = df[df["An"] == selected_year]

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
 
df_grouped = df.groupby(["Perioadă", "Țară"])[selected_indicator].sum().reset_index()
# Filtrare pentru luna selectată
df_month = df[df["Lună"] == selected_month]


selected_row = df_exp_imp_total.iloc[-1]
selected_row_Imp = df_exp_imp_total.iloc[-1]
selected_row_Exp = df_exp_imp_total.iloc[-1]

deficit_val = selected_row["Sold Comercial (mil. $)"]
deficit_val_Imp = selected_row_Imp["Importuri (mil. $)"]
deficit_val_Exp = selected_row_Exp["Exporturi (mil. $)"]

# Cele 4 diagrame Start

# Date PIB
df_pib_growth = pd.DataFrame({
    'An':             ['2020', '2021', '2022', '2023', '2024'],
    'Creștere PIB (%)': [-8.3, 13.9, -4.6, 0.4,0.1]
})
# Inflație 
df_inflatie = pd.DataFrame({
    'An': ['2021', '2022', '2023', '2024', '2025'],
    'Rata Inflației (%)': [5.1, 28.7, 13.4, 4.7, 7.8]
})

selected_year_int = int(selected_year)
deficit_val_Exp_int= int(deficit_val_Exp)
selected_row_Imp_int = int(deficit_val_Imp)

# Date Comerț Internațional
df_comert = pd.DataFrame({
    'An': [selected_year_int],
    'Exporturi (mil. $)': [deficit_val_Exp_int],
    'Importuri (mil. $)': [selected_row_Imp_int],
    'Deficit Comercial (mil. $)': [deficit_val]
})


# Date Rata Dobânzii
df_dobanda = pd.DataFrame({
    'Perioada': ['2022-04-08', '2022-05-12', '2023-02-07', '2023-03-20', '2023-05-11', '2023-06-20', '2023-07-11', '2024-02-06', '2024-03-21',  '2024-05-07', '2025-01-10', '2025-02-10'], 
    'Rata de Bază (%)': [21.5, 20, 17, 14, 10, 6,4.75, 4.25, 3.75,3.6, 5.6, 6.5]
})


# Layout compact cu 4 coloane
col1, col2, col3, col4 = st.columns(4)
with col1:
        st.subheader("Comerț Internațional")
        st.metric(label=f"Deficit situația curentă", value=f"{deficit_val:,.1f} mil. $")
        fig_comert = px.bar(df_comert, x="An", y=["Exporturi (mil. $)", "Importuri (mil. $)"], barmode='group', title="")
        fig_comert.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_comert, use_container_width=True)
# Diagrama Inflației
with col2:
    st.subheader("Rata medie a inflației")
    st.metric(label="Inflația 2025", value="7.8%")
    fig_inflatie = px.bar(df_inflatie, x="An", y="Rata Inflației (%)", title="")
    fig_inflatie.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_inflatie, use_container_width=True)

# Diagrama Comerțului Internațional
with col3:
    st.subheader("Evoluție PIB")
    st.metric(label="PIB 2024", value="+0.1%")
    fig_pib = px.bar(df_pib_growth, x="An", y="Creștere PIB (%)", 
                     title="", text_auto=True)
    fig_pib.update_yaxes(range=[-15, 20], zeroline=True, zerolinewidth=2, zerolinecolor="black")
    fig_pib.update_layout(
        height=250, 
        margin=dict(l=20, r=20, t=20, b=20), 
        showlegend=False
    )
    st.plotly_chart(fig_pib, use_container_width=True)
# Diagrama Ratei Dobânzii
with col4:
    st.subheader("Rata Dobânzii")
    st.metric(label="05 Feb 2025", value="6.5%")
    fig_dobanda = px.line(df_dobanda, x="Perioada", y="Rata de Bază (%)", title="")
    fig_dobanda.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_dobanda, use_container_width=True)

# Cele 4 diagrame Finish

# Adăugare titlu la mijloc de pagină 
st.markdown("<hr>", unsafe_allow_html=True)
st.title("Analiza comerțului internațional")
# Subtittlu mijloc ecran

# Crearea layout-ului cu două coloane
col1, col2 = st.columns(2)

df_top_import = df_month.sort_values(by="Importuri (mil. $)", ascending=False).head(10)

if df_top_import.empty:
     st.warning(f"Nu există date disponibile pentru  **{selected_month} {selected_year}**  privind importurile.")
else:
# Top 10 țări pentru importuri în coloana stângă
    with col1:
        st.subheader(f"Top 10 Țări - Importuri, {selected_month} {selected_year} ")
        df_top_import = df_month.sort_values(by="Importuri (mil. $)", ascending=False).head(10)
        other_import_value = df_month["Importuri (mil. $)"].sum() - df_top_import["Importuri (mil. $)"].sum()
        df_top_import = pd.concat([df_top_import, pd.DataFrame([{"Țară": "Altele", "Importuri (mil. $)": other_import_value}])], ignore_index=True)
        total_import = df_top_import["Importuri (mil. $)"].sum()
        df_top_import["Procent"] = (df_top_import["Importuri (mil. $)"] / total_import) * 100
        fig_pie_import = px.pie(df_top_import, names="Țară", values="Procent", title="Ponderea Top 10 Țări - Importuri", hole=0.4)
        st.plotly_chart(fig_pie_import, use_container_width=True)


df_top_export = df_month.sort_values(by="Exporturi (mil. $)", ascending=False).head(10)
if df_top_import.empty:
     st.warning(f"Nu există date disponibile pentru anul **{selected_month} {selected_year}** privind exporturile.")
else:
# Top 10 țări pentru exporturi în coloana dreaptă
    with col2:
        st.subheader(f"Top 10 Țări - Exporturi, {selected_month} {selected_year} ")
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
def format_value(value):
    return locale.format_string("%.1f", value / 1000, grouping=True)

locale.setlocale(locale.LC_NUMERIC)  # Setăm formatul pentru numere

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
total_trade_value = format_value(latest_data["Exporturi (mil. $)"] + latest_data["Importuri (mil. $)"])
export_change_value = format_value(export_change_abs)
import_change_value = format_value(import_change_abs)
trade_balance_value = format_value(trade_balance_change_abs)


def generate_description(selected_month, latest_data, previous_data):
    trade_balance_change_pct = (latest_data["Sold Comercial (mil. $)"] - previous_data["Sold Comercial (mil. $)"]) / abs(previous_data["Sold Comercial (mil. $)"]) * 100 if previous_data["Sold Comercial (mil. $)"] != 0 else 0
    export_change_pct = (latest_data["Exporturi (mil. $)"] - previous_data["Exporturi (mil. $)"]) / abs(previous_data["Exporturi (mil. $)"]) * 100 if previous_data["Exporturi (mil. $)"] != 0 else 0
    import_change_pct = (latest_data["Importuri (mil. $)"] - previous_data["Importuri (mil. $)"]) / abs(previous_data["Importuri (mil. $)"]) * 100 if previous_data["Importuri (mil. $)"] != 0 else 0

    return f"""
    Valoarea totală a schimburilor comerciale în {selected_month} a fost de **{format_value(latest_data["Exporturi (mil. $)"] + latest_data["Importuri (mil. $)"])} mil. dolari** în anul **{selected_year}**, 
    înregistrând o {'creștere' if trade_balance_change_pct > 0 else 'scădere'} de {abs(trade_balance_change_pct):.1f}% față de **aceeași perioadă** a anului trecut. 
    Exporturile s-au {'majorat' if export_change_pct > 0 else 'diminuat'} cu **{format_value(latest_data["Exporturi (mil. $)"] - previous_data["Exporturi (mil. $)"])} mil. dolari** ({export_change_pct:+.1f}%), 
    iar importurile s-au {'majorat' if import_change_pct > 0 else 'diminuat'} cu **{format_value(latest_data["Importuri (mil. $)"] - previous_data["Importuri (mil. $)"])} mil. dolari** ({import_change_pct:+.1f}%). 
    Deficitul balanței comerciale s-a {'majorat' if (latest_data["Sold Comercial (mil. $)"] - previous_data["Sold Comercial (mil. $)"]) > 0 else 'micșorat'} 
    cu **{format_value(latest_data["Sold Comercial (mil. $)"] - previous_data["Sold Comercial (mil. $)"])} mil. dolari.**
    """

# st.markdown(generate_description(selected_month, latest_data, previous_data))
# Text finish

# Step 2: Strip any extra whitespace from the strings
df_exports["Lună"] = df_exports["Lună"].str.strip()

# Step 3: Map the month names to numbers
df_exports["Lună"] = df_exports["Lună"].map(month_mapping)

# Step 4: Convert the column to integers
df_exports["Lună"] = df_exports["Lună"].astype(int)

# Convertim coloanele relevante
df_exports["An"] = df_exports["An"].astype(str)

df_exports["Lună"] = df_exports["Lună"].astype(str)

# Convertim valorile la format numeric
for col in ["Exporturi autohtone", "Reexporturi"]:
    df_exports[col] = pd.to_numeric(df_exports[col], errors='coerce').fillna(0)

# Sortăm după An și Lună pentru a păstra ordinea corectă
df_exports["Lună"] = df_exports["Lună"].astype(int)
df_exports = df_exports.sort_values(by=["An", "Lună"])




# Filtrare pentru anul selectat
df_exports_filtered = df_exports[df_exports["An"] == selected_year]

# Verificăm dacă există date pentru anul selectat
if df_exports_filtered.empty:
    st.warning(f"Nu există date disponibile pentru anul {selected_year} privind exporturile lunare autohtone și reexporturile de mărfuri străine.")
else:
    # Creăm graficul clustered bar chart cu separare pe ani
    fig_exp = px.bar(df_exports_filtered, x="Lună", y=["Exporturi autohtone", "Reexporturi"],
                     barmode="relative",
                     title=f"Exporturile lunare autohtone și reexporturile de mărfuri străine, {selected_year} (mil $)",
                     labels={"value": "Valoare (mil. $)", "variable": "Tip Export", "Lună": "Luna"},
                     color_discrete_map={"Exporturi autohtone": "#4C8BF5", "Reexporturi": "#A9C9E8"})

    # Ajustăm aspectul pentru un stil mai clar și ordonat
    fig_exp.update_layout(
        xaxis=dict(tickmode="linear", tickvals=list(range(1, 13))),  # Asigurăm că toate lunile sunt vizibile
        yaxis_title="Mil. $"
    )

    # Afișăm graficul
    st.plotly_chart(fig_exp, use_container_width=True)



# Curățăm și convertim coloana "An"
df_exp_lunar["An"] = df_exp_lunar["An"].astype(str).str.replace(",", "").astype(int)

# Asigură-te că `selected_year` este `int`
selected_year = int(selected_year)

# Aplică filtrarea
df_exports_filtered_Export = df_exp_lunar[df_exp_lunar["An"] == selected_year].copy()

# Verificăm câte luni sunt prezente în setul de date filtrat
num_months = df_exports_filtered_Export["Lună"].nunique()

if df_exports_filtered_Export.empty:
    st.warning(f"Nu există date disponibile pentru anul {selected_year} privind {selected_indicator}.")
elif num_months == 1:
    single_month = df_exports_filtered_Export["Lună"].iloc[0]
    # st.warning(f"Există date doar pentru luna {single_month} în anul {selected_year}.")

# Sortăm lunile corect
df_exports_filtered_Export["Sort_Index"] = df_exports_filtered_Export["Lună"].map(month_order)
df_exports_filtered_Export = df_exports_filtered_Export.sort_values(by="Sort_Index").drop(columns=["Sort_Index"])

# Creăm și afișăm graficul doar dacă există mai mult de o lună de date
if not df_exports_filtered_Export.empty:
    fig = px.bar(
        df_exports_filtered_Export, 
        x="Lună", 
        y=selected_indicator, 
        title=f"{selected_indicator} în {selected_year}",
        labels={selected_indicator: "Valoare (mil. $)"},
        barmode='relative'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Afișare tabel filtrat doar cu datele relevante
    st.subheader(f"Date {selected_indicator} {selected_year}")
    df_display = df_exports_filtered_Export[["An", "Lună", selected_indicator]]  # Selectăm doar coloanele relevante
    st.dataframe(df_display, use_container_width=True)



# Creăm un layout cu două coloane
col1, col2 = st.columns([4, 1])  # Jumătate-jumătate pentru text și grafic

# Filtrare date în funcție de luna selectată
df_filtered = df[df["Lună"] == selected_month]

# Grupăm datele după grupul de țări
df_countries_grouped = df_filtered.groupby("Grupă Țări")[["Exporturi (mil. $)", "Importuri (mil. $)"]].sum().reset_index()

# Calculăm totalul schimburilor comerciale pentru fiecare grupă
df_countries_grouped["Total Comerț"] = df_countries_grouped["Exporturi (mil. $)"] + df_countries_grouped["Importuri (mil. $)"] 

# Calculăm procentele și le rotunjim la cel mai apropiat număr întreg
df_countries_grouped["Procent"] = ((df_countries_grouped["Total Comerț"] / df_countries_grouped["Total Comerț"].sum()) * 100).round(0).astype(int)

# Crearea diagramei tip "donut" 
fig_donut = px.pie(df_countries_grouped, names="Grupă Țări", values="Procent",
                   hole=0.4,  
                   labels={"Grupă Țări": "Grupa de Țări"},
                   color_discrete_sequence=["#4C8BF5", "#A9C9E8", "#6C757D"])
total_exports = df_filtered["Exporturi (mil. $)"].sum() / 1000
total_imports = df_filtered["Importuri (mil. $)"].sum() / 1000
trade_deficit = total_exports - total_imports  # Deficitul comercial

# Adăugăm etichete personalizate cu procentaj + valoarea în milioane $
fig_donut.update_traces(
    textinfo="percent+label",
    hovertemplate="<b>%{label}</b><br>Procent: %{value}%<br>Valoare: %{customdata} mil. $",
    customdata=df_countries_grouped["Total Comerț"].round(0).astype(int)  
)

# Stil CSS pentru alinierea verticală a textului
st.markdown(
    """
    <style>
    .vertical-center {
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 10000%;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# Calculăm suma exporturilor autohtone pentru perioada selectată
exporturi_autohtone = df_exports_filtered["Exporturi autohtone"].sum()
reexporturi = df_exports_filtered["Reexporturi"].sum()


if df_countries_grouped.empty:
    st.warning("Nu există date pentru perioada selectată.")
    max_country_group = None  # Sau un fallback gol
else:
# COL 1 - Descrierea textului, aliniat vertical
    with col1:
        st.markdown('<div class="vertical-center" style="text-align: justify;">', unsafe_allow_html=True)
        
        st.subheader(f"Analiza schimburilor comerciale ({selected_month} {selected_year})")
        total_trade = df_countries_grouped["Total Comerț"].sum() / 1000
        max_country_group = df_countries_grouped.loc[df_countries_grouped["Total Comerț"].idxmax()]
        st.markdown(f"""
        Valoarea totală a schimburilor comerciale (X + M) în **{selected_month} {selected_year}** a fost de **{total_trade:,.1f} mil. dolari**. Exporturile au fost de **{total_exports:,.1f} mil. dolari**, iar importurile de **{total_imports:,.1f} mil. dolari**, determinând un **deficit comercial de {trade_deficit:,.1f} mil. dolari**.
        Cea mai mare pondere a schimburilor comerciale este deținută de:
        - **{max_country_group['Grupă Țări']}**, reprezentând **{max_country_group['Procent']}%** din total.
        - **Restul lumii** și **Statele CSI** constituind **{100 - max_country_group['Procent']}%** din schimburile comerciale.
        
      
      În anul **{selected_year}** exporturile de produse autohtone au fost de **{exporturi_autohtone:,.1f} mil. dolari** în, iar reexporturile de mărfuri străine au fost de **{reexporturi:,.1f} mil. dolari**. 

        """)
        st.markdown('</div>', unsafe_allow_html=True)

if df_countries_grouped.empty:
    st.warning("Alegeți o altă perioadă pentru a vizualiza datele.")
else:
    # COL 2 - Afișarea graficului
    with col2:
        st.plotly_chart(fig_donut, use_container_width=True)

# Definirea ordinii corecte pentru sortare
month_order = {
    "Ianuarie": 0,  # Facem "Ianuarie" prima
    "Ianuarie - Februarie": 1, "Ianuarie - Martie": 2, "Ianuarie - Aprilie": 3,
    "Ianuarie - Mai": 4, "Ianuarie - Iunie": 5, "Ianuarie - Iulie": 6, "Ianuarie - August": 7,
    "Ianuarie - Septembrie": 8, "Ianuarie - Octombrie": 9, "Ianuarie - Noiembrie": 10, "Ianuarie - Decembrie": 11
}

# Aplicăm mapping-ul pentru a avea valori numerice asociate perioadelor
df_total["Sort_Index"] = df_total["Perioadă"].map(month_order)

# Asigurăm că valorile nespecificate primesc un index mare pentru a fi plasate la final
df_total["Sort_Index"] = df_total["Sort_Index"].fillna(99)

# Sortare după index-ul definit (crescător, cu "Ianuarie" prima)
df_total = df_total.sort_values(by="Sort_Index", ascending=True).drop(columns=["Sort_Index"])

# Afișare grafic principal - Total agregat fără divizări
st.subheader(f"Evoluția {selected_indicator} (Perioadă - {selected_period})")
fig = px.bar(df_total, x="Perioadă", y=selected_indicator, title=f"{selected_indicator} în timp", 
             labels={selected_indicator: "Valoare (mil. $)"}, barmode='relative')
st.plotly_chart(fig, use_container_width=True)

# Filtrare pentru perioada selectată
df_grouped_filtered = df_grouped[df_grouped["Perioadă"] == selected_month ]

# Afișare tabel filtrat pe toată lățimea ecranului
st.subheader(f"Tabel **{selected_indicator} {selected_year}** - {selected_month}")  
if df_grouped_filtered.empty:
    st.warning(f"Nu există date pentru perioada selectată **{selected_month} {selected_year}.**")
st.dataframe(df_grouped_filtered, use_container_width=True)

# Eliminăm spațiile extra din coloana "Lună"
df_influenta["Lună"] = df_influenta["Lună"].str.strip()

# Aplicăm filtrarea corectă
df_influenta_filtered = df_influenta[
    (df_influenta["Lună"] == selected_month) & 
    (df_influenta["An"].astype(str) == str(selected_year))
]

# Dacă nu există date, afișăm o eroare clară
if df_influenta_filtered.empty:
    st.error(f" Nu sunt date pentru perioada selectată **{selected_month} {selected_year}.**")
    st.stop()

# Convertim "Grad" în numeric și eliminăm NaN
df_influenta_filtered["Grad"] = pd.to_numeric(df_influenta_filtered["Grad"], errors="coerce")
df_influenta_filtered = df_influenta_filtered.dropna(subset=["Grad"])

# Sortare pentru vizualizare corectă
df_influenta_filtered = df_influenta_filtered.sort_values(by="Grad", ascending=False)

# Creare diagramă cu bare orizontale
fig_influenta = px.bar(
    df_influenta_filtered,
    x="Grad",
    y="Denumire",
    orientation="h",
    title=f"Gradul de influență asupra exporturilor ({selected_month} {selected_year})",
    labels={"Grad": "Puncte procentuale (p.p.)", "Denumire": "Categorie de mărfuri"},
    color="Grad",
    color_continuous_scale="Blues_r",
    height=600
)

# Afișare grafic
st.plotly_chart(fig_influenta, use_container_width=True)
# Eliminăm spațiile extra din coloana "Lună"
df_influenta_Import["Lună"] = df_influenta_Import["Lună"].str.strip()

# Aplicăm filtrarea corectă
df_influenta_filtered_import = df_influenta_Import[
    (df_influenta_Import["Lună"] == selected_month) & 
    (df_influenta_Import["An"].astype(str) == str(selected_year))
]
# Dacă nu există date, afișăm un mesaj de eroare
if df_influenta_filtered_import.empty:
    st.error(f" Nu sunt date pentru perioada selectată **{selected_month} {selected_year}.**")
    st.stop()

# Convertim "Grad" în numeric și eliminăm NaN
df_influenta_filtered_import["Grad"] = pd.to_numeric(df_influenta_filtered_import["Grad"], errors="coerce")
df_influenta_filtered_import = df_influenta_filtered_import.dropna(subset=["Grad"])

# Sortare pentru vizualizare corectă
df_influenta_filtered_import = df_influenta_filtered_import.sort_values(by="Grad", ascending=False)

# Creare diagramă cu bare orizontale
fig_influenta_import = px.bar(
    df_influenta_filtered_import,
    x="Grad",
    y="Denumire",
    orientation="h",
    title=f"Gradul de influență asupra importurilor ({selected_month} {selected_year})",
    labels={"Grad": "Puncte procentuale (p.p.)", "Denumire": "Categorie de mărfuri"},
    color="Grad",
    color_continuous_scale="Blues_r",
    height=600
)

# Afișare grafic
st.plotly_chart(fig_influenta_import, use_container_width=True)



# Mapping între perioadă și foaia Excel
sheet_mapping = {
    "Ianuarie": "Import_NCM_I",
    "Ianuarie - Februarie": "Import_NCM_II",
    "Ianuarie - Martie": "Import_NCM_III",
    "Ianuarie - Aprilie": "Import_NCM_IV",
}

selected_sheet_name  = sheet_mapping.get(selected_month)

df_import_ncm_all = load_data()[6]  # sau alt index dacă ai modificat ordinea returnării

if isinstance(df_import_ncm_all, dict) and selected_sheet_name in df_import_ncm_all:
    df_import_ncm_luna = df_import_ncm_all[selected_sheet_name]
else:
    st.error(f"Nu s-au găsit date pentru perioada {selected_month}")
    st.stop()

# --- Extrage doar rândurile cu cifre romane împreună cu filtrul de lună ---
def is_roman(value):
    return bool(re.match(
        r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI)$",
        str(value).strip()
    ))

# --- Extractie grupe principale pe luna selectata ---
df_import_grupe = df_import_ncm_luna[df_import_ncm_luna["Cod"].apply(is_roman)].copy()
df_import_grupe["Denumire"] = df_import_grupe["Denumire"].str.strip()

# Conversie la mil. $
for col in ["2022", "2023", "2024", "2025"]:
    df_import_grupe[col] = pd.to_numeric(df_import_grupe[col], errors="coerce") / 1000

# Selectie grupe principale
st.subheader(f"Evoluția *importurilor* pe grupele principale de mărfuri în  **{selected_month}.**")
available_grupe = df_import_grupe["Denumire"].unique().tolist()
selected_grupe = st.multiselect("Selectează grupele de mărfuri:", options=available_grupe, default=available_grupe)

# Filtrare dupa selectie
df_import_grupe_filtered = df_import_grupe[df_import_grupe["Denumire"].isin(selected_grupe)]

# Reformatare pentru grafic
df_import_melt = df_import_grupe_filtered.melt(id_vars="Denumire", value_vars=["2022", "2023", "2024", "2025"],
                                                var_name="An", value_name="Importuri (mil. $)")
df_import_melt["An"] = df_import_melt["An"].astype(int).astype(str)

# Grafic importuri grupate
fig_import_grupe = px.bar(
    df_import_melt,
    x="An",
    y="Importuri (mil. $)",
    color="Denumire",
    barmode="group",
    title="Evoluția valorică a importurilor – Grupe principale",
    labels={"Denumire": "Grupă de mărfuri"}
)
st.plotly_chart(fig_import_grupe, use_container_width=True)

# Tabel aferent
st.dataframe(df_import_grupe_filtered.reset_index(drop=True), use_container_width=True)

# --- Ponderi si comparatii 2024/2025 ---
df_pondere = df_import_grupe_filtered.copy()
total_2024 = df_pondere["2024"].sum()
total_2025 = df_pondere["2025"].sum()
df_pondere["Pondere 2024 (%)"] = (df_pondere["2024"] / total_2024) * 100
df_pondere["Pondere 2025 (%)"] = (df_pondere["2025"] / total_2025) * 100
df_pondere["Diferență (p.p.)"] = df_pondere["Pondere 2025 (%)"] - df_pondere["Pondere 2024 (%)"]

# Reformatare pentru grafic
df_pondere_melt = df_pondere.melt(id_vars="Denumire", 
                                  value_vars=["Pondere 2024 (%)", "Pondere 2025 (%)"],
                                  var_name="An", value_name="Pondere (%)")

# Dicționar pentru scurtarea denumirilor
denumiri_scurtate = {
    "Animale vii si produse ale regnului animal": "Produse animale",
    "Produse ale regnului vegetal": "Produse vegetale",
    "Grasimi si uleiuri de origine animala sau vegetala si produse ale disocierii acestora; grasimi alimentare prelucrate; ceara de origine animala sau vegetala": "Grăsimi și uleiuri",
    "Produse ale industriei alimentare; bauturi, lichide alcoolice si otet; tutun si inlocuitori de tutun": "Alimente, băuturi, tutun",
    "Produse minerale": "Minerale",
    "Perle naturale sau de cultura, pietre pretioase sau semipretioase, metale pretioase, metale placate sau dublate cu metale pretioase si articole din aceste materiale; imitatii de bijuterii; monede": "Perle și bijuterii",
    "Masini si aparate, echipamente electrice si parti ale acestora; aparate de inregistrat sau de reprodus sunetul, aparate de inregistrat sau de reprodus imagini si sunet de televiziune si parti si accesorii ale acestor aparate": "Mașini și echipamente electrice",
    "Incaltaminte; obiecte de acoperit capul, umbrele; umbrele de ploaie; umbrele de soare; bastoane-scaun;  bice; cravase si parti ale acestora; pene si puf prelucrate si articole din acestea; flori artificiale; articole din par uman": "Încălțăminte și accesorii",
    "Articole din piatra, ipsos, ciment, azbest, mica sau din materiale similare; produse ceramice; sticla si articole din sticla": "Articole din piatră și sticlă",
    "Pasta din lemn sau din alte materiale fibroase celulozice; hirtie sau carton reciclabile (deseuri si maculatura); hirtie, carton si articole din acestea": "Pastă din lemn, hârtie și accesorii",
    "Produse ale industriei chimice sau ale industriilor conexe": "Industrie chimică",
    "Materiale plastice si articole din material plastic; cauciuc si articole din cauciuc": "Plastice și cauciuc",
    "Piei brute, piei finite, piei cu blana si produse din acestea; articole de curelarie si de selarie; articole de voiaj, genti de mina si articole similare; articole din intestine de animale (altele decit cele de la viermii de matase)": "Piei și blănuri",
    "Lemn si articole din lemn, carbune de lemn si articole din lemn; pluta si articole din pluta; articole din paie, alfa si alte materiale de impletit; cosuri si alte impletituri": "Lemn și articole din lemn",
    "Instrumente si aparate optice, fotografice sau cinematografice, de masura, de control sau de precizie; instrumente si aparate medico-chirurgicale; ceasornicarie; instrumente muzicale; parti si accesorii ale acestora": "Instrumente și aparate optice",
    "Vehicule, aparate de zbor (aeronave), instalatii plutitoare si echipamente auxiliare": "Vehicule",
    "IMPORT - total, mii dolari SUA": "Import total"
}
df_import_grupe_filtered["Denumire"] = df_import_grupe_filtered["Denumire"].replace(denumiri_scurtate)
df_pondere["Denumire"] = df_pondere["Denumire"].replace(denumiri_scurtate)
df_pondere_melt["Denumire"] = df_pondere_melt["Denumire"].replace(denumiri_scurtate)

# Grafic comparativ pondere
st.subheader(f"Ponderea fiecărei grupe în totalul importurilor: 2024 vs 2025")
fig_pondere = px.bar(
    df_pondere_melt,
    y="Denumire",
    x="Pondere (%)",
    color="An",
    orientation="h",
    barmode="group",
    title="Compararea ponderii grupelor în totalul importurilor – 2024 vs 2025",
    labels={"Denumire": "Grupă de mărfuri"}
)
fig_pondere.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_pondere, use_container_width=True)


# Tabel final
st.subheader("Tabel: Pondere 2024 - 2025")
df_pondere_display = df_pondere[["Denumire", "Pondere 2024 (%)", "Pondere 2025 (%)"]].round(2)
st.dataframe(df_pondere_display.reset_index(drop=True), use_container_width=True)


# def load_forecast_data():
#     path = "data/Model.xlsx"  # sau 'data/Model.xlsx' dacă fișierul e într-un folder separat
#     df_raw = pd.read_excel(path, sheet_name="EX_IM_gap model", header=None)
# # Lista completă de indicatori de utilizat
#     indicatori = [
#         "Real exports, mn USD",
#         "Real Imports, mn USD",  # ← această linie lipsea
#         "Foreign demand, index",
#         "REER, index (increase =appreciation)",
#         "Exchange rate",
#         "Real investment, mn MDL"
#     ]

#     data = {}
#     for indicator in indicatori:
#         # Identifică rândul în care apare fiecare indicator
#         idx = df_raw[df_raw[0] == indicator].index[0]
#         # Extrage valorile din coloanele 2 până la 26 (adică ani 2000–2024)
#         values = df_raw.loc[idx, 2:26].values
#         data[indicator] = pd.to_numeric(values, errors="coerce")

#     # Construim DataFrame cu indexul anilor 2000–2024
#     df = pd.DataFrame(data)
#     df.index = list(range(2000, 2000 + len(df)))
#     df.index.name = "An"
#     return df

# # === Afișare prognoză în aplicație ===
# st.subheader("Prognoza Exporturi și Importuri (2025–2026)")
# df_model = load_forecast_data()

# # Eliminăm valorile lipsă
# df_clean_exp = df_model.dropna(subset=["Real exports, mn USD"])
# X_exp = df_clean_exp[["Foreign demand, index", "REER, index (increase =appreciation)",
#                       "Exchange rate", "Real investment, mn MDL"]]
# y_exp = df_clean_exp["Real exports, mn USD"]

# df_clean_imp = df_model.dropna(subset=["Real Imports, mn USD"])
# X_imp = df_clean_imp[["Foreign demand, index", "REER, index (increase =appreciation)",
#                       "Exchange rate", "Real investment, mn MDL"]]
# y_imp = df_clean_imp["Real Imports, mn USD"]

# # Modele OLS
# X_exp = sm.add_constant(X_exp)
# X_imp = sm.add_constant(X_imp)
# model_exp = sm.OLS(y_exp, X_exp).fit()
# model_imp = sm.OLS(y_imp, X_imp).fit()

# # Creșteri medii pentru extrapolare
# growth = df_model.pct_change().mean()
# last_values = df_model.iloc[-1]

# # Prognozăm valorile explicative și rezultatele pentru 2025–2026
# future_rows = []
# for year in [2025, 2026]:
#     new_row = last_values * (1 + growth)
#     X_new_exp = sm.add_constant(new_row[X_exp.columns[1:]].values.reshape(1, -1), has_constant="add")
#     X_new_imp = sm.add_constant(new_row[X_imp.columns[1:]].values.reshape(1, -1), has_constant="add")
#     new_row["Real exports, mn USD"] = model_exp.predict(X_new_exp)[0]
#     new_row["Real Imports, mn USD"] = model_imp.predict(X_new_imp)[0]
#     future_rows.append(new_row)
#     last_values = new_row

# # Construim DataFrame cu prognoza
# forecast_df = pd.DataFrame(future_rows, index=[2025, 2026])
# forecast_display = forecast_df[["Real exports, mn USD", "Real Imports, mn USD"]].round(1)

# # Afișăm tabelul
# st.dataframe(forecast_display, use_container_width=True)

# # Grafic interactiv
# fig_forecast = px.line(
#     forecast_display.reset_index(),
#     x="index", y=forecast_display.columns,
#     markers=True,
#     title="Prognoza Exporturi și Importuri 2025–2026",
#     labels={"index": "An", "value": "Valoare (mil. USD)", "variable": "Indicator"}
# )
# # st.plotly_chart(fig_forecast, use_container_width=True)


# import plotly.graph_objects as go

# # Asumăm că df_model deja există și conține coloanele necesare

# # Reconstruim modelul dacă nu există
# X_exp = sm.add_constant(df_model[["Foreign demand, index", "REER, index (increase =appreciation)",
#                                   "Exchange rate", "Real investment, mn MDL"]])
# y_exp = df_model["Real exports, mn USD"]
# model_exp = sm.OLS(y_exp, X_exp).fit()

# X_imp = sm.add_constant(df_model[["Foreign demand, index", "REER, index (increase =appreciation)",
#                                   "Exchange rate", "Real investment, mn MDL"]])
# y_imp = df_model["Real Imports, mn USD"]
# model_imp = sm.OLS(y_imp, X_imp).fit()

# # Calculăm creșterea medie
# growth = df_model.pct_change().mean()
# last_values = df_model.iloc[-1]
# future_rows = []
# # Extindem prognoza până în 2028
# for year in [2025, 2026, 2027, 2028]:
#     new_row = last_values * (1 + growth)
#     X_future_exp = sm.add_constant(new_row[X_exp.columns[1:]].values.reshape(1, -1), has_constant="add")
#     X_future_imp = sm.add_constant(new_row[X_imp.columns[1:]].values.reshape(1, -1), has_constant="add")
#     new_row["Real exports, mn USD"] = model_exp.predict(X_future_exp)[0]
#     new_row["Real Imports, mn USD"] = model_imp.predict(X_future_imp)[0]
#     future_rows.append(new_row)
#     last_values = new_row

# # DataFrame cu prognoze
# forecast_df = pd.DataFrame(future_rows, index=[2025, 2026, 2027, 2028])
# forecast_df = forecast_df[["Real exports, mn USD", "Real Imports, mn USD"]]

# # Combinăm istoric și prognoză
# df_all = pd.concat([df_model[["Real exports, mn USD", "Real Imports, mn USD"]], forecast_df])
# df_all.index = df_all.index.astype(str)  # convertește anii în text pentru axa X

# fig = go.Figure()

# # Exporturi: istoric
# fig.add_trace(go.Scatter(
#     x=df_all.index[:25],  # 2000–2024
#     y=df_all["Real exports, mn USD"].iloc[:25],
#     mode='lines+markers',
#     name='Exporturi (istoric)',
#     line=dict(color='blue', dash='solid')
# ))

# # Exporturi: prognoză
# fig.add_trace(go.Scatter(
#     x=df_all.index[25:],  # 2025–2028
#     y=df_all["Real exports, mn USD"].iloc[25:],
#     mode='lines+markers',
#     name='Exporturi (prognoză)',
#     line=dict(color='blue', dash='dash')
# ))

# # Importuri: istoric
# fig.add_trace(go.Scatter(
#     x=df_all.index[:25],
#     y=df_all["Real Imports, mn USD"].iloc[:25],
#     mode='lines+markers',
#     name='Importuri (istoric)',
#     line=dict(color='green', dash='solid')
# ))

# # Importuri: prognoză
# fig.add_trace(go.Scatter(
#     x=df_all.index[25:],
#     y=df_all["Real Imports, mn USD"].iloc[25:],
#     mode='lines+markers',
#     name='Importuri (prognoză)',
#     line=dict(color='green', dash='dash')
# ))

# fig.update_layout(
#     title="Evoluția și Prognoza Exporturilor și Importurilor (2000–2028)",
#     xaxis_title="An",
#     yaxis_title="Valoare (mil. USD)",
#     xaxis=dict(type='category'),
#     legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
# )

# st.plotly_chart(fig, use_container_width=True)



st.markdown("""
    <hr style='border: 1px solid #ddd;'>
    <p style='text-align: center; color: grey;'>© 2025 APM. Toate drepturile rezervate.</p>
""", unsafe_allow_html=True)