

import streamlit as st
import json
import os
import csv
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


import pandas as pd
import plotly.express as px

# ==========================
# CONFIG STREAMLIT
# ==========================

st.set_page_config(page_title="Indicatori macroeconomici", layout="wide")

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
    .kpi-card {
        background-color: #f9fafb;
        border-radius: 0.75rem;
        padding: 0.75rem 0.9rem;
        margin-bottom: 0.75rem;
        border: 1px solid #e5e7eb;
    }
    .kpi-title {
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 0.4rem;
        color: #111827;
    }
    .kpi-item {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        padding: 0.10rem 0;
    }
    .kpi-period {
        color: #4b5563;
        margin-right: 0.5rem;
    }
    .kpi-value {
        font-weight: 600;
        color: #111827;
    }
</style>
""", unsafe_allow_html=True)

# ==========================
# CONSTANTE & PATH-URI
# ==========================

# Comerț exterior
COMERT_URL = "https://statistica.gov.md/ro/statistic_indicator_details/19"
COMERT_STATE_FILE = "data/ultima_actualizare.json"
COMERT_CSV_FILE = "data/istoric_comert.csv"

# PIB
PIB_URL = "https://statistica.gov.md/ro/statistic_indicator_details/12"
PIB_STATE_FILE = "data/ultima_actualizare_pib.json"

# Investiții în active imobilizate
INV_URL = "https://statistica.gov.md/ro/statistic_indicator_details/16"
INV_STATE_FILE = "data/ultima_actualizare_investitii.json"

# IPC
CPI_URL = "https://statistica.gov.md/ro/statistic_indicator_details/10"
CPI_STATE_FILE = "data/ultima_actualizare_cpi.json"

# Populație
POP_URL = "https://statistica.gov.md/ro/statistic_indicator_details/25"
POP_STATE_FILE = "data/ultima_actualizare_populatie.json"

# Forța de muncă / șomaj / NEET
LAB_URL = "https://statistica.gov.md/ro/statistic_indicator_details/1"
LAB_STATE_FILE = "data/ultima_actualizare_forta_munca.json"

# Câștig salarial & costul forței de muncă
WAGE_URL = "https://statistica.gov.md/ro/statistic_indicator_details/2"
WAGE_STATE_FILE = "data/ultima_actualizare_castiguri.json"

# Industrie
IND_URL = "https://statistica.gov.md/ro/statistic_indicator_details/13"
IND_STATE_FILE = "data/ultima_actualizare_industrie.json"

# Agricultură
AGR_URL = "https://statistica.gov.md/ro/statistic_indicator_details/15"
AGR_STATE_FILE = "data/ultima_actualizare_agricultura.json"


# ==========================
# FUNCȚII GENERALE
# ==========================

def init_driver():
    """Inițializează un driver Chrome headless pentru scraping."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)


def load_json_state(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json_state(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_data_actualizare(soup):
    """
    Caută textul care conține 'Actualizat' și întoarce data ca string.
    Dacă nu găsește nimic, întoarce 'Fără dată actualizare' ca să nu blocheze salvarea JSON-ului.
    """
    actualizare_tag = soup.find(string=lambda t: t and "Actualizat" in t)
    if not actualizare_tag:
        return "Fără dată actualizare"

    text = actualizare_tag.strip()
    if ":" in text:
        parts = text.split(":", 1)
        return parts[1].strip() or "Fără dată actualizare"
    return text or "Fără dată actualizare"


def parse_indicator_tables(soup, default_section=None):
    """
    Citește tabelele cu indicatori și întoarce un dict:
    { 'Titlu secțiune': { 'Etichetă (perioadă/indicator)': valoare_float, ... }, ... }

    default_section – nume folosit dacă nu găsim un titlu <div class="font-18"> înainte de tabel.
    """
    indicatori = {}

    # 1) Încercăm mai întâi tabelele de tip "tablekeyvalue"
    tables = soup.select("table.tablekeyvalue")

    # 2) Dacă nu găsim nimic, folosim toate tabelele
    if not tables:
        tables = soup.find_all("table")

    for table in tables:
        # Titlul secțiunii e, de obicei, în <div class="font-18"><b>...</b></div>
        title_div = table.find_previous("div", class_="font-18")
        sectiune = None

        if title_div:
            title_tag = title_div.find("b") or title_div
            sectiune = title_tag.get_text(strip=True)
        elif default_section:
            sectiune = default_section
        else:
            continue

        indicatori.setdefault(sectiune, {})

        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            perioada = cols[0].get_text(strip=True)
            raw_value = cols[1].get_text(strip=True)

            # curățăm valoarea: spații, virgule, etc.
            raw_value = raw_value.replace("\xa0", "").replace(",", ".").strip()
            raw_value_clean = re.sub(r"[^0-9\.\-]", "", raw_value)

            if not raw_value_clean:
                continue

            try:
                valoare = float(raw_value_clean)
            except ValueError:
                continue

            indicatori[sectiune][perioada] = valoare

    return indicatori

# -------------------- Helpers --------------------
def safe_read_excel(path, sheet_name=None):
    try:
        if sheet_name:
            return pd.read_excel(path, sheet_name=sheet_name)
        return pd.read_excel(path)
    except Exception:
        return pd.DataFrame()

def last_two(series: pd.Series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 2:
        return None, None
    return float(s.iloc[-1]), float(s.iloc[-2])

def pct_change(curr, prev):
    if curr is None or prev is None or prev == 0:
        return None
    return (curr - prev) / prev * 100


# -------------------- Load datasets (adaptate la structura ta) --------------------
# 1) Sector monetar (ex: Test_Data_Sector_Monetar.xlsx)
df_mon = safe_read_excel(os.path.join("data", "Test_Data_Sector_Monetar.xlsx"), sheet_name="Monetar")
# așteptat: An, PIB, ... (vezi Monetar.py)

# 2) Sector extern (dacă ai un fișier agregat pentru export/import total)
df_trade = safe_read_excel(os.path.join("data", "Trade_Total.xlsx"))  # <-- (creează/înlocuiește cu fișierul tău)
# așteptat: Date (sau Year/Month), Exports, Imports (și opțional Country/Partner)

# fallback demo dacă lipsește
if df_trade.empty:
    # date demo lunare – ca să vezi layout-ul
    idx = pd.date_range("2023-01-01", "2024-12-01", freq="MS")
    df_trade = pd.DataFrame({
        "Date": idx,
        "Țara": ["România"] * len(idx),
        "Partener comercial": ["Turcia"] * len(idx),
        "Exporturi": pd.Series(range(len(idx))) * 0.12 + 4.0,
        "Importuri": pd.Series(range(len(idx))) * 0.10 + 6.1,
    })
else:
    # dacă ai deja denumiri în engleză, nu schimbăm coloanele din fișier.
    # doar normalizăm pentru vizualizare:
    pass

# --- Normalizează pentru plot-uri fără să-ți strice fișierele ---
# Asigură maparea la coloane standard interne: Date, Exporturi, Importuri
col_date = "Date" if "Date" in df_trade.columns else ("Data" if "Data" in df_trade.columns else None)
col_exp  = "Exports" if "Exports" in df_trade.columns else ("Exporturi" if "Exporturi" in df_trade.columns else None)
col_imp  = "Imports" if "Imports" in df_trade.columns else ("Importuri" if "Importuri" in df_trade.columns else None)

if col_date is None or col_exp is None or col_imp is None:
    # fallback defensiv (în caz că lipsesc coloanele așteptate)
    df_trade = pd.DataFrame(columns=["Date", "Exports", "Imports"])
    col_date, col_exp, col_imp = "Date", "Exports", "Imports"

df_trade[col_date] = pd.to_datetime(df_trade[col_date], errors="coerce")
df_trade = df_trade.dropna(subset=[col_date]).sort_values(col_date)

# copie standardizată pentru utilizare în pagină
f = df_trade.copy()
f = f.rename(columns={col_date: "Date", col_exp: "Exporturi", col_imp: "Importuri"})



# -------------------- Filters row (identic ca structură; etichete în română) --------------------
min_d = f["Date"].min().date() if not f.empty else None
max_d = f["Date"].max().date() if not f.empty else None


# -------------------- KPI row (5 carduri) --------------------
# KPI 1: PIB (din monetar, dacă există), altfel demo
gdp_curr = gdp_prev = None
if not df_mon.empty and "PIB, mil lei" in df_mon.columns:
    df_mon = df_mon.sort_values("An")
    gdp_curr, gdp_prev = last_two(df_mon["PIB, mil lei"])
else:
    # demo
    gdp_curr, gdp_prev = 18.7, 17.2

gdp_delta = pct_change(gdp_curr, gdp_prev)

# KPI 2: Creștere PIB an/an (demo dacă nu ai serie)
gdp_yoy_curr, gdp_yoy_prev = 8.7, 5.2
gdp_yoy_delta = gdp_yoy_curr - gdp_yoy_prev

# KPI 3: Indicele producției industriale (demo)
ipi_curr, ipi_prev = 127.3, 118.5
ipi_delta = pct_change(ipi_curr, ipi_prev)

# KPI 4: Masa monetară M2 (demo)
m2_curr, m2_prev = 12.4, 11.8
m2_delta = pct_change(m2_curr, m2_prev)

# KPI 5: Sold comercial din f
if len(f) >= 2:
    tb = (f["Exporturi"].iloc[-1] - f["Importuri"].iloc[-1])
    tb_prev = (f["Exporturi"].iloc[-2] - f["Importuri"].iloc[-2])
else:
    tb, tb_prev = -2.1, -1.8
tb_delta = pct_change(tb, tb_prev)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric("Produsul Intern Brut (USD)", f"{gdp_curr:,.1f}", f"{gdp_delta:+.1f}%" if gdp_delta is not None else None)
    st.caption(f"vs anul precedent {gdp_prev:,.1f}")
with k2:
    st.metric("Creșterea PIB an/an (%)", f"{gdp_yoy_curr:,.1f}", f"{gdp_yoy_delta:+.1f}")
    st.caption(f"vs anul precedent {gdp_yoy_prev:,.1f}")
with k3:
    st.metric("Indicele producției industriale (puncte)", f"{ipi_curr:,.1f}", f"{ipi_delta:+.1f}%" if ipi_delta is not None else None)
    st.caption(f"vs anul precedent {ipi_prev:,.1f}")
with k4:
    st.metric("Masa monetară M2 (USD)", f"{m2_curr:,.1f}", f"{m2_delta:+.1f}%" if m2_delta is not None else None)
    st.caption(f"vs anul precedent {m2_prev:,.1f}")
with k5:
    st.metric("Soldul balanței comerciale (USD)", f"{tb:,.1f}", f"{tb_delta:+.1f}%" if tb_delta is not None else None)
    st.caption(f"vs anul precedent {tb_prev:,.1f}")


# Diagrame PIB (demo) + trend PIB
left, mid, right = st.columns([1, 1, 2])

with left:
    st.subheader("PIB pe activități economice")
    df_demo = pd.DataFrame({
        "Activitate": ["Servicii", "Industrie prelucrătoare", "Agricultură", "Construcții", "Transport", "Comerț", "IT", "Utilități"],
        "Valoare": [3240000, 2850000, 2410000, 1950000, 1680000, 1420000, 1150000, 410000]
    })
    fig = px.pie(df_demo, names="Activitate", values="Valoare", hole=0.55)
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), legend_title_text="Activitate")
    st.plotly_chart(fig, use_container_width=True)

with mid:
    st.subheader("PIB pe resurse")
    df_demo2 = pd.DataFrame({
        "Resursă": ["Muncă", "Capital", "Teren", "Tehnologie", "Resurse naturale", "Infrastructură", "Antreprenoriat"],
        "Valoare": [4120000, 3680000, 2950000, 2410000, 1890000, 1520000, 980000]
    })
    fig = px.pie(df_demo2, names="Resursă", values="Valoare", hole=0.55)
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), legend_title_text="Resursă")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Evoluția PIB în timp")
    # dacă ai serie reală, înlocuiești cu ea
    g = pd.DataFrame({"Data": pd.date_range("2023-01-01", "2024-12-01", freq="MS")})
    g["PIB"] = 16 + (pd.Series(range(len(g))) * 0.2)
    fig = px.line(g, x="Data", y="PIB", markers=True)
    fig.update_layout(margin=dict(l=20, r=10, t=30, b=10), xaxis_title="Data", yaxis_title="PIB")
    st.plotly_chart(fig, use_container_width=True)


st.markdown("---")

# ==========================
# SCRAPER COMERȚ EXTERIOR
# ==========================

def append_comert_to_csv(data_update, indicatori):
    header = ["Data actualizare", "Categorie", "Perioada", "Valoare"]
    file_exists = os.path.exists(COMERT_CSV_FILE)
    os.makedirs(os.path.dirname(COMERT_CSV_FILE), exist_ok=True)

    with open(COMERT_CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)

        for categorie, perioade in indicatori.items():
            for perioada, valoare in perioade.items():
                writer.writerow([data_update, categorie, perioada, valoare])


def fetch_comert_data():
    driver = init_driver()
    driver.get(COMERT_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(COMERT_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ Comerț: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup)
    if not indicatori:
        print("Comerț: nu s-au putut extrage indicatorii.")
        return None

    append_comert_to_csv(data_actualizare, indicatori)
    save_json_state(COMERT_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"Comerț: date actualizate la {data_actualizare}")
    return indicatori



# ==========================
# 2. PIB, INVESTIȚII, IPC – 3 COLOANE
# ==========================
col_pib, col_inv, col_cpi = st.columns(3)

# ----- PIB -----
with col_pib:
    pib_state = load_json_state(PIB_STATE_FILE)
    pib_data_actualizare = pib_state.get("data_actualizare")
    pib_indicatori = pib_state.get("indicatori", {})

    st.markdown(
        "### PIB",
        unsafe_allow_html=True,
    )

    if pib_indicatori:
        items = list(pib_indicatori.items())

        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"

            for perioada, valoare in perioade.items():
                if isinstance(valoare, (int, float)):
                    val_str = f"{valoare:,.1f}".replace(",", " ")
                else:
                    val_str = str(valoare)
                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există date salvate pentru indicatorii PIB. Rulează scraper-ul din sidebar.")

# ----- Investiții -----
with col_inv:
    inv_state = load_json_state(INV_STATE_FILE)
    inv_data_actualizare = inv_state.get("data_actualizare")
    inv_indicatori = inv_state.get("indicatori", {})

    st.markdown(
        "### Investiții în active imobilizate",
        unsafe_allow_html=True,
    )

    if inv_indicatori:
        items = list(inv_indicatori.items())

        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"

            for perioada, valoare in perioade.items():
                if isinstance(valoare, (int, float)):
                    val_str = f"{valoare:,.1f}".replace(",", " ")
                else:
                    val_str = str(valoare)

                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )

            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există date salvate pentru investiții. Rulează scraper-ul din sidebar.")

# ----- IPC -----
with col_cpi:
    cpi_state = load_json_state(CPI_STATE_FILE)
    cpi_data_actualizare = cpi_state.get("data_actualizare")
    cpi_indicatori = cpi_state.get("indicatori", {})

    st.markdown(
        "### Indicele prețurilor de consum (IPC)",
        unsafe_allow_html=True,
    )
    if cpi_indicatori:
        items = list(cpi_indicatori.items())

        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"

            for perioada, valoare in perioade.items():
                if isinstance(valoare, (int, float)):
                    val_str = f"{valoare:,.1f}".replace(",", " ")
                else:
                    val_str = str(valoare)

                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există încă date salvate pentru IPC. Rulează scraper-ul din sidebar.")
        
st.markdown("---")



# ==========================
# SCRAPER PIB
# ==========================

def fetch_pib_data():
    driver = init_driver()
    driver.get(PIB_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(PIB_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ PIB: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup)
    if not indicatori:
        print("PIB: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(PIB_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"PIB: date actualizate la {data_actualizare}")
    return indicatori


# ==========================
# SCRAPER INVESTIȚII
# ==========================

def fetch_invest_data():
    driver = init_driver()
    driver.get(INV_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(INV_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ Investiții: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup)
    if not indicatori:
        print("Investiții: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(INV_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"Investiții: date actualizate la {data_actualizare}")
    return indicatori


# ==========================
# SCRAPER IPC (CPI)
# ==========================

def fetch_cpi_data():
    driver = init_driver()
    driver.get(CPI_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(CPI_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ IPC: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup, default_section="Indicele prețurilor de consum (IPC)")
    if not indicatori:
        print("IPC: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(CPI_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"IPC: date actualizate la {data_actualizare}")
    return indicatori


# ==========================
# SCRAPER POPULAȚIE
# ==========================

def fetch_pop_data():
    driver = init_driver()
    driver.get(POP_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(POP_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ Populație: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup, default_section="Populație și demografie")
    if not indicatori:
        print("Populație: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(POP_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"Populație: date actualizate la {data_actualizare}")
    return indicatori


# ==========================
# SCRAPER FORȚA DE MUNCĂ / ȘOMAJ / NEET
# ==========================

def fetch_lab_data():
    driver = init_driver()
    driver.get(LAB_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(LAB_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ Forța de muncă: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup, default_section="Forța de muncă și șomaj")
    if not indicatori:
        print("Forța de muncă: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(LAB_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"Forța de muncă: date actualizate la {data_actualizare}")
    return indicatori


# ==========================
# SCRAPER CÂȘTIG SALARIAL & COST FORȚĂ MUNCĂ
# ==========================

def fetch_wage_data():
    driver = init_driver()
    driver.get(WAGE_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(WAGE_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ Câștiguri: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup, default_section="Câștigul salarial și costul forței de muncă")
    if not indicatori:
        print("Câștiguri: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(WAGE_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"Câștiguri: date actualizate la {data_actualizare}")
    return indicatori


# ==========================
# SCRAPER INDUSTRIE
# ==========================

def fetch_industry_data():
    driver = init_driver()
    driver.get(IND_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(IND_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ Industrie: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup, default_section="Producția industrială")
    if not indicatori:
        print("Industrie: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(IND_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"Industrie: date actualizate la {data_actualizare}")
    return indicatori


# ==========================
# SCRAPER AGRICULTURĂ
# ==========================

def fetch_agri_data():
    driver = init_driver()
    driver.get(AGR_URL)
    time.sleep(4)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    data_actualizare = get_data_actualizare(soup)

    last_state = load_json_state(AGR_STATE_FILE)
    if (
        last_state.get("data_actualizare") == data_actualizare
        and last_state.get("indicatori")
    ):
        print("ℹ Agricultură: datele nu s-au schimbat. Ultima actualizare:", data_actualizare)
        return None

    indicatori = parse_indicator_tables(soup, default_section="Producția agricolă")
    if not indicatori:
        print("Agricultură: nu s-au putut extrage indicatorii.")
        return None

    save_json_state(AGR_STATE_FILE, {
        "data_actualizare": data_actualizare,
        "indicatori": indicatori
    })
    print(f"Agricultură: date actualizate la {data_actualizare}")
    return indicatori

# ==========================
# 3. POPULAȚIE + CÂȘTIGURI și FORȚA DE MUNCĂ
# ==========================

col_left, col_right = st.columns([1.1, 1])  # ușor mai lată coloana stângă

# ----- STÂNGA: POPULAȚIE și CÂȘTIGURI -----
with col_left:
    # === Populație și demografie ===
    pop_state = load_json_state(POP_STATE_FILE)
    pop_data_actualizare = pop_state.get("data_actualizare")
    pop_indicatori = pop_state.get("indicatori", {})

    st.markdown(
        "### Populație și demografie",
        unsafe_allow_html=True,
    )

    if pop_indicatori:
        items = list(pop_indicatori.items())
        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"
            for perioada, valoare in perioade.items():
                val_str = f"{valoare:,.1f}".replace(",", " ") if isinstance(valoare, (int, float)) else str(valoare)
                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există încă date salvate pentru populație. Rulează scraper-ul din sidebar.")


    # === Câștigul salarial și costul forței de muncă ===
    wage_state = load_json_state(WAGE_STATE_FILE)
    wage_data_actualizare = wage_state.get("data_actualizare")
    wage_indicatori = wage_state.get("indicatori", {})

    st.markdown(
        "### Câștigul salarial și costul forței de muncă",
        unsafe_allow_html=True,
    )

    if wage_indicatori:
        items = list(wage_indicatori.items())
        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"
            for perioada, valoare in perioade.items():
                val_str = f"{valoare:,.1f}".replace(",", " ") if isinstance(valoare, (int, float)) else str(valoare)
                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există încă date salvate pentru câștigul salarial. Rulează scraper-ul din sidebar.")


# ----- DREAPTA: FORȚA DE MUNCĂ și ȘOMAJ -----
with col_right:
    lab_state = load_json_state(LAB_STATE_FILE)
    lab_data_actualizare = lab_state.get("data_actualizare")
    lab_indicatori = lab_state.get("indicatori", {})

    st.markdown(
        "### Forța de muncă și șomaj",
        unsafe_allow_html=True,
    )

    if lab_indicatori:
        items = list(lab_indicatori.items())
        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"
            for perioada, valoare in perioade.items():
                val_str = f"{valoare:,.1f}".replace(",", " ") if isinstance(valoare, (int, float)) else str(valoare)
                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există încă date salvate pentru forța de muncă. Rulează scraper-ul din sidebar.")



st.markdown("---")

# ==========================
# 1. COMERȚ EXTERIOR
# ==========================

comert_state = load_json_state(COMERT_STATE_FILE)
if not comert_state:
    st.warning(
        "Nu am găsit fișierul de stare pentru comerțul exterior "
        "`data/ultima_actualizare.json`. Rulează actualizarea din sidebar."
    )
else:
    data_actualizare = comert_state.get("data_actualizare", "n/d")
    indicatori = comert_state.get("indicatori", {})

    st.subheader(f"Comerț internațional")

    if not indicatori:
        st.info("Fișierul JSON nu conține indicatori de comerț. Verifică scriptul de scraping.")
    else:
        items = list(indicatori.items())

        # câte 3 secțiuni (Exporturi / Importuri / Deficit etc.) pe rând
        for i in range(0, len(items), 3):
            row_items = items[i:i + 3]
            cols = st.columns(len(row_items))

            for col, (sectiune, perioade) in zip(cols, row_items):
                with col:
                    if not perioade:
                        col.markdown(
                            f"**{sectiune}**<br/>"
                            "<span style='font-size:0.85rem;color:#6b7280;'>Nu există valori.</span>",
                            unsafe_allow_html=True,
                        )
                        continue

                    html = "<div class='kpi-card'>"
                    html += f"<div class='kpi-title'>{sectiune}</div>"

                    for perioada, valoare in perioade.items():
                        if isinstance(valoare, (int, float)):
                            val_str = f"{valoare:,.1f}".replace(",", " ")
                        else:
                            val_str = str(valoare)

                        html += (
                            "<div class='kpi-item'>"
                            f"<span class='kpi-period'>{perioada}</span>"
                            f"<span class='kpi-value'>{val_str}</span>"
                            "</div>"
                        )

                    html += "</div>"
                    col.markdown(html, unsafe_allow_html=True)



# -------------------- Charts grid --------------------


# Exporturi vs Importuri + Sold comercial
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Tendința exporturilor vs importurilor")
    tmp = f.copy()
    tmp["Luna"] = tmp["Date"].dt.strftime("%b %Y")
    fig = px.bar(tmp, x="Luna", y=["Exporturi", "Importuri"], barmode="group")
    fig.update_layout(margin=dict(l=20, r=10, t=30, b=10), xaxis_title="Luna", yaxis_title="Valoare")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Tendința soldului comercial")
    tmp = f.copy()
    tmp["Sold comercial"] = tmp["Exporturi"] - tmp["Importuri"]
    tmp["Luna"] = tmp["Date"].dt.strftime("%b %Y")
    fig = px.line(tmp, x="Luna", y="Sold comercial", markers=True)
    fig.update_layout(margin=dict(l=20, r=10, t=30, b=10), xaxis_title="Luna", yaxis_title="Sold comercial")
    st.plotly_chart(fig, use_container_width=True)





# ==========================
# 5. INDUSTRIE & AGRICULTURĂ
# ==========================

st.markdown("---")
col_ind, col_agr = st.columns(2)

# ----- INDUSTRIE (STÂNGA) -----
with col_ind:
    ind_state = load_json_state(IND_STATE_FILE)
    ind_data_actualizare = ind_state.get("data_actualizare")
    ind_indicatori = ind_state.get("indicatori", {})

    st.markdown(
        "### Industrie",
        unsafe_allow_html=True,
    )

    if ind_indicatori:
        items = list(ind_indicatori.items())

        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"

            for perioada, valoare in perioade.items():
                if isinstance(valoare, (int, float)):
                    val_str = f"{valoare:,.1f}".replace(",", " ")
                else:
                    val_str = str(valoare)

                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )

            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există încă date salvate pentru industrie. Rulează scraper-ul din sidebar.")


# ----- AGRICULTURĂ (DREAPTA) -----
with col_agr:
    agr_state = load_json_state(AGR_STATE_FILE)
    agr_data_actualizare = agr_state.get("data_actualizare")
    agr_indicatori = agr_state.get("indicatori", {})

    st.markdown(
        "### Agricultură",
        unsafe_allow_html=True,
    )

    if agr_indicatori:
        items = list(agr_indicatori.items())

        for sectiune, perioade in items:
            html = "<div class='kpi-card'>"
            html += f"<div class='kpi-title'>{sectiune}</div>"

            for perioada, valoare in perioade.items():
                if isinstance(valoare, (int, float)):
                    val_str = f"{valoare:,.1f}".replace(",", " ")
                else:
                    val_str = str(valoare)

                html += (
                    "<div class='kpi-item'>"
                    f"<span class='kpi-period'>{perioada}</span>"
                    f"<span class='kpi-value'>{val_str}</span>"
                    "</div>"
                )

            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Nu există încă date salvate pentru agricultură. Rulează scraper-ul din sidebar.")


st.markdown(
    """
    <div style="font-size:0.8rem; color:#6b7280;">
        <br/>
        <em>Notă:</em> Indicatorii sunt calculați pe baza datelor oficiale furnizate de 
        Biroul Național de Statistică (BNS) și Banca Națională a Moldovei (BNM). 
        Calcule MDED.
    </div>
    """,
    unsafe_allow_html=True
)













