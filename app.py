
import streamlit as st

# Define the pages
main_page = st.Page("Main.py", title="Indicatorii MacroEconomici")
page_2 = st.Page("Real.py", title="Sectorul Real")
page_3 = st.Page("Indicatori_Macro.py", title="Sectorul Extern")   
page_4 = st.Page("Monetar.py", title="Sectorul Monetar")
page_5 = st.Page("Public.py", title="Sectorul Public")
page_6 = st.Page("Social.py", title="Sectorul Social")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_5, page_6])

# Run the selected page
pg.run()