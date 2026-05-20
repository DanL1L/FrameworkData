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
                    "sursa": "BNS TFM08 (saved query)", "ts": ts, "eroare": None}

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
            "sursa": "BNS — date de referinta (offline)",
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
                    "sursa": "BNS TFM01 (saved query)", "ts": ts, "eroare": None}

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
            "sursa": "BNS — date de referinta (offline)",
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
                    "sursa": "BNS TFM03 (saved query)", "ts": ts, "eroare": None}

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
            "sursa": "BNS — date de referinta (offline)",
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


# ── 4. Populatie ocupata pe gen — barbati / femei / total ────────────────────

# Fallback — date cunoscute BNS (mii persoane, medii anuale)
_FALLBACK_POP_GEN = {
    "an":       [2015,  2016,  2017,  2018,  2019,  2020,  2021,  2022,  2023,  2024],
    "barbati":  [426.1, 432.2, 424.8, 422.5, 417.3, 401.8, 405.2, 411.4, 413.6, 408.2],
    "femei":    [412.3, 416.9, 411.7, 409.9, 406.7, 391.9, 393.4, 396.8, 398.8, 396.9],
    "total":    [838.4, 849.1, 836.5, 832.4, 824.0, 793.7, 798.6, 808.2, 812.4, 805.1],
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_populatie_gen_anual(ani: list = None) -> dict:
    """
    Populatie ocupata defalcata pe gen (barbati / femei / total) — date anuale BNS.
    Saved query: ef9f71d7-a859-4d5d-9c03-1cf128ff9616
    Tabel BNS:   SocEc/FM/TFM03

    Returneaza:
      {"data": DataFrame[an, barbati, femei, total],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Tentativa 1: saved query (returneaza date cu sex defalcat)
    df_raw = _try_saved_query("ef9f71d7-a859-4d5d-9c03-1cf128ff9616")
    if df_raw is not None:
        df = _normalizeaza_pop_gen(df_raw)
        if df is not None:
            return {"data": df, "live": True,
                    "sursa": "BNS TFM03 (saved query)", "ts": ts, "eroare": None}

    # Tentativa 2: POST pe TFM03 cu selectie sex
    query_gen = {
        "query": [
            {"code": "Sex",
             "selection": {"filter": "item", "values": ["1", "2", "TOT"]}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
        ],
        "response": {"format": "json"}
    }
    for tabel in ["SocEc/FM/TFM03/FM03.px", "SocEc/FM/TFM03/TFM03.px",
                  "SocEc/FM/TFM03/OCC01.px"]:
        df_raw = _try_post(tabel, query_gen)
        if df_raw is not None:
            df = _normalizeaza_pop_gen(df_raw)
            if df is not None:
                return {"data": df, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    # Tentativa 3: POST fara filtru sex (parsam ce vine)
    query_all = {
        "query": [
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
        ],
        "response": {"format": "json"}
    }
    for tabel in ["SocEc/FM/TFM03/FM03.px", "SocEc/FM/TFM03/TFM03.px"]:
        df_raw = _try_post(tabel, query_all)
        if df_raw is not None:
            df = _normalizeaza_pop_gen(df_raw)
            if df is not None:
                return {"data": df, "live": True,
                        "sursa": f"BNS {tabel}", "ts": ts, "eroare": None}

    # Fallback
    df_fb = pd.DataFrame(_FALLBACK_POP_GEN)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False,
            "sursa": "BNS — date de referinta (offline)",
            "ts": ts, "eroare": "API BNS indisponibil — se folosesc date de referinta"}


def _normalizeaza_pop_gen(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Normalizeaza raspunsul PX-Web la DataFrame wide:
      [an (int), barbati (float), femei (float), total (float)]

    Accepta structuri cu coloana Sex/Gen sau cu coloane separate.
    """
    if df is None or df.empty:
        return None
    try:
        an_col  = next((c for c in df.columns
                        if "an" in c.lower() or "year" in c.lower()), None)
        val_col = df.columns[-1]

        if an_col is None:
            return None

        df = df.copy()
        df[an_col]  = pd.to_numeric(df[an_col],  errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        # Detecta coloana de sex/gen
        sex_col = next((c for c in df.columns
                        if c not in [an_col, val_col]
                        and any(kw in c.lower() for kw in
                                ["sex", "gen", "masculin", "feminin", "barbat", "femei"])),
                       None)

        if sex_col:
            pivot = df.pivot_table(index=an_col, columns=sex_col,
                                   values=val_col, aggfunc="mean")
            pivot = pivot.reset_index().rename(columns={an_col: "an"})
            pivot.columns.name = None

            # Mapare flexibila la barbati / femei / total
            rename = {}
            for c in pivot.columns:
                cl = str(c).lower()
                if any(kw in cl for kw in ["masculin","barbat","male","m","b","1"]):
                    rename[c] = "barbati"
                elif any(kw in cl for kw in ["feminin","femei","female","f","2"]):
                    rename[c] = "femei"
                elif any(kw in cl for kw in ["total","ambele","tot","t","3"]):
                    rename[c] = "total"
            pivot = pivot.rename(columns=rename)

            has_b = "barbati" in pivot.columns
            has_f = "femei"   in pivot.columns
            has_t = "total"   in pivot.columns

            # Calculeaza total daca lipseste dar avem ambele genuri
            if has_b and has_f and not has_t:
                pivot["total"] = pivot["barbati"] + pivot["femei"]

            if has_b or has_f:
                return pivot.sort_values("an").reset_index(drop=True)

        # Nu am gasit coloana sex — returneaza doar total
        result = df[[an_col, val_col]].rename(
            columns={an_col: "an", val_col: "total"}
        ).dropna().sort_values("an").reset_index(drop=True)
        return result if not result.empty else None

    except Exception:
        return None


# ── 5. Salarii trimestriale BNS (SAL010) ─────────────────────────────────────

_SAL010_PATHS = [
    "40%20Statistica%20economica/11%20SAL/SAL010/serii%20trimestriale/SAL010.px",
    "40%20Statistica%20economica/11%20SAL/SAL010/SAL010.px",
    "SocEc/FM/TFM08/SAL010.px",
    "SocEc/FM/SAL010/SAL010.px",
]

_TRIM_MAP_SOC = {
    "I": "T1", "II": "T2", "III": "T3", "IV": "T4", "I-IV": "Anual",
    "0": "T1", "1":  "T2", "2":  "T3", "3":  "T4", "4":    "Anual",
    "Trimestrul I": "T1", "Trimestrul II": "T2",
    "Trimestrul III": "T3", "Trimestrul IV": "T4",
}

ANI_TRIM_REF = [str(a) for a in range(2018, 2026)]

_FALLBACK_SAL_TRIM = {
    "an":              [2019, 2020, 2021, 2022, 2023, 2024],
    "salariu_mediu_mdl": [6468, 7207, 8976, 11582, 13603, 15849],
}

_SAL020_PATHS = [
    "40%20Statistica%20economica/11%20SAL/SAL020/serii%20trimestriale/SAL020.px",
    "40%20Statistica%20economica/11%20SAL/SAL020/SAL020.px",
    "SocEc/FM/TFM01/SAL020.px",
    "SocEc/FM/SAL020/SAL020.px",
]

_FALLBACK_OCC_TRIM = {
    "an":              [2019, 2020, 2021, 2022, 2023, 2024],
    "rata_somaj":      [4.1,  3.8,  3.5,  3.2,  3.1,  2.9],
    "rata_ocupare":    [40.8, 39.3, 39.8, 40.2, 40.6, 40.4],
    "pop_ocupata_mii": [824.0, 793.7, 798.6, 808.2, 812.4, 805.1],
}


def _post_social(path: str, payload: dict) -> dict | None:
    try:
        r = requests.post(f"{BNS_BASE}/{path}", headers=HEADERS,
                          data=json.dumps(payload), timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _raw_social(data: dict) -> pd.DataFrame | None:
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


@st.cache_data(ttl=3600, show_spinner=False)
def get_salarii_trim_bns(ani: list = None) -> dict:
    """
    Castigul salarial mediu lunar brut — date trimestriale BNS SAL010.

    Returneaza:
      {"data": DataFrame[an, trim, trim_label, salariu_mediu_mdl],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_TRIM_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    payload = {
        "query": [
            {"code": "Ani",       "selection": {"filter": "item", "values": ani}},
            {"code": "Trimestre", "selection": {"filter": "all",  "values": []}},
        ],
        "response": {"format": "json"},
    }

    for path in _SAL010_PATHS:
        data = _post_social(path, payload)
        df_raw = _raw_social(data)
        if df_raw is not None:
            result = _parse_sal_trim(df_raw)
            if result is not None and not result.empty:
                return {"data": result, "live": True, "ts": ts, "eroare": None}

    df_fb = pd.DataFrame(_FALLBACK_SAL_TRIM)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False, "ts": ts,
            "eroare": "API BNS SAL010 indisponibil — date de referinta"}


def _parse_sal_trim(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    try:
        val_col = df.columns[-1]
        an_col  = next((c for c in df.columns if c.lower() in ("ani", "an")), None)
        tr_col  = next((c for c in df.columns if "trim" in c.lower()), None)

        if an_col is None:
            return None

        df = df.copy()
        df[an_col]  = pd.to_numeric(df[an_col], errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        # Daca exista dimensiune de activitate/total, filtreaza totalul
        other_cols = [c for c in df.columns if c not in {val_col, an_col, tr_col} and c]
        if other_cols:
            act_col = other_cols[0]
            # pastreaza doar randul "Total" sau primul indicator
            totals = df[df[act_col].str.lower().str.contains("total|total general", na=False)]
            if not totals.empty:
                df = totals

        result = df[[an_col] + ([tr_col] if tr_col else []) + [val_col]].copy()
        result = result.rename(columns={an_col: "an", val_col: "salariu_mediu_mdl"})
        if tr_col:
            result = result.rename(columns={tr_col: "trim"})
            result["trim_label"] = result["trim"].apply(
                lambda x: _TRIM_MAP_SOC.get(str(x).strip(), str(x).strip())
            )

        return result.dropna(subset=["salariu_mediu_mdl"]).sort_values(
            ["an"] + (["trim"] if "trim" in result.columns else [])
        ).reset_index(drop=True)
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_ocupare_trim_bns(ani: list = None) -> dict:
    """
    Piata muncii — date trimestriale BNS SAL020.
    Rata somaj, rata ocupare, populatie ocupata.

    Returneaza:
      {"data": DataFrame[an, trim, trim_label, rata_somaj, rata_ocupare, pop_ocupata_mii],
       "live": bool, "ts": str, "eroare": str|None}
    """
    ani = ani or ANI_TRIM_REF
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    payload = {
        "query": [
            {"code": "Indicatori", "selection": {"filter": "all", "values": []}},
            {"code": "Ani",        "selection": {"filter": "item", "values": ani}},
            {"code": "Trimestre",  "selection": {"filter": "all",  "values": []}},
        ],
        "response": {"format": "json"},
    }

    for path in _SAL020_PATHS:
        data = _post_social(path, payload)
        df_raw = _raw_social(data)
        if df_raw is not None:
            result = _parse_occ_trim(df_raw)
            if result is not None and not result.empty:
                return {"data": result, "live": True, "ts": ts, "eroare": None}

    df_fb = pd.DataFrame(_FALLBACK_OCC_TRIM)
    df_fb = df_fb[df_fb["an"].astype(str).isin(ani)].reset_index(drop=True)
    return {"data": df_fb, "live": False, "ts": ts,
            "eroare": "API BNS SAL020 indisponibil — date de referinta"}


def _parse_occ_trim(df: pd.DataFrame) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    try:
        val_col = df.columns[-1]
        an_col  = next((c for c in df.columns if c.lower() in ("ani", "an")), None)
        tr_col  = next((c for c in df.columns if "trim" in c.lower()), None)
        ind_col = next(
            (c for c in df.columns
             if c not in {val_col, an_col, tr_col}
             and any(kw in c.lower() for kw in ["indicator", "tip", "rata"])),
            next((c for c in df.columns if c not in {val_col, an_col, tr_col} and c), None)
        )

        if an_col is None:
            return None

        df = df.copy()
        df[an_col]  = pd.to_numeric(df[an_col], errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

        if ind_col:
            idx = [an_col] + ([tr_col] if tr_col else [])
            pivot = df.pivot_table(index=idx, columns=ind_col, values=val_col, aggfunc="first")
            pivot = pivot.reset_index()
            pivot.columns.name = None

            rename = {an_col: "an"}
            for c in pivot.columns:
                cl = str(c).lower()
                if "somaj" in cl or "șomaj" in cl or "unemploy" in cl:
                    rename[c] = "rata_somaj"
                elif "ocup" in cl:
                    rename[c] = "rata_ocupare"
                elif "populat" in cl or "mii pers" in cl:
                    rename[c] = "pop_ocupata_mii"
            pivot = pivot.rename(columns=rename)
        else:
            pivot = df.rename(columns={an_col: "an", val_col: "rata_somaj"})
            if tr_col:
                pivot = pivot.rename(columns={tr_col: "trim"})

        if tr_col and tr_col in pivot.columns:
            pivot = pivot.rename(columns={tr_col: "trim"})
            pivot["trim_label"] = pivot["trim"].apply(
                lambda x: _TRIM_MAP_SOC.get(str(x).strip(), str(x).strip())
            )
        elif "trim" in pivot.columns:
            pivot["trim_label"] = pivot["trim"].apply(
                lambda x: _TRIM_MAP_SOC.get(str(x).strip(), str(x).strip())
            )

        return pivot.sort_values(
            ["an"] + (["trim"] if "trim" in pivot.columns else [])
        ).reset_index(drop=True)
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