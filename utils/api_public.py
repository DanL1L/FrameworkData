"""
utils/api_public.py
Date finante publice din BNS PX-Web (serii trimestriale):

  FIN010100 — Executia bugetului public national
              venituri totale / cheltuieli totale / sold (mil. lei)

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

_FIN010100_PATHS = [
    "40%20Statistica%20economica/25%20FIN/FIN010/serii%20trimestriale/FIN010100.px",
    "40%20Statistica%20economica/25%20FIN/FIN010/FIN010100.px",
    "40%20Statistica%20economica/25%20FIN/FIN010/serii%20anuale/FIN010100.px",
]

_TRIM_MAP = {
    "I": "T1", "II": "T2", "III": "T3", "IV": "T4", "I-IV": "Anual",
    "0": "T1", "1":  "T2", "2":  "T3", "3":  "T4", "4":    "Anual",
    "Trimestrul I": "T1", "Trimestrul II": "T2",
    "Trimestrul III": "T3", "Trimestrul IV": "T4",
}

# ── Fallback anual (mld. lei) ─────────────────────────────────────────────────
_FALLBACK_BUGET = {
    "an":          [2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "venituri":    [38.1, 42.4, 42.1, 51.6, 63.8, 77.2, 88.4],
    "cheltuieli":  [40.2, 44.7, 47.8, 56.3, 71.2, 89.4, 103.1],
    "sold":        [-2.1, -2.3, -5.7, -4.7, -7.4, -12.2, -14.7],
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


# ── Executia bugetului public national (FIN010100) ───────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_buget_trim_bns(ani: list = None) -> dict:
    """
    Executia bugetului public national — date trimestriale BNS FIN010100.

    Returneaza:
      {"data": DataFrame[an, trim, trim_label, venituri, cheltuieli, sold] (mld. lei),
       "live": bool, "ts": str, "eroare": str|None}

    Nota: valorile sunt convertite din mil. lei in mld. lei (/ 1000).
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

    for path in _FIN010100_PATHS:
        data = _post(path, payload)
        df_raw = _raw(data)
        if df_raw is not None:
            result = _parse_buget(df_raw)
            if result is not None and not result.empty:
                return {"data": result, "live": True, "ts": ts, "eroare": None}

    df_fb = pd.DataFrame(_FALLBACK_BUGET)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False, "ts": ts,
            "eroare": "API BNS FIN010100 indisponibil — date de referinta"}


def _parse_buget(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    try:
        val_col = df.columns[-1]
        an_c    = _an_col(df)
        trim_c  = _trim_col(df)

        if an_c is None:
            return None

        # Coloana indicator (altceva decat an/trim/val)
        exclude = {val_col, an_c} | ({trim_c} if trim_c else set())
        ind_c   = next((c for c in df.columns if c not in exclude), None)

        df = df.copy()
        df[an_c]    = pd.to_numeric(df[an_c], errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        if ind_c:
            idx = [an_c] + ([trim_c] if trim_c else [])
            pivot = df.pivot_table(index=idx, columns=ind_c, values=val_col, aggfunc="first")
            pivot = pivot.reset_index()
            pivot.columns.name = None

            rename = {an_c: "an"}
            for c in pivot.columns:
                cl = str(c).lower()
                if "sold" in cl or "deficit" in cl or "excedent" in cl:
                    rename[c] = "sold"
                elif "venit" in cl:
                    rename[c] = "venituri"
                elif "chelt" in cl:
                    rename[c] = "cheltuieli"
            pivot = pivot.rename(columns=rename)
        else:
            pivot = df.rename(columns={an_c: "an", val_col: "venituri"})
            if trim_c:
                pivot = pivot.rename(columns={trim_c: "trim"})

        if trim_c and trim_c in pivot.columns:
            pivot = pivot.rename(columns={trim_c: "trim"})
            pivot["trim_label"] = pivot["trim"].apply(_trim_label)
        elif "trim" in pivot.columns:
            pivot["trim_label"] = pivot["trim"].apply(_trim_label)

        # Conversie mil -> mld daca valorile sunt mari
        for col in ["venituri", "cheltuieli", "sold"]:
            if col in pivot.columns:
                med = pivot[col].abs().median()
                if pd.notna(med) and med > 1000:
                    pivot[col] = (pivot[col] / 1000).round(3)

        if "an" not in pivot.columns:
            return None

        sort_by = ["an"] + (["trim"] if "trim" in pivot.columns else [])
        return pivot.sort_values(sort_by).reset_index(drop=True)
    except Exception:
        return None
