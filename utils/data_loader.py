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
    required_sheets = ["Start_Data", "Exp_Reexp", "Influenta_Export", "Influenta_Import", "Exp_Lunar", "Exp_imp_Total"]

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

    return df, df_exp_reexp, df_influenta, df_influenta_Import, df_exp_lunar, df_exp_imp_Total
