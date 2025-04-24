import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import load_data
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
        <h1 style='color: #1f4e79;'> Principalii Indicatorii macroeconomici</h1>
        <p><strong>Analiza și Prognozare Macroeconomică</strong></p>
         <p style='text-align: justify;'>Această pagină oferă o <strong>monitorizare și analiză</strong> a situației macroeconomice din Republica Moldova, prezentând informații despre <strong>importuri, 
         exporturi și balanța comercială</strong>. Scopul principal este <strong>informarea factorilor de decizie</strong> - conducerea ministerului, instituțiile de stat, organizațiile internaționale și publicul larg.
          Prin analiza datelor comerciale și prognozele economice pe termen mediu, contribuim la eficientizarea procesului de luare a deciziilor, inclusiv la <strong>elaborarea Cadrului Bugetar pe 
          Termen Mediu și a Legii bugetului de stat</strong>.</p>
    """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# Încărcarea datelor
df, df_exports, df_influenta, df_influenta_Import, df_exp_lunar, df_exp_imp_total  = load_data()

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



# Cele 4 diagrame Start

# Date PIB
df_pib_growth = pd.DataFrame({
    'An':             ['2020', '2021', '2022', '2023', '2024'],
    'Creștere PIB (%)': [-8.3, 13.9, -4.6, 0.4,0.1]
})
# Inflație 
df_inflatie = pd.DataFrame({
    'An': ['2020', '2021', '2022', '2023', '2024'],
    'Rata Inflației (%)': [3.8, 5.1, 28.7, 13.4, 4.7]
})

selected_year_int = int(selected_year)

# Date Comerț Internațional
df_comert = pd.DataFrame({
    'An': [selected_year_int - 1, selected_year_int],
    'Exporturi (mil. $)': [4048.6, 3555.1],
    'Importuri (mil. $)': [8675.3, 9065.2],
    'Deficit Comercial (mil. $)': [-4626.7, -5510.1]
})

# Date Rata Dobânzii
df_dobanda = pd.DataFrame({
    'Perioada': ['2022-04-08', '2022-05-12', '2023-02-07', '2023-03-20', '2023-05-11', '2023-06-20', '2023-07-11', '2024-02-06', '2024-03-21',  '2024-05-07', '2025-01-10', '2025-02-10'], 
    'Rata de Bază (%)': [21.5, 20, 17, 14, 10, 6,4.75, 4.25, 3.75,3.6, 5.6, 6.5]
})

selected_row = df_exp_imp_total.iloc[-1]
deficit_val = selected_row["Sold Comercial (mil. $)"]


# Layout compact cu 4 coloane
col1, col2, col3, col4 = st.columns(4)



with col1:
        st.subheader("Comerț Internațional")
        st.metric(label=f"Deficit **{selected_month} {selected_year}**", value=f"{deficit_val:,.1f} mil. $")
        fig_comert = px.bar(df_comert, x="An", y=["Exporturi (mil. $)", "Importuri (mil. $)"], barmode='group', title="")
        fig_comert.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_comert, use_container_width=True)

    

# Diagrama Inflației
with col2:
    st.subheader("Rata medie a inflației")
    st.metric(label="Inflația 2024", value="4.7%")
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
    st.metric(label="10 Ian 2025", value="6.5%")
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
col1, col2 = st.columns([1, 1])  # Jumătate-jumătate pentru text și grafic

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
        st.markdown('<div class="vertical-center">', unsafe_allow_html=True)
        
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










# Filtrare pentru perioada selectată
df_grouped_filtered = df_grouped[df_grouped["Perioadă"] == selected_month]

# Afișare tabel filtrat pe toată lățimea ecranului
st.subheader("Tabel Date")
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

st.markdown("""
    <hr style='border: 1px solid #ddd;'>
    <p style='text-align: center; color: grey;'>© 2025 APM. Toate drepturile rezervate.</p>
""", unsafe_allow_html=True)