import streamlit as st
from pathlib import Path

main_page = st.Page("src/pages/main_page.py", title="Home")
analyse_page = st.Page("src/pages/analyse.py", title="Analise Empresas")
petz_page = st.Page("src/pages/analisePetz.py", title="Analise Petz")
cobasi_page = st.Page("src/pages/analiseCobasi.py", title="Analise Cobasi")
about_page = st.Page("src/pages/about.py", title="Sobre")

LOGO = Path(__file__).parent / "assets" / "logo_petzcobasi.png"

st.logo(str(LOGO), size="large")

st.markdown(
    """
    <style>
    [data-testid="stLogo"],
    [data-testid="stSidebarLogo"],
    [data-testid="stSidebarHeader"] img {
        height: 7rem !important;
        max-height: none !important;
        width: auto !important;
        max-width: 100% !important;
    }
    [data-testid="stSidebarHeader"] {
        height: auto !important;
        min-height: 7rem;
        padding-top: 1rem;
        padding-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
pg = st.navigation([main_page, analyse_page, petz_page, cobasi_page, about_page])

pg.run()
#python -m streamlit run app.py