"""
excel_loader.py — Modul central de citire date din fisiere Excel per sector.

Fisiere asteptate in /data/:
  Data.xlsx                  → Sector Extern (comert, export/import lunar, NCM)
  Date_Sector_Monetar.xlsx   → Sector Monetar (PIB, IPC, rezerve, baza monetara)
  Date_Sector_Social.xlsx    → Sector Social (ocupare, somaj, salarii, trimestrial)
  Date_Sector_Real.xlsx      → Sector Real (PIB componente, industrie, agricultura)
  Date_Sector_Public.xlsx    → Sector Public (buget, venituri, cheltuieli, datorie)

Fiecare functie returneaza dict: {"data": DataFrame, "sursa": str, "live": bool}
Daca fisierul nu exista sau are eroare → fallback la date demo.
"""

import pandas as pd
import numpy as np
import os
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__))


def _path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def _file_exists(filename: str) -> bool:
    return os.path.isfile(_path(filename))


def _sursa(filename: str, sheet: str = "") -> str:
    s = f"Excel: {filename}"
    if sheet:
        s += f" [{sheet}]"
    return s


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR MONETAR — Date_Sector_Monetar.xlsx
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_monetar() -> dict:
    """
    Sector Monetar — loader robust
    Fix:
    - diacritice unicode
    - coloane duplicate
    - conversii numerice sigure
    - compatibilitate multiple versiuni Excel
    """

    import unicodedata as _uc
    import os as _os
    fname = "Date_Sector_Monetar.xlsx"
    _here = _os.path.dirname(_os.path.abspath(__file__))
    _root = _os.path.dirname(_here)

    _candidates = [
        _os.path.join(_here, fname),
        _os.path.join(_root, "data", fname),
        _os.path.join(_root, fname),
        _os.path.join("data", fname),
        fname,
    ]

    _path_found = next((p for p in _candidates if _os.path.isfile(p)), None)

    if _path_found is None:
        return {
            "data": pd.DataFrame(),
            "sursa": f"{fname} negasit",
            "live": False
        }

    try:
        df = pd.read_excel(
            _path_found,
            sheet_name="Monetar",
            engine="openpyxl"
        )

        # =========================================================
        # CLEAN HEADERS
        # =========================================================

        df.columns = [str(c).strip() for c in df.columns]

        def _n(txt):
            txt = str(txt).strip().lower()
            txt = _uc.normalize("NFKD", txt)
            txt = txt.encode("ascii", "ignore").decode()
            return txt

        rename_map = {}

        for c in df.columns:

            cl = _n(c)
            # AN
            if cl == "an":
                rename_map[c] = "an"
            # IPC
            elif (
                ("ipc" in cl)
                or (
                    "preturilor de consum" in cl
                    and (
                        "sfarsit" in cl
                        or "sfirsit" in cl
                        or "sfarsitul" in cl
                        or "sfirsitul" in cl
                        or "anului" in cl
                    )
                )
            ):
                rename_map[c] = "ipc_sfarsit_an"
            elif ("ipc" in cl or "infl" in cl) and "medi" in cl:
                rename_map[c] = "ipc_medie_an"

            # REZERVE
            elif "rezerv" in cl:
                rename_map[c] = "rezerve_mil_eur"

            # PIB
            elif "pib" in cl:
                rename_map[c] = "pib_mil_lei"

            # RATA BAZA
            elif "rata" in cl and "baz" in cl:
                rename_map[c] = "rata_baza_pct"

            # BANI LICHIZI IN CIRCULATIE (MO) — trebuie verificat inaintea "baza monetara"
            elif "bani" in cl or "lichiz" in cl or "(mo)" in cl:
                rename_map[c] = "bani_lichizi_mo_mil_lei"

            # BAZA MONETARA (agregat mai larg — include rezerve bancare)
            elif "baz" in cl and "monetar" in cl:
                rename_map[c] = "baza_monetara_mil_lei"

            # CREDITE
            elif "credit" in cl and "juridic" in cl:
                rename_map[c] = "credite_juridice_mil_lei"

            elif "credit" in cl and "fizic" in cl:
                rename_map[c] = "credite_fizice_mil_lei"

            elif "credit" in cl and "consum" in cl:
                rename_map[c] = "credite_consum_mil_lei"

            elif "credit" in cl and "imobi" in cl:
                rename_map[c] = "credite_imobil_mil_lei"

            elif "credit" in cl and "alte" in cl:
                rename_map[c] = "credite_alte_mil_lei"

            # DEPOZITE TERMEN
            elif "depozit" in cl and "termen" in cl and "juridic" in cl:
                rename_map[c] = "depozite_termen_juridice_mil_lei"

            elif "depozit" in cl and "termen" in cl and "fizic" in cl:
                rename_map[c] = "depozite_termen_fizice_mil_lei"

            # STRUCTURA DEPOZITE
            elif "depozit" in cl and "vedere" in cl:
                rename_map[c] = "depozite_vedere_mn_mil_lei"

            elif "depozit" in cl and "termen" in cl and (
                "national" in cl or
                "moneda" in cl or
                "mn" in cl
            ):
                rename_map[c] = "depozite_termen_mn_mil_lei"

            elif "depozit" in cl and "valut" in cl:
                rename_map[c] = "depozite_valuta_mil_lei"

            # DEPOZITE TOTAL
            elif (
                "depozit" in cl
                and "termen" not in cl
                and "vedere" not in cl
                and "valut" not in cl
                and "juridic" not in cl
                and "fizic" not in cl
            ):
                rename_map[c] = "depozite_mil_lei"

        # =========================================================
        # RENAME
        # =========================================================

        df = df.rename(columns=rename_map)

        # =========================================================
        # ELIMINA COLOANE DUPLICATE
        # =========================================================

        df = df.loc[:, ~df.columns.duplicated()]

        # =========================================================
        # CONVERSII
        # =========================================================

        if "an" not in df.columns:
            return {
                "data": pd.DataFrame(),
                "sursa": f"{fname}: coloana AN lipseste",
                "live": False
            }

        df["an"] = pd.to_numeric(
            df["an"],
            errors="coerce"
        ).astype("Int64")

        numeric_cols = [c for c in df.columns if c != "an"]

        for col in numeric_cols:

            df[col] = (
                df[col]
                .astype(str)
                .str.replace(" ", "", regex=False)
                .str.replace(",", ".", regex=False)
            )

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        # =========================================================
        # SORT
        # =========================================================

        df = (
            df
            .dropna(subset=["an"])
            .sort_values("an")
            .reset_index(drop=True)
        )

        # =========================================================
        # COLOANE CALCULATE
        # =========================================================

        if (
            "credite_juridice_mil_lei" in df.columns
            and
            "credite_fizice_mil_lei" in df.columns
        ):
            df["credite_total_mil_lei"] = (
                df["credite_juridice_mil_lei"].fillna(0)
                +
                df["credite_fizice_mil_lei"].fillna(0)
            )

        dep_cols = [
            c for c in [
                "depozite_vedere_mn_mil_lei",
                "depozite_termen_mn_mil_lei",
                "depozite_valuta_mil_lei"
            ]
            if c in df.columns
        ]

        if dep_cols:
            df["depozite_total_mil_lei"] = (
                df[dep_cols]
                .fillna(0)
                .sum(axis=1)
            )

        elif "depozite_mil_lei" in df.columns:
            df["depozite_total_mil_lei"] = df["depozite_mil_lei"]

        return {
            "data": df,
            "sursa": _sursa(fname, "Monetar"),
            "live": True
        }

    except Exception as e:
        return {
            "data": pd.DataFrame(),
            "sursa": f"Eroare {fname}: {e}",
            "live": False
        }

# ─────────────────────────────────────────────────────────────────────────────
# SECTOR SOCIAL — Date_Sector_Social.xlsx
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_social() -> dict:
    """
    Foaie: Social
    Coloane: An, Trimestrul, Populatia ocupata (mii), Nr someri (mii),
             Rata somajului (%), Rata de ocupare (%), Castig mediu salarial (MDL)
    """
    fname = "Date_Sector_Social.xlsx"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name="Social", engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl == "an":
                rename_map[c] = "an"
            elif "trimestrul" in cl or "trimestru" in cl:
                rename_map[c] = "trimestru"
            elif "ocupat" in cl:
                rename_map[c] = "populatie_ocupata_mii"
            elif "somer" in cl or "şomer" in cl or "șomer" in cl:
                rename_map[c] = "nr_someri_mii"
            elif "somaj" in cl or "şomaj" in cl or "șomaj" in cl:
                rename_map[c] = "rata_somaj_pct"
            elif "ocupare" in cl:
                rename_map[c] = "rata_ocupare_pct"
            elif "salar" in cl or "câştig" in cl or "castig" in cl:
                rename_map[c] = "salariu_mediu_mdl"

        df = df.rename(columns=rename_map)
        df["an"] = pd.to_numeric(df["an"], errors="coerce").astype("Int64")
        for col in ["populatie_ocupata_mii","nr_someri_mii","rata_somaj_pct",
                    "rata_ocupare_pct","salariu_mediu_mdl"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Construim eticheta trimestru combinata (ex. "T1 2024")
        if "trimestru" in df.columns:
            import re
            def _short(t):
                t = str(t).strip()
                m = re.search(r"\b(IV|III|II|I)\b", t)
                if m:
                    num = {"I": 1, "II": 2, "III": 3, "IV": 4}[m.group()]
                    return f"T{num}"
                return t
            df["trim_label"] = df.apply(
                lambda r: f"{_short(r.get('trimestru',''))} {int(r['an'])}" if pd.notna(r["an"]) else "", axis=1
            )

        df = df.dropna(subset=["an"]).sort_values(["an","trimestru"]).reset_index(drop=True)
        return {"data": df, "sursa": _sursa(fname, "Social"), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare {fname}: {e}", "live": False}


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR EXTERN — Data.xlsx
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_extern_lunar() -> dict:
    """
    Foaie: Exp_Lunar
    Coloane: An, Luna, Exporturi (mil.$), Importuri (mil.$), Sold Comercial (mil.$)
    Date lunare 2022–2025.
    """
    fname = "Data.xlsx"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name="Exp_Lunar", engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl == "an":
                rename_map[c] = "an"
            elif "lun" in cl:
                rename_map[c] = "luna"
            elif "export" in cl:
                rename_map[c] = "export_mil_usd"
            elif "import" in cl:
                rename_map[c] = "import_mil_usd"
            elif "sold" in cl:
                rename_map[c] = "sold_mil_usd"

        df = df.rename(columns=rename_map)
        df["an"] = pd.to_numeric(df["an"], errors="coerce").astype("Int64")
        for col in ["export_mil_usd","import_mil_usd","sold_mil_usd"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ordine calendaristica luna
        LUNI_ORD = ["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie",
                    "Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"]
        def _luna_nr(luna_str):
            luna_str = str(luna_str).strip().rstrip()
            for i, l in enumerate(LUNI_ORD):
                if l.lower() in luna_str.lower():
                    return i + 1
            return 13

        df["luna_nr"] = df["luna"].apply(_luna_nr)
        df["label"] = df.apply(lambda r: f"{str(r['luna']).strip()[:3]} {int(r['an'])}", axis=1)
        df = df.dropna(subset=["an"]).sort_values(["an","luna_nr"]).reset_index(drop=True)
        return {"data": df, "sursa": _sursa(fname, "Exp_Lunar"), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare {fname}: {e}", "live": False}


@st.cache_data(ttl=300, show_spinner=False)
def load_extern_reexport() -> dict:
    """
    Foaie: Exp_Reexp
    Coloane: An, Luna, Exporturi autohtone, Reexporturi
    """
    fname = "Data.xlsx"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name="Exp_Reexp", engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl == "an":
                rename_map[c] = "an"
            elif "lun" in cl:
                rename_map[c] = "luna"
            elif "autohton" in cl:
                rename_map[c] = "export_autohton"
            elif "reexport" in cl:
                rename_map[c] = "reexport"

        df = df.rename(columns=rename_map)
        df["an"] = pd.to_numeric(df["an"], errors="coerce").astype("Int64")
        for col in ["export_autohton","reexport"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        LUNI_ORD = ["Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie",
                    "Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie"]
        df["luna_nr"] = df["luna"].apply(
            lambda x: next((i+1 for i,l in enumerate(LUNI_ORD) if l.lower() in str(x).lower()), 13)
        )
        df["label"] = df.apply(lambda r: f"{str(r['luna']).strip()[:3]} {int(r['an'])}", axis=1)
        df = df.dropna(subset=["an"]).sort_values(["an","luna_nr"]).reset_index(drop=True)
        return {"data": df, "sursa": _sursa(fname, "Exp_Reexp"), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare {fname}: {e}", "live": False}


@st.cache_data(ttl=300, show_spinner=False)
def load_extern_influenta(tip: str = "Export") -> dict:
    """
    Foaie: Influenta_Export sau Influenta_Import
    Coloane: An, Luna, Denumire, Grad (contributie %)
    tip: "Export" sau "Import"
    """
    fname = "Data.xlsx"
    sheet = f"Influenta_{tip}"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name=sheet, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl == "an":
                rename_map[c] = "an"
            elif "lun" in cl:
                rename_map[c] = "luna"
            elif "denum" in cl:
                rename_map[c] = "denumire"
            elif "grad" in cl:
                rename_map[c] = "grad_pct"

        df = df.rename(columns=rename_map)
        df["an"]      = pd.to_numeric(df["an"], errors="coerce").astype("Int64")
        df["grad_pct"] = pd.to_numeric(df["grad_pct"], errors="coerce")
        df = df.dropna(subset=["an","grad_pct"]).reset_index(drop=True)
        return {"data": df, "sursa": _sursa(fname, sheet), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare {sheet}: {e}", "live": False}


@st.cache_data(ttl=300, show_spinner=False)
def load_extern_tari() -> dict:
    """
    Foaie: Start_Data
    Coloane: An, Luna, Tara, Grupa Tari, Trimestru, Semestru, Exporturi, Importuri, Sold
    Date per tara, lunar.
    """
    fname = "Data.xlsx"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name="Start_Data", engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl == "an":
                rename_map[c] = "an"
            elif "lun" in cl:
                rename_map[c] = "luna"
            elif "ţară" in cl or "tara" in cl or "ţara" in cl:
                rename_map[c] = "tara"
            elif "grup" in cl:
                rename_map[c] = "grupa_tari"
            elif "trimestru" in cl:
                rename_map[c] = "trimestru"
            elif "semestru" in cl:
                rename_map[c] = "semestru"
            elif "export" in cl:
                rename_map[c] = "export_mil_usd"
            elif "import" in cl:
                rename_map[c] = "import_mil_usd"
            elif "sold" in cl:
                rename_map[c] = "sold_mil_usd"

        df = df.rename(columns=rename_map)
        df["an"] = pd.to_numeric(df["an"], errors="coerce").astype("Int64")
        for col in ["export_mil_usd","import_mil_usd","sold_mil_usd"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["an"]).reset_index(drop=True)
        return {"data": df, "sursa": _sursa(fname, "Start_Data"), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare Start_Data: {e}", "live": False}


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR REAL — Date_Sector_Real.xlsx (template — fisier de creat)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_real() -> dict:
    """
    Foaie asteptata: Real
    Coloane: An, Crestere PIB (%), PIB nominal (mil lei), Industrie (%), Agricultura (%), Constructii (%), Servicii (%)
    """
    fname = "Date_Sector_Real.xlsx"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa (foloseste template)", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name=0, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        df["an"] = pd.to_numeric(df.iloc[:,0], errors="coerce").astype("Int64")
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["an"]).sort_values("an").reset_index(drop=True)
        return {"data": df, "sursa": _sursa(fname), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare {fname}: {e}", "live": False}


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR PUBLIC — Date_Sector_Public.xlsx (template — fisier de creat)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_public() -> dict:
    """
    Foaie asteptata: Public
    Coloane: An, Venituri (% PIB), Cheltuieli (% PIB), Sold bugetar (% PIB), Datorie publica (% PIB)
    """
    fname = "Date_Sector_Public.xlsx"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa (foloseste template)", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name=0, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        df["an"] = pd.to_numeric(df.iloc[:,0], errors="coerce").astype("Int64")
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["an"]).sort_values("an").reset_index(drop=True)
        return {"data": df, "sursa": _sursa(fname), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare {fname}: {e}", "live": False}


# ─────────────────────────────────────────────────────────────────────────────
# Utilitare
# ─────────────────────────────────────────────────────────────────────────────

def fisiere_disponibile() -> dict:
    """Returneaza starea fisierelor Excel per sector."""
    files = {
        "Extern":  "Data.xlsx",
        "Monetar": "Date_Sector_Monetar.xlsx",
        "Social":  "Date_Sector_Social.xlsx",
        "Real":    "Date_Sector_Real.xlsx",
        "Public":   "Date_Sector_Public.xlsx",
        "Servicii":  "Date_Servicii.xlsx",
    }
    return {
        sector: {
            "fisier":  fname,
            "exista":  _file_exists(fname),
            "path":    _path(fname),
        }
        for sector, fname in files.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR EXTERN — Servicii — Date_Servicii.xlsx
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_servicii() -> dict:
    """
    Foaie: Imp_Exp_Servicii
    Coloane: An, Trimestrul, Exporturi (mil.$), Importuri (mil.$), Sold Comercial (mil.$)
    Date trimestriale 2015–2025.
    """
    fname = "Date_Servicii.xlsx"
    if not _file_exists(fname):
        return {"data": pd.DataFrame(), "sursa": f"{fname} — fisier lipsa", "live": False}
    try:
        df = pd.read_excel(_path(fname), sheet_name="Imp_Exp_Servicii", engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl == "an":
                rename_map[c] = "an"
            elif "trimestrul" in cl or "trimestru" in cl:
                rename_map[c] = "trimestru"
            elif "export" in cl:
                rename_map[c] = "export_servicii_mil_usd"
            elif "import" in cl:
                rename_map[c] = "import_servicii_mil_usd"
            elif "sold" in cl:
                rename_map[c] = "sold_servicii_mil_usd"

        df = df.rename(columns=rename_map)
        df["an"] = pd.to_numeric(df["an"], errors="coerce").astype("Int64")
        for col in ["export_servicii_mil_usd", "import_servicii_mil_usd", "sold_servicii_mil_usd"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ordine trimestriala + eticheta
        import re
        def _trim_nr(t):
            t = str(t).strip()
            m = re.search(r"\b(IV|III|II|I)\b", t)
            if m:
                return {"I": 1, "II": 2, "III": 3, "IV": 4}[m.group()]
            return 5

        def _trim_label(an, t):
            m = re.search(r"\b(IV|III|II|I)\b", str(t))
            num = {"I": 1, "II": 2, "III": 3, "IV": 4}.get(m.group(), "?") if m else "?"
            return f"T{num} {int(an)}" if pd.notna(an) else ""

        df["trim_nr"]    = df["trimestru"].apply(_trim_nr)
        df["trim_label"] = df.apply(lambda r: _trim_label(r["an"], r["trimestru"]), axis=1)
        df = df.dropna(subset=["an"]).sort_values(["an", "trim_nr"]).reset_index(drop=True)

        return {"data": df, "sursa": _sursa(fname, "Imp_Exp_Servicii"), "live": True}
    except Exception as e:
        return {"data": pd.DataFrame(), "sursa": f"Eroare {fname}: {e}", "live": False}