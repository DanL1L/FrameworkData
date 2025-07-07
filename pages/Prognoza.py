# pages/prognoza.py

import streamlit as st
import pandas as pd
import statsmodels.api as sm
import plotly.graph_objects as go
import plotly.express as px
import scipy

from utils.data_loader import load_forecast_data  # dacă ai funcția acolo

st.set_page_config(page_title="Prognoza Comerț", layout="wide")
st.title("Prognoza Exporturi și Importuri 2025–2028")

def load_forecast_data():
    path = "data/Model.xlsx"  # sau 'data/Model.xlsx' dacă fișierul e într-un folder separat
    df_raw = pd.read_excel(path, sheet_name="EX_IM_gap model", header=None)
# Lista completă de indicatori de utilizat
    indicatori = [
        "Real exports, mn USD",
        "Real Imports, mn USD",  # ← această linie lipsea
        "Foreign demand, index",
        "REER, index (increase =appreciation)",
        "Exchange rate",
        "Real investment, mn MDL"
    ]

    data = {}
    for indicator in indicatori: 
        # Identifică rândul în care apare fiecare indicator
        idx = df_raw[df_raw[0] == indicator].index[0]
        # Extrage valorile din coloanele 2 până la 26 (adică ani 2000–2024)
        values = df_raw.loc[idx, 2:26].values
        data[indicator] = pd.to_numeric(values, errors="coerce")

    # Construim DataFrame cu indexul anilor 2000–2024
    df = pd.DataFrame(data)
    df.index = list(range(2000, 2000 + len(df)))
    df.index.name = "An"
    return df

# === Afișare prognoză în aplicație ===
st.subheader("Prognoza Exporturi și Importuri (2025–2026)")
df_model = load_forecast_data()

# Eliminăm valorile lipsă
df_clean_exp = df_model.dropna(subset=["Real exports, mn USD"])
X_exp = df_clean_exp[["Foreign demand, index", "REER, index (increase =appreciation)",
                      "Exchange rate", "Real investment, mn MDL"]]
y_exp = df_clean_exp["Real exports, mn USD"]

df_clean_imp = df_model.dropna(subset=["Real Imports, mn USD"])
X_imp = df_clean_imp[["Foreign demand, index", "REER, index (increase =appreciation)",
                      "Exchange rate", "Real investment, mn MDL"]]
y_imp = df_clean_imp["Real Imports, mn USD"]

# Modele OLS
X_exp = sm.add_constant(X_exp)
X_imp = sm.add_constant(X_imp)
model_exp = sm.OLS(y_exp, X_exp).fit()
model_imp = sm.OLS(y_imp, X_imp).fit()

# Creșteri medii pentru extrapolare
growth = df_model.pct_change().mean()
last_values = df_model.iloc[-1]

# Prognozăm valorile explicative și rezultatele pentru 2025–2026
future_rows = []
for year in [2025, 2026]:
    new_row = last_values * (1 + growth)
    X_new_exp = sm.add_constant(new_row[X_exp.columns[1:]].values.reshape(1, -1), has_constant="add")
    X_new_imp = sm.add_constant(new_row[X_imp.columns[1:]].values.reshape(1, -1), has_constant="add")
    new_row["Real exports, mn USD"] = model_exp.predict(X_new_exp)[0]
    new_row["Real Imports, mn USD"] = model_imp.predict(X_new_imp)[0]
    future_rows.append(new_row)
    last_values = new_row

# Construim DataFrame cu prognoza
forecast_df = pd.DataFrame(future_rows, index=[2025, 2026])
forecast_display = forecast_df[["Real exports, mn USD", "Real Imports, mn USD"]].round(1)

# Afișăm tabelul
st.dataframe(forecast_display, use_container_width=True)

# Grafic interactiv
fig_forecast = px.line(
    forecast_display.reset_index(),
    x="index", y=forecast_display.columns,
    markers=True,
    title="Prognoza Exporturi și Importuri 2025–2026",
    labels={"index": "An", "value": "Valoare (mil. USD)", "variable": "Indicator"}
)
# st.plotly_chart(fig_forecast, use_container_width=True)


import plotly.graph_objects as go

# Asumăm că df_model deja există și conține coloanele necesare

# Reconstruim modelul dacă nu există
X_exp = sm.add_constant(df_model[["Foreign demand, index", "REER, index (increase =appreciation)",
                                  "Exchange rate", "Real investment, mn MDL"]])
y_exp = df_model["Real exports, mn USD"]
model_exp = sm.OLS(y_exp, X_exp).fit()

X_imp = sm.add_constant(df_model[["Foreign demand, index", "REER, index (increase =appreciation)",
                                  "Exchange rate", "Real investment, mn MDL"]])
y_imp = df_model["Real Imports, mn USD"]
model_imp = sm.OLS(y_imp, X_imp).fit()

# Calculăm creșterea medie
growth = df_model.pct_change().mean()
last_values = df_model.iloc[-1]
future_rows = []
# Extindem prognoza până în 2028
for year in [2025, 2026, 2027, 2028]:
    new_row = last_values * (1 + growth)
    X_future_exp = sm.add_constant(new_row[X_exp.columns[1:]].values.reshape(1, -1), has_constant="add")
    X_future_imp = sm.add_constant(new_row[X_imp.columns[1:]].values.reshape(1, -1), has_constant="add")
    new_row["Real exports, mn USD"] = model_exp.predict(X_future_exp)[0]
    new_row["Real Imports, mn USD"] = model_imp.predict(X_future_imp)[0]
    future_rows.append(new_row)
    last_values = new_row

# DataFrame cu prognoze
forecast_df = pd.DataFrame(future_rows, index=[2025, 2026, 2027, 2028])
forecast_df = forecast_df[["Real exports, mn USD", "Real Imports, mn USD"]]

# Combinăm istoric și prognoză
df_all = pd.concat([df_model[["Real exports, mn USD", "Real Imports, mn USD"]], forecast_df])
df_all.index = df_all.index.astype(str)  # convertește anii în text pentru axa X

fig = go.Figure()

# Exporturi: istoric
fig.add_trace(go.Scatter(
    x=df_all.index[:25],  # 2000–2024
    y=df_all["Real exports, mn USD"].iloc[:25],
    mode='lines+markers',
    name='Exporturi (istoric)',
    line=dict(color='blue', dash='solid')
))

# Exporturi: prognoză
fig.add_trace(go.Scatter(
    x=df_all.index[25:],  # 2025–2028
    y=df_all["Real exports, mn USD"].iloc[25:],
    mode='lines+markers',
    name='Exporturi (prognoză)',
    line=dict(color='blue', dash='dash')
))

# Importuri: istoric
fig.add_trace(go.Scatter(
    x=df_all.index[:25],
    y=df_all["Real Imports, mn USD"].iloc[:25],
    mode='lines+markers',
    name='Importuri (istoric)',
    line=dict(color='green', dash='solid')
))

# Importuri: prognoză
fig.add_trace(go.Scatter(
    x=df_all.index[25:],
    y=df_all["Real Imports, mn USD"].iloc[25:],
    mode='lines+markers',
    name='Importuri (prognoză)',
    line=dict(color='green', dash='dash')
))

fig.update_layout(
    title="Evoluția și Prognoza Exporturilor și Importurilor (2000–2028)",
    xaxis_title="An",
    yaxis_title="Valoare (mil. USD)",
    xaxis=dict(type='category'),
    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
)

st.plotly_chart(fig, use_container_width=True)

# Text explicativ
st.markdown("""
**Metodologie:**

Modelul utilizează regresie liniară (OLS) pentru a estima relația dintre exporturi/importuri reale și următorii factori explicativi:
- Cererea externă
- Rata reală efectivă de schimb (REER)
- Rata de schimb valutar
- Investițiile reale

Pe baza datelor istorice din perioada 2000–2024, modelul a estimat coeficienții și a aplicat o rată medie de creștere (CAGR) pentru a simula valorile din anii 2025–2028.
""")
