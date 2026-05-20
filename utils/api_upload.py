"""
Upload si parsare fisiere Excel/CSV
Detecteaza automat structura si mapeaza la indicatorii din dashboard.
"""

import pandas as pd
import io
import streamlit as st
from datetime import datetime


# ── Parsare fisier ────────────────────────────────────────────────────────────

def parse_uploaded_file(uploaded_file) -> dict:
    """
    Parseaza un fisier Excel sau CSV incarcat via st.file_uploader.
    Returneaza dict cu: {sheet_name: DataFrame}
    """
    name = uploaded_file.name.lower()
    result = {}

    try:
        if name.endswith(".csv"):
            # Detecteaza separatorul automat
            content = uploaded_file.read().decode("utf-8-sig", errors="replace")
            sep = ";" if content.count(";") > content.count(",") else ","
            df = pd.read_csv(io.StringIO(content), sep=sep,
                             thousands=".", decimal=",")
            df = _clean_df(df)
            result["Sheet1"] = df

        elif name.endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(uploaded_file)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet,
                                   header=None)  # citim fara header initial
                df = _detect_header(df)
                df = _clean_df(df)
                result[sheet] = df

    except Exception as e:
        st.error(f"Eroare la parsarea fisierului: {e}")

    return result


def _detect_header(df: pd.DataFrame) -> pd.DataFrame:
    """Detecteaza randul de header si il seteaza ca index de coloane."""
    # Cauta primul rand cu mai mult de 50% celule ne-goale
    for i, row in df.iterrows():
        filled = row.notna().sum()
        if filled >= max(2, len(df.columns) * 0.4):
            df.columns = [str(c).strip() for c in df.iloc[i]]
            df = df.iloc[i+1:].reset_index(drop=True)
            return df
    return df


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Curata DataFrame: strip, converteste numere, elimina randuri goale."""
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        # Incearca conversie numerica
        try:
            cleaned = df[col].astype(str).str.replace(" ", "").str.replace(",", ".").str.replace("%","")
            numeric = pd.to_numeric(cleaned, errors="coerce")
            if numeric.notna().sum() / len(numeric) > 0.5:
                df[col] = numeric
        except Exception:
            pass

        # Incearca conversie data
        if df[col].dtype == object:
            try:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="ignore")
            except Exception:
                pass

    return df


# ── Detectare tip serie ───────────────────────────────────────────────────────

INDICATOR_KEYWORDS = {
    "pib":        ["pib", "gdp", "produs intern brut"],
    "ipc":        ["ipc", "inflatie", "preturi consum", "cpi"],
    "export":     ["export", "exporturi"],
    "import":     ["import", "importuri"],
    "somaj":      ["somaj", "someri", "somer", "unemployment"],
    "salariu":    ["salariu", "salarii", "castig salarial", "wage"],
    "pensie":     ["pensie", "pensii", "pension"],
    "curs":       ["curs", "valutar", "eur", "usd", "exchange"],
    "rezerve":    ["rezerve", "reserve"],
    "buget":      ["buget", "fiscal", "venituri", "cheltuieli"],
}


def detect_indicator_type(col_name: str) -> str:
    """Detecteaza tipul de indicator dintr-un nume de coloana."""
    col_lower = col_name.lower()
    for tip, keywords in INDICATOR_KEYWORDS.items():
        if any(kw in col_lower for kw in keywords):
            return tip
    return "necunoscut"


def auto_map_columns(df: pd.DataFrame) -> dict:
    """
    Mapeaza automat coloanele unui DataFrame la indicatorii din dashboard.
    Returneaza dict {coloana: tip_indicator}
    """
    mapping = {}
    for col in df.columns:
        tip = detect_indicator_type(col)
        if tip != "necunoscut":
            mapping[col] = tip
    return mapping


# ── Template Excel de import ──────────────────────────────────────────────────

def generate_template() -> bytes:
    """
    Genereaza un fisier Excel template cu structura standardizata
    pentru importul datelor in dashboard.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()

    # ── Sheet 1: Sector Real ──
    ws1 = wb.active
    ws1.title = "Sector Real"

    headers = ["An", "PIB nominal (mil. MDL)", "Crestere PIB real (%)",
               "PIB/locuitor (USD PPP)", "FBCF (% PIB)"]
    sample  = [
        [2020, 196300, -7.4, 11800, 22.1],
        [2021, 279100, 13.9, 14820, 23.4],
        [2022, 338120, -5.0, 15640, 22.8],
        [2023, 370840, -5.9, 16200, 21.8],
        [2024, 388600,  2.1, 18200, 21.3],
    ]

    _write_sheet(ws1, headers, sample, "Sector Real — PIB si crestere economica")

    # ── Sheet 2: Preturi ──
    ws2 = wb.create_sheet("Preturi")
    headers2 = ["Luna/An", "IPC total (%)", "Inflatie de baza (%)",
                "Alimente (%)", "Energie (%)"]
    sample2  = [
        ["Ian-24", 6.0, 4.5, 7.2, 4.1],
        ["Feb-24", 5.8, 4.3, 7.0, 3.9],
        ["Mar-24", 5.5, 4.2, 6.8, 3.7],
    ]
    _write_sheet(ws2, headers2, sample2, "Preturi — IPC si componente")

    # ── Sheet 3: Sector Extern ──
    ws3 = wb.create_sheet("Sector Extern")
    headers3 = ["An", "Export (mil. USD)", "Import (mil. USD)",
                "Deficit CA (% PIB)", "Rezerve BNM (mil. USD)"]
    sample3  = [
        [2022, 3188, 7562, -11.2, 3960],
        [2023, 3284, 7648,  -9.8, 4210],
        [2024, 3421, 7810,  -8.4, 4450],
    ]
    _write_sheet(ws3, headers3, sample3, "Sector Extern — comert si balanta de plati")

    # ── Sheet 4: Sector Monetar ──
    ws4 = wb.create_sheet("Sector Monetar")
    headers4 = ["Data", "Rata BNM (%)", "Curs EUR/MDL", "Curs USD/MDL", "M3 (mil. MDL)"]
    sample4  = [
        ["2024-01-04", 7.5, 19.18, 17.96, 82400],
        ["2024-04-04", 6.0, 19.35, 18.10, 84200],
        ["2024-07-04", 4.5, 19.40, 18.15, 86800],
    ]
    _write_sheet(ws4, headers4, sample4, "Sector Monetar — politica monetara")

    # ── Sheet 5: Sector Public ──
    ws5 = wb.create_sheet("Sector Public")
    headers5 = ["An", "Venituri (% PIB)", "Cheltuieli (% PIB)",
                "Deficit (% PIB)", "Datorie publica (% PIB)"]
    sample5  = [
        [2022, 33.2, 36.2, -3.0, 33.6],
        [2023, 32.7, 35.5, -2.8, 32.1],
        [2024, 33.1, 36.5, -3.4, 31.2],
    ]
    _write_sheet(ws5, headers5, sample5, "Sector Public — finante publice")

    # ── Sheet 6: Sector Social ──
    ws6 = wb.create_sheet("Sector Social")
    headers6 = ["An", "Rata somajului (%)", "Salariu mediu (MDL)",
                "Pensie medie (MDL)", "Rata saraciei (%)"]
    sample6  = [
        [2022, 3.1, 8642, 2460, 23.8],
        [2023, 2.8, 9850, 2840, 21.2],
        [2024, 2.6, 11200, 3200, 19.8],
    ]
    _write_sheet(ws6, headers6, sample6, "Sector Social — piata muncii si saracie")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _write_sheet(ws, headers, data, title):
    """Helper pentru formatarea unui sheet Excel."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    # Titlu
    ws.merge_cells("A1:E1")
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=12, color="FFFFFF")
    ws["A1"].fill = PatternFill(fgColor="0C447C", fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Headers
    for j, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=j, value=h)
        cell.font = Font(bold=True, size=10, color="0C447C")
        cell.fill = PatternFill(fgColor="E6F1FB", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")

    # Date
    for i, row in enumerate(data, 3):
        for j, val in enumerate(row, 1):
            cell = ws.cell(row=i, column=j, value=val)
            cell.alignment = Alignment(horizontal="center")
            if i % 2 == 0:
                cell.fill = PatternFill(fgColor="F9F8F5", fill_type="solid")

    # Latimi coloane
    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 30)
