"""
utils/api_productie.py — Productia industriala si agricola (total, mil. lei)
Sursa: BNS PX-Web API

Tabele confirmate:
  40%20Statistica%20economica/14%20Industrie/
    → "Valoarea productiei industriale fabricate"
    → Activitati economice cod "0" = Industrie total
    → Unitati: mii lei → impartit la 1000 pentru mil. lei

  40%20Statistica%20economica/16%20AGR/AGR010/AGR010100.px
    → "Productia globala agricola"
    → Ramuri cod "0" = total, Categorii "0" = toate, Unitate "0" = Milioane lei
    → Unitati: milioane lei (mil. lei) — fara conversie
"""

import requests
import pandas as pd
import json
import streamlit as st
from datetime import datetime

BNS_BASE = "https://statbank.statistica.md/PxWeb/api/v1/ro"
HEADERS  = {"Content-Type": "application/json", "Accept": "application/json"}
TIMEOUT  = 15

_IND_PATH = "40%20Statistica%20economica/14%20Industrie/"
_IND_QUERY = {
    "query": [
        {"code": "Activitati economice", "selection": {"filter": "item", "values": ["0"]}}
    ],
    "response": {"format": "json"}
}

_AGR_PATH = "40%20Statistica%20economica/16%20AGR/AGR010/AGR010100.px"
_AGR_QUERY = {
    "query": [
        {"code": "Ramuri ale agriculturii",   "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Categorii de gospodarii",   "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Unitatea de masura",        "selection": {"filter": "item", "values": ["0"]}},
    ],
    "response": {"format": "json"}
}

_NULL_VALS = {"..", "...", "-", "n/a", "N/A", ""}


def _parse_ind(data: dict) -> pd.DataFrame | None:
    """
    Parseaza raspunsul pentru tabelul Industrie.
    key[0]=activitate, key[1]=an. Valori in MII LEI → impartit la 1000 → mil. lei.
    """
    if not isinstance(data, dict) or "data" not in data:
        return None
    rows = []
    for item in data["data"]:
        key = item.get("key", [])
        val_str = (item.get("values") or [None])[0]
        try:
            val = float(val_str) if val_str and str(val_str).strip() not in _NULL_VALS else None
        except (ValueError, TypeError):
            val = None
        try:
            an = int(key[1]) if len(key) > 1 else None
        except (ValueError, TypeError):
            an = None
        if an and val and val > 0:
            rows.append({"an": an, "valoare_mil_lei": val / 1000.0})
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("an").reset_index(drop=True)
    return df if not df.empty else None


def _parse_agr(data: dict) -> pd.DataFrame | None:
    """
    Parseaza raspunsul pentru tabelul AGR010100.
    key[0]=ramura, key[1]=an, key[2]=categorie, key[3]=unitate.
    Valori in MILIOANE LEI = mil. lei — fara conversie.
    """
    if not isinstance(data, dict) or "data" not in data:
        return None
    rows = []
    for item in data["data"]:
        key = item.get("key", [])
        val_str = (item.get("values") or [None])[0]
        try:
            val = float(val_str) if val_str and str(val_str).strip() not in _NULL_VALS else None
        except (ValueError, TypeError):
            val = None
        try:
            an = int(key[1]) if len(key) > 1 else None
        except (ValueError, TypeError):
            an = None
        if an and val and val > 0:
            rows.append({"an": an, "valoare_mil_lei": val})
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("an").reset_index(drop=True)
    return df if not df.empty else None


@st.cache_data(ttl=3600)
def get_productie_industriala_bns() -> dict:
    """
    Productia industriala totala (mil. lei, preturi curente), date anuale BNS.
    Sursa: 40 Statistica economica / 14 Industrie / Activitati economice = 0 (total).
    Returneaza {'data': df[an, valoare_mil_lei], 'live': bool, 'eroare': str|None}
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        r = requests.post(
            f"{BNS_BASE}/{_IND_PATH}",
            headers=HEADERS,
            data=json.dumps(_IND_QUERY),
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            df = _parse_ind(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True,
                        "sursa": f"BNS IND — live ({ts})", "eroare": None}
    except Exception as e:
        pass
    return {"data": pd.DataFrame(), "live": False,
            "sursa": "BNS IND", "eroare": "API BNS indisponibil"}


@st.cache_data(ttl=3600)
def get_productie_agricola_val_bns() -> dict:
    """
    Productia globala agricola totala (mil. lei, preturi curente), date anuale BNS.
    Sursa: AGR010100.px, Ramuri=0 (total), Categorii=0 (toate), Unitate=0 (Milioane lei).
    Returneaza {'data': df[an, valoare_mil_lei], 'live': bool, 'eroare': str|None}
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        r = requests.post(
            f"{BNS_BASE}/{_AGR_PATH}",
            headers=HEADERS,
            data=json.dumps(_AGR_QUERY),
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            df = _parse_agr(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True,
                        "sursa": f"BNS AGR010100 — live ({ts})", "eroare": None}
    except Exception as e:
        pass
    return {"data": pd.DataFrame(), "live": False,
            "sursa": "BNS AGR", "eroare": "API BNS indisponibil"}
