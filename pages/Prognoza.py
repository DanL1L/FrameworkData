# pages/prognoza.py

import streamlit as st
import pandas as pd
import statsmodels.api as sm
import plotly.graph_objects as go
import plotly.express as px

from statsmodels.tsa.api import VAR
from statsmodels.tsa.arima.model import ARIMA
# ======================
# === DATE MODEL CLASIC
# ======================

def load_forecast_data():
    path = "data/Model.xlsx"
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

st.set_page_config(page_title="Prognoza Comerț", layout="wide")
st.title("Prognoza Exporturi și Importuri 2025–2028")

df_model = load_forecast_data()

# === MODEL GAP OLS
X_exp = sm.add_constant(df_model[["Foreign demand, index", "REER, index (increase =appreciation)",
                                  "Exchange rate", "Real investment, mn MDL"]])
y_exp = df_model["Real exports, mn USD"]
model_exp = sm.OLS(y_exp, X_exp).fit()

X_imp = sm.add_constant(df_model[["Foreign demand, index", "REER, index (increase =appreciation)",
                                  "Exchange rate", "Real investment, mn MDL"]])
y_imp = df_model["Real Imports, mn USD"]
model_imp = sm.OLS(y_imp, X_imp).fit()

# === PROGNOZĂ 2025–2028
growth = df_model.pct_change().mean()
last_values = df_model.iloc[-1]
future_rows = []
for year in [2025, 2026, 2027, 2028]:
    new_row = last_values * (1 + growth)
    X_new_exp = sm.add_constant(new_row[X_exp.columns[1:]].values.reshape(1, -1), has_constant="add")
    X_new_imp = sm.add_constant(new_row[X_imp.columns[1:]].values.reshape(1, -1), has_constant="add")
    new_row["Real exports, mn USD"] = model_exp.predict(X_new_exp)[0]
    new_row["Real Imports, mn USD"] = model_imp.predict(X_new_imp)[0]
    future_rows.append(new_row)
    last_values = new_row

forecast_df = pd.DataFrame(future_rows, index=[2025, 2026, 2027, 2028])
forecast_df = forecast_df[["Real exports, mn USD", "Real Imports, mn USD"]]

# === Afișare grafic gap model
df_all = pd.concat([df_model[["Real exports, mn USD", "Real Imports, mn USD"]], forecast_df])
df_all.index = df_all.index.astype(str)
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_all.index[:25], y=df_all["Real exports, mn USD"].iloc[:25],
                         mode='lines+markers', name='Exporturi (istoric)', line=dict(color='blue')))
fig.add_trace(go.Scatter(x=df_all.index[25:], y=df_all["Real exports, mn USD"].iloc[25:],
                         mode='lines+markers', name='Exporturi (prognoză)', line=dict(color='blue', dash='dash')))
fig.add_trace(go.Scatter(x=df_all.index[:25], y=df_all["Real Imports, mn USD"].iloc[:25],
                         mode='lines+markers', name='Importuri (istoric)', line=dict(color='green')))
fig.add_trace(go.Scatter(x=df_all.index[25:], y=df_all["Real Imports, mn USD"].iloc[25:],
                         mode='lines+markers', name='Importuri (prognoză)', line=dict(color='green', dash='dash')))
fig.update_layout(title="Evoluția Exporturilor și Importurilor (2000–2028)",
                  xaxis_title="An", yaxis_title="mil. USD", xaxis=dict(type='category'))
st.plotly_chart(fig, use_container_width=True)


# ========================
# === DATE BOP EXTINSE ===
# ========================
st.subheader("Prognoza detaliată pe baza BoP")

@st.cache_data
def load_bop_data():
    df = pd.read_excel("data/BoP-data.xlsx", sheet_name="Selected_data", header=None)
    df.columns = df.iloc[0]
    df = df[1:]
    df = df.rename(columns={df.columns[0]: "Quarter", "Import of goods ": "Import of goods"})
    df["Year"] = df["Quarter"].str.extract(r'(\d{4})').astype(int)
    

    df["Quarter_Label"] = df["Quarter"]  # păstrăm denumirea trimestrelor ex: 2015_Q1

    cols = ["Quarter_Label", "Year", "Export of goods", "Import of goods", "Export of services", "Import of services",
            "Euro-Average of Q", "Gross External Debt", "General government Ext. Debt"]
    df = df[cols].copy()
    df = df[df["Year"] >= 2020]
    for c in cols[2:]:  # începem de la prima coloană numerică
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna()

df_bop = load_bop_data()

# === Funcție pentru modelare și prognoză pe 4 trimestre ===
def forecast_indicator(df, target):
    predictors = ["Euro-Average of Q", "Gross External Debt", "General government Ext. Debt"]
    X = sm.add_constant(df[predictors])
    y = df[target]
    model = sm.OLS(y, X).fit()

    # Calculăm creșterea medie doar pe coloane numerice
    growth = df[predictors + [target]].pct_change().mean()
    last_row = df.iloc[-1]

    results = []
    for year in range(2025, 2029):  # pentru fiecare an
        for q in range(1, 5):       # pentru fiecare trimestru
            next_row = last_row.copy()
            for col in predictors + [target]:
                next_row[col] = next_row[col] * (1 + growth[col])
            X_new = sm.add_constant(next_row[predictors].values.reshape(1, -1), has_constant="add")
            pred = model.predict(X_new)[0]
            results.append(pred)
            last_row = next_row
    return results

# === Calculăm prognoze complete
export_goods = forecast_indicator(df_bop, "Export of goods")
import_goods = forecast_indicator(df_bop, "Import of goods")
export_services = forecast_indicator(df_bop, "Export of services")
import_services = forecast_indicator(df_bop, "Import of services")

# === Index pentru trimestre viitoare
forecast_index = [f"{year}_Q{q}" for year in range(2025, 2029) for q in range(1, 5)]
df_forecast = pd.DataFrame({
    "Exporturi bunuri": export_goods,
    "Importuri bunuri": import_goods,
    "Exporturi servicii": export_services,
    "Importuri servicii": import_services,
}, index=forecast_index)

# === Pregătim istoricul trimestrial
df_bop.set_index("Quarter_Label", inplace=True)
df_history = df_bop[[
    "Export of goods", "Import of goods", "Export of services", "Import of services"]].copy()
df_history.columns = ["Exporturi bunuri", "Importuri bunuri", "Exporturi servicii", "Importuri servicii"]

# === Combinăm tot
combined_bop = pd.concat([df_history, df_forecast])
st.dataframe(df_forecast.round(1), use_container_width=True)

# === Grafic general 
fig2 = px.line(combined_bop.reset_index(), x="index", y=combined_bop.columns,
               title="Comerț Exterior (Bunuri și Servicii) pe Trimestre 2020 – 2028",
               markers=True, labels={"index": "Trimestru", "value": "mil. USD", "variable": "Indicator"})
st.plotly_chart(fig2, use_container_width=True)


# def forecast_arima(df):
#     target_vars = [
#         "Export of goods",
#         "Import of goods",
#         "Export of services",
#         "Import of services"
#     ]
#     forecast_horizon = 16  # 4 ani × 4 trimestre

#     forecasts = {}

#     for var in target_vars:
#         series = df[var].dropna()
#         model = ARIMA(series, order=(1,1,1))
#         fitted = model.fit()
#         pred = fitted.forecast(steps=forecast_horizon)
#         forecasts[var] = pred.values

#     # Construim DataFrame-ul final
#     index = [f"{year}_Q{q}" for year in range(2025, 2029) for q in range(1, 5)]

#     df_forecast = pd.DataFrame({
#         "Exporturi bunuri": forecasts["Export of goods"],
#         "Importuri bunuri": forecasts["Import of goods"],
#         "Exporturi servicii": forecasts["Export of services"],
#         "Importuri servicii": forecasts["Import of services"]
#     }, index=index)

#     return df_forecast

# from statsmodels.tsa.api import VAR

# def forecast_var(df):
#     # Selectăm doar seriile pentru model
#     df_model = df[[
#         "Export of goods", "Import of goods",
#         "Export of services", "Import of services"
#     ]].copy()

#     # Verificăm că sunt toate numerice
#     df_model = df_model.apply(pd.to_numeric, errors="coerce").dropna()

#     # Estimăm lagul optim
#     model = VAR(df_model)
#     selected_lag = model.select_order(maxlags=8)
#     optimal_lag = selected_lag.aic

#     # Re-antrenăm modelul cu lag-ul optim
#     var_model = model.fit(optimal_lag)

#     # Prognozăm 16 trimestre (4 ani)
#     forecast = var_model.forecast(df_model.values, steps=16)

#     # Construim indexul trimestrial viitor
#     future_index = [f"{year}_Q{q}" for year in range(2025, 2029) for q in range(1, 5)]

#     # Creăm DataFrame cu rezultate
#     df_forecast = pd.DataFrame(forecast, columns=[
#         "Exporturi bunuri", "Importuri bunuri",
#         "Exporturi servicii", "Importuri servicii"
#     ], index=future_index)

#     return df_forecast



# def forecast_ols(df):
#     predictors = ["Euro-Average of Q", "Gross External Debt", "General government Ext. Debt"]
#     targets = ["Export of goods", "Import of goods", "Export of services", "Import of services"]

#     df_model = df[predictors + targets].copy()
#     df_model = df_model.apply(pd.to_numeric, errors="coerce").dropna()

#     # Calculăm creșterea medie istorică
#     growth = df_model.pct_change().mean()
#     last_row = df_model.iloc[-1].copy()

#     results = { "Exporturi bunuri": [], "Importuri bunuri": [],
#                 "Exporturi servicii": [], "Importuri servicii": [] }

#     for year in range(2025, 2029):
#         # Actualizăm datele pentru anul respectiv
#         for col in predictors + targets:
#             last_row[col] *= (1 + growth[col])

#         X_new = sm.add_constant(last_row[predictors].values.reshape(1, -1), has_constant="add")

#         for target, label in zip(targets, results.keys()):
#             model = sm.OLS(df_model[target], sm.add_constant(df_model[predictors])).fit()
#             pred = model.predict(X_new)[0]
#             results[label].extend([pred] * 4)  # replicăm pentru Q1-Q4

#     forecast_index = [f"{year}_Q{q}" for year in range(2025, 2029) for q in range(1, 5)]
#     df_forecast = pd.DataFrame(results, index=forecast_index)

#     return df_forecast

# # === Selectare model de prognoză
# model_type = st.selectbox(
#     "Selectează modelul de prognoză",
#     ["OLS", "ARIMA", "VAR"]
# )


# if model_type == "OLS":
#     df_forecast = forecast_ols(df_bop)
# elif model_type == "ARIMA":
#     df_forecast = forecast_arima(df_bop)
# else:  # VAR
#     df_forecast = forecast_var(df_bop)



# # Istoric
# df_bop_trim = df_bop.set_index("Quarter_Label")[
#     ["Export of goods", "Import of goods", "Export of services", "Import of services"]
# ].copy()
# df_bop_trim.columns = ["Exporturi bunuri", "Importuri bunuri", "Exporturi servicii", "Importuri servicii"]

# # Combină
# combined = pd.concat([df_bop_trim, df_forecast])
# st.dataframe(df_forecast.round(1), use_container_width=True)

# # Grafic
# fig = px.line(combined.reset_index(), x="index", y=combined.columns,
#               title=f"Prognoză Comerț Exterior ({model_type})",
#               markers=True, labels={"index": "Trimestru", "value": "mil. USD", "variable": "Indicator"})
# st.plotly_chart(fig, use_container_width=True)



# if model_type == "OLS":
#     st.markdown("**Model utilizat:** Regressie OLS pe baza cursului EUR, datoriei externe totale și guvernamentale.")
# elif model_type == "ARIMA":
#     st.markdown("**Model utilizat:** ARIMA (model univariabil autoregresiv cu integrări și medie mobilă).")
# else:
#     st.markdown("**Model utilizat:** VAR (vector autoregresiv multivariabil pentru toate cele 4 serii).")



st.markdown("""
**Notă metodologică:** Prognozele sunt generate cu modele OLS individuale pentru fiecare indicator (
exporturi/importuri de bunuri/servicii) folosind 3 variabile explicative: cursul de schimb (EUR),
datoria externă  și datoria gov.
""")
