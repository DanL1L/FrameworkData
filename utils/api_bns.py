"""
BNS PX-Web API Integration
Base URL: https://statbank.statistica.md/PxWeb/api/v1/ro
"""

import requests
import pandas as pd
import json
from datetime import datetime
import streamlit as st

BNS_BASE   = "https://statbank.statistica.md/PxWeb/api/v1/ro"
HEADERS    = {"Content-Type": "application/json", "Accept": "application/json"}
TIMEOUT    = 15

BNS_TABLES = {
    "pib_anual":       "SocEc/NA/TNA01/",
    "pib_trimestrial": "SocEc/NA/TNA04/",
    "pib_componente":  "SocEc/NA/TNA06/",
    "ipc_lunar":       "SocEc/Pr/TPR01/",
    "ipc_componente":  "SocEc/Pr/TPR02/",
    "export_anual":    "SocEc/CE/TCE01/",
    "import_anual":    "SocEc/CE/TCE02/",
    "comert_tari":     "SocEc/CE/TCE05/",
    "somaj":           "SocEc/FM/TFM01/",
    "salariu":         "SocEc/FM/TFM08/",
    "ocupare":         "SocEc/FM/TFM03/",
    "industrie":       "SocEc/IN/TIN01/",
    "agricultura":     "SocEc/AG/TAG01/",
}


@st.cache_data(ttl=3600, show_spinner=False)
def bns_list(path: str = "") -> list:
    url = f"{BNS_BASE}/{path}" if path else BNS_BASE
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def bns_metadata(table_path: str) -> dict:
    url = f"{BNS_BASE}/{table_path}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600, show_spinner=False)
def bns_fetch(table_path: str, query: dict) -> pd.DataFrame:
    """
    Extrage date dintr-un tabel BNS via POST PX-Web.

    Exemplu query:
        {
            "query": [
                {"code": "Ani",
                 "selection": {"filter": "item", "values": ["2022","2023","2024"]}},
                {"code": "Indicatori",
                 "selection": {"filter": "all", "values": ["*"]}}
            ],
            "response": {"format": "json"}
        }
    """
    url = f"{BNS_BASE}/{table_path}"
    try:
        r = requests.post(url, headers=HEADERS,
                          data=json.dumps(query), timeout=TIMEOUT)
        r.raise_for_status()
        return _parse_pxweb(r.json())
    except requests.exceptions.ConnectionError:
        return pd.DataFrame({"eroare": ["Conexiune esuata — verifica retea/VPN"]})
    except requests.exceptions.Timeout:
        return pd.DataFrame({"eroare": ["Timeout dupa 15s — API BNS lent"]})
    except requests.exceptions.HTTPError as e:
        return pd.DataFrame({"eroare": [f"HTTP {e.response.status_code}"]})
    except Exception as e:
        return pd.DataFrame({"eroare": [str(e)]})


def _parse_pxweb(data: dict) -> pd.DataFrame:
    if "columns" not in data or "data" not in data:
        return pd.DataFrame({"eroare": ["Format neasteptat"]})
    cols = [c["text"] for c in data["columns"]]
    rows = [item["key"] + item["values"] for item in data["data"]]
    df = pd.DataFrame(rows, columns=cols)
    df.iloc[:, -1] = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    return df


# ── Query builders ──────────────────────────────────────────────────────────

def q_ani(ani=None, cod_indicatori="*"):
    ani = ani or ["2019","2020","2021","2022","2023","2024"]
    return {
        "query": [
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Indicatori",
             "selection": {"filter": "all", "values": [cod_indicatori]}}
        ],
        "response": {"format": "json"}
    }

def q_top(n=24, dim="Luni"):
    return {
        "query": [
            {"code": dim,
             "selection": {"filter": "top", "values": [str(n)]}}
        ],
        "response": {"format": "json"}
    }

def q_trimestre(n=8):
    return {
        "query": [
            {"code": "Trimestre",
             "selection": {"filter": "top", "values": [str(n)]}}
        ],
        "response": {"format": "json"}
    }

def q_full(ani=None):
    ani = ani or ["2019","2020","2021","2022","2023","2024"]
    return {
        "query": [
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}}
        ],
        "response": {"format": "json"}
    }


# ── Functii high-level per sector ──────────────────────────────────────────

def get_pib_anual():
    return bns_fetch("SocEc/NA/TNA01/PIB01", q_ani())

def get_ipc_lunar():
    return bns_fetch("SocEc/Pr/TPR01/IPC01", q_top(24, "Luni"))

def get_ipc_componente():
    return bns_fetch("SocEc/Pr/TPR02/IPC02", q_top(12, "Luni"))

def get_export_anual():
    return bns_fetch("SocEc/CE/TCE01/CE01", q_full())

def get_import_anual():
    return bns_fetch("SocEc/CE/TCE02/CE02", q_full())

def get_somaj():
    return bns_fetch("SocEc/FM/TFM01/FM01", q_trimestre(8))

def get_salariu():
    return bns_fetch("SocEc/FM/TFM08/FM08", q_full())


# ── Status conexiune ────────────────────────────────────────────────────────

def test_bns() -> dict:
    try:
        r = requests.get(BNS_BASE, headers=HEADERS, timeout=TIMEOUT)
        return {
            "status": "ok" if r.status_code == 200 else "error",
            "http": r.status_code,
            "ms": int(r.elapsed.total_seconds() * 1000),
            "ts": datetime.now().strftime("%H:%M:%S"),
        }
    except Exception as e:
        return {"status": "error", "msg": str(e),
                "ts": datetime.now().strftime("%H:%M:%S")}
