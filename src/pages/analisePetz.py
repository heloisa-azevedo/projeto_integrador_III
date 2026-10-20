#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st

from src.util.graficos import correlacao, linha, info

from src.data import dadosPetz

@st.cache_data(ttl=60 * 60 * 24, show_spinner="Buscando dados no RI, pode levar alguns instantes...")
def obter_analises():
    return dadosPetz.carregar_analises()

analises = obter_analises()
df_petz = analises["Petz"]
df_fusao = analises['Fusão']


st.title("Comparação da Petz antes e após a Fusão", text_alignment='center')
st.markdown(
    "<p style='text-align:center; max-width:800px; margin:0 auto 2rem'>"
    "O objetivo da comparação é entender se a fusão foi benéfica ou não para a empresa Petz."
    "</p>",
    unsafe_allow_html=True,
    )
st.divider()

col1, col2 = st.columns(2)

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

with col1:
    st.subheader(f"Informações sobre o conjunto de dados da Petz")
    info(df_petz)
    st.dataframe(df_petz)
    st.dataframe(df_petz.describe())


with col2:
    st.subheader(f"Informações sobre o conjunto de dados da Fusão")
    info(df_fusao)
    st.dataframe(df_fusao)
    st.dataframe(df_fusao.describe())

st.subheader(f"Correlaçao entre os dados da Petz e da Fusão", text_alignment='center')
fig_corrA = correlacao(df_petz)
fig_corrB = correlacao(df_fusao)
st.pyplot(fig_corrA)
st.pyplot(fig_corrB)

st.divider()

st.subheader(f"Comportamento da empresa ao longo do tempo")

col_a = st.selectbox("Selecione a métrica a sem comparada:", df_petz.columns)
fig_lin = linha(df_petz, df_fusao,"Trimestre", col_a, "Petz")
st.pyplot(fig_lin)
