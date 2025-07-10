import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from io import BytesIO
from pymongo import MongoClient
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Datele oficiale ale BNS")

# === Sidebar ===
st.sidebar.header("Selectare perioadă")
frecventa = st.sidebar.selectbox("Frecvența datelor", ["Lunar", "Trimestrial", "Anual"])

url_map = {
    "Lunar": "https://statbank.statistica.md/PxWeb/api/v1/ro/40%20Statistica%20economica/21%20EXT/EXT010/serii%20lunare",
    "Trimestrial": "https://statbank.statistica.md/PxWeb/api/v1/ro/40%20Statistica%20economica/21%20EXT/EXT010/serii%20trimestriale",
    "Anual": "https://statbank.statistica.md/PxWeb/api/v1/ro/40%20Statistica%20economica/21%20EXT/EXT010/serii%20anuale"
}
url_base_dir = url_map[frecventa]

# === Alegere serie ===
try:
    res = requests.get(url_base_dir)
    if res.status_code == 200:
        files = res.json()
        fisier_optiuni = {f["text"]: f["id"] for f in files}
        fisier_selectat = st.sidebar.selectbox("Selectează fișierul", list(fisier_optiuni.keys()))
        fisier_id = fisier_optiuni[fisier_selectat]
        url_base = f"{url_base_dir}/{fisier_id}"
    else:
        st.error(f"Eroare la accesarea directorului: {res.status_code}")
        st.stop()
except Exception as e:
    st.error(f"Eroare la accesarea directorului: {e}")
    st.stop()

# === Metadate și selectare variabile ===
@st.cache_data
def get_metadata(url):
    r = requests.get(url)
    if r.status_code == 200:
        try:
            return r.json()
        except:
            return {}
    return {}

metadata = get_metadata(url_base)

if not metadata or "variables" not in metadata:
    st.warning("Nu s-au putut încărca variabilele pentru acest fișier.")
    st.stop()

st.sidebar.header("Filtre disponibile")
dimensiuni = {}
coduri_dim = {}

for dim in metadata["variables"]:
    nume = dim["text"]
    cod = dim["code"]
    valori = dim["values"]
    etichete = dim["valueTexts"]
    optiuni = dict(zip(valori, etichete))
    dimensiuni[nume] = optiuni
    coduri_dim[nume] = cod

selectii = {}
for nume_dim, optiuni in dimensiuni.items():
    chei = list(optiuni.keys())
    etichete = list(optiuni.values())
    selectie = st.sidebar.multiselect(nume_dim, etichete, default=etichete[:1])
    valori_selectate = [chei[etichete.index(s)] for s in selectie]
    if valori_selectate:
        selectii[nume_dim] = valori_selectate

# ===  POST ===
payload = {"query": [], "response": {"format": "json-stat2"}}
for nume_dim, cod in coduri_dim.items():
    valori = selectii.get(nume_dim, list(dimensiuni[nume_dim].keys())[:1])
    payload["query"].append({
        "code": cod,
        "selection": {"filter": "item", "values": valori}
    })
# === Afișare date ===
if st.sidebar.button("Afișează datele"):
    r = requests.post(url_base, json=payload)
    if r.status_code == 200:
        try:
            data = r.json()
            valori = data["value"]
            categorii = [list(data["dimension"][dim]["category"]["label"].values())
                         for dim in data["dimension"] if dim not in ["id", "size"]]
            index = pd.MultiIndex.from_product(categorii,
                                               names=[dim for dim in data["dimension"] if dim not in ["id", "size"]])
            df = pd.DataFrame(valori, index=index, columns=["Valoare"]).reset_index()

            st.success("Date preluate cu succes!")
           
            # Afișează denumirea și ultima dată de actualizare în format european
            fisier_info = next((f for f in files if f["id"] == fisier_id), None)
            if fisier_info:
                denumire = fisier_info["text"]
                raw_date = fisier_info.get("updated", "")[:10]
                try:
                    parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
                    ultima_data = parsed_date.strftime("%d.%m.%Y")
                except:
                    ultima_data = "n/a"
                st.markdown(f"### {denumire}")
                st.markdown(f"**Ultima actualizare:** `{ultima_data}`")
            st.dataframe(df, use_container_width=True)
            
            # Grafic
            col_timp = next((col for col in df.columns if any(x in col.lower() for x in ["an", "lun", "trimestru", "perioad"])), None)
            if col_timp:
                fig = px.line(df, x=col_timp, y="Valoare", color=df.columns[0], markers=True,
                              title="Evoluția indicatorului")
                st.plotly_chart(fig, use_container_width=True)

            # Export Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name="Date")
            st.download_button("Descarcă Excel", output.getvalue(),
                               file_name=f"{fisier_id}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            st.error(f"Eroare la procesarea datelor: {str(e)}")
    else:
        st.error(f"Eroare API (POST): {r.status_code}")

# === Opțional: Salvare în MongoDB ===
st.sidebar.markdown("---")
salvare_format = st.sidebar.radio("Salvează în:", ["Excel", "MongoDB"])
btn = st.sidebar.button("Afișează și salvează datele")

if btn:
    r = requests.post(url_base, json=payload)
    if r.status_code == 200:
        try:
            data = r.json()
            valori = data["value"]
            categorii = [list(data["dimension"][dim]["category"]["label"].values())
                         for dim in data["dimension"] if dim not in ["id", "size"]]
            index = pd.MultiIndex.from_product(categorii,
                                               names=[dim for dim in data["dimension"] if dim not in ["id", "size"]])
            df = pd.DataFrame(valori, index=index, columns=["Valoare"]).reset_index()

            st.dataframe(df, use_container_width=True)

            if salvare_format == "Excel":
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="Date")
                st.download_button("Descarcă Excel", output.getvalue(),
                                   file_name="exporturi_importuri.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            elif salvare_format == "MongoDB":
                client = MongoClient("mongodb://localhost:27017/")
                db = client["statistica"]
                collection = db["exporturi_importuri"]
                collection.insert_many(df.to_dict(orient="records"))
                st.success("Datele au fost salvate în MongoDB!")
        except Exception as e:
            st.error(f"Eroare la procesare: {str(e)}")
    else:
        st.error(f"Eroare API (POST): {r.status_code}")
