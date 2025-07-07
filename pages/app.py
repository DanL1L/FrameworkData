import streamlit as st

# Define the pages
main_page = st.Page("Indicatori_Macro.py", title="Indicatorii MacroEconomici")
page_2 = st.Page("Prognoza.py", title="Prognoza")
page_3 = st.Page("Export.py", title="Export")
page_4 = st.Page("Import.py", title="Import")
page_5 = st.Page("Raport_PDF.py", title="Rapoarte")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_5])

# Run the selected page
pg.run()