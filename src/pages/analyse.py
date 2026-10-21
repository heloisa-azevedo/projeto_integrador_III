#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st
import html
from io import StringIO

import matplotlib.pyplot as plt
import seaborn as sns
from src.util.graficos import correlacao, linha, info

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

empresas = list(analises.keys())
abas = st.tabs(empresas)

for i, aba in enumerate(abas):
    with aba:
        empresa = empresas[i]
        df = analises[empresa]
        st.header(f"Analise referente à {empresa}")
        info(df)
        st.markdown(
            f"""
            <div style="max-width:800px; margin:0 auto 2rem;">
                <p style="text-align:left; font-weight:bold;">Informações gerais sobre o dataset:, sendo:</p>
                <ul style="margin: 0 auto; text-align: left;">
                    <li><strong>Número de itens vazios:</strong> - {df.isna().sum().sum()};</li>
                    <li><strong>Quantidade de colunas:</strong> - {len(df.columns)};</li>
                    <li><strong>Quantidade de linhas:</strong> - {len(df)};</li>
                    <li><strong>Tipo de dados presentes:</strong> - {df.dtypes}.</li>                              
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )    

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

        st.subheader(f"Informações sobre o conjunto de dados da {empresa}")
        st.dataframe(df)
        st.dataframe(df.describe())

        st.subheader(f"Correlaçao entre os dados da {empresa}", text_alignment='center')
        fig_corr = correlacao(df)
        st.pyplot(fig_corr)

        st.divider()

        if empresa != "Fusão":
            st.subheader(f"Comportamento da empresa {empresa} antes e após a Fusão", text_alignment='center')
            col_a = st.selectbox("Selecione a métrica a sem comparada:", df.columns, key=f"metrica_{i}")
            fig_lin = linha(df, "Trimestre", col_a, empresa, analises["Fusão"], "Fusão")
        
        else:
            st.subheader("Comportamento da empresa Fundida ao longo do tempo", text_alignment='center')
            col_a = st.selectbox("Selecione a métrica a sem comparada:", df.columns, key=f"metrica_{i}")
            fig_lin = linha(df, "Trimestre", col_a)

        st.pyplot(fig_lin)
