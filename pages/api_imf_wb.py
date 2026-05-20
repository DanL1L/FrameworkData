"""
IMF WEO & World Bank API Clients
  - IMF: imf.org/external/datamapper/api
  - World Bank: api.worldbank.org/v2
"""

import requests
import pandas as pd
import streamlit as st

IMF_BASE = "https://www.imf.org/external/datamapper/api/v1"
WB_BASE  = "https://api.worldbank.org/v2"
MD_ISO   = "MDA"   # codul Moldova pentru ambele API-uri


# ── IMF DataMapper API ─────────────────────────────────────────────────────

# Indicatori IMF WEO folositi in dashboard
IMF_INDICATORS = {
    "pib_crestere":        "NGDP_RPCH",   # Real GDP growth %
    "pib_nominal_usd":     "NGDPD",       # GDP nominal, mld USD
    "pib_pc_ppp":          "PPPPC",       # GDP per capita PPP
    "inflatie_ipc":        "PCPIPCH",     # CPI inflation %
    "deficit_ca_pib":      "BCA_NGDPDZ",  # Cont curent % PIB
    "deficit_bugetar_pib": "GGXCNL_NGDP", # Sold bugetar % PIB
    "datorie_publica_pib": "GGXWDG_NGDP", # Datorie publica % PIB
    "somaj":               "LUR",         # Rata somajului %
}


@st.cache_data(ttl=86400, show_spinner=False)
def imf_get_indicator(indicator_code: str, country: str = MD_ISO,
                      an_start: int = 2015, an_end: int = 2029) -> pd.DataFrame:
    """
    Extrage un indicator IMF WEO pentru o tara si interval de ani.
    Include si prognozele (an_end poate fi in viitor).
    """
    url = f"{IMF_BASE}/{indicator_code}/{country}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()

        values = data.get("values", {}).get(indicator_code, {}).get(country, {})
        records = [
            {"an": int(yr), "value": float(val)}
            for yr, val in values.items()
            if val is not None and an_start <= int(yr) <= an_end
        ]
        df = pd.DataFrame(records).sort_values("an").reset_index(drop=True)
        df["_sursa"] = "IMF WEO"
        return df
    except Exception as e:
        return _imf_fallback(indicator_code, an_start, an_end, str(e))


@st.cache_data(ttl=86400, show_spinner=False)
def imf_get_multiple(indicators: list, country: str = MD_ISO,
                     an_start: int = 2019, an_end: int = 2029) -> pd.DataFrame:
    """Extrage mai multi indicatori IMF si combina intr-un DataFrame wide."""
    frames = {}
    for code in indicators:
        df = imf_get_indicator(code, country, an_start, an_end)
        if not df.empty and "an" in df.columns:
            frames[code] = df.set_index("an")["value"]

    if not frames:
        return pd.DataFrame()

    return pd.DataFrame(frames).reset_index().rename(columns={"index": "an"})


@st.cache_data(ttl=86400, show_spinner=False)
def imf_comparatie_regionala(indicator_code: str, tari: dict = None,
                              an_start: int = 2019, an_end: int = 2024) -> pd.DataFrame:
    """
    Comparatie regionala pentru un indicator.
    tari: {"MDA": "Moldova", "ROU": "Romania", "UKR": "Ucraina", ...}
    """
    if tari is None:
        tari = {
            "MDA": "Moldova", "ROU": "Romania",
            "GEO": "Georgia", "ARM": "Armenia",
            "BGR": "Bulgaria", "UKR": "Ucraina"
        }

    frames = []
    for iso, nume in tari.items():
        df = imf_get_indicator(indicator_code, iso, an_start, an_end)
        if not df.empty and "an" in df.columns:
            df["tara"] = nume
            frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ── World Bank API ─────────────────────────────────────────────────────────

WB_INDICATORS = {
    "pib_usd":             "NY.GDP.MKTP.CD",   # GDP (current US$)
    "pib_crestere":        "NY.GDP.MKTP.KD.ZG", # GDP growth %
    "pib_pc_usd":          "NY.GDP.PCAP.CD",   # GDP per capita USD
    "inflatie":            "FP.CPI.TOTL.ZG",   # Inflation CPI %
    "somaj":               "SL.UEM.TOTL.ZS",   # Unemployment %
    "export_pib":          "NE.EXP.GNFS.ZS",   # Exports % GDP
    "import_pib":          "NE.IMP.GNFS.ZS",   # Imports % GDP
    "fdi_pib":             "BX.KLT.DINV.WD.GD.ZS",  # FDI % GDP
    "saracie_550":         "SI.POV.UMIC",       # Poverty < $5.50/day
    "salariu_minim":       "PA.NUS.PPP",        # PPP conversion
    "speranta_viata":      "SP.DYN.LE00.IN",   # Life expectancy
    "populatie":           "SP.POP.TOTL",       # Total population
}


@st.cache_data(ttl=86400, show_spinner=False)
def wb_get_indicator(indicator_code: str, country: str = MD_ISO,
                     an_start: int = 2010, an_end: int = 2024) -> pd.DataFrame:
    """
    Extrage un indicator World Bank pentru Moldova.
    """
    url = f"{WB_BASE}/country/{country}/indicator/{indicator_code}"
    params = {
        "format": "json",
        "per_page": 100,
        "date": f"{an_start}:{an_end}",
        "mrv": 15,
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        if len(data) < 2 or not data[1]:
            raise ValueError("Date goale de la World Bank")

        records = [
            {"an": int(item["date"]), "value": float(item["value"])}
            for item in data[1]
            if item.get("value") is not None
        ]
        df = pd.DataFrame(records).sort_values("an").reset_index(drop=True)
        df["_sursa"] = "World Bank"
        return df
    except Exception as e:
        return _wb_fallback(indicator_code, an_start, an_end, str(e))


@st.cache_data(ttl=86400, show_spinner=False)
def wb_get_multiple(indicators: list, country: str = MD_ISO,
                    an_start: int = 2015, an_end: int = 2024) -> pd.DataFrame:
    """DataFrame wide cu mai multi indicatori WB."""
    frames = {}
    for code in indicators:
        df = wb_get_indicator(code, country, an_start, an_end)
        if not df.empty and "an" in df.columns:
            frames[code] = df.set_index("an")["value"]

    if not frames:
        return pd.DataFrame()

    return pd.DataFrame(frames).reset_index().rename(columns={"index": "an"})


# ── Fallbacks ──────────────────────────────────────────────────────────────

def _imf_fallback(code, an_start, an_end, err) -> pd.DataFrame:
    """Returneaza date demo cand IMF API nu e accesibil."""
    from data.demo_data import YEARS, pib_real_growth, prog_medd

    demo_map = {
        "NGDP_RPCH": dict(zip(YEARS, pib_real_growth)),
        "PCPIPCH":   dict(zip(YEARS, [6.7, 7.1, 9.2, 30.2, 12.3, 5.2])),
    }
    if code in demo_map:
        records = [
            {"an": yr, "value": v}
            for yr, v in demo_map[code].items()
            if an_start <= yr <= an_end
        ]
        # adauga prognoze
        for i, yr in enumerate(range(2025, an_end + 1)):
            records.append({"an": yr, "value": prog_medd[min(i+1, len(prog_medd)-1)]})
    else:
        records = [{"an": yr, "value": None} for yr in range(an_start, an_end + 1)]

    df = pd.DataFrame(records).sort_values("an")
    df["_sursa"] = "IMF WEO (demo)"
    df["_error"] = err
    return df


def _wb_fallback(code, an_start, an_end, err) -> pd.DataFrame:
    import numpy as np
    df = pd.DataFrame({
        "an": range(an_start, an_end + 1),
        "value": np.nan,
        "_sursa": "World Bank (indisponibil)",
        "_error": err,
    })
    return df
