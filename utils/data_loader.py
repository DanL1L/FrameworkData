import pandas as pd
import os

def load_data(file_path = os.path.join(os.path.dirname(__file__), '../data/Data.xlsx')):
    """
    Încărcarea și procesarea datelor din fișierul Excel.
    :param file_path: Calea către fișierul Excel
    :return: Două DataFrame-uri - unul pentru datele generale și altul pentru exporturi/reexporturi
    """
    
    # Verificăm foile disponibile în fișier
    sheets = pd.ExcelFile(file_path).sheet_names
    required_sheets = ["Start_Data", "Exp_Reexp","Influenta_Export"]

    # Asigurăm că ambele foi există
    for sheet in required_sheets:
        if sheet not in sheets:
            raise ValueError(f"Foaia '{sheet}' nu există în fișierul Excel. Foi disponibile: {sheets}")

    # Încărcăm datele din fiecare foaie
    df_general = pd.read_excel(file_path, sheet_name="Start_Data")
    df_exp_reexp = pd.read_excel(file_path, sheet_name="Exp_Reexp")

    # Preprocesare pentru "Start_Data"
    df_general["An"] = df_general["An"].fillna(method="ffill").astype("Int64")
    df_general = df_general.dropna(subset=["Lună", "Țară"])
    df_general = df_general[["An", "Lună", "Țară", "Grupă Țări", "Trimestru", "Semestru", 
                             "Exporturi (mil. $)", "Importuri (mil. $)", "Sold Comercial (mil. $)"]]

    # Preprocesare pentru "Exp_Reexp"
    df_exp_reexp["An"] = df_exp_reexp["An"].fillna(method="ffill").astype("Int64")
    df_exp_reexp = df_exp_reexp.dropna(subset=["Lună"])
    df_exp_reexp = df_exp_reexp[["An", "Lună", "Exporturi autohtone", "Reexporturi"]]

    

    return df_general, df_exp_reexp
