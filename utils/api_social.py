"""
utils/api_social.py
Scraper date anuale sociale din BNS PX-Web:

  (1) Castigul salarial mediu lunar brut
      saved query: 61bba808-4c00-4a35-9c0d-946caaa33cb8
      tabel: SocEc/FM/TFM08

  (2) Rata de activitate, ocupare si somaj
      saved query: 08546b68-0d6b-4746-9623-1c5c50916b8f
      tabel: SocEc/FM/TFM01

  (3) Populatie ocupata si someri (nivel absolut, mii persoane)
      saved query: ef9f71d7-a859-4d5d-9c03-1cf128ff9616
      tabel: SocEc/FM/TFM03

Cache: ttl=3600 (refresh automat la fiecare ora)

Extindere ulterioara: adauga noi functii dupa acelasi pattern
si apeleaza-le in page_social.py.
"""

import requests
import pandas as pd
import json
import streamlit as st
from datetime import datetime

BNS_BASE   = "https://statbank.statistica.md/PxWeb/api/v1/ro"
HEADERS    = {"Content-Type": "application/json", "Accept": "application/json"}
TIMEOUT    = 12
ANI_REF    = [str(a) for a in range(2015, 2026)]

# ── Fallback — date cunoscute ─────────────────────────────────────────────────
_FALLBACK_SALARII = {
    "an":    [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "total": [3990, 4490, 5084, 5732, 6468, 7207, 8976, 11582, 13603, 15849],
}

_FALLBACK_PIATA_MUNCII = {
    "an":              [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "rata_activitate": [42.4, 42.2, 42.8, 42.5, 42.4, 40.9, 41.4, 41.8, 42.1, 41.9],
    "rata_ocupare":    [40.7, 40.5, 41.2, 40.9, 40.8, 39.3, 39.8, 40.2, 40.6, 40.4],
    "rata_somaj":      [4.0,  4.2,  3.7,  3.4,  3.2,  3.9,  3.4,  3.1,  3.4,  2.9],
}

_FALLBACK_POPULATIE = {
    "an":              [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "pop_ocupata_mii": [838.4, 849.1, 836.5, 832.4, 824.0, 793.7, 798.6, 808.2, 812.4, 805.1],
    "someri_mii":      [35.0,  37.2,  32.4,  29.5,  27.3,  32.1,  28.4,  26.1,  28.7,  24.2],
}


# ── 1. Castig salarial mediu lunar brut ──────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_salarii_anual(ani: list = None) -> dict:
    """
    Castigul salarial mediu lunar brut — date anuale din BNS.
    Saved query: 61bba808-4c00-4a35-9c0d-946caaa33cb8

    Returneaza:
      {"data": DataFrame[an, total, ...sectoare], "live": bool,
       "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Tentativa 1: saved query GET
    df = _try_saved_query("61bba808-4c00-4a35-9c0d-946caaa33cb8")
    if df is not None:
        df = _normalizeaza_salarii(df)
        if df is not None:
            return {"data": df, "live": True,
                    "sursa": "BNS", "ts": ts, "eroare": None}

    # Tentativa 2: POST direct pe TFM08
    query = {
        "query": [
            {"code": "Activitati",
             "selection": {"filter": "item", "values": ["TOTAL"]}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
        ],
        "response": {"format": "json"}
    }
    for tabel in ["SocEc/FM/TFM08/FM08.px", "SocEc/FM/TFM08/TFM08.px",
                  "SocEc/FM/TFM08/SAL01.px"]:
        df = _try_post(tabel, query)
        if df is not None:
            df = _normalizeaza_salarii(df)
            if df is not None:
                return {"data": df, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    # Fallback
    df_fb = pd.DataFrame(_FALLBACK_SALARII)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False,
            "sursa": "BNS",
            "ts": ts, "eroare": "API BNS indisponibil"}


# ── 2. Rata activitate, ocupare, somaj ───────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_piata_muncii_anual(ani: list = None) -> dict:
    """
    Rata de activitate, ocupare si somaj — date anuale din BNS.
    Saved query: 08546b68-0d6b-4746-9623-1c5c50916b8f

    Returneaza:
      {"data": DataFrame[an, rata_activitate, rata_ocupare, rata_somaj],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Tentativa 1: saved query GET
    df = _try_saved_query("08546b68-0d6b-4746-9623-1c5c50916b8f")
    if df is not None:
        df = _normalizeaza_piata(df)
        if df is not None:
            return {"data": df, "live": True,
                    "sursa": "BNS", "ts": ts, "eroare": None}

    # Tentativa 2: POST direct pe TFM01
    query = {
        "query": [
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
        ],
        "response": {"format": "json"}
    }
    for tabel in ["SocEc/FM/TFM01/FM01.px", "SocEc/FM/TFM01/TFM01.px",
                  "SocEc/FM/TFM01/SOM01.px"]:
        df = _try_post(tabel, query)
        if df is not None:
            df = _normalizeaza_piata(df)
            if df is not None:
                return {"data": df, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    # Fallback
    df_fb = pd.DataFrame(_FALLBACK_PIATA_MUNCII)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False,
            "sursa": "BNS ",
            "ts": ts, "eroare": "API BNS indisponibil"}


# ── 3. Populatie ocupata si someri (nivel absolut, mii persoane) ─────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_populatie_someri_anual(ani: list = None) -> dict:
    """
    Populatie ocupata si numar someri — date anuale BNS, mii persoane.
    Saved query: ef9f71d7-a859-4d5d-9c03-1cf128ff9616
    Tabel BNS: SocEc/FM/TFM03 (populatie ocupata) / TFM01 (someri absolut)

    Returneaza:
      {"data": DataFrame[an, pop_ocupata_mii, someri_mii],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Tentativa 1: saved query GET
    df = _try_saved_query("ef9f71d7-a859-4d5d-9c03-1cf128ff9616")
    if df is not None:
        df = _normalizeaza_populatie(df)
        if df is not None:
            return {"data": df, "live": True,
                    "sursa": "BNS", "ts": ts, "eroare": None}

    # Tentativa 2: POST pe TFM03 (populatie ocupata + someri)
    query_q = {
        "query": [
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
        ],
        "response": {"format": "json"}
    }
    for tabel in ["SocEc/FM/TFM03/FM03.px", "SocEc/FM/TFM03/TFM03.px",
                  "SocEc/FM/TFM03/OCC01.px", "SocEc/FM/TFM01/FM01.px"]:
        df = _try_post(tabel, query_q)
        if df is not None:
            df = _normalizeaza_populatie(df)
            if df is not None:
                return {"data": df, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    # Fallback
    df_fb = pd.DataFrame(_FALLBACK_POPULATIE)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False,
            "sursa": "BNS",
            "ts": ts, "eroare": "API BNS indisponibil"}


# ── Helpers interni ───────────────────────────────────────────────────────────

def _try_saved_query(sq_id: str) -> pd.DataFrame | None:
    """GET pe endpoint saved query BNS."""
    try:
        r = requests.get(
            f"{BNS_BASE}/sq/{sq_id}",
            headers=HEADERS, timeout=TIMEOUT
        )
        if r.status_code == 200:
            return _parse_pxweb(r.json())
    except Exception:
        pass
    return None


def _try_post(tabel: str, query: dict) -> pd.DataFrame | None:
    """POST pe un tabel PX-Web."""
    try:
        r = requests.post(
            f"{BNS_BASE}/{tabel}",
            headers=HEADERS,
            data=json.dumps(query),
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return _parse_pxweb(r.json())
    except Exception:
        pass
    return None


def _parse_pxweb(data: dict) -> pd.DataFrame | None:
    """Converteste raspuns PX-Web JSON la DataFrame raw."""
    if not isinstance(data, dict):
        return None
    if "columns" not in data or "data" not in data:
        return None
    try:
        cols = [c["text"] for c in data["columns"]]
        rows = [item["key"] + item["values"] for item in data["data"]]
        df = pd.DataFrame(rows, columns=cols)
        # ultima coloana = valoarea numerica
        df.iloc[:, -1] = pd.to_numeric(df.iloc[:, -1], errors="coerce")
        return df
    except Exception:
        return None


def _normalizeaza_salarii(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Normalizeaza DataFrame raw PX-Web la:
      [an (int), total (float), ...coloane_sectoare]
    """
    if df is None or df.empty:
        return None
    try:
        # Detecta coloana An
        an_col  = next((c for c in df.columns if "an" in c.lower() or "year" in c.lower()), None)
        val_col = df.columns[-1]

        if an_col is None:
            return None

        # Daca exista coloana de activitate/sector → pivot
        act_col = next((c for c in df.columns
                        if c not in [an_col, val_col]
                        and ("activit" in c.lower() or "sector" in c.lower()
                             or "tip" in c.lower())), None)

        if act_col:
            df[an_col]  = pd.to_numeric(df[an_col],  errors="coerce")
            df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
            pivot = df.pivot_table(index=an_col, columns=act_col,
                                   values=val_col, aggfunc="mean")
            pivot = pivot.reset_index().rename(columns={an_col: "an"})
            pivot.columns.name = None
            # standardizeaza coloana total
            total_col = next((c for c in pivot.columns
                              if "total" in str(c).lower() or c == "Total"), None)
            if total_col:
                pivot = pivot.rename(columns={total_col: "total"})
            return pivot.sort_values("an").reset_index(drop=True)
        else:
            df = df.rename(columns={an_col: "an", val_col: "total"})
            df["an"] = pd.to_numeric(df["an"], errors="coerce")
            return df[["an","total"]].dropna().sort_values("an").reset_index(drop=True)

    except Exception:
        return None


def _normalizeaza_piata(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Normalizeaza DataFrame raw PX-Web la:
      [an (int), rata_activitate, rata_ocupare, rata_somaj]
    """
    if df is None or df.empty:
        return None
    try:
        an_col  = next((c for c in df.columns if "an" in c.lower() or "year" in c.lower()), None)
        val_col = df.columns[-1]
        ind_col = next((c for c in df.columns
                        if c not in [an_col, val_col]
                        and ("indicator" in c.lower() or "rata" in c.lower()
                             or "tip" in c.lower())), None)

        if an_col is None:
            return None

        df[an_col]  = pd.to_numeric(df[an_col],  errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        if ind_col:
            pivot = df.pivot_table(index=an_col, columns=ind_col,
                                   values=val_col, aggfunc="mean")
            pivot = pivot.reset_index().rename(columns={an_col: "an"})
            pivot.columns.name = None

            # Mapare flexibila la coloane standard
            rename = {}
            for c in pivot.columns:
                cl = str(c).lower()
                if "activit" in cl:
                    rename[c] = "rata_activitate"
                elif "ocup" in cl:
                    rename[c] = "rata_ocupare"
                elif "somaj" in cl or "șomaj" in cl or "somer" in cl:
                    rename[c] = "rata_somaj"
            pivot = pivot.rename(columns=rename)
            return pivot.sort_values("an").reset_index(drop=True)
        else:
            # DataFrame cu o singura serie — returneaza ca rata_somaj (default)
            df = df.rename(columns={an_col: "an", val_col: "rata_somaj"})
            return df[["an","rata_somaj"]].dropna().sort_values("an").reset_index(drop=True)

    except Exception:
        return None


def _normalizeaza_populatie(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Normalizeaza DataFrame raw PX-Web la:
      [an (int), pop_ocupata_mii (float), someri_mii (float)]

    Accepta structuri diferite:
      - Tabel cu coloana indicator (pivot pe ocupati/someri)
      - Tabel cu doua coloane numerice (populatie + someri)
      - Tabel cu o singura serie (populatie ocupata)
    """
    if df is None or df.empty:
        return None
    try:
        an_col  = next((c for c in df.columns
                        if "an" in c.lower() or "year" in c.lower()), None)
        val_col = df.columns[-1]

        if an_col is None:
            return None

        df[an_col]  = pd.to_numeric(df[an_col],  errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        # Detecta coloana de indicator (tip populatie/someri)
        ind_col = next((c for c in df.columns
                        if c not in [an_col, val_col]
                        and any(kw in c.lower() for kw in
                                ["indicator", "tip", "categor", "populat", "somer"])),
                       None)

        if ind_col:
            pivot = df.pivot_table(index=an_col, columns=ind_col,
                                   values=val_col, aggfunc="mean")
            pivot = pivot.reset_index().rename(columns={an_col: "an"})
            pivot.columns.name = None

            rename = {}
            for c in pivot.columns:
                cl = str(c).lower()
                if any(kw in cl for kw in ["ocup", "employ", "activ"]):
                    rename[c] = "pop_ocupata_mii"
                elif any(kw in cl for kw in ["somer", "unemploy", "sомaj"]):
                    rename[c] = "someri_mii"
            pivot = pivot.rename(columns=rename)

            # Asigura ca avem cel putin o coloana utila
            has_occ = "pop_ocupata_mii" in pivot.columns
            has_som = "someri_mii" in pivot.columns
            if has_occ or has_som:
                return pivot.sort_values("an").reset_index(drop=True)

        # Fallback: o singura serie numerica → presupunem populatie ocupata
        result = df[[an_col, val_col]].rename(
            columns={an_col: "an", val_col: "pop_ocupata_mii"}
        ).dropna().sort_values("an").reset_index(drop=True)
        return result if not result.empty else None

    except Exception:
        return None


# ── Status test ───────────────────────────────────────────────────────────────

def test_social_api() -> dict:
    try:
        r = requests.get(BNS_BASE, headers=HEADERS, timeout=TIMEOUT)
        return {"status": "ok" if r.status_code == 200 else "error",
                "ms": int(r.elapsed.total_seconds() * 1000)}
    except Exception as e:
        return {"status": "error", "msg": str(e)}