"""
utils/api_comert_extern.py
Surse BNS PX-Web — Comert exterior pe tari si grupe de tari

Tabel principal (lunar, USD):
  EXT015000.px — Exporturi, importuri si balanta comerciala, serie lunara 2005-2026
  Sursa saved query: https://statbank.statistica.md/PxWeb/sq/7db36e25-fdce-478e-8956-a25caad5e220

Tabele anuale (pe tari individuale):
  EXT010200.px — Export pe tari, 1997-2024
  EXT010300.px — Import pe tari, 1997-2024

Saved queries (vechi):
  Import pe tari:  adb8f8cc-85d9-480c-ab01-29ceb2622d63
  Export pe tari:  42a72b84-effc-45c7-961c-a43596ec9478
  Grupe de tari:   11dec439-841d-4284-8713-7ff7c3538e49

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

_LUNI_ABREV = ["ian", "feb", "mar", "apr", "mai", "iun",
               "iul", "aug", "sep", "oct", "nov", "dec"]

# ── EXT015000: date lunare export/import/balanta pe grupe de tari ─────────────

_EXT015000 = "40%20Statistica%20economica/21%20EXT/EXT010/serii%20lunare/EXT015000.px"

_LUNI_TEXTS = ["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie",
               "Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"]
_IND_MAP   = {"0": "export_mil_usd", "1": "import_mil_usd", "2": "sold_mil_usd"}
_GRUPE_MAP = {"0": "Total", "1": "CSI", "2": "UE", "3": "Alte tari"}


@st.cache_data(ttl=3600, show_spinner=False)
def get_comert_ext_bns(ani: list = None) -> dict:
    """
    Extrage din BNS EXT015000.px date lunare (mil. USD):
      exporturi, importuri, balanta comerciala, pe grupe de tari (Total/CSI/UE/Alte).
    Sursa: https://statbank.statistica.md/PxWeb/sq/7db36e25-fdce-478e-8956-a25caad5e220

    Returneaza:
      {"data": DataFrame[an, luna_nr, luna_text, label, grupa,
                         export_mil_usd, import_mil_usd, sold_mil_usd],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2015, 2027)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    query = {
        "query": [
            {"code": "Indicatori",        "selection": {"filter": "item", "values": ["0","1","2"]}},
            {"code": "Grupe de tari",     "selection": {"filter": "item", "values": ["0","1","2","3"]}},
            {"code": "Ani",               "selection": {"filter": "item", "values": ani}},
            {"code": "Unitatea de masura","selection": {"filter": "item", "values": ["0"]}},
            {"code": "Luni",              "selection": {"filter": "item",
                                                        "values": [str(i) for i in range(12)]}},
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_EXT015000}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_ext015000(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True,
                        "sursa": "BNS EXT015000 — live API",
                        "ts": ts, "eroare": None}
            err_msg = f"parse esuat (HTTP 200, rows={len(r.json().get('data', []))})"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False,
            "sursa": "BNS EXT015000", "ts": ts,
            "eroare": f"EXT015000: {err_msg}"}


_SQ_EUR = "https://statbank.statistica.md/PxWeb/sq/8361a49c-6c49-4ed1-b853-b48b7a3c0eb0"
# JSON-stat format: size=[Indicatori(3), Grupe(1), Ani(N), Unitate(2), Luni(13)]
# Unitate 0 = Milioane EURO | Luni 0..11 = Ian..Dec | 12 = Ian-Dec total anual


def _parse_jsonstat_ext(d: dict) -> dict | None:
    """Parseaza JSON-stat BNS → {(ind_idx, an_idx, luna_idx): mil_eur} + ani_list."""
    vals_raw = d.get("value", [])
    dims     = d.get("dimension", {})
    size     = d.get("size", [])
    if not vals_raw or not dims or len(size) < 5:
        return None

    # stride[i] = prod(size[i+1..n-1])
    n       = len(size)
    strides = [1] * n
    for i in range(n - 2, -1, -1):
        strides[i] = strides[i + 1] * size[i + 1]

    ani_labels = list(dims.get("Ani", {}).get("category", {}).get("label", {}).values())

    result = {}
    for ind in range(size[0]):          # 0=Export, 1=Import
        for an in range(size[2]):
            for luna in range(size[4]):
                if luna == 12:          # luna 12 = total Ian-Dec, o ignoram
                    continue
                flat = (ind * strides[0]
                        + 0   * strides[1]   # grupe=0 Total
                        + an  * strides[2]
                        + 0   * strides[3]   # unitate=0 Milioane EURO
                        + luna)
                v = vals_raw[flat] if flat < len(vals_raw) else None
                if v is not None and not (isinstance(v, float) and v != v):
                    result[(ind, an, luna)] = float(v)

    return {"vals": result, "ani": ani_labels}


@st.cache_data(ttl=3600, show_spinner=False)
def get_comert_ytd_bns() -> dict:
    """
    Calculeaza Export si Import YTD cumulat (ian. – ultima luna disponibila)
    vs acelasi interval an precedent, in Milioane EURO.
    Sursa: BNS saved query 8361a49c (JSON-stat).

    Returneaza:
      {
        "exp_pct":   float | None,
        "imp_pct":   float | None,
        "exp_delta": float | None,   # crestere absoluta, mil. EUR
        "imp_delta": float | None,
        "exp_cur":   float | None,   # total YTD, mil. EUR
        "imp_cur":   float | None,
        "perioada":  str,            # ex: "ian.-mar. 2026 / ian.-mar. 2025"
        "luna_max":  int,            # ultima luna cu date, 1-based
        "an_cur":    int,
        "live":      bool,
        "eroare":    str | None,
      }
    """
    an_cur  = datetime.now().year
    an_prev = an_cur - 1
    _EMPTY  = {"exp_pct": None, "imp_pct": None, "exp_delta": None, "imp_delta": None,
               "exp_cur": None, "imp_cur": None, "perioada": "",
               "luna_max": None, "an_cur": an_cur, "live": False}

    try:
        r = requests.get(_SQ_EUR, timeout=TIMEOUT)
        if r.status_code != 200:
            return {**_EMPTY, "eroare": f"HTTP {r.status_code}"}

        parsed = _parse_jsonstat_ext(r.json())
        if not parsed:
            return {**_EMPTY, "eroare": "Parse JSON-stat esuat"}

        vals     = parsed["vals"]
        ani_list = parsed["ani"]

        try:
            cur_idx  = ani_list.index(str(an_cur))
            prev_idx = ani_list.index(str(an_prev))
        except ValueError:
            return {**_EMPTY, "eroare": f"Anul {an_cur}/{an_prev} lipseste din API"}

        # Ultima luna cu date pentru Export(0) si Import(1) in anul curent
        months_exp = {luna for (ind, an, luna) in vals if ind == 0 and an == cur_idx}
        months_imp = {luna for (ind, an, luna) in vals if ind == 1 and an == cur_idx}
        common = months_exp & months_imp
        if not common:
            return {**_EMPTY, "eroare": "Nu sunt date pentru anul curent"}

        luna_max_0 = max(common)   # 0-based (0=ian, 2=mar, ...)

        # Sume YTD ian. → luna_max_0 inclusiv
        exp_cur  = sum(vals.get((0, cur_idx,  m), 0.0) for m in range(luna_max_0 + 1))
        imp_cur  = sum(vals.get((1, cur_idx,  m), 0.0) for m in range(luna_max_0 + 1))
        exp_prev = sum(vals.get((0, prev_idx, m), 0.0) for m in range(luna_max_0 + 1))
        imp_prev = sum(vals.get((1, prev_idx, m), 0.0) for m in range(luna_max_0 + 1))

        if not exp_prev or not imp_prev:
            return {**_EMPTY, "eroare": "Date insuficiente an precedent"}

        exp_pct = (exp_cur / exp_prev - 1) * 100
        imp_pct = (imp_cur / imp_prev - 1) * 100

        abrev = _LUNI_ABREV[luna_max_0]
        per   = (f"ian. {an_cur} / ian. {an_prev}" if luna_max_0 == 0
                 else f"ian.-{abrev}. {an_cur} / ian.-{abrev}. {an_prev}")

        return {
            "exp_pct":   round(exp_pct, 1),
            "imp_pct":   round(imp_pct, 1),
            "exp_delta": round(exp_cur - exp_prev, 1),
            "imp_delta": round(imp_cur - imp_prev, 1),
            "exp_cur":   round(exp_cur, 1),
            "imp_cur":   round(imp_cur, 1),
            "perioada":  per,
            "luna_max":  luna_max_0 + 1,
            "an_cur":    an_cur,
            "live":      True,
            "eroare":    None,
        }

    except Exception as e:
        return {**_EMPTY, "eroare": str(e)}


def _parse_ext015000(data: dict) -> pd.DataFrame | None:
    """
    Parseaza raspunsul PX-Web de la EXT015000.
    Structura key: [Indicatori, Grupe de tari, Ani, Unitatea de masura, Luni]
    """
    if not isinstance(data, dict) or "data" not in data:
        return None

    rows = []
    for item in data["data"]:
        ind, grp, an, _, luna_code = item["key"]
        val_str = item["values"][0]
        try:
            val = float(val_str) if val_str and val_str.strip() not in ("..", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        luna_idx = int(luna_code)
        rows.append({
            "an":        int(an),
            "luna_nr":   luna_idx + 1,
            "luna_text": _LUNI_TEXTS[luna_idx],
            "grupa":     _GRUPE_MAP.get(grp, grp),
            "indicator": _IND_MAP.get(ind, ind),
            "valoare":   val,
        })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    pivot = df.pivot_table(
        index=["an", "luna_nr", "luna_text", "grupa"],
        columns="indicator", values="valoare", aggfunc="first",
    ).reset_index()
    pivot.columns.name = None

    for col in ["export_mil_usd", "import_mil_usd", "sold_mil_usd"]:
        if col not in pivot.columns:
            pivot[col] = None

    pivot["label"] = pivot.apply(
        lambda r: f"{r['luna_text'][:3]} {int(r['an'])}", axis=1
    )
    return pivot.sort_values(["an", "luna_nr"]).reset_index(drop=True)


# ── EXT013200: date trimestriale export/import pe sectiuni NCM ───────────────
# Inlocuieste EXT010400 (anual). Codul trim '4' = Trimestrele I-IV (total anual).

_EXT013200 = "40%20Statistica%20economica/21%20EXT/EXT010/serii%20trimestriale/EXT013200.px"

# Sectiunile principale NCM (cifre romane) — fara capitole individuale
_SECTIUNI_CODES = [
    "Total","I.","II.","III.","IV.","V.","VI.","VII.","VIII.",
    "IX.","X.","XI.","XII.","XIII.","XIV.","XV.","XVI.","XVII.","XVIII.","XX.","XXI.",
]

_SECTIUNI_LABELS = {
    "Total":   "Total",
    "I.":      "I. Animale, produse animale",
    "II.":     "II. Produse vegetale",
    "III.":    "III. Grasimi si uleiuri",
    "IV.":     "IV. Alimente, bauturi, tutun",
    "V.":      "V. Produse minerale",
    "VI.":     "VI. Produse chimice",
    "VII.":    "VII. Mase plastice, cauciuc",
    "VIII.":   "VIII. Piei si articole pielarie",
    "IX.":     "IX. Lemn si produse lemnoase",
    "X.":      "X. Hirtie si carton",
    "XI.":     "XI. Textile",
    "XII.":    "XII. Incaltaminte",
    "XIII.":   "XIII. Piatra, sticla, ceramica",
    "XIV.":    "XIV. Pietre pretioase, metale nobile",
    "XV.":     "XV. Metale comune",
    "XVI.":    "XVI. Masini si echipamente",
    "XVII.":   "XVII. Mijloace de transport",
    "XVIII.":  "XVIII. Instrumente, aparate optice",
    "XX.":     "XX. Marfuri diverse",
    "XXI.":    "XXI. Obiecte de arta",
}

# Trimestre cod BNS → (trim_nr, eticheta afisata)
# trim_nr=0 = total anual (T1-T4)
_TRIM_NCM_MAP = {
    "0": (1, "T1"),
    "1": (2, "T2"),
    "2": (3, "T3"),
    "3": (4, "T4"),
    "4": (0, "Anual"),
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_comert_produse_bns(ani: list = None) -> dict:
    """
    EXT013200.px — comert exterior pe sectiuni NCM, trimestrial + anual (mii USD → mil. USD).
    Sursa: https://statbank.statistica.md/PxWeb/sq/60604d6a-33f4-479b-9ce0-974aa6f19378

    Returneaza:
      {"data": DataFrame[an, trim_nr, trim_label, sectiune, sectiune_label,
                         export_mil_usd, import_mil_usd],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    trim_nr: 1=T1, 2=T2, 3=T3, 4=T4, 0=Anual (T1-T4)
    """
    ani = ani or [str(a) for a in range(2019, 2026)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    query = {
        "query": [
            {"code": "Indicatori",
             "selection": {"filter": "item", "values": ["0", "1"]}},
            {"code": "Sectiuni si capitole conform NCM",
             "selection": {"filter": "item", "values": _SECTIUNI_CODES}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Trimestre",
             "selection": {"filter": "item", "values": ["0", "1", "2", "3", "4"]}},
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_EXT013200}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_ext013200(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True,
                        "sursa": "BNS EXT013200 — live API",
                        "ts": ts, "eroare": None}
            err_msg = f"Parse esuat (rows returnate: {len(r.json().get('data',[]))})"
        else:
            err_msg = f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False,
            "sursa": "BNS EXT013200", "ts": ts,
            "eroare": f"API BNS indisponibil — {err_msg}"}


def _parse_ext013200(data: dict) -> pd.DataFrame | None:
    """
    Parseaza EXT013200. key: [Indicatori, Sectiune, Ani, Trimestre]
    Valori in mii USD → mil. USD.
    Returneaza wide: [an, trim_nr, trim_label, sectiune, sectiune_label,
                      export_mil_usd, import_mil_usd]
    """
    if not isinstance(data, dict) or "data" not in data:
        return None

    IND_MAP = {"0": "export_mil_usd", "1": "import_mil_usd"}
    rows = []
    for item in data["data"]:
        ind, sect, an, trim_cod = item["key"]
        val_str = item["values"][0]
        try:
            val = float(val_str) / 1000.0 if val_str and val_str.strip() not in ("..", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        trim_nr, trim_short = _TRIM_NCM_MAP.get(trim_cod, (trim_cod, trim_cod))
        trim_label = f"{trim_short} {an}" if trim_short != "Anual" else an
        rows.append({
            "an":             int(an),
            "trim_nr":        trim_nr,
            "trim_label":     trim_label,
            "sectiune":       sect,
            "sectiune_label": _SECTIUNI_LABELS.get(sect, sect),
            "indicator":      IND_MAP.get(ind, ind),
            "valoare":        val,
        })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    pivot = df.pivot_table(
        index=["an", "trim_nr", "trim_label", "sectiune", "sectiune_label"],
        columns="indicator", values="valoare", aggfunc="first",
    ).reset_index()
    pivot.columns.name = None

    for col in ["export_mil_usd", "import_mil_usd"]:
        if col not in pivot.columns:
            pivot[col] = None

    return pivot.sort_values(["an", "trim_nr", "sectiune"]).reset_index(drop=True)


# ── EXT020100: indici valorici, valoare unitara, volum fizic (trimestrial) ────

_EXT020100 = "40%20Statistica%20economica/21%20EXT/EXT020/EXT020100.px"

_TRIM_MAP = {
    "I quarter":   (1, "T1"),
    "II quarter":  (2, "T2"),
    "III quarter": (3, "T3"),
    "IV quarter":  (4, "T4"),
}
_INDICE_MAP = {
    "Value indices":      "ind_valoric",
    "Unit value indices": "ind_val_unitara",
    "Volume indices":     "ind_volum",
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_indici_comert_bns(ani: list = None) -> dict:
    """
    EXT020100.px — indici valorici, valoarea unitara si volum fizic, trimestrial.
    Sursa: https://statbank.statistica.md/PxWeb/sq/c30993e3-bbb2-47a2-a349-4d1dda38b124
    Baza: perioada corespunzatoare a anului precedent = 100.

    Returneaza:
      {"data": DataFrame[an, trim_nr, trim_label, indicatori,
                         ind_valoric, ind_val_unitara, ind_volum],
       "live": bool, "sursa": str, "ts": str, "eroare": str|None}
    """
    ani = ani or [str(a) for a in range(2015, 2026)]
    ts  = datetime.now().strftime("%d.%m.%Y %H:%M")

    query = {
        "query": [
            {"code": "Indicatori",
             "selection": {"filter": "item", "values": ["Export", "Import"]}},
            {"code": "Indici",
             "selection": {"filter": "item",
                           "values": ["Value indices", "Unit value indices", "Volume indices"]}},
            {"code": "Ani",
             "selection": {"filter": "item", "values": ani}},
            {"code": "Trimestre",
             "selection": {"filter": "item",
                           "values": ["I quarter", "II quarter", "III quarter", "IV quarter"]}},
        ],
        "response": {"format": "json"},
    }

    err_msg = ""
    try:
        r = requests.post(f"{BNS_BASE}/{_EXT020100}",
                          headers=HEADERS, data=json.dumps(query), timeout=TIMEOUT)
        if r.status_code == 200:
            df = _parse_ext020100(r.json())
            if df is not None and not df.empty:
                return {"data": df, "live": True,
                        "sursa": "BNS EXT020100 — live API",
                        "ts": ts, "eroare": None}
            err_msg = f"parse esuat (HTTP 200, rows={len(r.json().get('data',[]))})"
        else:
            err_msg = f"HTTP {r.status_code}"
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"

    return {"data": pd.DataFrame(), "live": False,
            "sursa": "BNS EXT020100", "ts": ts,
            "eroare": f"EXT020100: {err_msg}"}


def _parse_ext020100(data: dict) -> pd.DataFrame | None:
    """
    Parseaza EXT020100. key: [Indicatori, Indici, Ani, Trimestre]
    Returneaza DataFrame wide: [an, trim_nr, trim_label, indicatori,
                                 ind_valoric, ind_val_unitara, ind_volum]
    """
    if not isinstance(data, dict) or "data" not in data:
        return None

    rows = []
    for item in data["data"]:
        indicatori, indice_cod, an, trim_cod = item["key"]
        val_str = item["values"][0]
        try:
            val = float(val_str) if val_str and val_str.strip() not in ("..", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        trim_nr, trim_short = _TRIM_MAP.get(trim_cod, (0, trim_cod))
        rows.append({
            "an":          int(an),
            "trim_nr":     trim_nr,
            "trim_label":  f"{trim_short} {an}",
            "indicatori":  indicatori,
            "indice_col":  _INDICE_MAP.get(indice_cod, indice_cod),
            "valoare":     val,
        })

    if not rows:
        return None

    df = pd.DataFrame(rows)
    pivot = df.pivot_table(
        index=["an", "trim_nr", "trim_label", "indicatori"],
        columns="indice_col", values="valoare", aggfunc="first",
    ).reset_index()
    pivot.columns.name = None

    for col in ["ind_valoric", "ind_val_unitara", "ind_volum"]:
        if col not in pivot.columns:
            pivot[col] = None

    return pivot.sort_values(["an", "trim_nr"]).reset_index(drop=True)


# ── EXT013000 / EXT013100: export/import pe tari partenere (trimestrial) ─────

_EXT013000 = "40%20Statistica%20economica/21%20EXT/EXT010/serii%20trimestriale/EXT013000.px"
_EXT013100 = "40%20Statistica%20economica/21%20EXT/EXT010/serii%20trimestriale/EXT013100.px"

# EXT013000 Trimestre codes (string): I, II, III, IV, I-IV
_TRIM_EXP_MAP = {"I": "T1", "II": "T2", "III": "T3", "IV": "T4", "I-IV": "Anual"}
# EXT013100 Trimestre codes (numeric): 0=T1, 1=T2, 2=T3, 3=T4, 4=Anual
_TRIM_IMP_MAP = {"0": "T1", "1": "T2", "2": "T3", "3": "T4", "4": "Anual"}

_TARI_EXPORT = {
    "0": "Total",         "1": "Afganistan",    "2": "Austria",
    "3": "Belarus",       "4": "Belgia",         "5": "Bulgaria",
    "6": "Cehia",         "7": "China",          "8": "Elvetia",
    "9": "Fed. Rusa",     "10": "Franta",        "11": "Georgia",
    "12": "Germania",     "13": "Grecia",        "14": "Irak",
    "15": "Italia",       "16": "Kazahstan",     "17": "Lituania",
    "18": "Polonia",      "19": "Portugalia",    "20": "Olanda",
    "21": "Marea Britanie", "22": "Romania",     "23": "Slovacia",
    "24": "Spania",       "25": "SUA",           "26": "Turcia",
    "27": "Ucraina",      "28": "Ungaria",       "29": "Uzbekistan",
}

_TARI_IMPORT = {
    "0": "Total",         "1": "Austria",        "2": "Belarus",
    "3": "Belgia",        "4": "Brazilia",       "5": "Bulgaria",
    "6": "Cehia",         "7": "China",          "8": "Coreea de Sud",
    "9": "Elvetia",       "10": "Fed. Rusa",     "11": "Finlanda",
    "12": "Franta",       "13": "Germania",      "14": "Grecia",
    "15": "India",        "16": "Israel",        "17": "Italia",
    "18": "Japonia",      "19": "Kazahstan",     "20": "Lituania",
    "21": "Polonia",      "22": "Olanda",        "23": "Marea Britanie",
    "24": "Romania",      "25": "Slovacia",      "26": "Slovenia",
    "27": "Spania",       "28": "SUA",           "29": "Suedia",
    "30": "Taiwan",       "31": "Turcia",        "32": "Ucraina",
    "33": "Ungaria",      "34": "Vietnam",
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_comert_tari_bns(ani: list = None) -> dict:
    """
    EXT013000 (Export pe Tari) + EXT013100 (Import pe Tari), trimestrial + anual.
    Valori in mii USD → mil. USD.
    Surse:
      Export: https://statbank.statistica.md/PxWeb/sq/8558619d-c569-4704-ba5d-c81a146b8ace
      Import: https://statbank.statistica.md/PxWeb/sq/0f627b71-57e6-44e2-a215-5493d764cb07

    Returneaza:
      {"export": DataFrame[an, trim_label, tara_cod, tara, export_mil_usd],
       "import": DataFrame[an, trim_label, tara_cod, tara, import_mil_usd],
       "live_exp": bool, "live_imp": bool, "ts": str, "eroare": str|None}
    trim_label: "T1" | "T2" | "T3" | "T4" | "Anual"
    """
    ani = ani or [str(a) for a in range(2019, 2026)]
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")

    df_exp, live_exp, err_exp = None, False, ""
    try:
        query_exp = {
            "query": [
                {"code": "Tari",      "selection": {"filter": "item",
                                                     "values": [str(i) for i in range(30)]}},
                {"code": "Ani",       "selection": {"filter": "item", "values": ani}},
                {"code": "Trimestre", "selection": {"filter": "item",
                                                     "values": ["I","II","III","IV","I-IV"]}},
            ],
            "response": {"format": "json"},
        }
        r = requests.post(f"{BNS_BASE}/{_EXT013000}",
                          headers=HEADERS, data=json.dumps(query_exp), timeout=TIMEOUT)
        if r.status_code == 200:
            df_exp = _parse_ext013000(r.json())
            if df_exp is not None and not df_exp.empty:
                live_exp = True
            else:
                err_exp = "parse esuat"
        else:
            err_exp = f"HTTP {r.status_code}"
    except Exception as e:
        err_exp = f"{type(e).__name__}: {e}"

    df_imp, live_imp, err_imp = None, False, ""
    try:
        query_imp = {
            "query": [
                {"code": "Tari",      "selection": {"filter": "item",
                                                     "values": [str(i) for i in range(35)]}},
                {"code": "Ani",       "selection": {"filter": "item", "values": ani}},
                {"code": "Trimestre", "selection": {"filter": "item",
                                                     "values": ["0","1","2","3","4"]}},
            ],
            "response": {"format": "json"},
        }
        r = requests.post(f"{BNS_BASE}/{_EXT013100}",
                          headers=HEADERS, data=json.dumps(query_imp), timeout=TIMEOUT)
        if r.status_code == 200:
            df_imp = _parse_ext013100(r.json())
            if df_imp is not None and not df_imp.empty:
                live_imp = True
            else:
                err_imp = "parse esuat"
        else:
            err_imp = f"HTTP {r.status_code}"
    except Exception as e:
        err_imp = f"{type(e).__name__}: {e}"

    errs = []
    if err_exp:
        errs.append(f"Export: {err_exp}")
    if err_imp:
        errs.append(f"Import: {err_imp}")

    return {
        "export":   df_exp if df_exp is not None else pd.DataFrame(),
        "import":   df_imp if df_imp is not None else pd.DataFrame(),
        "live_exp": live_exp,
        "live_imp": live_imp,
        "ts":       ts,
        "eroare":   "; ".join(errs) if errs else None,
    }


def _parse_ext013000(data: dict) -> pd.DataFrame | None:
    """EXT013000 key: [Tari, Ani, Trimestre] → export_mil_usd (mii USD ÷ 1000)."""
    if not isinstance(data, dict) or "data" not in data:
        return None
    rows = []
    for item in data["data"]:
        tara_cod, an, trim_cod = item["key"]
        val_str = item["values"][0]
        try:
            val = float(val_str) / 1000.0 if val_str and val_str.strip() not in ("..", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        rows.append({
            "an":           int(an),
            "trim_label":   _TRIM_EXP_MAP.get(trim_cod, trim_cod),
            "tara_cod":     tara_cod,
            "tara":         _TARI_EXPORT.get(tara_cod, tara_cod),
            "export_mil_usd": val,
        })
    return pd.DataFrame(rows) if rows else None


def _parse_ext013100(data: dict) -> pd.DataFrame | None:
    """EXT013100 key: [Tari, Ani, Trimestre] → import_mil_usd (mii USD ÷ 1000)."""
    if not isinstance(data, dict) or "data" not in data:
        return None
    rows = []
    for item in data["data"]:
        tara_cod, an, trim_cod = item["key"]
        val_str = item["values"][0]
        try:
            val = float(val_str) / 1000.0 if val_str and val_str.strip() not in ("..", "", "-", "n/a") else None
        except (ValueError, TypeError):
            val = None
        rows.append({
            "an":           int(an),
            "trim_label":   _TRIM_IMP_MAP.get(trim_cod, trim_cod),
            "tara_cod":     tara_cod,
            "tara":         _TARI_IMPORT.get(tara_cod, tara_cod),
            "import_mil_usd": val,
        })
    return pd.DataFrame(rows) if rows else None


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
