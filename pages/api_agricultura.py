"""
utils/api_agricultura.py — Date BNS Agricultura
Tabele nationale:
  AGR020060 — Culturi agricole (suprafata, roada, recolta), anual 2016-2025
  AGR020070 — Plantatii multianuale (pomicole, viticole), anual 2016-2025
  AGR030200 — Productia principalelor produse animaliere (carne, lapte, oua)
  AGR030100 — Efectivul de animale la 1 ianuarie

Tabele teritoriale:
  AGR020600reg — Productia globala culturi pe raioane/regiuni, anual 2007-2025
  AGR030300reg — Efectivul de animale pe raioane/regiuni, anual 2007-2026

Referinta saved query: cc82ded8-2a6a-483c-b40a-ba667b32efac
"""

import requests
import pandas as pd
import json
import streamlit as st
from datetime import datetime

BNS_BASE = "https://statbank.statistica.md/PxWeb/api/v1/ro"
HEADERS  = {"Content-Type": "application/json", "Accept": "application/json"}
TIMEOUT  = 15

_AGR020060  = "40%20Statistica%20economica/16%20AGR/AGR020/AGR020060.px"
_AGR020600R = "40%20Statistica%20economica/16%20AGR/AGR020/AGR020600reg.px"
_AGR030300R = "40%20Statistica%20economica/16%20AGR/AGR030/AGR030300reg.px"
_AGR020070 = "40%20Statistica%20economica/16%20AGR/AGR020/AGR020070.px"
_AGR030100 = "40%20Statistica%20economica/16%20AGR/AGR030/AGR030100.px"
_AGR030200 = "40%20Statistica%20economica/16%20AGR/AGR030/AGR030200.px"

# ── Coduri culturi cheie (AGR020060) ─────────────────────────────────────────
_CULTURI_CODES = {
    "1":  "Cereale",
    "10": "Porumb",
    "26": "Floarea-soarelui",
    "28": "Soia",
    "63": "Legume",
    "42": "Cartofi",
}

# ── Coduri plantatii cheie (AGR020070) ────────────────────────────────────────
_PLANTATII_CODES = {
    "0":  "Pomicole",
    "24": "Viticole",
}

# ── Coduri produse animaliere (AGR030200) ─────────────────────────────────────
_ANIMALE_PROD_CODES = {
    "0": "Carne (greutate vie)",
    "6": "Lapte",
    "7": "Oua",
}
_ANIMALE_PROD_UNITS = {
    "0": "mii tone",
    "6": "mii tone",
    "7": "mln. bucati",
}

# ── Coduri specii animale (AGR030100) ─────────────────────────────────────────
_SPECII_CODES = {
    "0": "Bovine",
    "2": "Porcine",
    "3": "Ovine",
}


# ── 1. Culturi agricole ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_culturi_bns(ani: list = None) -> dict:
    """
    AGR020060 — Recolta globala (mii tone) pe culturi agricole cheie.
    Returneaza:
      {"data": DataFrame[an, cultura, recolta_mii_tone],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2016, 2026)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    query = {
        "query": [
            {"code": "Culturi",
             "selection": {"filter": "item",
                           "values": list(_CULTURI_CODES.keys())}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Categorii de gospodarii",
             "selection": {"filter": "item", "values": ["0"]}},
            {"code": "Indicatori",
             "selection": {"filter": "item", "values": ["2"]}},  # Recolta globala, mii tone
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_AGR020060}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_agr_simple(r.json(), _CULTURI_CODES, "cultura", "recolta_mii_tone")
            if df is not None and not df.empty:
                return {"data": df, "live": True, "ts": ts, "eroare": None}
            err_msg = "parse esuat"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False, "ts": ts,
            "eroare": f"AGR020060: {err_msg}"}


# ── 2. Plantatii multianuale ──────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_plantatii_bns(ani: list = None) -> dict:
    """
    AGR020070 — Recolta globala (mii tone) plantatii pomicole si viticole.
    Returneaza:
      {"data": DataFrame[an, plantatie, recolta_mii_tone],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2016, 2026)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    query = {
        "query": [
            {"code": "Culturi",
             "selection": {"filter": "item",
                           "values": list(_PLANTATII_CODES.keys())}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Categorii de gospodarii",
             "selection": {"filter": "item", "values": ["0"]}},
            {"code": "Indicatori",
             "selection": {"filter": "item", "values": ["3"]}},  # Recolta globala, mii tone
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_AGR020070}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_agr_simple(r.json(), _PLANTATII_CODES, "plantatie", "recolta_mii_tone")
            if df is not None and not df.empty:
                return {"data": df, "live": True, "ts": ts, "eroare": None}
            err_msg = "parse esuat"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False, "ts": ts,
            "eroare": f"AGR020070: {err_msg}"}


# ── 3. Productia animala ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_productie_animala_bns(ani: list = None) -> dict:
    """
    AGR030200 — Productia principalelor produse animaliere.
      Carne (mii tone greutate vie), Lapte (mii tone), Oua (mln. buc.)
    Returneaza:
      {"data": DataFrame[an, produs, valoare, unitate],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2010, 2026)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    query = {
        "query": [
            {"code": "Principale produse animaliere",
             "selection": {"filter": "item",
                           "values": list(_ANIMALE_PROD_CODES.keys())}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Categorii de gospodarii",
             "selection": {"filter": "item", "values": ["0"]}},
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_AGR030200}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_agr030200(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True, "ts": ts, "eroare": None}
            err_msg = "parse esuat"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False, "ts": ts,
            "eroare": f"AGR030200: {err_msg}"}


# ── 4. Efectivul de animale ───────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_efectiv_animale_bns(ani: list = None) -> dict:
    """
    AGR030100 — Efectivul de animale la 1 ianuarie (mii capete).
    Returneaza:
      {"data": DataFrame[an, specie, mii_capete],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2010, 2027)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    query = {
        "query": [
            {"code": "Specii de animale",
             "selection": {"filter": "item",
                           "values": list(_SPECII_CODES.keys())}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Categorii de producatori",
             "selection": {"filter": "item", "values": ["0"]}},
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_AGR030100}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_agr_simple(r.json(), _SPECII_CODES, "specie", "mii_capete")
            if df is not None and not df.empty:
                return {"data": df, "live": True, "ts": ts, "eroare": None}
            err_msg = "parse esuat"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False, "ts": ts,
            "eroare": f"AGR030100: {err_msg}"}


# ── Parseri ───────────────────────────────────────────────────────────────────

def _parse_agr_simple(data: dict, cod_map: dict,
                      col_categ: str, col_val: str) -> pd.DataFrame | None:
    """
    Parser generic pentru tabele cu structura key: [cod_categ, Ani, ...].
    cod_map: {cod_bns: label_afisat}
    Returneaza DataFrame[an, col_categ, col_val].
    """
    if not isinstance(data, dict) or "data" not in data:
        return None
    rows = []
    for item in data["data"]:
        cod = item["key"][0]
        an  = item["key"][1]
        val_str = item["values"][0]
        try:
            val = float(val_str) if val_str and val_str.strip() not in ("..", "...", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        rows.append({
            "an":      int(an),
            col_categ: cod_map.get(cod, cod),
            col_val:   val,
        })
    return pd.DataFrame(rows).dropna(subset=[col_val]) if rows else None


# ── Constante teritoriale ─────────────────────────────────────────────────────

# Regiuni principale (coduri BNS)
_REGIUNI_CODES = {
    "40": "Nord",
    "41": "Centru",
    "42": "Sud",
    "34": "Mun. Chisinau",
    "33": "UTA Gagauzia",
}

# Toate raioanele + municipii (exclusiv "Total pe tara" si coduri regionale)
_RAIOANE_CODES = {
    "35": "Mun. Balti",
    "3":  "Briceni",
    "10": "Donduseni",
    "11": "Drochia",
    "13": "Edinet",
    "14": "Falesti",
    "15": "Floresti",
    "16": "Glodeni",
    "21": "Ocnita",
    "24": "Riscani",
    "25": "Singerei",
    "26": "Soroca",
    "1":  "Anenii Noi",
    "6":  "Calarasi",
    "9":  "Criuleni",
    "12": "Dubasari",
    "17": "Hincesti",
    "18": "Ialoveni",
    "20": "Nisporeni",
    "22": "Orhei",
    "23": "Rezina",
    "28": "Soldanesti",
    "27": "Straseni",
    "31": "Telenesti",
    "32": "Ungheni",
    "2":  "Basarabeasca",
    "4":  "Cahul",
    "5":  "Cantemir",
    "7":  "Causeni",
    "8":  "Cimislia",
    "19": "Leova",
    "29": "Stefan Voda",
    "30": "Taraclia",
    "34": "Mun. Chisinau",
    "33": "UTA Gagauzia",
}

# Regiune parinte per raion (pentru colorare in grafice)
_RAION_REGIUNE = {
    "35": "Nord",  "3": "Nord",  "10": "Nord", "11": "Nord", "13": "Nord",
    "14": "Nord",  "15": "Nord", "16": "Nord", "21": "Nord", "24": "Nord",
    "25": "Nord",  "26": "Nord",
    "1":  "Centru","6":  "Centru","9":  "Centru","12":"Centru","17":"Centru",
    "18": "Centru","20": "Centru","22": "Centru","23":"Centru","28":"Centru",
    "27": "Centru","31": "Centru","32": "Centru",
    "2":  "Sud",   "4":  "Sud",   "5":  "Sud",  "7": "Sud",  "8": "Sud",
    "19": "Sud",   "29": "Sud",   "30": "Sud",
    "34": "Chisinau",
    "33": "Gagauzia",
}

_REGIUNE_COLOR = {
    "Nord":     "#185FA5",
    "Centru":   "#1D9E75",
    "Sud":      "#E8A823",
    "Chisinau": "#534AB7",
    "Gagauzia": "#E24B4A",
}

# Culturi disponibile in AGR020600reg
_CULTURI_REG_CODES = {
    "0":  "Cereale",
    "7":  "Porumb",
    "14": "Floarea-soarelui",
    "15": "Soia",
    "17": "Cartofi",
    "18": "Legume",
}

# Specii disponibile in AGR030300reg
_SPECII_REG_CODES = {
    "0": "Bovine",
    "2": "Porcine",
    "3": "Ovine/Caprine",
}


# ── 5. Culturi regionale ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_culturi_regionale_bns(ani: list = None) -> dict:
    """
    AGR020600reg — Productia globala (mii tone) pe culturi si regiuni/raioane.
    Valori in chintale → /10000 = mii tone.

    Returneaza:
      {"data": DataFrame[an, cod_reg, regiune, regiune_parinte, cultura, recolta_mii_tone],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2019, 2026)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    toate_cod = list(dict.fromkeys(list(_REGIUNI_CODES.keys()) + list(_RAIOANE_CODES.keys())))

    query = {
        "query": [
            {"code": "Raioane/Regiuni",
             "selection": {"filter": "item", "values": toate_cod}},
            {"code": "Culturi agricole",
             "selection": {"filter": "item",
                           "values": list(_CULTURI_REG_CODES.keys())}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Indicatori",
             "selection": {"filter": "item", "values": ["2"]}},  # Productia globala, chintale
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_AGR020600R}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_agr_regional_culturi(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True, "ts": ts, "eroare": None}
            err_msg = "parse esuat"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False, "ts": ts,
            "eroare": f"AGR020600reg: {err_msg}"}


# ── 6. Animale regionale ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_animale_regionale_bns(ani: list = None) -> dict:
    """
    AGR030300reg — Efectivul de animale (mii capete) pe specii si regiuni/raioane.
    Valori in capete → /1000 = mii capete.

    Returneaza:
      {"data": DataFrame[an, cod_reg, regiune, regiune_parinte, specie, mii_capete],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2019, 2027)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    toate_cod = list(dict.fromkeys(list(_REGIUNI_CODES.keys()) + list(_RAIOANE_CODES.keys())))

    query = {
        "query": [
            {"code": "Raioane/Regiuni",
             "selection": {"filter": "item", "values": toate_cod}},
            {"code": "Categorii  de gospodarii",
             "selection": {"filter": "item", "values": ["0"]}},
            {"code": "Specii de animale",
             "selection": {"filter": "item",
                           "values": list(_SPECII_REG_CODES.keys())}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_AGR030300R}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_agr_regional_animale(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True, "ts": ts, "eroare": None}
            err_msg = "parse esuat"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False, "ts": ts,
            "eroare": f"AGR030300reg: {err_msg}"}


def _parse_agr_regional_culturi(data: dict) -> pd.DataFrame | None:
    """
    AGR020600reg key: [Raioane/Regiuni, Culturi, Ani, Indicatori]
    Valori in chintale → / 10000 = mii tone.
    """
    if not isinstance(data, dict) or "data" not in data:
        return None
    toate_reg = {**_REGIUNI_CODES, **_RAIOANE_CODES}
    rows = []
    for item in data["data"]:
        cod_reg, cod_cult, an, _ = item["key"]
        val_str = item["values"][0]
        try:
            val = float(val_str) / 10000.0 if val_str and val_str.strip() not in ("..", "...", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        rows.append({
            "an":             int(an),
            "cod_reg":        cod_reg,
            "regiune":        toate_reg.get(cod_reg, cod_reg),
            "regiune_parinte":_RAION_REGIUNE.get(cod_reg, _REGIUNI_CODES.get(cod_reg, "?")),
            "este_regiune":   cod_reg in _REGIUNI_CODES,
            "cultura":        _CULTURI_REG_CODES.get(cod_cult, cod_cult),
            "recolta_mii_tone": val,
        })
    return pd.DataFrame(rows).dropna(subset=["recolta_mii_tone"]) if rows else None


def _parse_agr_regional_animale(data: dict) -> pd.DataFrame | None:
    """
    AGR030300reg key: [Raioane/Regiuni, Categorii, Specii, Ani]
    Valori in capete → / 1000 = mii capete.
    """
    if not isinstance(data, dict) or "data" not in data:
        return None
    toate_reg = {**_REGIUNI_CODES, **_RAIOANE_CODES}
    rows = []
    for item in data["data"]:
        cod_reg, _, cod_sp, an = item["key"]
        val_str = item["values"][0]
        try:
            val = float(val_str) / 1000.0 if val_str and val_str.strip() not in ("..", "...", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        rows.append({
            "an":             int(an),
            "cod_reg":        cod_reg,
            "regiune":        toate_reg.get(cod_reg, cod_reg),
            "regiune_parinte":_RAION_REGIUNE.get(cod_reg, _REGIUNI_CODES.get(cod_reg, "?")),
            "este_regiune":   cod_reg in _REGIUNI_CODES,
            "specie":         _SPECII_REG_CODES.get(cod_sp, cod_sp),
            "mii_capete":     val,
        })
    return pd.DataFrame(rows).dropna(subset=["mii_capete"]) if rows else None


def _parse_agr030200(data: dict) -> pd.DataFrame | None:
    """
    AGR030200: key = [produs_cod, Ani, categorie].
    Adauga coloana 'unitate' per produs.
    """
    if not isinstance(data, dict) or "data" not in data:
        return None
    rows = []
    for item in data["data"]:
        cod = item["key"][0]
        an  = item["key"][1]
        val_str = item["values"][0]
        try:
            val = float(val_str) if val_str and val_str.strip() not in ("..", "...", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        rows.append({
            "an":      int(an),
            "produs":  _ANIMALE_PROD_CODES.get(cod, cod),
            "valoare": val,
            "unitate": _ANIMALE_PROD_UNITS.get(cod, ""),
        })
    return pd.DataFrame(rows).dropna(subset=["valoare"]) if rows else None
