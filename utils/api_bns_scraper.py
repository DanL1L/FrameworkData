"""
utils/api_bns_scraper.py
Scraper pentru widget-ul de indicatori cheie de pe statistica.gov.md/ro

Indicatori disponibili in widget (8 total):
  0 — Populatia           → /statistic_indicator_details/25
  1 — Rata inflatiei      → /statistic_indicator_details/10
  2 — PIB                 → /statistic_indicator_details/12
  4 — Productia agricola  → /statistic_indicator_details/15
  5 — Rata somajului      → /statistic_indicator_details/1
  6 — Salariul mediu      → /statistic_indicator_details/2
  7 — Export              → /statistic_indicator_details/19
  8 — Import              → /statistic_indicator_details/19

Fiecare element <a class="itemkey"> contine 3 <div>:
  [0] titlu | [1] valoare | [2] perioada

Cache: ttl=3600 (refresh automat la fiecare ora)
"""

import re
import requests
from bs4 import BeautifulSoup
import streamlit as st
from datetime import datetime

BNS_HOME          = "https://statistica.gov.md/ro"
INFLATIE_URL      = "https://statistica.gov.md/ro/statistic_indicator_details/10"
PIATA_MUNCII_URL  = "https://statistica.gov.md/ro/statistic_indicator_details/1"
SALARIU_URL       = "https://statistica.gov.md/ro/statistic_indicator_details/2"
TIMEOUT           = 12
USER_AGENT    = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── Fallback — valori cunoscute la momentul scrierii ──────────────────────────
_FALLBACK = [
    {"titlu": "Populatia",          "valoare": "2 381,3 mii",   "perioada": "La 1 ianuarie 2025",           "url": "https://statistica.gov.md/ro/statistic_indicator_details/25"},
    {"titlu": "Rata inflatiei",     "valoare": "+1,8%",          "perioada": "apr. 2026 / mar. 2026",        "url": "https://statistica.gov.md/ro/statistic_indicator_details/10"},
    {"titlu": "PIB",                "valoare": "+2,4%",          "perioada": "Anul 2025 / Anul 2024",        "url": "https://statistica.gov.md/ro/statistic_indicator_details/12"},
    {"titlu": "Productia agricola", "valoare": "+8,5%",          "perioada": "ian.-mar. 2026 / ian.-mar. 2025", "url": "https://statistica.gov.md/ro/statistic_indicator_details/15"},
    {"titlu": "Rata somajului",     "valoare": "2,9%",           "perioada": "Trim. IV 2025",                "url": "https://statistica.gov.md/ro/statistic_indicator_details/1"},
    {"titlu": "Salariul mediu",     "valoare": "16 355,1 lei",   "perioada": "Trim. IV 2025",                "url": "https://statistica.gov.md/ro/statistic_indicator_details/2"},
    {"titlu": "Export",             "valoare": "+7,8%",          "perioada": "feb. 2026 / ian. 2026",        "url": "https://statistica.gov.md/ro/statistic_indicator_details/19"},
    {"titlu": "Import",             "valoare": "+17,7%",         "perioada": "feb. 2026 / ian. 2026",        "url": "https://statistica.gov.md/ro/statistic_indicator_details/19"},
]

# Mapare titlu → accent color pentru kpi_card
INDICATOR_COLOR = {
    "Populatia":          "blue",
    "Rata inflatiei":     "pink",
    "PIB":                "green",
    "Productia agricola": "teal",
    "Rata somajului":     "amber",
    "Salariul mediu":     "teal",
    "Export":             "green",
    "Import":             "purple",
}

# Logica pozitiv/negativ per indicator
# True = valoare mai mare e buna, False = valoare mai mica e buna
INDICATOR_POSITIVE_WHEN_UP = {
    "Populatia":          True,
    "Rata inflatiei":     False,   # inflatie mai mica = bine
    "PIB":                True,
    "Productia agricola": True,
    "Rata somajului":     False,   # somaj mai mic = bine
    "Salariul mediu":     True,
    "Export":             True,
    "Import":             None,    # neutru
}

@st.cache_data(ttl=3600, show_spinner=False)
def get_indicatori_cheie() -> dict:
    """
    Scrapeaza widget-ul de indicatori cheie de pe statistica.gov.md/ro.

    Returneaza:
      {
        "data":   [{"titlu", "valoare", "perioada", "url", "color", "pozitiv"}, ...],
        "live":   bool,
        "sursa":  str,
        "ts":     str,
        "eroare": str | None,
      }
    """
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        r = requests.get(
            BNS_HOME,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        r.encoding = "utf-8"

        soup = BeautifulSoup(r.text, "html.parser")
        indicatori = _parse_widget(soup)

        if indicatori:
            return {
                "data":   indicatori,
                "live":   True,
                "sursa":  "statistica.gov.md",
                "ts":     ts,
                "eroare": None,
            }

        return {
            "data":   _enrich_fallback(),
            "live":   False,
            "sursa":  "statistica.gov.md",
            "ts":     ts,
            "eroare": "Structura HTML modificata — se folosesc date de referinta.",
        }

    except requests.exceptions.ConnectionError:
        eroare = "Conexiune esuata — statistica.gov.md inaccesibil"
    except requests.exceptions.Timeout:
        eroare = f"Timeout dupa {TIMEOUT}s"
    except requests.exceptions.HTTPError as e:
        eroare = f"HTTP {e.response.status_code}"
    except Exception as e:
        eroare = f"Eroare: {e}"

    return {
        "data":   _enrich_fallback(),
        "live":   False,
        "sursa":  "BNS statistica.gov.md",
        "ts":     ts,
        "eroare": eroare,
    }


def _parse_widget(soup: BeautifulSoup) -> list:
    """
    Parseaza elementele <a class="itemkey"> din pagina.
    Structura: <a> → <img> + <div>titlu</div> + <div>valoare</div> + <div>perioada</div>
    """
    indicatori = []
    elems = soup.find_all(class_="itemkey")

    for el in elems:
        divs = el.find_all("div")
        if len(divs) < 3:
            continue

        titlu    = divs[0].get_text(strip=True)
        valoare  = divs[1].get_text(strip=True)
        perioada = divs[2].get_text(strip=True)

        href = el.get("href", "")
        if href and not href.startswith("http"):
            href = "https://statistica.gov.md" + href

        if not titlu or not valoare:
            continue

        # Normalizeaza titlul pentru mapare color
        titlu_norm = _normalizeaza(titlu)

        indicatori.append({
            "titlu":   titlu,
            "valoare": valoare,
            "perioada": perioada,
            "url":     href,
            "color":   INDICATOR_COLOR.get(titlu_norm, "blue"),
            "pozitiv": _calc_pozitiv(valoare, titlu_norm),
        })

    return indicatori


def _enrich_fallback() -> list:
    """Adauga color si pozitiv la datele fallback."""
    result = []
    for ind in _FALLBACK:
        titlu_norm = _normalizeaza(ind["titlu"])
        result.append({
            **ind,
            "color":   INDICATOR_COLOR.get(titlu_norm, "blue"),
            "pozitiv": _calc_pozitiv(ind["valoare"], titlu_norm),
        })
    return result


def _normalizeaza(titlu: str) -> str:
    """Normalizeaza diacritice pentru mapare."""
    return (titlu
            .replace("ţ", "t").replace("Ţ", "T")
            .replace("ș", "s").replace("Ș", "S")
            .replace("ă", "a").replace("Ă", "A")
            .replace("î", "i").replace("Î", "I")
            .replace("â", "a").replace("Â", "A")
            .strip())


def _calc_pozitiv(valoare: str, titlu_norm: str) -> bool:
    """Determina daca valoarea e pozitiva in context (buna/rea)."""
    v = valoare.strip()
    are_plus  = v.startswith("+")
    are_minus = v.startswith("-")

    pozitiv_cand_creste = INDICATOR_POSITIVE_WHEN_UP.get(titlu_norm, True)

    if pozitiv_cand_creste is None:
        return True   # neutru → afisam verde
    if are_plus:
        return pozitiv_cand_creste
    if are_minus:
        return not pozitiv_cand_creste
    return True       # valoare absoluta (ex: 2381,3 mii) → mereu verde


@st.cache_data(ttl=3600, show_spinner=False)
def get_inflatie_ytd() -> dict:
    """
    Scrapeaza pagina de detalii IPC (statistic_indicator_details/10) si extrage
    randul YTD cumulat de forma 'ian-xxx YYYY / ian-xxx YYYY, %'.

    Returneaza:
      {
        "valoare":  "+5,6%",                              # IPC - 100 cu semn
        "perioada": "ian-apr. 2026 / ian-apr. 2025",      # eticheta randul
        "live":     bool,
        "ts":       str,
        "eroare":   str | None,
      }
    """
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        r = requests.get(
            INFLATIE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        r.encoding = "utf-8"

        soup = BeautifulSoup(r.text, "html.parser")

        # Tabelul cu valorile IPC are clasa 'tablekeyvalue'
        tbl = soup.find("table", class_="tablekeyvalue")
        if not tbl:
            raise ValueError("Nu s-a gasit table.tablekeyvalue pe pagina IPC")

        # Cauta randul YTD: contine 'ian-' in eticheta (ex: 'ian-apr. 2026 / ian-apr. 2025, %')
        for row in tbl.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            label     = cells[0].get_text(strip=True)
            value_str = cells[1].get_text(strip=True)

            if "ian-" in label.lower() and value_str:
                # Elimina sufixul ', %' din eticheta de perioada
                perioada = label.replace(", %", "").strip()

                # Calculeaza rata inflatiei = IPC - 100
                ipc  = float(value_str.replace(",", ".").replace("\xa0", "").strip())
                rata = ipc - 100

                # Formateaza cu separator zecimal romanesc si semn
                rata_fmt = f"{rata:.1f}".replace(".", ",")
                valoare  = f"+{rata_fmt}%" if rata >= 0 else f"{rata_fmt}%"

                return {
                    "valoare":  valoare,
                    "perioada": perioada,
                    "live":     True,
                    "ts":       ts,
                    "eroare":   None,
                }

        raise ValueError("Randul 'ian-' nu a fost gasit in tabelul IPC")

    except requests.exceptions.ConnectionError:
        eroare = "Conexiune esuata — statistica.gov.md inaccesibil"
    except requests.exceptions.Timeout:
        eroare = f"Timeout dupa {TIMEOUT}s"
    except requests.exceptions.HTTPError as e:
        eroare = f"HTTP {e.response.status_code}"
    except Exception as e:
        eroare = f"Eroare inflatie: {e}"

    return {
        "valoare":  "+5,6%",
        "perioada": "ian-apr. 2026 / ian-apr. 2025",
        "live":     False,
        "ts":       ts,
        "eroare":   eroare,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_label(s: str) -> str:
    """Normalizeaza diacritice la ASCII simplu, lowercase — pentru matching robust."""
    return (s.lower()
            .replace("ș", "s").replace("ş", "s")
            .replace("ț", "t").replace("ţ", "t")
            .replace("ă", "a").replace("î", "i").replace("â", "a"))


def _parse_ro_float(val_str: str) -> float | None:
    """Converteste "15 987,1" sau "10,4" (format romanesc) la float."""
    try:
        cleaned = val_str.strip().replace("\xa0", "").replace(" ", "").replace(" ", "").replace(",", ".")
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


# ── Piata muncii trimestrial (indicatori_details/1) ───────────────────────────

_FALLBACK_PM_TRIM = {
    "perioada":       "Trim. I 2026",
    "pop_ocupata_mii": 811.1,
    "someri_bim_mii":  93.6,
    "rata_somaj_bim":  10.4,
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_piata_muncii_trim_scraper() -> dict:
    """
    Scrapeaza statistic_indicator_details/1:
      - Perioada (ex: "Trim. I 2026")
      - Populatie ocupata (mii pers.)
      - Someri BIM (mii pers.)
      - Rata somajului BIM (%)

    Returneaza:
      {"perioada", "pop_ocupata_mii", "someri_bim_mii", "rata_somaj_bim",
       "live", "sursa", "ts", "eroare"}
    """
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")
    eroare = None

    try:
        r = requests.get(PIATA_MUNCII_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")

        # Perioada din primul div.font-18 > b
        perioada = ""
        div_p = soup.find("div", class_="font-18")
        if div_p:
            b_tag = div_p.find("b")
            perioada = (b_tag or div_p).get_text(strip=True)

        result = {
            "perioada":        perioada,
            "pop_ocupata_mii": None,
            "someri_bim_mii":  None,
            "rata_somaj_bim":  None,
        }

        tbl = soup.find("table", class_="tablekeyvalue")
        if tbl:
            for row in tbl.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                label = _norm_label(cells[0].get_text(strip=True))
                val   = _parse_ro_float(cells[1].get_text(strip=True))
                if val is None:
                    continue
                if "populatie ocupata" in label:
                    result["pop_ocupata_mii"] = val
                elif "someri bim" in label:
                    result["someri_bim_mii"] = val
                elif "rata" in label and "somajului" in label:
                    result["rata_somaj_bim"] = val

        if result["pop_ocupata_mii"] is not None or result["rata_somaj_bim"] is not None:
            return {**result, "live": True,
                    "sursa": "statistica.gov.md · indicatori/1", "ts": ts, "eroare": None}

        raise ValueError("Date piata muncii negasite in pagina")

    except requests.exceptions.ConnectionError:
        eroare = "Conexiune esuata — statistica.gov.md inaccesibil"
    except requests.exceptions.Timeout:
        eroare = f"Timeout dupa {TIMEOUT}s"
    except requests.exceptions.HTTPError as e:
        eroare = f"HTTP {e.response.status_code}"
    except Exception as e:
        eroare = str(e)

    return {**_FALLBACK_PM_TRIM, "live": False,
            "sursa": "statistica.gov.md (fallback)", "ts": ts, "eroare": eroare}


# ── Salariu trimestrial (indicatori_details/2) ────────────────────────────────

_FALLBACK_SAL_TRIM_SCRAPER = {
    "perioada":        "Trim. I 2026",
    "salariu_total":   15987.1,
    "salariu_bugetar": 13287.9,
    "salariu_real":    16909.6,
    "salariu_anual":   15472.1,
    "an_salariu":      2025,
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_salariu_trim_scraper() -> dict:
    """
    Scrapeaza statistic_indicator_details/2:
      - Perioada (ex: "Trim. I 2026")
      - Castigul salarial mediu lunar brut: total, sector bugetar, sector real (lei)

    Returneaza:
      {"perioada", "salariu_total", "salariu_bugetar", "salariu_real",
       "live", "sursa", "ts", "eroare"}
    """
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")
    eroare = None

    try:
        r = requests.get(SALARIU_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")

        result = {
            "perioada":        "",
            "salariu_total":   None,
            "salariu_bugetar": None,
            "salariu_real":    None,
            "salariu_anual":   None,
            "an_salariu":      None,
        }

        tbl = soup.find("table", class_="tablekeyvalue")
        if tbl:
            in_trim_section = False
            for row in tbl.find_all("tr"):
                cells = row.find_all("td")
                if not cells:
                    continue

                b_tag  = cells[0].find("b")
                b_text = b_tag.get_text(strip=True) if b_tag else ""

                # Randul de perioada: <b>Trim. I 2026, lei</b>
                if b_tag and "trim." in b_text.lower():
                    result["perioada"] = b_text.replace(", lei", "").replace(",lei", "").strip()
                    in_trim_section = True
                    continue

                if len(cells) < 2:
                    continue

                label = _norm_label(cells[0].get_text(strip=True))
                val   = _parse_ro_float(cells[1].get_text(strip=True))
                if val is None:
                    continue

                # Randuri trimestru curent (total / sector bugetar / sector real)
                if in_trim_section:
                    if label == "total":
                        result["salariu_total"] = val
                    elif "bugetar" in label:
                        result["salariu_bugetar"] = val
                    elif label == "sector real":
                        result["salariu_real"] = val

                # Randul anual: "Anul 2025, lei"
                m = re.search(r"anul\s+(\d{4})", label)
                if m:
                    result["salariu_anual"] = val
                    result["an_salariu"]    = int(m.group(1))

        if result["salariu_total"] is not None:
            return {**result, "live": True,
                    "sursa": "statistica.gov.md · indicatori/2", "ts": ts, "eroare": None}

        raise ValueError("Date salariale negasite in pagina")

    except requests.exceptions.ConnectionError:
        eroare = "Conexiune esuata — statistica.gov.md inaccesibil"
    except requests.exceptions.Timeout:
        eroare = f"Timeout dupa {TIMEOUT}s"
    except requests.exceptions.HTTPError as e:
        eroare = f"HTTP {e.response.status_code}"
    except Exception as e:
        eroare = str(e)

    return {**_FALLBACK_SAL_TRIM_SCRAPER, "live": False,
            "sursa": "statistica.gov.md (fallback)", "ts": ts, "eroare": eroare}