"""
Data Loader — strat unificat de date
Prioritate: (1) fisier upload → (2) API live → (3) date demo

Toate paginile dashboardului cer date exclusiv prin acest modul.
"""

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
import os

# Importa clientii API
try:
    from utils.api_bns import (
        get_pib_crestere_anual, get_ipc_lunar,
        get_comert_exterior_lunar, get_salarii_sectoare, get_somaj_trimestrial,
    )
    BNS_OK = True
except Exception:
    BNS_OK = False

try:
    from utils.api_bnm import (
        get_cursuri_valutare, get_cursuri_multiple,
        get_rata_politica_monetara, get_rezerve_internationale,
        get_agregate_monetare,
    )
    BNM_OK = True
except Exception:
    BNM_OK = False

try:
    from utils.api_imf_wb import (
        imf_get_indicator, imf_comparatie_regionala,
        wb_get_indicator, IMF_INDICATORS, WB_INDICATORS,
    )
    IMF_OK = True
except Exception:
    IMF_OK = False

from data.demo_data import *


# ── Indicator de stare surse ───────────────────────────────────────────────

def status_surse() -> dict:
    """Testeaza conectivitatea si returneaza starea fiecarei surse."""
    import requests
    status = {}

    for nume, url in [
        ("BNS", "https://statbank.statistica.md/api/v1/ro"),
        ("BNM", "https://bnm.md/en/official_exchange_rates?period=2025-01-01,2025-01-02&currency=EUR"),
        ("IMF", "https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/MDA"),
        ("World Bank", "https://api.worldbank.org/v2/country/MDA/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=1"),
    ]:
        try:
            r = requests.get(url, timeout=8)
            status[nume] = "ok" if r.status_code == 200 else f"eroare {r.status_code}"
        except Exception as e:
            status[nume] = f"indisponibil"

    return status


DATA_PATH = "data"  # folderul unde ții Excel-urile

def load_from_excel_file(filename: str) -> pd.DataFrame | None:
    """
    Citește un fișier Excel din folderul /data.
    Returnează DataFrame sau None dacă nu există.
    """
    try:
        path = os.path.join(DATA_PATH, filename)
        if os.path.exists(path):
            return pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        print(f"Eroare citire Excel {filename}: {e}")
    return None

# ── Sector Real ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_pib_crestere() -> dict:
    """PIB real, crestere (%), date anuale. Sursa primara: BNS."""
    try:
        if BNS_OK:
            df = get_pib_crestere_anual()
            if not df.empty and "error" not in df.columns:
                return {"data": df, "sursa": "BNS API", "live": True}
    except Exception:
        pass

    # Fallback demo
    df = pd.DataFrame({"an": YEARS, "crestere_pib": pib_real_growth})
    return {"data": df, "sursa": "Date", "live": False}


@st.cache_data(ttl=3600, show_spinner=False)
def load_ipc() -> dict:
    """IPC lunar, componente. Sursa primara: BNS."""
    try:
        if BNS_OK:
            df = get_ipc_lunar()
            if not df.empty and "error" not in df.columns:
                return {"data": df, "sursa": "BNS API", "live": True}
    except Exception:
        pass

    # Fallback demo — serie lunara ultimele 12 luni
    months_short = ["Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Nov","Dec","Ian","Feb"]
    df = pd.DataFrame({
        "luna": months_short,
        "IPC total": [8.5,12.4,15.2,18.6,16.1,12.3,9.8,7.2,6.8,6.4,6.0,5.2],
        "Inflatie de baza": [6.1,9.2,11.4,14.0,13.1,10.5,8.2,6.0,5.5,4.9,4.5,4.1],
        "Alimente": [9.8,14.1,18.2,22.4,19.6,14.8,12.1,9.4,8.9,8.2,7.6,6.8],
        "Energie": [5.2,8.4,10.1,12.8,11.2,8.9,5.4,3.8,3.5,3.3,3.1,3.3],
    })
    return {"data": df, "sursa": "Date", "live": False}


# ── Sector Extern ──────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_comert_exterior() -> dict:
    """Export/import anual si trimestrial. Sursa primara: BNS + BNM."""
    try:
        if BNS_OK:
            df = get_comert_exterior_lunar()
            if not df.empty and "error" not in df.columns:
                return {"data": df, "sursa": "BNS API", "live": True}
    except Exception:
        pass

    df = pd.DataFrame({
        "an": YEARS,
        "export_mln_usd": export_vals,
        "import_mln_usd": import_vals,
        "deficit_ca_pib": deficit_ca_pib,
        "remitente_pib": remitente_pib,
    })
    return {"data": df, "sursa": "Date", "live": False}


@st.cache_data(ttl=3600, show_spinner=False)
def load_rezerve() -> dict:
    """Rezerve internationale BNM. Sursa primara: BNM API."""
    try:
        if BNM_OK:
            df = get_rezerve_internationale()
            if not df.empty and "error" not in df.columns:
                return {"data": df, "sursa": "BNM API", "live": True}
    except Exception:
        pass

    df = pd.DataFrame({
        "an": YEARS,
        "rezerve_total_mln_usd": rezerve_bnm,
        "luni_import": rezerve_luni,
    })
    return {"data": df, "sursa": "Date", "live": False}


# ── Sector Monetar ─────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def load_rata_bnm() -> dict:
    """Rata de baza BNM. Sursa primara: BNM API."""
    try:
        if BNM_OK:
            df = get_rata_politica_monetara()
            if not df.empty and "error" not in df.columns:
                return {"data": df, "sursa": "BNM API", "live": True}
    except Exception:
        pass

    df = pd.DataFrame({
        "date": pd.to_datetime([
            "2023-01-01","2023-04-01","2023-07-01","2023-10-01",
            "2024-01-01","2024-04-01","2024-07-01","2024-10-01",
            "2025-01-01","2025-02-01"
        ]),
        "rata_baza": rate_bnm_vals,
        "overnight_credit": [v + 2.5 for v in rate_bnm_vals],
        "overnight_depozit": [v - 1.5 for v in rate_bnm_vals],
    })
    return {"data": df, "sursa": "Date ", "live": False}


@st.cache_data(ttl=1800, show_spinner=False)
def load_cursuri(valute: list = None) -> dict:
    """Cursuri valutare. Sursa primara: BNM API."""
    if valute is None:
        valute = ["EUR", "USD", "RON"]
    try:
        if BNM_OK:
            df = get_cursuri_multiple(valute)
            if not df.empty:
                return {"data": df, "sursa": "BNM API", "live": True}
    except Exception:
        pass

    df = pd.DataFrame({
        "date": pd.to_datetime([f"2024-{str(m).zfill(2)}-01" for m in range(1, 13)]),
        "EUR": [19.12, 19.18, 19.25, 19.30, 19.20, 19.15, 19.28, 19.35, 19.42, 19.38, 19.40, 19.40],
        "USD": [17.82, 17.95, 18.05, 18.12, 18.02, 17.98, 18.08, 18.15, 18.22, 18.18, 18.15, 18.22],
        "RON": [3.85, 3.87, 3.89, 3.91, 3.88, 3.86, 3.90, 3.92, 3.94, 3.91, 3.90, 3.93],
    })
    return {"data": df, "sursa": "Date ", "live": False}


# ── Prognoze IMF ───────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def load_prognoze_imf() -> dict:
    """Prognoze IMF WEO pentru Moldova 2024-2029."""
    try:
        if IMF_OK:
            df = imf_get_indicator("NGDP_RPCH", an_start=2019, an_end=2029)
            if not df.empty and "error" not in df.columns:
                return {"data": df, "sursa": "IMF WEO API", "live": True}
    except Exception:
        pass

    df = pd.DataFrame({
        "an": [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029],
        "value": [4.3, -7.4, 13.9, -5.0, -5.9, 2.1, 3.2, 3.9, 4.4, 4.7, 4.8],
    })
    return {"data": df, "sursa": "Date ", "live": False}


# ── Upload fișier Excel/CSV ────────────────────────────────────────────────

def load_from_upload(uploaded_file) -> dict:
    """
    Parseaza un fisier Excel sau CSV incarcat de utilizator.
    Detecteaza automat structura (coloana date + coloane numerice).
    """
    if uploaded_file is None:
        return {"data": None, "error": "Niciun fisier incarcat"}

    try:
        name = uploaded_file.name.lower()
        if name.endswith(".csv"):
            # Incearca mai multe separatoare
            for sep in [",", ";", "\t"]:
                try:
                    df = pd.read_csv(uploaded_file, sep=sep)
                    if df.shape[1] > 1:
                        break
                except Exception:
                    continue
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")

        # Detecteaza coloana de date
        date_col = None
        for col in df.columns:
            if any(kw in str(col).lower() for kw in ["an", "data", "luna", "trimest", "year", "date"]):
                date_col = col
                break

        # Coloane numerice
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        return {
            "data": df,
            "date_col": date_col,
            "numeric_cols": num_cols,
            "rows": len(df),
            "cols": list(df.columns),
            "sursa": f"Upload: {uploaded_file.name}",
            "live": False,
        }

    except Exception as e:
        return {"data": None, "error": str(e)}


# ── Helper badge sursa ─────────────────────────────────────────────────────

def sursa_badge(result: dict) -> str:
    """Returneaza HTML badge pentru sursa datelor."""
    if result.get("live"):
        return f'<span style="font-size:10px;background:#E1F5EE;color:#0F6E56;padding:3px 8px;border-radius:3px;border:1px solid #9FE1CB;font-family:monospace">Sursa — {result["sursa"]}</span>'
    else:
        return f'<span style="font-size:10px;background:#FAEEDA;color:#854F0B;padding:3px 8px;border-radius:3px;border:1px solid #FAC775;font-family:monospace">DEMO — {result["sursa"]}</span>'



"""
utils/data_loader.py — versiunea îmbunătățită
Corecturi aplicate:
  1. @st.cache_data pe toate funcțiile de încărcare (eliminare re-citire la fiecare click)
  2. fillna(method='ffill') → ffill() (pandas ≥ 2.0 compatibil)
  3. Fallback demo complet când fișierele lipsesc
  4. load_forecast_data() mutată aici din Prognoza.py (DRY)
"""
