"""
utils/api_comert_extern.py
Surse BNS PX-Web — Comert exterior pe tari si grupe de tari

Saved queries:
  Import pe tari:  adb8f8cc-85d9-480c-ab01-29ceb2622d63
  Export pe tari:  42a72b84-effc-45c7-961c-a43596ec9478
  Grupe de tari:   11dec439-841d-4284-8713-7ff7c3538e49

Tabele BNS:
  SocEc/CE/TCE05/ — Comert exterior pe tari si grupe de tari

Cache: ttl=3600
"""

import requests
import pandas as pd
import json
import streamlit as st
from datetime import datetime

BNS_BASE = "https://statbank.statistica.md/PxWeb/api/v1/ro"
HEADERS  = {"Content-Type": "application/json", "Accept": "application/json"}
TIMEOUT  = 15
ANI_REF  = [str(a) for a in range(2019, 2026)]

# ── Fallback date cunoscute ───────────────────────────────────────────────────

_FALLBACK_GRUPE = {
    "an": [2019, 2020, 2021, 2022, 2023, 2024],
    "grupe": {
        "UE":         {"export": [1340, 1310, 1640, 1780, 1890, 1970],
                       "import": [2680, 2430, 3210, 3320, 3380, 3510]},
        "CSI":        {"export": [620,  535,  640,  610,  530,  490],
                       "import": [1240, 1000, 1820, 1750, 1610, 1520]},
        "Alte state": {"export": [850,  795,  826,  798,  864,  961],
                       "import": [1900, 1710, 2352, 2492, 2658, 2780]},
    }
}

_FALLBACK_TOP_EXPORT = [
    {"tara": "România",      "valoare": 842},
    {"tara": "Italia",       "valoare": 298},
    {"tara": "Germania",     "valoare": 215},
    {"tara": "Turcia",       "valoare": 198},
    {"tara": "Polonia",      "valoare": 164},
    {"tara": "Marea Britanie","valoare": 142},
    {"tara": "Rusia",        "valoare": 128},
    {"tara": "Bulgaria",     "valoare": 117},
    {"tara": "Franța",       "valoare": 98},
    {"tara": "Cehia",        "valoare": 87},
]

_FALLBACK_TOP_IMPORT = [
    {"tara": "România",      "valoare": 1320},
    {"tara": "China",        "valoare": 820},
    {"tara": "Germania",     "valoare": 680},
    {"tara": "Turcia",       "valoare": 520},
    {"tara": "Italia",       "valoare": 410},
    {"tara": "Ucraina",      "valoare": 380},
    {"tara": "Polonia",      "valoare": 360},
    {"tara": "Rusia",        "valoare": 310},
    {"tara": "Franța",       "valoare": 290},
    {"tara": "Ungaria",      "valoare": 240},
]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Grupe de tari — pie chart CSI / UE / Alte state
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def get_grupe_tari(ani: list = None) -> dict:
    """
    Export si Import pe grupe de tari (UE / CSI / Alte state).
    Saved query: 11dec439-841d-4284-8713-7ff7c3538e49

    Returneaza:
      {"data": DataFrame[an, grupa, export_mil_usd, import_mil_usd],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    df = _try_saved_query("11dec439-841d-4284-8713-7ff7c3538e49")
    if df is not None:
        result = _normalizeaza_grupe(df)
        if result is not None:
            return {"data": result, "live": True,
                    "sursa": "BNS TCE05 (saved query)", "ts": ts, "eroare": None}

    # POST direct pe TCE05
    for tabel in ["SocEc/CE/TCE05/CE05.px", "SocEc/CE/TCE05/TCE05.px"]:
        df = _try_post(tabel, {
            "query": [{"code": "Ani", "selection": {"filter": "item", "values": ani}}],
            "response": {"format": "json"}
        })
        if df is not None:
            result = _normalizeaza_grupe(df)
            if result is not None:
                return {"data": result, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    # Fallback
    rows = []
    for grupa, vals in _FALLBACK_GRUPE["grupe"].items():
        for i, a in enumerate(_FALLBACK_GRUPE["an"]):
            if str(a) in ani:
                rows.append({
                    "an": a, "grupa": grupa,
                    "export_mil_usd": vals["export"][i],
                    "import_mil_usd": vals["import"][i],
                })
    df_fb = pd.DataFrame(rows)
    return {"data": df_fb, "live": False,
            "sursa": "BNS — date de referinta (offline)",
            "ts": ts, "eroare": "API BNS indisponibil"}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Export pe tari — top 10
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def get_export_tari(ani: list = None) -> dict:
    """
    Export pe tari partenere (mil. USD).
    Saved query: 42a72b84-effc-45c7-961c-a43596ec9478

    Returneaza:
      {"data": DataFrame[an, tara, export_mil_usd],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    df = _try_saved_query("42a72b84-effc-45c7-961c-a43596ec9478")
    if df is not None:
        result = _normalizeaza_tari(df, "export_mil_usd")
        if result is not None:
            return {"data": result, "live": True,
                    "sursa": "BNS TCE05 Export (saved query)", "ts": ts, "eroare": None}

    for tabel in ["SocEc/CE/TCE01/CE01.px", "SocEc/CE/TCE05/CE05.px"]:
        df = _try_post(tabel, {
            "query": [{"code": "Ani", "selection": {"filter": "item", "values": ani}}],
            "response": {"format": "json"}
        })
        if df is not None:
            result = _normalizeaza_tari(df, "export_mil_usd")
            if result is not None:
                return {"data": result, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    df_fb = pd.DataFrame(_FALLBACK_TOP_EXPORT).rename(columns={"valoare": "export_mil_usd"})
    df_fb["an"] = int(ani[-1]) if ani else 2024
    return {"data": df_fb, "live": False,
            "sursa": "BNS — date de referinta (offline)",
            "ts": ts, "eroare": "API BNS indisponibil"}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Import pe tari — top 10
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def get_import_tari(ani: list = None) -> dict:
    """
    Import pe tari partenere (mil. USD).
    Saved query: adb8f8cc-85d9-480c-ab01-29ceb2622d63

    Returneaza:
      {"data": DataFrame[an, tara, import_mil_usd],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    df = _try_saved_query("adb8f8cc-85d9-480c-ab01-29ceb2622d63")
    if df is not None:
        result = _normalizeaza_tari(df, "import_mil_usd")
        if result is not None:
            return {"data": result, "live": True,
                    "sursa": "BNS TCE05 Import (saved query)", "ts": ts, "eroare": None}

    for tabel in ["SocEc/CE/TCE02/CE02.px", "SocEc/CE/TCE05/CE05.px"]:
        df = _try_post(tabel, {
            "query": [{"code": "Ani", "selection": {"filter": "item", "values": ani}}],
            "response": {"format": "json"}
        })
        if df is not None:
            result = _normalizeaza_tari(df, "import_mil_usd")
            if result is not None:
                return {"data": result, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    df_fb = pd.DataFrame(_FALLBACK_TOP_IMPORT).rename(columns={"valoare": "import_mil_usd"})
    df_fb["an"] = int(ani[-1]) if ani else 2024
    return {"data": df_fb, "live": False,
            "sursa": "BNS — date de referinta (offline)",
            "ts": ts, "eroare": "API BNS indisponibil"}


# ═══════════════════════════════════════════════════════════════════════════════
# Normalizare
# ═══════════════════════════════════════════════════════════════════════════════

def _normalizeaza_grupe(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Normalizeaza raspuns PX-Web la:
      [an (int), grupa (str), export_mil_usd (float), import_mil_usd (float)]
    """
    if df is None or df.empty:
        return None
    try:
        an_col  = next((c for c in df.columns if "an" in c.lower() or "year" in c.lower()), None)
        val_col = df.columns[-1]
        if an_col is None:
            return None

        df[an_col]  = pd.to_numeric(df[an_col],  errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        # Cauta coloana grupa/tara
        grp_col = next((c for c in df.columns
                        if c not in [an_col, val_col]
                        and any(kw in c.lower() for kw in
                                ["grup", "tara", "tar", "country", "region"])), None)
        # Cauta coloana flux (export/import)
        flux_col = next((c for c in df.columns
                         if c not in [an_col, val_col, grp_col]
                         and any(kw in c.lower() for kw in
                                 ["flux", "tip", "export", "import", "indicator"])), None)

        if grp_col and flux_col:
            pivot = df.pivot_table(
                index=[an_col, grp_col], columns=flux_col,
                values=val_col, aggfunc="sum"
            ).reset_index()
            pivot.columns = [str(c).strip() for c in pivot.columns]
            pivot.columns.name = None

            # Redenumire flexibila
            rename = {an_col: "an", grp_col: "grupa"}
            for c in pivot.columns:
                cl = str(c).lower()
                if "export" in cl and "import" not in cl:
                    rename[c] = "export_mil_usd"
                elif "import" in cl:
                    rename[c] = "import_mil_usd"
            pivot = pivot.rename(columns=rename)

            has_exp = "export_mil_usd" in pivot.columns
            has_imp = "import_mil_usd" in pivot.columns
            if has_exp or has_imp:
                return pivot.sort_values("an").reset_index(drop=True)

        # Fallback: un singur indicator — returnam ca export
        if grp_col:
            result = df[[an_col, grp_col, val_col]].rename(columns={
                an_col: "an", grp_col: "grupa", val_col: "export_mil_usd"
            })
            return result.sort_values("an").reset_index(drop=True)

    except Exception:
        pass
    return None


def _normalizeaza_tari(df: pd.DataFrame, col_val: str) -> pd.DataFrame | None:
    """
    Normalizeaza raspuns PX-Web la:
      [an (int), tara (str), {col_val} (float)]
    """
    if df is None or df.empty:
        return None
    try:
        an_col  = next((c for c in df.columns if "an" in c.lower() or "year" in c.lower()), None)
        val_col = df.columns[-1]
        if an_col is None:
            return None

        df[an_col]  = pd.to_numeric(df[an_col],  errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        tara_col = next((c for c in df.columns
                         if c not in [an_col, val_col]
                         and any(kw in c.lower() for kw in
                                 ["tara", "tar", "country", "partener", "stat"])), None)

        if tara_col:
            result = df[[an_col, tara_col, val_col]].rename(columns={
                an_col: "an", tara_col: "tara", val_col: col_val
            })
            return result.dropna().sort_values("an").reset_index(drop=True)

    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _try_saved_query(sq_id: str) -> pd.DataFrame | None:
    try:
        r = requests.get(f"{BNS_BASE}/sq/{sq_id}",
                         headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            return _parse_pxweb(r.json())
    except Exception:
        pass
    return None


def _try_post(tabel: str, query: dict) -> pd.DataFrame | None:
    try:
        r = requests.post(f"{BNS_BASE}/{tabel}",
                          headers=HEADERS,
                          data=json.dumps(query),
                          timeout=TIMEOUT)
        if r.status_code == 200:
            return _parse_pxweb(r.json())
    except Exception:
        pass
    return None


def _parse_pxweb(data: dict) -> pd.DataFrame | None:
    if not isinstance(data, dict):
        return None
    if "columns" not in data or "data" not in data:
        return None
    try:
        cols = [c["text"] for c in data["columns"]]
        rows = [item["key"] + item["values"] for item in data["data"]]
        df = pd.DataFrame(rows, columns=cols)
        df.iloc[:, -1] = pd.to_numeric(df.iloc[:, -1], errors="coerce")
        return df
    except Exception:
        return None
