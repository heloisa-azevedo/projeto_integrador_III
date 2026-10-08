import streamlit as st

main_page = st.Page("src/pages/main_page.py", title="Home")
analyse_page = st.Page("src/pages/analyse.py", title="Analise")
about_page = st.Page("src/pages/about.py", title="Sobre")

# navegação entre as paginas
pg = st.navigation([main_page, analyse_page, about_page])


pg.run()
#python -m streamlit run app.py