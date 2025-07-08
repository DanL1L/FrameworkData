import streamlit as st

# Define the pages
main_page = st.Page("pages/Indicatori_Macro.py", title="Indicatorii MacroEconomici")
page_2 = st.Page("pages/Prognoza.py", title="Prognoza")
page_3 = st.Page("pages/Export.py", title="Export")
page_4 = st.Page("pages/Import.py", title="Import")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4])

# Run the selected page
pg.run()
