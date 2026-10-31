"""Dados e método: fonte, decisões de método, fórmulas e as tabelas para conferência."""
import pandas as pd
import streamlit as st

from src.analysis.indicadores import DIAS_TRIMESTRE, LIMIAR_DIAS, LIMIAR_PP, rotulo_trimestre
from src.util.componentes import barra_lateral_dados, exigir_base
from src.util.graficos import correlacao, info

barra_lateral_dados()
base, caminho = exigir_base()
ind = base["indicadores"]

st.title("Dados e método")

st.subheader("Fonte")
st.markdown(
    f"""
Todos os números vêm da **Planilha Interativa** publicada no site de Relações com Investidores do Grupo Petz Cobasi
(origem: {caminho}). As contas estão em R$ mil e foram convertidas para R$ milhões nos gráficos.

- **De 1T23 a 4T25** os trimestres são **pro forma**: a companhia recalculou o histórico como se Petz e Cobasi já fossem
  uma só empresa. Isso permite comparar negócios do mesmo tamanho antes e depois da fusão.
- **1T26 e 2T26** são os números do grupo combinado, após a conclusão da fusão em 2 de janeiro de 2026.
- Petz e Cobasi aparecem separadas apenas na receita bruta e nos dados operacionais (lojas, inaugurações, área e SSS).
"""
)

st.subheader("Por que IAS17 e não IFRS16")
st.markdown(
    "A planilha traz as demonstrações nas duas normas. Na IFRS16, o aluguel das lojas sai das despesas e vira depreciação "
    "e juros, o que aumenta artificialmente o EBITDA de um varejista com muitas lojas alugadas. Na IAS17, o aluguel continua "
    "como despesa operacional, e as margens refletem melhor o custo real de operar as lojas. Por isso a análise usa as abas IAS17."
)

st.subheader("Como cada indicador é calculado")
formulas = pd.DataFrame([
    ("Margem bruta", "Lucro bruto ÷ receita líquida"),
    ("Margem EBITDA ajustada", "EBITDA ajustado ÷ receita líquida"),
    ("Despesas com vendas / receita", "Despesas com vendas ÷ receita líquida"),
    ("Despesas G&A / receita", "Despesas gerais e administrativas ÷ receita líquida"),
    ("Prazo com fornecedores", f"Fornecedores ÷ CMV do trimestre × {DIAS_TRIMESTRE} dias"),
    ("Dias de estoque", f"Estoques ÷ CMV do trimestre × {DIAS_TRIMESTRE} dias"),
    ("Prazo de recebimento", f"Contas a receber ÷ receita bruta do trimestre × {DIAS_TRIMESTRE} dias"),
    ("Ciclo de caixa", "Dias de estoque + prazo de recebimento − prazo com fornecedores"),
    ("Caixa total", "Caixa e equivalentes + aplicações financeiras (curto e longo prazo)"),
    ("Dívida bruta", "Empréstimos, financiamentos e debêntures (curto e longo prazo)"),
    ("Receita por m²", "Receita bruta da bandeira ÷ área de vendas da bandeira"),
], columns=["Indicador", "Fórmula"])
st.dataframe(formulas, hide_index=True, width="stretch")

st.subheader("Comparações")
st.markdown(
    f"""
- **Antes × depois:** cada trimestre pós-fusão é comparado com o mesmo trimestre do ano anterior, o que neutraliza a
  sazonalidade do varejo. Margens são calculadas sobre a soma das contas do período, e não pela média das margens.
- **Contra a tendência:** para cada indicador, ajustamos por mínimos quadrados uma tendência linear com efeito de cada
  trimestre do ano, usando só 1T23 a 4T25. A projeção para 2026 é o que se esperaria sem a fusão; a diferença para o
  real é o efeito estimado.
- **Mudança relevante:** variações acima de {f'{LIMIAR_PP * 100:.1f}'.replace('.', ',')} ponto percentual nas margens ou de
  {LIMIAR_DIAS} dias nos prazos. Abaixo disso, tratamos como estabilidade.
- **Sobreposição:** uma cidade tem sobreposição quando há pelo menos uma loja de cada bandeira, segundo a aba
  Lista de Lojas da planilha.
"""
)

st.subheader("Tabelas para conferência")
aba1, aba2, aba3, aba4 = st.tabs(["Indicadores por trimestre", "Contas da planilha", "Lista de lojas", "Exploração dos dados"])

with aba1:
    colunas = {
        "receita_liquida": ("Receita líquida (R$ mi)", "%.1f", 1), "margem_bruta": ("Margem bruta", "%.1f%%", 100),
        "despesas_vendas_pct": ("Desp. vendas / receita", "%.1f%%", 100), "despesas_ga_pct": ("Desp. G&A / receita", "%.1f%%", 100),
        "margem_ebitda": ("Margem EBITDA", "%.1f%%", 100), "prazo_fornecedores": ("Prazo fornecedores (dias)", "%.0f", 1),
        "prazo_estoques": ("Dias de estoque", "%.0f", 1), "ciclo_caixa": ("Ciclo de caixa (dias)", "%.0f", 1),
        "sss_consolidado": ("SSS consolidado", "%.1f%%", 100), "capex_total": ("CAPEX (R$ mi)", "%.1f", 1),
    }
    tabela = pd.DataFrame({c: ind[c] * mult for c, (_, _, mult) in colunas.items()})
    tabela.index = [rotulo_trimestre(p) + (" (pro forma)" if ind.loc[p, "pro_forma"] else "") for p in tabela.index]
    st.dataframe(tabela.iloc[::-1], width="stretch",
                 column_config={c: st.column_config.NumberColumn(r, format=f) for c, (r, f, _) in colunas.items()})
    st.download_button("Baixar indicadores (CSV)", ind.to_csv().encode("utf-8-sig"), "indicadores_petzcobasi.csv",
                       icon=":material/download:")

with aba2:
    contas = base["contas"].drop(columns="pro_forma")
    contas.index = [rotulo_trimestre(p) for p in contas.index]
    st.caption("Valores em R$ mil, como na planilha original.")
    st.dataframe(contas.T, width="stretch")
    st.download_button("Baixar contas (CSV)", base["contas"].to_csv().encode("utf-8-sig"), "contas_petzcobasi.csv",
                       icon=":material/download:")
    if base["ausentes"]:
        st.warning("Contas não encontradas na planilha: " + ", ".join(base["ausentes"]) +
                   ". Ajuste os padrões no dicionário CONTAS em src/data/dadosPetz.py.")

with aba3:
    lojas = base["lojas"]
    st.caption(f"{len(lojas)} lojas, segundo a aba Lista de Lojas.")
    st.dataframe(lojas, hide_index=True, width="stretch", height=420)
    st.download_button("Baixar lista de lojas (CSV)", lojas.to_csv(index=False).encode("utf-8-sig"), "lojas_petzcobasi.csv",
                       icon=":material/download:")

with aba4:
    contas_num = base["contas"].drop(columns="pro_forma")
    contas_num.index = [rotulo_trimestre(p) for p in contas_num.index]
    st.markdown("**Dicionário das principais contas**")
    st.dataframe(pd.DataFrame([
        ("Receita bruta", "Faturamento total da empresa, antes de impostos e devoluções."),
        ("Receita líquida", "Valor das vendas e serviços depois de impostos e deduções."),
        ("CMV", "Custo das mercadorias vendidas e dos serviços prestados."),
        ("Lucro bruto", "Receita líquida menos o CMV."),
        ("EBITDA ajustado", "Métrica não contábil que mostra o desempenho operacional sem itens não recorrentes."),
        ("Lucro líquido", "Ganho real sobre as operações, depois de juros e impostos."),
        ("Caixa e equivalentes", "Dinheiro disponível imediatamente ou em aplicações de liquidez imediata."),
        ("Aplicações financeiras", "Investimentos financeiros feitos pela empresa."),
        ("Empréstimos de curto prazo", "Obrigações financeiras que devem ser pagas em até 12 meses."),
        ("Empréstimos de longo prazo", "Obrigações financeiras com vencimento em mais de 12 meses."),
        ("Estoques", "Valor financeiro total das mercadorias em estoque."),
        ("Fornecedores", "Valores devidos a fornecedores por compras a prazo."),
        ("Fluxo de caixa operacional", "Dinheiro gerado pelas operações do dia a dia da empresa."),
        ("SSS (vendas mesmas lojas)", "Crescimento das vendas só das lojas abertas há mais de 12 meses."),
        ("Penetração digital", "Percentual das vendas feitas por canais digitais."),
    ], columns=["Conta", "O que significa"]), hide_index=True, width="stretch")

    st.markdown("**Estrutura dos dados** (`DataFrame.info()`)")
    st.caption(f"{len(contas_num)} trimestres, {contas_num.shape[1]} contas e {int(contas_num.isna().sum().sum())} valores vazios.")
    info(contas_num)

    st.markdown("**Estatísticas descritivas** (R$ mil)")
    st.dataframe(contas_num.describe().T, width="stretch")

    st.markdown("**Correlação entre os indicadores**")
    st.caption("Com só 14 trimestres e séries que crescem juntas, correlações altas podem ser coincidência. "
               "Use este gráfico para explorar os dados, não como evidência para a hipótese.")
    colunas_corr = ["receita_liquida", "margem_bruta", "despesas_vendas_pct", "despesas_ga_pct", "margem_ebitda",
                    "prazo_fornecedores", "prazo_estoques", "sss_consolidado", "penetracao_digital", "capex_total"]
    st.pyplot(correlacao(ind[colunas_corr].astype(float)))
