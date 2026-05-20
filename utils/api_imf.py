"""
IMF & World Bank API Integration
IMF:  https://www.imf.org/external/datamapper/api/
WB:   https://api.worldbank.org/v2/
"""

import requests
import pandas as pd
import streamlit as st

TIMEOUT   = 15
IMF_BASE  = "https://www.imf.org/external/datamapper/api/v1"
WB_BASE   = "https://api.worldbank.org/v2"
MD_ISO    = "MDA"  # cod ISO Moldova


# ── IMF DataMapper ────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def imf_indicator(indicator: str, country: str = MD_ISO) -> pd.DataFrame:
    """
    Extrage un indicator IMF WEO pentru o tara.
    Indicatori frecventi:
      NGDP_RPCH   → crestere PIB real (%)
      PCPIPCH     → inflatie IPC (%)
      BCA_NGDPD   → cont curent (% PIB)
      GGXWDG_NGDP → datorie guvernamentala bruta (% PIB)
      LUR         → rata somajului (%)
      NGDPDPC     → PIB pe cap de locuitor (USD)
    """
    url = f"{IMF_BASE}/indicators/{indicator}/countries/{country}"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        values = data.get("values", {}).get(indicator, {}).get(country, {})
        if values:
            df = pd.DataFrame(
                [(yr, val) for yr, val in values.items()],
                columns=["an", indicator]
            )
            df["an"] = df["an"].astype(int)
            df[indicator] = pd.to_numeric(df[indicator], errors="coerce")
            return df.sort_values("an")
        return pd.DataFrame({"eroare": ["Date indisponibile pentru acest indicator"]})
    except Exception as e:
        return pd.DataFrame({"eroare": [str(e)]})


@st.cache_data(ttl=86400, show_spinner=False)
def imf_weo_multi(indicators: list, country: str = MD_ISO,
                  ani_start: int = 2015) -> pd.DataFrame:
    """Extrage mai multi indicatori IMF si ii combina intr-un DataFrame."""
    dfs = []
    for ind in indicators:
        df = imf_indicator(ind, country)
        if "eroare" not in df.columns:
            df = df[df["an"] >= ani_start]
            dfs.append(df.set_index("an"))
    if dfs:
        return pd.concat(dfs, axis=1).reset_index()
    return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def imf_regional_compare(indicator: str,
                          countries: list = None) -> pd.DataFrame:
    """Compara Moldova cu tari din regiune."""
    if countries is None:
        countries = ["MDA","ROU","UKR","BGR","SRB","ARM","GEO"]
    labels = {"MDA":"Moldova","ROU":"Romania","UKR":"Ucraina",
              "BGR":"Bulgaria","SRB":"Serbia","ARM":"Armenia","GEO":"Georgia"}
    dfs = []
    for iso in countries:
        df = imf_indicator(indicator, iso)
        if "eroare" not in df.columns:
            df = df.rename(columns={indicator: labels.get(iso, iso)})
            dfs.append(df.set_index("an"))
    if dfs:
        return pd.concat(dfs, axis=1).reset_index()
    return pd.DataFrame()


# ── World Bank API ────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def wb_indicator(indicator: str, country: str = "MD",
                 ani_start: int = 2010) -> pd.DataFrame:
    """
    Extrage un indicator World Bank.
    Indicatori frecventi:
      NY.GDP.MKTP.KD.ZG  → crestere PIB real (%)
      FP.CPI.TOTL.ZG     → inflatie (%)
      SL.UEM.TOTL.ZS     → somaj (% forta munca)
      SI.POV.NAHC        → saracie (% populatie)
      SP.POP.TOTL        → populatie totala
      BX.TRF.PWKR.DT.GD.ZS → remitente (% PIB)
      GC.DOD.TOTL.GD.ZS  → datorie publica (% PIB)
    """
    url = f"{WB_BASE}/country/{country}/indicator/{indicator}"
    params = {
        "format":    "json",
        "per_page":  100,
        "mrv":       20,
        "date":      f"{ani_start}:2024",
    }
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        if len(payload) < 2 or not payload[1]:
            return pd.DataFrame({"eroare": ["Date indisponibile"]})
        records = [
            {"an": int(item["date"]),
             indicator: float(item["value"]) if item["value"] is not None else None}
            for item in payload[1]
        ]
        df = pd.DataFrame(records).dropna().sort_values("an")
        return df
    except Exception as e:
        return pd.DataFrame({"eroare": [str(e)]})


@st.cache_data(ttl=86400, show_spinner=False)
def wb_multi(indicators: dict, country: str = "MD",
             ani_start: int = 2010) -> pd.DataFrame:
    """
    Extrage mai multi indicatori WB cu aliasuri.
    indicators = {"alias": "cod_wb", ...}
    """
    dfs = []
    for alias, cod in indicators.items():
        df = wb_indicator(cod, country, ani_start)
        if "eroare" not in df.columns:
            df = df.rename(columns={cod: alias})
            dfs.append(df.set_index("an"))
    if dfs:
        return pd.concat(dfs, axis=1).reset_index()
    return pd.DataFrame()


# ── Seturi predefinite utile ──────────────────────────────────────────────────

def get_imf_overview() -> pd.DataFrame:
    """Indicatori macroeconomici principali IMF pentru Moldova."""
    return imf_weo_multi(
        ["NGDP_RPCH", "PCPIPCH", "BCA_NGDPD", "LUR", "GGXWDG_NGDP"],
        ani_start=2015
    )

def get_wb_social() -> pd.DataFrame:
    """Indicatori sociali World Bank pentru Moldova."""
    return wb_multi({
        "Saracie (%)":    "SI.POV.NAHC",
        "Somaj (%):":     "SL.UEM.TOTL.ZS",
        "Remitente (%PIB)":"BX.TRF.PWKR.DT.GD.ZS",
        "Populatie (mil)": "SP.POP.TOTL",
    }, ani_start=2010)

def get_imf_prognoze() -> pd.DataFrame:
    """Prognoze PIB si inflatie IMF (include ani viitori)."""
    return imf_weo_multi(["NGDP_RPCH","PCPIPCH"], ani_start=2020)


def test_imf() -> dict:
    from datetime import datetime
    try:
        r = requests.get(f"{IMF_BASE}/countries/MDA", timeout=TIMEOUT)
        return {"status":"ok","http":r.status_code,
                "ms":int(r.elapsed.total_seconds()*1000),
                "ts":datetime.now().strftime("%H:%M:%S")}
    except Exception as e:
        return {"status":"error","msg":str(e),
                "ts":datetime.now().strftime("%H:%M:%S")}

def test_wb() -> dict:
    from datetime import datetime
    try:
        r = requests.get(f"{WB_BASE}/country/MD?format=json", timeout=TIMEOUT)
        return {"status":"ok","http":r.status_code,
                "ms":int(r.elapsed.total_seconds()*1000),
                "ts":datetime.now().strftime("%H:%M:%S")}
    except Exception as e:
        return {"status":"error","msg":str(e),
                "ts":datetime.now().strftime("%H:%M:%S")}
