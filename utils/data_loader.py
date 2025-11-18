import pandas as pd
import os

def load_data(file_path=os.path.join(os.path.dirname(__file__), '../data/Data.xlsx')):
    """
    Încărcarea și procesarea datelor din fișierul Excel.
    :param file_path: Calea către fișierul Excel
    :return: Trei DataFrame-uri - unul pentru datele generale, unul pentru exporturi/reexporturi și unul pentru influența exporturilor
    """
    
    # Verificăm foile disponibile în fișier
    sheets = pd.ExcelFile(file_path).sheet_names
    required_sheets = ["Start_Data", "Exp_Reexp", "Influenta_Export", "Influenta_Import", "Exp_Lunar", "Exp_imp_Total","Import_NCM_I", "Import_NCM_II", "Import_NCM_III","Import_NCM_IV", "Import_NCM_V", "Import_NCM_VI", "Import_NCM_VII", "Import_NCM_VIII","Import_NCM_IX"]

    # Asigurăm că toate foile necesare există
    for sheet in required_sheets:
        if sheet not in sheets:
            raise ValueError(f"Foaia '{sheet}' nu există în fișierul Excel. Foi disponibile: {sheets}")

    # Încărcăm datele din fiecare foaie
    df = pd.read_excel(file_path, sheet_name="Start_Data")
    df_exp_reexp = pd.read_excel(file_path, sheet_name="Exp_Reexp")
    df_exp_lunar = pd.read_excel(file_path, sheet_name="Exp_Lunar")
    df_influenta = pd.read_excel(file_path, sheet_name="Influenta_Export")
    df_influenta_Import = pd.read_excel(file_path, sheet_name="Influenta_Import")
    df_exp_imp_Total = pd.read_excel(file_path, sheet_name="Exp_imp_Total")
    
    # Preprocesare pentru "Start_Data"
    df["An"] = df["An"].fillna(method="ffill").astype("Int64")
    df = df.dropna(subset=["Lună", "Țară"])
    df = df[["An", "Lună", "Țară", "Grupă Țări", "Trimestru", "Semestru", 
                             "Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]]

    # Preprocesare pentru "Exp_Reexp"
    df_exp_reexp["An"] = df_exp_reexp["An"].fillna(method="ffill").astype("Int64")
    df_exp_reexp = df_exp_reexp.dropna(subset=["Lună"])
    df_exp_reexp = df_exp_reexp[["An", "Lună", "Exporturi autohtone", "Reexporturi"]]

    # Preprocesare pentru "Influenta_Export"
    df_influenta["An"] = df_influenta["An"].fillna(method="ffill").astype("Int64")
    df_influenta = df_influenta.dropna(subset=["Lună", "Denumire"])
    df_influenta = df_influenta[["An", "Lună", "Denumire", "Grad"]]

    # Preprocesare pentru "Influenta_Import"
    df_influenta_Import["An"] = df_influenta_Import["An"].fillna(method="ffill").astype("Int64")
    df_influenta_Import = df_influenta_Import.dropna(subset=["Lună", "Denumire"])
    df_influenta_Import = df_influenta_Import[["An", "Lună", "Denumire", "Grad"]]

    # Preprocesare pentru "Exp_Lunar"
    df_exp_lunar["An"] = df_exp_lunar["An"].fillna(method="ffill").astype("Int64")
    df_exp_lunar = df_exp_lunar.dropna(subset=["Lună"])
    df_exp_lunar = df_exp_lunar[["An", "Lună", "Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]]

    # Preprocesare pentru "Exp_imp_Total"
    df_exp_imp_Total["An"] = df_exp_imp_Total["An"].fillna(method="ffill").astype("Int64")
    df_exp_imp_Total = df_exp_imp_Total.dropna(subset=["Lună"])
    df_exp_imp_Total = df_exp_imp_Total[["An", "Lună", "Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]]

    # Preluăm toate foile relevante pentru Import_NCM
    sheet_names = [s for s in sheets if s.startswith("Import_NCM_")]
    df_import_ncm_all = {}

    for sheet in sheet_names:
        df_tmp = pd.read_excel(file_path, sheet_name=sheet)
        df_tmp.columns = ["Cod", "Lună", "Denumire", "2022", "2023", "2024", "2025"]
        df_tmp = df_tmp.dropna(subset=["Cod", "Denumire"])
        df_tmp["Cod"] = df_tmp["Cod"].astype(str).str.strip()
        df_tmp["Lună"] = df_tmp["Lună"].astype(str).str.strip()
        df_tmp["Denumire"] = df_tmp["Denumire"].astype(str).str.strip()
        df_import_ncm_all[sheet] = df_tmp

    return df, df_exp_reexp, df_influenta, df_influenta_Import, df_exp_lunar, df_exp_imp_Total, df_import_ncm_all


def load_forecast_data():
    path = "data/Model.xlsx"  # ajustează dacă fișierul e în altă locație
    df_raw = pd.read_excel(path, sheet_name="EX_IM_gap model", header=None)

    indicatori = [
        "Real exports, mn USD",
        "Real Imports, mn USD",
        "Foreign demand, index",
        "REER, index (increase =appreciation)",
        "Exchange rate",
        "Real investment, mn MDL"
    ]

    data = {}
    for indicator in indicatori:
        idx = df_raw[df_raw[0] == indicator].index[0]
        values = df_raw.loc[idx, 2:26].values
        data[indicator] = pd.to_numeric(values, errors="coerce")

    df = pd.DataFrame(data)
    df.index = list(range(2000, 2000 + len(df)))
    df.index.name = "An"
    return df
