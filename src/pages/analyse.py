#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st
import html

from src.data.dadosPetz import analises

import matplotlib.pyplot as plt
import seaborn as sns
from src.util.graficos import correlacao

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

if len(opcao) != 1:
    st.info("É preciso selecionar um conjunto de dados.")
    st.stop()

df = analises[opcao[0]]

st.dataframe(df)

st.subheader(f"Correlaçao entre os dados de {opcao[0]}", text_alignment='center')
fig_corr = correlacao(df)
st.pyplot(fig_corr)