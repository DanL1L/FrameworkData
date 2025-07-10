import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Date import NCM 9 Cifre", layout="wide")
st.markdown("# Date import NCM 9 Cifre")

# === Funcții ===
def incarca_date(cale_fisier: str = "data/Import_Date_9_Cifre.xlsx") -> pd.DataFrame:
    try:
        return pd.read_excel(cale_fisier)
    except Exception as e:
        st.error(f"Eroare la încărcarea fișierului: {e}")
        return pd.DataFrame()

def curata_coduri(df: pd.DataFrame) -> pd.DataFrame:
    df['Cod_2'] = df['Cod_2'].astype(str).str.zfill(2)
    df['Cod_4'] = df['Cod_4'].astype(str).str.zfill(4)
    df['Cod_6'] = df['Cod_6'].astype(str).str.zfill(6)
    df['Cod_8'] = df['Cod_8'].astype(str).str.zfill(8)
    df['Cod NCM'] = df['Cod NCM'].astype(str).str.zfill(9)
    return df

def filtreaza_dupa_cod_si_an(df: pd.DataFrame, lungime_cod: int = 9, an: int = None) -> pd.DataFrame:
    if lungime_cod not in [2, 4, 6, 8, 9]:
        raise ValueError("Lungimea codului trebuie să fie 2, 4, 6, 8 sau 9.")

    coloana_cod = {
        2: 'Cod_2',
        4: 'Cod_4',
        6: 'Cod_6',
        8: 'Cod_8',
        9: 'Cod NCM'
    }[lungime_cod]

    df_filtrat = df.copy()
    if an is not None:
        df_filtrat = df_filtrat[df_filtrat['Anul'] == an]

    df_filtrat = df_filtrat[[coloana_cod, 'Tari', 'Cantitatea', 'Valoarea, mii dolari SUA', 'Anul']]
    df_filtrat = df_filtrat.rename(columns={coloana_cod: 'Cod selectat'})

    # Conversie la numeric pentru agregare și afișare corectă
    df_filtrat['Cantitatea'] = pd.to_numeric(df_filtrat['Cantitatea'], errors='coerce')
    df_filtrat['Valoarea, mii dolari SUA'] = pd.to_numeric(df_filtrat['Valoarea, mii dolari SUA'], errors='coerce')

    return df_filtrat.sort_values(by='Valoarea, mii dolari SUA', ascending=False).reset_index(drop=True)

# === UI Sidebar ===
st.sidebar.header("Filtrul de selectare")
df = incarca_date()
df = curata_coduri(df)

if not df.empty:
    ani_disponibili = sorted(df['Anul'].dropna().unique(), reverse=True)
    an_selectat = st.sidebar.selectbox("Selectează anul", ani_disponibili)

    nivel_cod = st.sidebar.radio("Lungimea codului NCM", options=[2, 4, 6, 8, 9], index=4)

    cod_utilizator = st.sidebar.text_input("Introdu codul dorit (parțial sau complet):", value="", max_chars=9)

    # === Filtrare ===
    df_filtrat = filtreaza_dupa_cod_si_an(df, lungime_cod=nivel_cod, an=an_selectat)

    if cod_utilizator:
        df_filtrat = df_filtrat[df_filtrat['Cod selectat'].str.startswith(cod_utilizator)]

 # === Tabel rezultat ===
    st.write(f"### Rezultate pentru anul **{an_selectat}**, cod NCM de **{nivel_cod} cifre**")
    st.dataframe(df_filtrat, use_container_width=True)
    st.caption(f"{len(df_filtrat)} rânduri afișate")

    # === Evoluție în timp doar dacă codul a fost introdus ===
if cod_utilizator:
    # === Preluăm toate datele pentru codul introdus (toți anii)
    df_grafic = filtreaza_dupa_cod_si_an(df, lungime_cod=nivel_cod, an=None)
    df_grafic = df_grafic[df_grafic['Cod selectat'].str.startswith(cod_utilizator)]

    if not df_grafic.empty:
        df_grafic['Anul'] = pd.to_numeric(df_grafic['Anul'], errors='coerce').astype('Int64')
        df_grafic = df_grafic.dropna(subset=['Anul'])

        evolutie = df_grafic.groupby('Anul').agg({
            'Cantitatea': 'sum',
            'Valoarea, mii dolari SUA': 'sum'
        }).reset_index()

        st.subheader("Evoluția în timp a codului selectat")
        col1, col2 = st.columns(2)

        with col1:
            fig_valoare = px.line(
                evolutie,
                x="Anul",
                y="Valoarea, mii dolari SUA",
                title="Evoluția valorii (mii USD)",
                markers=True
            )
            fig_valoare.update_layout(xaxis=dict(dtick=1))
            st.plotly_chart(fig_valoare, use_container_width=True)

        with col2:
            fig_cantitate = px.line(
                evolutie,
                x="Anul",
                y="Cantitatea",
                title="Evoluția cantității",
                markers=True
            )
            fig_cantitate.update_layout(xaxis=dict(dtick=1))
            st.plotly_chart(fig_cantitate, use_container_width=True)

        # === Pondere valorică a codului în secțiune ===
        cod_2 = cod_utilizator[:2]
        df_sectiune = df[df['Cod_2'] == cod_2]

        df_sectiune['Cantitatea'] = pd.to_numeric(df_sectiune['Cantitatea'], errors='coerce')
        df_sectiune['Valoarea, mii dolari SUA'] = pd.to_numeric(df_sectiune['Valoarea, mii dolari SUA'], errors='coerce')
        df_sectiune['Anul'] = pd.to_numeric(df_sectiune['Anul'], errors='coerce').astype('Int64')

        total_sectiune = df_sectiune.groupby('Anul')['Valoarea, mii dolari SUA'].sum().reset_index(name="Total secțiune")
        total_produs = evolutie[['Anul', 'Valoarea, mii dolari SUA']].rename(columns={'Valoarea, mii dolari SUA': 'Valoare produs'})

        df_pondere = pd.merge(total_sectiune, total_produs, on='Anul', how='inner')
        df_pondere['Pondere (%)'] = (df_pondere['Valoare produs'] / df_pondere['Total secțiune']) * 100

        st.subheader(f" Ponderea produsului {cod_utilizator} în secțiunea {cod_2}")
        st.dataframe(df_pondere, use_container_width=True)
        # === Pondere în total exporturi ===

        df_total_export = df.copy()
        df_total_export['Valoarea, mii dolari SUA'] = pd.to_numeric(df_total_export['Valoarea, mii dolari SUA'], errors='coerce')
        df_total_export['Anul'] = pd.to_numeric(df_total_export['Anul'], errors='coerce').astype('Int64')

        total_export = df_total_export.groupby('Anul')['Valoarea, mii dolari SUA'].sum().reset_index(name="Total exporturi")
        df_total_pondere = pd.merge(total_export, total_produs, on='Anul', how='inner')
        df_total_pondere['Pondere total (%)'] = (df_total_pondere['Valoare produs'] / df_total_pondere['Total exporturi']) * 100

        

        #  Afișăm ultima pondere cu metric
        if not df_pondere.empty:
            ultimul_an = df_pondere['Anul'].max()
            pondere_ultim = df_pondere[df_pondere['Anul'] == ultimul_an]['Pondere (%)'].values[0]
            st.metric(f"Pondere în cadrul secțiunii {ultimul_an}", f"{pondere_ultim:.2f}%")
            ultimul_an_total = df_total_pondere['Anul'].max()
            pondere_total = df_total_pondere[df_total_pondere['Anul'] == ultimul_an_total]['Pondere total (%)'].values[0]
            st.metric(f"Pondere în total importuri în {ultimul_an_total}", f"{pondere_total:.2f}%")

        
         # === Principalele destinații după Țări ===
        if 'Tari' in df.columns:
            top_tari = df_grafic.groupby('Tari')['Valoarea, mii dolari SUA'].sum().reset_index()
            top_tari = top_tari.sort_values(by='Valoarea, mii dolari SUA', ascending=False).head(10)

            # st.subheader(f"Top 10 țări pentru codul {cod_utilizator}")
            # st.dataframe(top_tari, use_container_width=True)

            fig_tari = px.bar(
                top_tari,
                x='Valoarea, mii dolari SUA',
                y='Tari',
                orientation='h',
                title='Top 10 țări (valoare totală) 2020 - 2024',
                text_auto='.2s'
            )
            fig_tari.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_tari, use_container_width=True)


        

        # === Distribuția pe An ===

        # === Destinații pe Grupe de țări (ex: UE, CSI) ===
        # if 'Grupe' in df.columns:
        #     top_grupe = df_grafic.groupby('Grupe')['Valoarea, mii dolari SUA'].sum().reset_index()
        #     top_grupe = top_grupe.sort_values(by='Valoarea, mii dolari SUA', ascending=False)

        #     st.subheader("Distribuția pe grupe de țări")
        #     st.dataframe(top_grupe, use_container_width=True)

        #     fig_grupe = px.pie(
        #         top_grupe,
        #         names='Grupe',
        #         values='Valoarea, mii dolari SUA',
        #         title='Distribuția valorică pe grupe de țări'
        #     )
        #     st.plotly_chart(fig_grupe, use_container_width=True)


