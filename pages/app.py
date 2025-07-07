import streamlit as st

# Define the pages
main_page = st.Page("Indicatori_Macro.py", title="Indicatorii MacroEconomici")
page_2 = st.Page("Prognoza.py", title="Prognoza")
page_3 = st.Page("Date.py", title="Date")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3])

# Run the selected page
pg.run()
