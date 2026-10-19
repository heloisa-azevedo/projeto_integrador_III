#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st
import html
from io import StringIO

import matplotlib.pyplot as plt
import seaborn as sns
from src.util.graficos import correlacao

from src.data import dadosPetz

@st.cache_data(ttl=60 * 60 * 24, show_spinner="Buscando dados no RI, pode levar alguns instantes...")
def obter_analises():
    return dadosPetz.carregar_analises()

analises = obter_analises()

st.title("Analise do RI do grupo Petz Cobasi", text_alignment='center')
st.markdown(
    "<p style='text-align:center; max-width:800px; margin:0 auto 2rem'>"
    "O objetivo da analise é descobrir se dada uma das empresas do grupo, era favorável para realizar a fusão. "
    "A hipotese vai ser medida sobre o poder de mercado, analisando o aumento de suas margens de lucro, "
    "comparando-as a antes e depois da fusão ser realizada."
    "</p>",
    unsafe_allow_html=True,
    )
st.divider()

opcao = st.multiselect("Selecione o conjunto de dados:", ['Petz', 'Cobasi'], max_selections=1)
empresa = opcao[0]

if len(opcao) != 1:
    st.info("É preciso selecionar um conjunto de dados.")
    st.stop()

df = analises[empresa]

st.subheader(f"Exibição do conjunto de dados da {empresa}", text_alignment='center')

buffer = StringIO()
df.info(buf=buffer)
st.markdown(
    """
    <style>
    pre code {
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.code(buffer.getvalue(), language="text")

st.dataframe(df)

st.dataframe(df.describe())

st.subheader(f"Correlaçao entre os dados da {empresa}", text_alignment='center')
fig_corr = correlacao(df)
st.pyplot(fig_corr)
