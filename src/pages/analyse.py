#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st
import html
from io import StringIO

import matplotlib.pyplot as plt
import seaborn as sns
from src.util.graficos import correlacao, linha

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

if len(opcao) != 1:
    st.info("É preciso selecionar um conjunto de dados.")
    st.stop()

empresa = opcao[0]
df = analises[empresa]

st.subheader(f"Exibição do conjunto de dados da {empresa}", text_alignment='center')

buffer = StringIO()
df.info(buf=buffer)
st.markdown(
    """
    <style>
    pre code {
        color: black !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.code(buffer.getvalue(), language="text")

st.markdown(
    """
    <div style="max-width:800px; margin:0 auto 2rem;">
        <p style="text-align:left; font-weight:bold;">Foram escolhidas 16 colunas para realizar a análise, sendo:</p>
        <ul style="margin: 0 auto; text-align: left;">
            <li><strong>Receita Bruta</strong> - Faturamento total da empresa;</li>
            <li><strong>Receita Líquida</strong> -  Valor total das vendas ou serviços prestados;</li>
            <li><strong>EBITDA Ajustado</strong> -  Uma métrica financeira não GAAP que fornece uma visão normalizada do desempenho operacional;</li>
            <li><strong>Lucro Líquido</strong> - Ganho real sobre as operações;</li>
            <li><strong>Caixa Equivalente</strong> - O dinheiro vivo que a empresa tem disponível imediatamente ou aplicações de liquidez imediata;</li>
            <li><strong>Aplicações Financeiras</strong> - Investimentos feitos pela empresa; </li>
            <li><strong>Empréstimos CP</strong> - Obrigações financeiras que devem ser pagas em até 12 meses;</li>
            <li><strong>Empréstimos LP</strong> - Obrigações financeiras que devem ser pegas num período superior a 12 meses;</li>
            <li><strong>Estoque</strong> - Valor financeiro total de mercadorias;</li>
            <li><strong>Fluxo de Caixa Operacional</strong> - O dinheiro real gerado pelas operações do dia a dia da empresa;</li>
            <li><strong>SSS Percentual</strong> - Indicador que mede o crescimento das vendas apenas das lojas que já estavam abertas há mais de 12 meses;</li>
            <li><strong>Penetração Digital</strong> - Percentual das vendas totais da empresa que foram realizadas por canais digitais;</li>
            <li><strong>Margem EBITDA</strong> - Indica a rentabilidade operacional da empresa;</li>
            <li><strong>Dívida Bruta</strong> - Soma de todas as obrigações financeiras da empresa;</li>
            <li><strong>Caixa Total</strong> - Soma de todo o dinheiro disponível e das reservas financeiras da empresa;</li>
            <li><strong>Dívida Líquida</strong> - Situação Geral de endividamento da empresa.</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)

st.dataframe(df)

st.dataframe(df.describe())

st.subheader(f"Correlaçao entre os dados da {empresa}", text_alignment='center')
fig_corr = correlacao(df)
st.pyplot(fig_corr)

st.divider()

st.subheader(f"Comportamento da empresa ao longo do tempo")
for i in df.columns:
    fig_lin = linha(df, "Trimestre", i)
    st.pyplot(fig_lin)