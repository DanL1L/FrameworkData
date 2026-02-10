# app_bns_pxweb.py
# ------------------------------------------------------------
# Streamlit – Acces date BNS (PX-Web / Statbank)
# + Fix 429 (Too Many Requests): cache + retry/backoff + Session
# + Salvare automată (UPSERT) pentru Lunar: Exporturi/Importuri/Balanța comercială
#   în fișierul DAta.xlsx -> foaia Exp_Lunar (An, Lună, Exporturi, Importuri, Sold)
# + Debug: afișează calea exactă unde se scrie + previzualizare după salvare
# ------------------------------------------------------------

import time
import random
from io import BytesIO
from datetime import datetime
from pathlib import Path
import unicodedata

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# =========================
# CONFIG UI
# =========================
st.set_page_config(layout="wide")
st.title("Datele oficiale ale BNS")

# =========================
# EXCEL TARGET (Exp_Lunar)
# =========================
EXCEL_DATA_FILE = Path("data/Data.xlsx")  # ajustează dacă e în alt folder (ex: Path("data/DAta.xlsx"))
EXCEL_SHEET_EXP = "Exp_Lunar"

# =========================
# HTTP SESSION + RETRY
# =========================
SESSION = requests.Session()

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Streamlit PX-Web client)",
    "Accept": "application/json",
}

def get_with_retry(url: str, retries: int = 6, timeout: int = 30) -> requests.Response:
    """GET cu retry + exponential backoff pentru 429."""
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
            last = r
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                wait = (2 ** i) + random.random()
                time.sleep(wait)
                continue
            return r
        except requests.RequestException:
            wait = (2 ** i) + random.random()
            time.sleep(wait)
            last = None
    if last is not None:
        return last
    raise RuntimeError("Eroare rețea: nu s-a putut efectua GET după retry-uri.")

def post_with_retry(url: str, payload: dict, retries: int = 6, timeout: int = 60) -> requests.Response:
    """POST cu retry + exponential backoff pentru 429."""
    last = None
    for i in range(retries):
        try:
            r = SESSION.post(url, json=payload, timeout=timeout, headers=DEFAULT_HEADERS)
            last = r
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                wait = (2 ** i) + random.random()
                time.sleep(wait)
                continue
            return r
        except requests.RequestException:
            wait = (2 ** i) + random.random()
            time.sleep(wait)
            last = None
    if last is not None:
        return last
    raise RuntimeError("Eroare rețea: nu s-a putut efectua POST după retry-uri.")

# =========================
# PX-WEB DIRECTORY ENDPOINTS
# =========================
url_map = {
    "Lunar": "https://statbank.statistica.md/PxWeb/api/v1/ro/40%20Statistica%20economica/21%20EXT/EXT010/serii%20lunare",
    "Trimestrial": "https://statbank.statistica.md/PxWeb/api/v1/ro/40%20Statistica%20economica/21%20EXT/EXT010/serii%20trimestriale",
    "Anual": "https://statbank.statistica.md/PxWeb/api/v1/ro/40%20Statistica%20economica/21%20EXT/EXT010/serii%20anuale",
}

# =========================
# CACHED CALLS
# =========================
@st.cache_data(ttl=3600, show_spinner=False)
def list_directory(url_base_dir: str) -> list:
    """Listează tabelele dintr-un director PX-Web. Cache 1 oră."""
    r = get_with_retry(url_base_dir)
    if r.status_code != 200:
        raise RuntimeError(f"Directory error {r.status_code}: {r.text[:300]}")
    return r.json()

@st.cache_data(ttl=3600, show_spinner=False)
def get_metadata(url_table: str) -> dict:
    """Metadate pentru un tabel PX-Web. Cache 1 oră."""
    r = get_with_retry(url_table)
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return {}
    return {}

def detect_time_column(cols):
    """Detectează coloana timp (an/lună/trimestru/perioadă) din dataframe."""
    for col in cols:
        c = str(col).lower()
        if any(x in c for x in ["an", "ani", "luna", "luni", "lun", "trimestru", "perioad", "quarter", "month", "year", "time"]):
            return col
    return None

# =========================
# TEXT NORMALIZATION (diacritice safe)
# =========================
def _norm(s: str) -> str:
    """lower + remove diacritics + trim"""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s

# =========================
# SALVARE Exp_Lunar -> DAta.xlsx (UPSERT)
# =========================
def save_exp_lunar_to_excel(df_px: pd.DataFrame, excel_path: Path, sheet_name: str = "Exp_Lunar"):
    """
    Așteaptă df_px cu rânduri tip:
      Indicatori | Grupe de tari | Ani | Unitatea de masura | Luni | Valoare
    și salvează în Excel în format:
      An | Lună | Exporturi (mil. $) | Importuri (mil. $) | Sold Comercial (mil. $)
    cu upsert după (An, Lună).
    """
    if df_px.empty:
        st.warning("Nu am date de salvat (df gol).")
        return

    # Debug path
    st.info(f"Scriere în fișier: {excel_path.resolve()} | foaia: {sheet_name}")

    # Detect columns
    col_ind = next((c for c in df_px.columns if "indicator" in _norm(c)), None)
    col_year = next((c for c in df_px.columns if _norm(c) in ["ani", "an", "year"]), None)
    col_month = next((c for c in df_px.columns if _norm(c) in ["luni", "luna", "month"]), None)

    if not col_ind or not col_year or not col_month or "Valoare" not in df_px.columns:
        st.error(
            "Nu pot identifica coloanele necesare.\n"
            f"Am găsit: Indicator={col_ind}, An={col_year}, Lună={col_month}, Valoare={'Valoare' in df_px.columns}"
        )
        return

    dfw = df_px.copy()

    # Filter Total (if exists)
    col_group = next((c for c in dfw.columns if "grupe" in _norm(c) and "tari" in _norm(c)), None)
    if col_group:
        dfw = dfw[dfw[col_group].astype(str).apply(_norm).str.contains("total", na=False)]

    # Normalize indicator names
    dfw["_ind_norm"] = dfw[col_ind].astype(str).apply(_norm)

    # Keep wanted indicators (robust)
    wanted = {"exporturi", "importuri", "balanta comerciala"}
    dfw = dfw[dfw["_ind_norm"].isin(wanted)].copy()

    if dfw.empty:
        st.warning("În selecția curentă nu există rânduri pentru Exporturi/Importuri/Balanța comercială (după filtrare).")
        st.write("Indicatori disponibili (normalizați):", sorted(set(df_px[col_ind].astype(str).apply(_norm))))
        return

    # numeric year
    dfw[col_year] = pd.to_numeric(dfw[col_year], errors="coerce")
    dfw = dfw.dropna(subset=[col_year, col_month])

    # pivot (An, Lună) -> indicatori
    pivot = (
        dfw.pivot_table(index=[col_year, col_month], columns="_ind_norm", values="Valoare", aggfunc="sum")
        .reset_index()
    )

    pivot = pivot.rename(columns={
        col_year: "An",
        col_month: "Lună",
        "exporturi": "Exporturi (mil. $)",
        "importuri": "Importuri (mil. $)",
        "balanta comerciala": "Sold Comercial (mil. $)",
    })

    needed = ["An", "Lună", "Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]
    for c in needed:
        if c not in pivot.columns:
            pivot[c] = pd.NA
    pivot = pivot[needed].copy()

    pivot["An"] = pd.to_numeric(pivot["An"], errors="coerce").astype("Int64")
    pivot = pivot.dropna(subset=["An", "Lună"])

    if pivot.empty:
        st.warning("Pivotul a ieșit gol (nu am An/Lună valide).")
        return

    # Read existing
    if excel_path.exists():
        try:
            existing = pd.read_excel(excel_path, sheet_name=sheet_name)
        except Exception:
            existing = pd.DataFrame(columns=needed)
    else:
        existing = pd.DataFrame(columns=needed)

    # Normalize existing
    if "An" in existing.columns:
        existing["An"] = pd.to_numeric(existing["An"], errors="coerce").astype("Int64")
    else:
        existing["An"] = pd.Series(dtype="Int64")
    if "Lună" not in existing.columns:
        existing["Lună"] = pd.NA

    # Upsert by (An, Lună)
    key_new = set((int(a), str(l)) for a, l in zip(pivot["An"], pivot["Lună"]))

    if not existing.empty:
        keep_mask = ~existing.apply(
            lambda r: ((int(r["An"]) if pd.notna(r["An"]) else -1), str(r["Lună"])) in key_new,
            axis=1
        )
        existing = existing[keep_mask].copy()

    combined = pd.concat([existing, pivot], ignore_index=True)

    # Optional: calendar sorting for Romanian months
    month_order = {
        "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4, "mai": 5, "iunie": 6,
        "iulie": 7, "august": 8, "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12
    }
    combined["_m"] = combined["Lună"].astype(str).apply(_norm).map(month_order)
    combined = combined.sort_values(["An", "_m", "Lună"], kind="stable").drop(columns=["_m"])

    # Write excel (file must be closed)
    try:
        if excel_path.exists():
            with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                combined.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                combined.to_excel(writer, sheet_name=sheet_name, index=False)
    except PermissionError:
        st.error(" Nu pot scrie în Excel: fișierul este deschis/blocat. Închide Data.xlsx și încearcă din nou.")
        return

    st.success(f"Salvat în {excel_path.name} → foaia '{sheet_name}' (upsert după An+Lună).")
    st.subheader("Previzualizare foaia Exp_Lunar (după salvare)")
    st.dataframe(combined, use_container_width=True)

# =========================
# SIDEBAR – SELECT PERIOD/FREQUENCY
# =========================
st.sidebar.header("Selectare perioadă")
frecventa = st.sidebar.selectbox("Frecvența datelor", ["Lunar", "Trimestrial", "Anual"])
url_base_dir = url_map[frecventa]

# Load list one time (avoid 429)
if "files_cache" not in st.session_state:
    st.session_state["files_cache"] = None
if "last_dir" not in st.session_state:
    st.session_state["last_dir"] = None

st.sidebar.caption("Recomandat: încarcă lista o singură dată (evită 429).")

if st.sidebar.button("Încarcă lista de fișiere"):
    try:
        st.session_state["files_cache"] = list_directory(url_base_dir)
        st.session_state["last_dir"] = url_base_dir
        st.sidebar.success("Lista de fișiere a fost încărcată.")
    except Exception as e:
        st.sidebar.error(f"Eroare la accesarea directorului: {e}")

if st.session_state["last_dir"] != url_base_dir:
    st.session_state["files_cache"] = None

files = st.session_state["files_cache"]
if not files:
    st.info("Selectează frecvența și apasă «Încarcă lista de fișiere».")
    st.stop()

# =========================
# SELECT TABLE
# =========================
fisier_optiuni = {f["text"]: f["id"] for f in files if "text" in f and "id" in f}
fisier_selectat = st.sidebar.selectbox("Selectează fișierul", list(fisier_optiuni.keys()))
fisier_id = fisier_optiuni[fisier_selectat]
url_base = f"{url_base_dir}/{fisier_id}"

# =========================
# METADATA & FILTERS
# =========================
metadata = get_metadata(url_base)
if not metadata or "variables" not in metadata:
    st.warning("Nu s-au putut încărca variabilele pentru acest fișier.")
    st.stop()

st.sidebar.header("Filtre disponibile")

dimensiuni = {}   # {nume_dim: {value_code: value_label}}
coduri_dim = {}   # {nume_dim: code_dim}

for dim in metadata["variables"]:
    nume = dim.get("text", "")
    cod = dim.get("code", "")
    valori = dim.get("values", [])
    etichete = dim.get("valueTexts", [])
    optiuni = dict(zip(valori, etichete))
    if nume and cod and optiuni:
        dimensiuni[nume] = optiuni
        coduri_dim[nume] = cod

selectii = {}
for nume_dim, optiuni in dimensiuni.items():
    chei = list(optiuni.keys())
    etichete = list(optiuni.values())

    # default: prima opțiune (ca să nu trimiți payload mare)
    default_labels = etichete[:1] if len(etichete) > 0 else []
    selectie_labels = st.sidebar.multiselect(nume_dim, etichete, default=default_labels)

    valori_selectate = [chei[etichete.index(lbl)] for lbl in selectie_labels if lbl in etichete]
    if valori_selectate:
        selectii[nume_dim] = valori_selectate

# =========================
# BUILD PAYLOAD
# =========================
payload = {"query": [], "response": {"format": "json-stat2"}}

for nume_dim, cod in coduri_dim.items():
    values = selectii.get(nume_dim, list(dimensiuni[nume_dim].keys())[:1])
    payload["query"].append({
        "code": cod,
        "selection": {"filter": "item", "values": values}
    })

# =========================
# MAIN ACTION
# =========================
if st.sidebar.button("Afișează datele"):
    r = post_with_retry(url_base, payload)

    if r.status_code != 200:
        st.error(f"Eroare API (POST): {r.status_code} | {r.text[:300]}")
        st.stop()

    try:
        data = r.json()

        if "value" not in data or "dimension" not in data:
            st.error("Răspuns API invalid: lipsesc câmpuri necesare ('value'/'dimension').")
            st.stop()

        valori = data["value"]

        dim_order = [d for d in data["dimension"].keys() if d not in ["id", "size"]]

        categorii = []
        for dim in dim_order:
            cat = data["dimension"][dim]["category"]
            labels = list(cat["label"].values())
            categorii.append(labels)

        index = pd.MultiIndex.from_product(categorii, names=dim_order)
        df = pd.DataFrame(valori, index=index, columns=["Valoare"]).reset_index()

        st.success("Date preluate cu succes!")

        fisier_info = next((f for f in files if f.get("id") == fisier_id), None)
        if fisier_info:
            denumire = fisier_info.get("text", fisier_id)
            raw_date = (fisier_info.get("updated", "") or "")[:10]

            status = "❓"
            ultima_data = "n/a"
            try:
                parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
                ultima_data = parsed_date.strftime("%d.%m.%Y")
                zile_diferenta = (datetime.today() - parsed_date).days
                status = "🟢" if zile_diferenta <= 30 else "🔴"
            except Exception:
                pass

            st.markdown(f"### {denumire}")
            st.markdown(f"**Ultima actualizare:** `{ultima_data}`  {status}")

        st.dataframe(df, use_container_width=True)

        # =========================
        # SALVARE AUTOMATĂ (Lunar): Exporturi/Importuri/Balanța comercială
        # =========================
        if frecventa == "Lunar":
            # funcția filtrează ea, deci o chemăm direct
            save_exp_lunar_to_excel(df, EXCEL_DATA_FILE, EXCEL_SHEET_EXP)

        # =========================
        # ANALIZĂ ANUALĂ (dacă e cazul)
        # =========================
        if frecventa == "Anual":
            st.subheader("Evoluția anuală și ratele de creștere (%)")

            col_ani = next((c for c in df.columns if _norm(c) in ["ani", "an", "year"]), None)
            col_indicator = next((c for c in df.columns if "indicator" in _norm(c)), None)

            if col_ani and col_indicator:
                df_total = df.groupby([col_indicator, col_ani])["Valoare"].sum().reset_index()
                df_total.sort_values([col_indicator, col_ani], inplace=True)

                df_total["Valoare_lag"] = df_total.groupby(col_indicator)["Valoare"].shift(1)
                df_total["Rată (%)"] = ((df_total["Valoare"] - df_total["Valoare_lag"]) / df_total["Valoare_lag"] * 100).round(2)

                df_val = df_total.pivot(index=col_indicator, columns=col_ani, values="Valoare").round(2)
                df_rate = df_total.pivot(index=col_indicator, columns=col_ani, values="Rată (%)").round(2)

                df_combined = pd.concat({"Valoare": df_val, "Rată (%)": df_rate}, axis=0).sort_index()
                st.dataframe(df_combined, use_container_width=True)
            else:
                st.info("Nu am putut identifica automat coloanele pentru 'Indicator' și 'Ani' în acest tabel.")

            col_grupe = next((c for c in df.columns if "grupe" in _norm(c) and "tari" in _norm(c)), None)
            if col_grupe:
                try:
                    df_pie = df.groupby(col_grupe)["Valoare"].sum().reset_index()
                    if len(df_pie) == 1 and _norm(df_pie[col_grupe].iloc[0]) == "total":
                        st.info("Diagrama circulară nu este afișată deoarece datele includ doar totalul.")
                    else:
                        st.markdown("#### Ponderi pe grupe de țări (cumulativ):")
                        fig_pie = px.pie(df_pie, names=col_grupe, values="Valoare", title="Ponderea pe grupe de țări")
                        st.plotly_chart(fig_pie, use_container_width=True)
                except Exception as e:
                    st.warning(f"Nu s-a putut genera diagrama circulară: {e}")

        # =========================
        # GRAFIC (linie)
        # =========================
        col_timp = detect_time_column(df.columns)
        if col_timp:
            color_col = next((c for c in df.columns if c not in [col_timp, "Valoare"]), None)
            if color_col:
                fig = px.line(df, x=col_timp, y="Valoare", color=color_col, markers=True, title="Evoluția indicatorului")
            else:
                fig = px.line(df, x=col_timp, y="Valoare", markers=True, title="Evoluția indicatorului")
            st.plotly_chart(fig, use_container_width=True)

        # =========================
        # EXPORT EXCEL (download)
        # =========================
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Date")

        st.download_button(
            "Descarcă Excel",
            output.getvalue(),
            file_name=f"{fisier_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Eroare la procesarea datelor: {str(e)}")
