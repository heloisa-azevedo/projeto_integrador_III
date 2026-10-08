#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st

from src.data.dadosPetz import analises

opcao = st.multiselect("Selecione a empresa:", analises.keys(), max_selections=1)

if len(opcao) != 1:
    st.info("É preciso selecionar um conjunto de dados.")
    st.stop()

df = analises[opcao[0]]

st.dataframe(df)