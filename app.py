from pathlib import Path

import streamlit as st

from src.util.estilo import aplicar_estilo

# set_page_config fica aqui (e só aqui), antes de qualquer outro comando
st.set_page_config(
    page_title="Petz Cobasi | Antes e depois da fusão",
    page_icon="🐾",
    layout="wide",
)

ASSETS = Path(__file__).parent / "assets"
# Versão recortada (sem a margem transparente) em azul-marinho, para a sidebar azul-clara
st.logo(str(ASSETS / "logo_petzcobasi_marinho.png"), size="large")
aplicar_estilo()

paginas = [
    st.Page("src/pages/main_page.py", title="Início", icon=":material/home:", default=True),
    st.Page("src/pages/analyse.py", title="Análise", icon=":material/insights:"),
    st.Page("src/pages/explicacoes.py", title="Por que variou?", icon=":material/auto_awesome:"),
    st.Page("src/pages/conclusao.py", title="Conclusão", icon=":material/task_alt:"),
    st.Page("src/pages/metodologia.py", title="Dados e método", icon=":material/table_chart:"),
    st.Page("src/pages/about.py", title="Sobre", icon=":material/groups:"),
]
st.navigation(paginas).run()

# Para rodar: python -m streamlit run app.py
