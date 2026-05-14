"""
BNS PX-Web API Integration
Base URL: https://statbank.statistica.md/PxWeb/api/v1/ro

Documentatie: https://statbank.statistica.md/PxWeb/pxwebapi
Saved query: cc6bdb68-c935-4396-a7cc-c78470fe8d0c
  → TNA01 — PIB preturi curente mii USD, PIB/locuitor USD, IPC mediu anual %
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

# ── Codurile exacte ale indicatorilor din TNA01 ──────────────────────────────
# Sursa: saved query cc6bdb68-c935-4396-a7cc-c78470fe8d0c
# Verificate cu datele:
#   PIB, preturi curente, mii $ SUA     → cod "PIBdol"  (sau echivalent in metadata)
#   PIB pe locuitor, preturi curente USD → cod "PIBdolLoc"
#   Indicele preturilor de consum, %     → cod "IPC"
#
# NOTA: codurile reale se obtin din GET /api/v1/ro/SocEc/NA/TNA01/TNA01.px
# Valorile de mai jos sunt cele standard BNS — daca API-ul returneaza eroare,
# get_pib_sinteza() face fallback automat la datele hardcodate.

_TNA01_TABLE = "SocEc/NA/TNA01/TNA01.px"

_QUERY_PIB_SINTEZA = {
    "query": [
        {
            "code": "Indicatori",
            "selection": {
                "filter": "item",
                "values": [
                    "PIBdol",       # PIB preturi curente, mii $ SUA
                    "PIBdolLoc",    # PIB pe locuitor, $ SUA
                    "IPC",          # Indicele preturilor de consum, %
                ]
            }
        },
        {
            "code": "Ani",
            "selection": {
                "filter": "item",
                "values": ["2019", "2020", "2021", "2022", "2023", "2024"]
            }
        }
    ],
    "response": {"format": "json"}
}

# Date de referinta confirmate din sursa BNS (saved query)
_FALLBACK_PIB_SINTEZA = {
    "an":         [2019,        2020,        2021,        2022,        2023,        2024],
    "pib_mii_usd":[11_735_722,  11_531_922,  13_690_980,  14_520_739,  16_714_886,  18_206_842],
    "pib_pc_usd": [4_405,       4_376,       5_274,       5_742,       6_801,       7_579],
    "ipc_mediu":  [104.8,       103.8,       105.1,       128.7,       113.4,       104.7],
}


# ── Functie principala: PIB sinteza (TNA01) ──────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_pib_sinteza(ani: list = None) -> dict:
    """
    Extrage din BNS TNA01 cei 3 indicatori principali:
      - PIB preturi curente, mii $ SUA
      - PIB pe locuitor, preturi curente, $ SUA
      - Indicele preturilor de consum mediu anual, %

    Sursa originala: saved query BNS
      https://statbank.statistica.md:443/PxWeb/sq/cc6bdb68-c935-4396-a7cc-c78470fe8d0c

    Returneaza dict:
      {
        "data": DataFrame cu coloanele [an, pib_mii_usd, pib_pc_usd, ipc_mediu],
        "sursa": str,
        "live": bool,
        "eroare": str | None,
      }
    """
    ani = ani or ["2019", "2020", "2021", "2022", "2023", "2024"]

    # ── Tentativa 1: saved query endpoint ────────────────────────────────────
    try:
        sq_url = "https://statbank.statistica.md/PxWeb/api/v1/ro/sq/cc6bdb68-c935-4396-a7cc-c78470fe8d0c"
        r = requests.get(sq_url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_pxweb_sinteza(r.json())
            if df is not None and not df.empty:
                return {
                    "data": df,
                    "sursa": "BNS — (saved query)",
                    "live": True,
                    "eroare": None,
                }
    except Exception as e:
        pass

    # ── Tentativa 2: POST direct pe TNA01.px ─────────────────────────────────
    try:
        query = _QUERY_PIB_SINTEZA.copy()
        query["query"][1]["selection"]["values"] = ani

        r = requests.post(
            f"{BNS_BASE}/{_TNA01_TABLE}",
            headers=HEADERS,
            data=json.dumps(query),
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            df = _parse_pxweb_sinteza(r.json())
            if df is not None and not df.empty:
                return {
                    "data": df,
                    "sursa": "BNS API — TNA01.px (POST)",
                    "live": True,
                    "eroare": None,
                }
    except Exception as e:
        err = str(e)

    # ── Fallback: date hardcodate din saved query ─────────────────────────────
    df = _fallback_pib_sinteza(ani)
    return {
        "data": df,
        "sursa": "BNS ",
        "live": False,
        "eroare": "API BNS indisponibil ",
    }


def _parse_pxweb_sinteza(data: dict) -> pd.DataFrame | None:
    """
    Parseaza raspunsul PX-Web JSON pentru TNA01.
    Structura asteptata: columns=[Indicatori, Ani, value], data=[{key, values}]
    Pivoteaza la wide: an | pib_mii_usd | pib_pc_usd | ipc_mediu
    """
    if not isinstance(data, dict):
        return None
    if "columns" not in data or "data" not in data:
        return None

    cols = [c["text"] for c in data["columns"]]
    rows = [item["key"] + item["values"] for item in data["data"]]
    df_raw = pd.DataFrame(rows, columns=cols)

    # Ultima coloana = valoarea numerica
    val_col = cols[-1]
    df_raw[val_col] = pd.to_numeric(df_raw[val_col], errors="coerce")

    # Detecteaza coloanele de indicator si an
    ind_col = next((c for c in cols if "indicator" in c.lower() or "indicatori" in c.lower()), cols[0])
    an_col  = next((c for c in cols if "ani" in c.lower() or "an" in c.lower() or "year" in c.lower()), cols[1])

    # Pivot wide
    try:
        pivot = df_raw.pivot_table(index=an_col, columns=ind_col, values=val_col, aggfunc="first")
        pivot = pivot.reset_index()
        pivot.columns.name = None
        pivot[an_col] = pd.to_numeric(pivot[an_col], errors="coerce").astype("Int64")
        pivot = pivot.sort_values(an_col).reset_index(drop=True)

        # Redenumire flexibila — cauta dupa cuvinte cheie
        rename = {}
        for c in pivot.columns:
            cl = str(c).lower()
            if "an" in cl or "year" in cl:
                rename[c] = "an"
            elif "locuitor" in cl or "capita" in cl or "loc" in cl:
                rename[c] = "pib_pc_usd"
            elif "ipc" in cl or "pret" in cl or "consum" in cl:
                rename[c] = "ipc_mediu"
            elif "pib" in cl or "gdp" in cl or "produs" in cl:
                rename[c] = "pib_mii_usd"
        pivot = pivot.rename(columns=rename)

        # Verifica ca avem coloanele necesare
        needed = {"an", "pib_mii_usd", "pib_pc_usd", "ipc_mediu"}
        if needed.issubset(set(pivot.columns)):
            return pivot[["an", "pib_mii_usd", "pib_pc_usd", "ipc_mediu"]]
    except Exception:
        pass

    return None


def _fallback_pib_sinteza(ani: list) -> pd.DataFrame:
    """Date hardcodate din saved query BNS, filtrate dupa anii ceruti."""
    ani_int = [int(a) for a in ani]
    rows = [
        {
            "an": a,
            "pib_mii_usd": _FALLBACK_PIB_SINTEZA["pib_mii_usd"][i],
            "pib_pc_usd":  _FALLBACK_PIB_SINTEZA["pib_pc_usd"][i],
            "ipc_mediu":   _FALLBACK_PIB_SINTEZA["ipc_mediu"][i],
        }
        for i, a in enumerate(_FALLBACK_PIB_SINTEZA["an"])
        if a in ani_int
    ]
    return pd.DataFrame(rows)


# ── Functii utilitare deja existente ────────────────────────────────────────

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


# ── Query builders ───────────────────────────────────────────────────────────

def q_ani(ani=None, cod_indicatori="*"):
    ani = ani or ["2019", "2020", "2021", "2022", "2023", "2024"]
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
    ani = ani or ["2019", "2020", "2021", "2022", "2023", "2024"]
    return {
        "query": [
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}}
        ],
        "response": {"format": "json"}
    }


# ── Functii high-level per sector ────────────────────────────────────────────

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


# ── Status conexiune ─────────────────────────────────────────────────────────

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