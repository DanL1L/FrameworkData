"""
utils/api_productie.py — Productia industriala si agricola (total, mil. lei)
Sursa: BNS PX-Web API, tabele anuale cu preturi curente.

Tabele incercate (caile exacte nu sunt confirmate, se incearca in ordine):
  IND010100 / IND0101 — Productia industriala (mil. lei, preturi curente)
  AGR010100 / AGR010  — Productia globala agricola (mil. lei, preturi curente)
"""

import requests
import pandas as pd
import json
import streamlit as st
from datetime import datetime

BNS_BASE = "https://statbank.statistica.md/PxWeb/api/v1/ro"
HEADERS  = {"Content-Type": "application/json", "Accept": "application/json"}
TIMEOUT  = 15

_NULL_VALS = {"..", "...", "-", "n/a", "N/A", ""}

_IND_PATHS = [
    "40%20Statistica%20economica/14%20Industrie/IND010/IND010100.px",
    "40%20Statistica%20economica/14%20Industrie/IND010/IND0101.px",
    "40%20Statistica%20economica/15%20IND/IND010/IND010100.px",
    "40%20Statistica%20economica/14%20IND/IND010/IND010100.px",
    "40%20Statistica%20economica/14%20Industrie/IND010100.px",
]

_AGR_VAL_PATHS = [
    "40%20Statistica%20economica/16%20AGR/AGR010/AGR010100.px",
    "40%20Statistica%20economica/16%20AGR/AGR010/serii%20anuale/AGR010100.px",
    "40%20Statistica%20economica/16%20AGR/AGR010/AGR010200.px",
    "40%20Statistica%20economica/16%20AGR/AGR010/AGR010000.px",
]


def _parse_annual_total(data: dict) -> pd.DataFrame | None:
    """
    Parser generic pentru tabele BNS cu structura [... Ani ... valoare].
    Returneaza DataFrame cu coloanele [an (int), valoare_mil_lei (float)],
    agregate (suma) pe an — ignora subtotaluri, ia maximul per an.
    """
    if not isinstance(data, dict) or "data" not in data:
        return None

    meta_cols = data.get("columns", [])
    col_codes  = [c.get("code", "") for c in meta_cols]

    # Gaseste indexul dimensiunii "Ani" / "An" / "Years"
    an_idx = None
    for i, code in enumerate(col_codes):
        if any(k in code.lower() for k in ("ani", "an", "year")):
            an_idx = i
            break

    rows = []
    for item in data["data"]:
        key    = item.get("key", [])
        val_str = (item.get("values") or [None])[0]
        try:
            val = float(val_str) if val_str and str(val_str).strip() not in _NULL_VALS else None
        except (ValueError, TypeError):
            val = None

        # Determina anul
        an = None
        if an_idx is not None and an_idx < len(key):
            try:
                an = int(key[an_idx])
            except (ValueError, TypeError):
                pass
        if an is None:
            for k in key:
                try:
                    v = int(k)
                    if 2000 <= v <= 2030:
                        an = v
                        break
                except (ValueError, TypeError):
                    pass

        if an is not None and val is not None and val > 0:
            rows.append({"an": an, "valoare_mil_lei": val})

    if not rows:
        return None

    df = pd.DataFrame(rows)
    # Ia maximul pe an (evita dubla-numarare a subtotalurilor)
    df = df.groupby("an")["valoare_mil_lei"].max().reset_index()
    df = df.sort_values("an").reset_index(drop=True)
    return df if not df.empty else None


def _fetch_paths(paths: list[str], label: str) -> dict:
    ts      = datetime.now().strftime("%Y-%m-%d %H:%M")
    query   = {"query": [], "response": {"format": "json"}}
    err_msg = ""

    for path in paths:
        try:
            r = requests.post(
                f"{BNS_BASE}/{path}",
                headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT,
            )
            if r.status_code == 200:
                df = _parse_annual_total(r.json())
                if df is not None and not df.empty:
                    tbl = path.split("/")[-1].replace(".px", "")
                    return {"data": df, "live": True,
                            "sursa": f"BNS {tbl} — live ({ts})",
                            "ts": ts, "eroare": None}
                err_msg = f"parse esuat ({path.split('/')[-1]})"
            else:
                err_msg = f"HTTP {r.status_code} ({path.split('/')[-1]})"
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False,
            "sursa": f"BNS {label}", "ts": ts,
            "eroare": f"{label} indisponibil: {err_msg}"}


@st.cache_data(ttl=3600)
def get_productie_industriala_bns() -> dict:
    """
    Productia industriala totala (mil. lei, preturi curente), date anuale BNS.
    Returneaza {'data': df[an, valoare_mil_lei], 'live': bool, 'eroare': str|None}
    """
    return _fetch_paths(_IND_PATHS, "IND010100")


@st.cache_data(ttl=3600)
def get_productie_agricola_val_bns() -> dict:
    """
    Productia globala agricola totala (mil. lei, preturi curente), date anuale BNS.
    Returneaza {'data': df[an, valoare_mil_lei], 'live': bool, 'eroare': str|None}
    """
    return _fetch_paths(_AGR_VAL_PATHS, "AGR010100")
