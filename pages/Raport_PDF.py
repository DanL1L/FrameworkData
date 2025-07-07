import streamlit as st
import os

st.set_page_config(page_title="Rapoarte PDF", layout="wide")
st.title("Vizualizare Rapoarte PDF")

# Calea către fișiere PDF servite static
pdf_folder = "Raport"
pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

if not pdf_files:
    st.warning("Nu s-au găsit fișiere PDF.")
else:
    selected_pdf = st.selectbox("Selectează raportul:", pdf_files)

    # Cale relativă față de URL (important!)
    iframe_path = f"Raport/{selected_pdf}"

    # Afișare în iframe
    st.markdown(
        f'<iframe src="{iframe_path}" width="100%" height="800px" style="border: 1px solid #ccc;"></iframe>',
        unsafe_allow_html=True
    )

    # Buton de descărcare
    with open(os.path.join(pdf_folder, selected_pdf), "rb") as f:
        st.download_button(
            label="Descarcă raportul PDF",
            data=f,
            file_name=selected_pdf,
            mime="application/pdf"
        )
