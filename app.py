
import streamlit as st

# Define the pages
main_page = st.Page("pages/Main.py", title="Indicatorii MacroEconomici")
page_2 = st.Page("pages/Real.py", title="Sectorul Real")
page_3 = st.Page("pages/Indicatori_Macro.py", title="Sectorul Extern")   
page_4 = st.Page("pages/Monetar.py", title="Sectorul Monetar")
page_5 = st.Page("pages/Public.py", title="Sectorul Public")
page_6 = st.Page("pages/Social.py", title="Sectorul Social")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_5, page_6])

# Run the selected page

pg.run()

