"""
utils/api_monetar.py
Date monetare din BNS PX-Web (serii trimestriale):

  FIN011600 — Agregate monetare M0 / M1 / M2 / M3 (mil. lei)
  FIN010400 — Soldul creditelor si depozitelor (fizice / juridice, mil. lei)

Cache: ttl=3600 (refresh automat la fiecare ora)
"""

import requests
import pandas as pd
import json
import streamlit as st
from datetime import datetime

BNS_BASE = "https://statbank.statistica.md/PxWeb/api/v1/ro"
HEADERS  = {"Content-Type": "application/json", "Accept": "application/json"}
TIMEOUT  = 12

ANI_REF = [str(a) for a in range(2018, 2026)]

_FIN011600_PATHS = [
    "40%20Statistica%20economica/25%20FIN/FIN010/serii%20trimestriale/FIN011600.px",
    "40%20Statistica%20economica/25%20FIN/FIN011/serii%20trimestriale/FIN011600.px",
    "40%20Statistica%20economica/25%20FIN/FIN010/FIN011600.px",
]

_FIN010400_PATHS = [
    "40%20Statistica%20economica/25%20FIN/FIN010/serii%20trimestriale/FIN010400.px",
    "40%20Statistica%20economica/25%20FIN/FIN010/FIN010400.px",
    "40%20Statistica%20economica/25%20FIN/FIN010/serii%20anuale/FIN010400.px",
]

_TRIM_MAP = {
    "I": "T1", "II": "T2", "III": "T3", "IV": "T4", "I-IV": "Anual",
    "0": "T1", "1":  "T2", "2":  "T3", "3":  "T4", "4":    "Anual",
    "Trimestrul I": "T1", "Trimestrul II": "T2",
    "Trimestrul III": "T3", "Trimestrul IV": "T4",
}

# ── Fallback anual (medii/solduri la sfarsit de an, mil. lei) ─────────────────
_FALLBACK_AGR = {
    "an":  [2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "M0":  [17120, 19820, 22190, 29130, 26840, 29110, 31200],
    "M1":  [38420, 44560, 53280, 71440, 63710, 74820, 82100],
    "M2":  [82340, 98430, 117640, 147280, 134510, 161840, 183400],
    "M3":  [91870, 109850, 131570, 163200, 150320, 180240, 204600],
}

_FALLBACK_CR_DEP = {
    "an":              [2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "credite_fizice":  [14280, 17830, 18420, 23140, 30210, 38640, 47120],
    "credite_juridice":[21430, 24560, 21830, 25680, 31540, 37820, 43200],
    "dep_fizice":      [44120, 54320, 62840, 81430, 76890, 94280, 108700],
    "dep_juridice":    [18340, 21480, 27340, 34860, 31240, 38420, 44100],
}


# ── Helpers interni ───────────────────────────────────────────────────────────

def _post(path: str, payload: dict) -> dict | None:
    try:
        r = requests.post(f"{BNS_BASE}/{path}", headers=HEADERS,
                          data=json.dumps(payload), timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _raw(data: dict) -> pd.DataFrame | None:
    if not isinstance(data, dict) or "columns" not in data or "data" not in data:
        return None
    try:
        cols = [c["text"] for c in data["columns"]]
        rows = [item["key"] + item["values"] for item in data["data"]]
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=cols)
        null_vals = {"..", "...", "-", "n/a", "", "N/A"}
        df.iloc[:, -1] = df.iloc[:, -1].apply(
            lambda v: None if str(v).strip() in null_vals else v
        )
        df.iloc[:, -1] = pd.to_numeric(df.iloc[:, -1], errors="coerce")
        return df
    except Exception:
        return None


def _trim_label(raw: str) -> str:
    return _TRIM_MAP.get(str(raw).strip(), str(raw).strip())


def _an_col(df: pd.DataFrame) -> str | None:
    return next((c for c in df.columns if c.lower() in ("ani", "an", "year", "years")), None)


def _trim_col(df: pd.DataFrame) -> str | None:
    return next((c for c in df.columns if "trim" in c.lower()), None)


def _ind_col(df: pd.DataFrame, val_col: str, an_c: str, trim_c: str | None) -> str | None:
    exclude = {val_col, an_c}
    if trim_c:
        exclude.add(trim_c)
    return next((c for c in df.columns if c not in exclude), None)


# ── 1. Agregate monetare M0 / M1 / M2 / M3 ───────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_agregate_monetare_bns(ani: list = None) -> dict:
    """
    Agregate monetare M0/M1/M2/M3 din BNS FIN011600 (trimestriale).

    Returneaza:
      {"data": DataFrame[an, trim, trim_label, M0, M1, M2, M3] (mil. lei),
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    payload = {
        "query": [
            {"code": "Indicatori", "selection": {"filter": "all", "values": []}},
            {"code": "Ani",        "selection": {"filter": "item", "values": ani}},
            {"code": "Trimestre",  "selection": {"filter": "all", "values": []}},
        ],
        "response": {"format": "json"},
    }

    for path in _FIN011600_PATHS:
        data = _post(path, payload)
        df_raw = _raw(data)
        if df_raw is not None:
            result = _parse_agregate(df_raw)
            if result is not None and not result.empty:
                return {"data": result, "live": True, "ts": ts, "eroare": None}

    df_fb = pd.DataFrame(_FALLBACK_AGR)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False, "ts": ts,
            "eroare": "API BNS FIN011600 indisponibil — date de referinta"}


def _parse_agregate(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    try:
        val_col  = df.columns[-1]
        an_c     = _an_col(df)
        trim_c   = _trim_col(df)
        ind_c    = _ind_col(df, val_col, an_c or "", trim_c)

        if an_c is None or ind_c is None:
            return None

        df = df.copy()
        df[an_c]    = pd.to_numeric(df[an_c], errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        idx = [an_c] + ([trim_c] if trim_c else [])
        pivot = df.pivot_table(index=idx, columns=ind_c, values=val_col, aggfunc="first")
        pivot = pivot.reset_index()
        pivot.columns.name = None

        # Detecta M0–M3 dupa nume
        rename = {an_c: "an"}
        for c in pivot.columns:
            cl = str(c).lower()
            if "m0" in cl or "baza monetara" in cl or "bani in circulatie" in cl:
                rename[c] = "M0"
            elif "m1" in cl and "m1" not in str(rename.values()):
                rename[c] = "M1"
            elif "m2" in cl and "m2" not in str(rename.values()):
                rename[c] = "M2"
            elif "m3" in cl and "m3" not in str(rename.values()):
                rename[c] = "M3"
        pivot = pivot.rename(columns=rename)

        if trim_c:
            rename[trim_c] = "trim"
            pivot = pivot.rename(columns={trim_c: "trim"})
            pivot["trim_label"] = pivot["trim"].apply(_trim_label)

        needed = {"an", "M0"}
        if not needed.issubset(set(pivot.columns)):
            return None

        return pivot.sort_values(["an"] + (["trim"] if "trim" in pivot.columns else [])).reset_index(drop=True)
    except Exception:
        return None


# ── 2. Soldul creditelor si depozitelor (FIN010400) ──────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_credite_depozite_bns(ani: list = None) -> dict:
    """
    Soldul creditelor si depozitelor bancare din BNS FIN010400 (trimestriale).

    Returneaza:
      {"data": DataFrame[an, trim, trim_label,
                          credite_fizice, credite_juridice, dep_fizice, dep_juridice]
               (mil. lei),
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    payload = {
        "query": [
            {"code": "Indicatori", "selection": {"filter": "all", "values": []}},
            {"code": "Ani",        "selection": {"filter": "item", "values": ani}},
            {"code": "Trimestre",  "selection": {"filter": "all", "values": []}},
        ],
        "response": {"format": "json"},
    }

    for path in _FIN010400_PATHS:
        data = _post(path, payload)
        df_raw = _raw(data)
        if df_raw is not None:
            result = _parse_credite_dep(df_raw)
            if result is not None and not result.empty:
                return {"data": result, "live": True, "ts": ts, "eroare": None}

    df_fb = pd.DataFrame(_FALLBACK_CR_DEP)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False, "ts": ts,
            "eroare": "API BNS FIN010400 indisponibil — date de referinta"}


def _parse_credite_dep(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    try:
        val_col = df.columns[-1]
        an_c    = _an_col(df)
        trim_c  = _trim_col(df)
        ind_c   = _ind_col(df, val_col, an_c or "", trim_c)

        if an_c is None or ind_c is None:
            return None

        df = df.copy()
        df[an_c]    = pd.to_numeric(df[an_c], errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        idx = [an_c] + ([trim_c] if trim_c else [])
        pivot = df.pivot_table(index=idx, columns=ind_c, values=val_col, aggfunc="first")
        pivot = pivot.reset_index()
        pivot.columns.name = None

        rename = {an_c: "an"}
        for c in pivot.columns:
            cl = str(c).lower()
            if ("credit" in cl or "imprumut" in cl) and ("fizic" in cl or "persoane fizice" in cl):
                rename[c] = "credite_fizice"
            elif ("credit" in cl or "imprumut" in cl) and ("juridic" in cl or "persoane juridice" in cl):
                rename[c] = "credite_juridice"
            elif ("depozit" in cl) and ("fizic" in cl or "persoane fizice" in cl):
                rename[c] = "dep_fizice"
            elif ("depozit" in cl) and ("juridic" in cl or "persoane juridice" in cl):
                rename[c] = "dep_juridice"
        pivot = pivot.rename(columns=rename)

        if trim_c:
            pivot = pivot.rename(columns={trim_c: "trim"})
            pivot["trim_label"] = pivot["trim"].apply(_trim_label)

        if "an" not in pivot.columns:
            return None

        return pivot.sort_values(["an"] + (["trim"] if "trim" in pivot.columns else [])).reset_index(drop=True)
    except Exception:
        return None
