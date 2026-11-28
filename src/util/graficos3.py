#LOCAL QUE A ANALISE DEVE OCORRER
import streamlit as st
import html
from io import StringIO

import matplotlib.pyplot as plt
import seaborn as sns
from src.util.graficos import correlacao, linha
from src.util import graficos2, graficos3

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
plt.close(fig_corr)

st.divider()

st.subheader(f"Comportamento da empresa ao longo do tempo")
# O trimestre é o índice do DataFrame, não uma coluna.
# Criamos uma cópia com o índice convertido em coluna para o gráfico.
df_linha = df.reset_index()
for i in df.columns:
    fig_lin = linha(df_linha, "Trimestre", i)
    st.pyplot(fig_lin)
    plt.close(fig_lin)

st.divider()

# ==============================================================================
# SEÇÃO: ANÁLISES FINANCEIRAS COMPLEMENTARES
# ==============================================================================
st.header("Análises Financeiras Complementares", text_alignment="center")
st.markdown(
    "<p style='text-align:center; max-width:850px; margin:0 auto 2rem'>"
    "Visualizações estatísticas e financeiras complementares investigando rentabilidade, distribuição dos resultados, "
    "endividamento, liquidez, eficiência operacional e comparações entre Petz e Cobasi."
    "</p>",
    unsafe_allow_html=True
)

# 1. Histogramas Financeiros
st.subheader(f"1. Histogramas Financeiros e Operacionais ({empresa})")
fig1 = graficos2.grafico_histogramas_financeiros(df, empresa)
st.pyplot(fig1)
plt.close(fig1)

st.divider()

# 2. Boxplots Financeiros Comparativos
st.subheader("2. Boxplots Financeiros Comparativos (Petz vs. Cobasi)")
fig2 = graficos2.grafico_boxplots_financeiros(analises)
st.pyplot(fig2)
plt.close(fig2)

st.divider()

# 3 e 4. Dispersões (Organizados em 2 Colunas para melhor leitura)
col_disp1, col_disp2 = st.columns(2)
with col_disp1:
    st.subheader("3. Receita Líquida vs. Lucro Líquido")
    fig3 = graficos2.grafico_dispersao_receita_lucro(analises)
    st.pyplot(fig3)
    plt.close(fig3)

with col_disp2:
    st.subheader("4. EBITDA vs. Margem EBITDA")
    fig4 = graficos2.grafico_dispersao_ebitda_margem(analises)
    st.pyplot(fig4)
    plt.close(fig4)

st.divider()

# 5. Estrutura de Endividamento
st.subheader(f"5. Estrutura de Endividamento e Posição Financeira ({empresa})")
fig5 = graficos2.grafico_comparacao_divida(df, empresa)
st.pyplot(fig5)
plt.close(fig5)

st.divider()

# 6. Liquidez e Composição da Dívida
st.subheader(f"6. Liquidez Disponível e Cobertura da Dívida de Curto Prazo ({empresa})")
fig6 = graficos2.grafico_liquidez_composicao_divida(df, empresa)
st.pyplot(fig6)
plt.close(fig6)

st.divider()

# 7. Variação Percentual QoQ
st.subheader(f"7. Variação Percentual Trimestre contra Trimestre (QoQ) ({empresa})")
fig7 = graficos2.grafico_variacao_percentual_qoq(df, empresa)
st.pyplot(fig7)
plt.close(fig7)

st.divider()

# 8. Margem EBITDA vs. Margem Líquida
st.subheader(f"8. Análise da Margem EBITDA e da Margem Líquida ({empresa})")
fig8 = graficos2.grafico_margens_ebitda_liquida(df, empresa)
st.pyplot(fig8)
plt.close(fig8)

st.divider()

# 9. Evolução Relativa Base 100
st.subheader(f"9. Evolução Relativa dos Indicadores Financeiros — Base 100 ({empresa})")
fig9 = graficos2.grafico_evolucao_relativa_base100(df, empresa)
st.pyplot(fig9)
plt.close(fig9)

st.divider()

# 10. Relação entre Estoques e Receita Líquida
st.subheader("10. Relação entre Estoques e Receita Líquida")
fig10 = graficos2.grafico_relacao_estoques_receita(analises)
st.pyplot(fig10)
plt.close(fig10)

st.divider()

# ==============================================================================
# SEÇÃO: ANÁLISES FINANCEIRAS — PETZ E COBASI
# ==============================================================================
st.header("Análises Financeiras — Petz e Cobasi", text_alignment="center")
st.markdown(
    "<p style='text-align:center; max-width:850px; margin:0 auto 1.5rem'>"
    "Investigação aprofundada sobre a união entre Petz e Cobasi: avaliação de melhorias de desempenho "
    "da Petz após a união, rentabilidade, geração de caixa e comparação direta com a Cobasi nos períodos coincidentes."
    "</p>",
    unsafe_allow_html=True
)

# Configuração explícita do marco temporal de corte da união.
# Mantém os marcos históricos e acrescenta todos os trimestres disponíveis
# a partir de 1T25, ordenados cronologicamente até o mais recente da base.
def _trimestre_valido(valor):
    texto = str(valor).strip()
    return len(texto) >= 4 and texto[0] in "1234" and texto[1:2].upper() == "T" and texto[2:].isdigit()

trimestres_base = [str(t).strip() for t in analises["Petz"].index if _trimestre_valido(t)]
trimestres_desde_1t25 = [t for t in trimestres_base if graficos3.chave_ordenacao_trimestre(t) >= graficos3.chave_ordenacao_trimestre("1T25")]
marcos_historicos = ["2T24", "3T24", "1T25"]
trimestres_opcoes = sorted(
    set(marcos_historicos + trimestres_desde_1t25),
    key=graficos3.chave_ordenacao_trimestre
)

# Se 1T25 não existir no índice, ainda mantém esse marco como padrão.
indice_padrao = trimestres_opcoes.index("1T25") if "1T25" in trimestres_opcoes else 0

c1, c2 = st.columns([1, 2])
with c1:
    trimestre_corte = st.selectbox(
        "Marco temporal de corte da união:",
        options=trimestres_opcoes,
        index=indice_padrao,
        help="Escolha o trimestre que será usado para separar o período pré-união do pós-união. As opções após 1T25 são geradas a partir dos trimestres disponíveis na base."
    )
with c2:
    st.info(
        f"**Configuração ativa:** Pré-União (< {trimestre_corte}) vs. Pós-União (>= {trimestre_corte}). "
        "A classificação respeita o histórico de divulgações do RI sem criar dados artificiais."
    )

# ------------------------------------------------------------------------------
# Categoria 1: Desempenho da Petz antes e depois da união
# ------------------------------------------------------------------------------
st.subheader("1. Desempenho da Petz Antes e Depois da União")

st.markdown("#### Gráfico 1 — Comparação de Médias Trimestrais (Receita Líquida, EBITDA e Lucro)")
fig_g1 = graficos3.grafico_petz_pre_pos_barras(analises["Petz"], trimestre_corte=trimestre_corte)
st.pyplot(fig_g1)
plt.close(fig_g1)

st.markdown("#### Gráfico 4 — Boxplots Distributivos e Volatilidade (Petz)")
fig_g4 = graficos3.grafico_petz_boxplots_pre_pos(analises["Petz"], trimestre_corte=trimestre_corte)
st.pyplot(fig_g4)
plt.close(fig_g4)

st.divider()

# ------------------------------------------------------------------------------
# Categoria 2: Rentabilidade e geração de caixa
# ------------------------------------------------------------------------------
st.subheader("2. Rentabilidade e Geração de Caixa")

st.markdown("#### Gráfico 2 — Margens de Rentabilidade da Petz (Agregada vs. Trimestral)")
fig_g2 = graficos3.grafico_petz_margens_pre_pos(analises["Petz"], trimestre_corte=trimestre_corte)
st.pyplot(fig_g2)
plt.close(fig_g2)

st.markdown("#### Gráfico 3 — Liquidez, Dívida Líquida e Fluxo de Caixa Operacional (Petz)")
fig_g3 = graficos3.grafico_petz_divida_caixa_fco(analises["Petz"], trimestre_corte=trimestre_corte)
st.pyplot(fig_g3)
plt.close(fig_g3)

st.markdown("#### Gráfico 5 — Crescimento da Receita (YoY) vs. Margem EBITDA (Petz)")
fig_g5 = graficos3.grafico_petz_crescimento_vs_rentabilidade(analises["Petz"], trimestre_corte=trimestre_corte)
st.pyplot(fig_g5)
plt.close(fig_g5)

st.markdown("#### Gráfico 6 — Estoques vs. Receita Líquida (Petz)")
fig_g6 = graficos3.grafico_petz_estoques_vs_receita(analises["Petz"], trimestre_corte=trimestre_corte)
st.pyplot(fig_g6)
plt.close(fig_g6)

st.markdown("#### Gráfico 7 — Lucro Líquido vs. Fluxo de Caixa Operacional (Petz)")
fig_g7 = graficos3.grafico_petz_lucro_vs_fco(analises["Petz"], trimestre_corte=trimestre_corte)
st.pyplot(fig_g7)
plt.close(fig_g7)

st.divider()

# ------------------------------------------------------------------------------
# Categoria 3: Comparação entre Petz e Cobasi
# ------------------------------------------------------------------------------
st.subheader("3. Comparação entre Petz e Cobasi nos Períodos Coincidentes")

st.markdown("#### Gráfico 8 — Comparação de Resultados Financeiros (Trimestres Comuns)")
fig_g8 = graficos3.grafico_comparacao_petz_cobasi_resultados(analises)
st.pyplot(fig_g8)
plt.close(fig_g8)

st.markdown("#### Gráfico 9 — Comparação de Margens Operacionais e Líquidas")
fig_g9 = graficos3.grafico_comparacao_petz_cobasi_rentabilidade(analises)
st.pyplot(fig_g9)
plt.close(fig_g9)

st.markdown("#### Gráfico 10 — Índice de Desempenho Relativo (Base 100)")
fig_g10 = graficos3.grafico_indice_base100_petz_cobasi(analises)
st.pyplot(fig_g10)
plt.close(fig_g10)

st.divider()

# ------------------------------------------------------------------------------
# Categoria 4: Distribuição e estabilidade dos indicadores
# ------------------------------------------------------------------------------
st.subheader("4. Distribuição e Estabilidade dos Indicadores")

emp_hist = st.selectbox("Selecione a empresa para visualização dos histogramas:", options=["Petz", "Cobasi"], index=0)
fig_g11 = graficos3.grafico_histogramas_distribuicao_estabilidade(analises, empresa=emp_hist)
st.pyplot(fig_g11)
plt.close(fig_g11)

