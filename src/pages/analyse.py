#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st
import html
from io import StringIO

import matplotlib.pyplot as plt
import seaborn as sns
from src.util.graficos import correlacao, linha, info

from src.data import dadosPetz

from src.util.extrator_noticias import contexto_para_llm
from src.util.llm import explicar_variacoes, linkar_fontes

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

        if empresa == "Fusão":
            st.markdown(
                """
                <style>
                
                div.stAlert {
                    background-color: #b0ddf7  !important;        
                    border-radius: 6px !important;
                    text-align: center !important;
                }
                
                
                div.stAlert svg {
                    fill: #1D2858 !important;
                }
                div.stAlert p {
                    color: #1D2858 !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            st.warning("Os dados presentes antes de 2026 são suposições de como seria se as empresas Petz e Cobasi tivessem se fundido anteriormente")

        st.dataframe(df.describe())

        st.subheader(f"Correlaçao entre os dados da {empresa}", text_alignment='center')
        fig_corr = correlacao(df)
        st.pyplot(fig_corr)

        st.divider()

st.subheader("Comportamento das empresas ao longo do tempo", text_alignment='center')

col_a = st.selectbox("Selecione a métrica a ser comparada:", df.columns)

fig_lin = linha(
    lista_dados=list(analises.values()), 
    x="Trimestre", 
    y=col_a, 
    lista_empresas=empresas
)

st.plotly_chart(fig_lin, use_container_width=True)


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Buscando notícias, pode levar alguns instantes...")
def obter_contexto(empresa, coluna, df_coluna):
    nome_busca = "Petz Cobasi" if empresa == "Fusão" else empresa
    return contexto_para_llm(df_coluna, nome_busca, top=3, retornar_fontes=True)


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Gerando explicação...")
def obter_explicacao(empresa, coluna, contexto):
    return explicar_variacoes(empresa, coluna, contexto)


st.subheader("Por que a métrica variou?", text_alignment='center')
st.caption("Explicação gerada por IA a partir de notícias do período. Confira as fontes na aba ao lado.")

for empresa, df_emp in analises.items():
    with st.expander(f"{empresa} — {col_a}"):
        try:
            contexto, fontes = obter_contexto(empresa, col_a, df_emp[[col_a]])
            explicacao = obter_explicacao(empresa, col_a, contexto)
        except Exception as e:
            st.error(f"Não foi possível gerar a explicação agora: {e}")
            continue

        aba_exp, aba_not = st.tabs(["Explicação", "Notícias usadas"])
        aba_exp.markdown(linkar_fontes(explicacao, fontes))
        aba_not.markdown(contexto)