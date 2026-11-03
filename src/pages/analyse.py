"""Análise antes × depois da fusão: as mesmas sete seções do painel interativo."""
import pandas as pd
import streamlit as st

from src.analysis.indicadores import anos_completos, faixas_do_periodo, rotulo_trimestre
from src.util.componentes import (barra_lateral_dados, cuidados, destaques, exigir_base, leitura, leitura_com_ia,
                                  legenda_limiares, quadro)
from src.util.estilo import fmt_int, fmt_pct, fmt_reais_mi
from src.util.graficos import CONFIG, grafico_barras, grafico_cidades, grafico_linhas

barra_lateral_dados()
base, _ = exigir_base()
ind = base["indicadores"]
tend = base["tendencias"]
faixas = faixas_do_periodo(ind)

st.title("Antes e depois da fusão")
st.markdown(
    f'<p class="pc-lead">De {faixas["pre"]} os números são pro forma da companhia, como se Petz e Cobasi já fossem uma só '
    f"empresa; {faixas['pos']} {'é' if faixas['n_pos'] == 1 else 'são'} o grupo combinado. A área sombreada dos "
    "gráficos marca o período pós-fusão.</p>",
    unsafe_allow_html=True,
)


def grafico(fig):
    st.plotly_chart(fig, config=CONFIG)


abas = st.tabs(["Resumo", "Crescimento", "Margens", "Capital de giro", "Expansão", "Sobreposição", "Caixa e dívida"])

# ============================================================== RESUMO
with abas[0]:
    if not base["depois"]:
        st.info("Ainda não há trimestres publicados depois da fusão na planilha carregada.")
    else:
        txt_antes = " e ".join(rotulo_trimestre(p) for p in base["antes"])
        txt_depois = " e ".join(rotulo_trimestre(p) for p in base["depois"])
        st.subheader("Antes × depois")
        st.markdown(f'<p class="pc-nota">Grupo combinado em <b>{txt_depois}</b> contra o pro forma de <b>{txt_antes}</b>: '
                    "os mesmos trimestres um ano antes. Margens calculadas sobre as somas dos trimestres.</p>",
                    unsafe_allow_html=True)
        quadro(base["comparacao"].to_dict("records"),
               [("Antes", "antes", "antes"), ("Depois", "depois", "depois"), ("Variação", "delta", "delta")])
        legenda_limiares()

        st.subheader("Contra a tendência")
        st.markdown(f'<p class="pc-nota">Ajustamos a tendência e a sazonalidade de {faixas["pre"]} e projetamos o período '
                    "pós-fusão como se ela não tivesse acontecido. A diferença entre o real e o projetado é o efeito "
                    "estimado (média dos trimestres pós-fusão).</p>", unsafe_allow_html=True)
        quadro(base["resumo_tendencia"].to_dict("records"),
               [("Tendência", "tendencia", "antes"), ("Real", "real", "depois"), ("Diferença", "diferenca", "delta")])

        st.subheader("O que os números sugerem")
        leitura(base["comparacao"], ind, base["depois"])

        leitura_com_ia(base, "leitura_ia_analise")

        st.subheader("Cuidados na interpretação")
        cuidados(base)

# ============================================================== CRESCIMENTO
with abas[1]:
    grafico(grafico_barras(ind, [("receita_bruta_petz", "Petz", "Petz"), ("receita_bruta_cobasi", "Cobasi", "Cobasi")],
                           "mi", "Receita bruta por bandeira (R$ milhões)", altura=400))
    st.caption("As duas marcas continuam operando separadas depois da fusão.")
    c1, c2 = st.columns(2)
    with c1:
        grafico(grafico_linhas(ind, [("cresc_petz", "Petz", "Petz"), ("cresc_cobasi", "Cobasi", "Cobasi")], "pct",
                               "Crescimento da receita bruta sobre o ano anterior"))
    with c2:
        grafico(grafico_linhas(ind, [("sss_petz", "Petz", "Petz"), ("sss_cobasi", "Cobasi", "Cobasi"),
                                     ("sss_consolidado", "Consolidado", "Grupo")], "pct", "Vendas mesmas lojas (SSS)"))
    c1, c2 = st.columns(2)
    with c1:
        grafico(grafico_linhas(ind, [("receita_m2_petz", "Petz", "Petz"), ("receita_m2_cobasi", "Cobasi", "Cobasi")], "m2",
                               "Receita bruta por m² de loja (R$ no trimestre)"))
        st.caption("Inclui as vendas digitais atribuídas a cada bandeira.")
    with c2:
        grafico(grafico_linhas(ind, [("penetracao_digital", "Penetração digital", "Grupo")], "pct",
                               "Penetração digital (% da receita bruta)"))

# ============================================================== MARGENS
METRICAS = {
    "Margem bruta": ("margem_bruta", "Lucro bruto ÷ receita líquida. Sobe quando o preço de venda aumenta ou o custo de compra cai."),
    "Margem EBITDA": ("margem_ebitda", "EBITDA ajustado ÷ receita líquida. Exclui itens não recorrentes, como os custos da fusão."),
    "Despesas com vendas": ("despesas_vendas_pct", "Despesas com vendas ÷ receita líquida. Inclui pessoal de loja, aluguel (IAS17), frete e marketing."),
    "Despesas G&A": ("despesas_ga_pct", "Despesas gerais e administrativas ÷ receita líquida. Sede e áreas de apoio."),
    "Margem líquida": ("margem_liquida", "Lucro líquido ÷ receita líquida. Afetada por itens não recorrentes e pelo resultado financeiro."),
}
with abas[2]:
    c1, c2 = st.columns([3, 1])
    escolha = c1.segmented_control("Indicador", list(METRICAS), default="Margem bruta", key="metrica_margem") or "Margem bruta"
    coluna, explicacao = METRICAS[escolha]
    com_tendencia = c2.toggle("Tendência sem fusão", value=True, disabled=coluna not in tend)
    grafico(grafico_linhas(ind, [(coluna, "Real", "Grupo")], "pct", escolha,
                           tendencia=tend.get(coluna) if com_tendencia else None, altura=420))
    st.caption(explicacao + (f" A linha pontilhada é a tendência de {faixas['pre_anos']} projetada sem a fusão."
                             if com_tendencia and coluna in tend else ""))

# ============================================================== CAPITAL DE GIRO
with abas[3]:
    grafico(grafico_linhas(ind, [("prazo_fornecedores", "Real", "Grupo")], "dias",
                           "Prazo com fornecedores: real × tendência", tendencia=tend.get("prazo_fornecedores"), altura=400))
    st.caption("Fornecedores no balanço ÷ CMV do trimestre × 91 dias. O quanto o real fica acima da linha pontilhada "
               "é o ganho de prazo atribuível ao período pós-fusão.")
    c1, c2 = st.columns(2)
    with c1:
        grafico(grafico_linhas(ind, [("prazo_fornecedores", "Fornecedores", "Grupo"), ("prazo_estoques", "Estoque", 0),
                                     ("prazo_recebimento", "Recebimento", 1)], "dias", "Prazos médios"))
        st.caption("Estoque e fornecedores sobre o CMV; recebimento sobre a receita bruta.")
    with c2:
        grafico(grafico_linhas(ind, [("ciclo_caixa", "Ciclo de caixa", "Grupo")], "dias", "Ciclo de caixa"))
        st.caption("Estoque + recebimento − fornecedores. Quanto menor, menos capital o grupo precisa para girar o negócio.")

# ============================================================== EXPANSÃO
with abas[4]:
    anual = base["anual"]
    completos = [str(a) for a in anos_completos(ind)]
    if len(completos) >= 2:
        primeiro, ultimo = completos[0], completos[-1]
        ini, fim = anual.loc[primeiro, "inauguracoes"], anual.loc[ultimo, "inauguracoes"]
        # título escolhido pelos números: queda/alta de mais de 30% entre o primeiro e o último ano completo
        if fim < ini * 0.7:
            st.subheader("O ritmo de abertura de lojas caiu")
            st.markdown('<p class="pc-nota">Menos disputa por novos pontos também é uma forma de reduzir a '
                        "concorrência: vale comparar o ritmo de inaugurações com o período de análise da fusão.</p>",
                        unsafe_allow_html=True)
        elif fim > ini * 1.3:
            st.subheader("O ritmo de abertura de lojas acelerou")
        else:
            st.subheader("O ritmo de abertura de lojas ficou estável")
        destaques([
            (fmt_int(ini), f"inaugurações em {primeiro}"),
            (fmt_int(fim), f"inaugurações em {ultimo}"),
            (fmt_reais_mi(anual.loc[primeiro, "capex_lojas_novas"]), f"investidos em lojas novas em {primeiro}"),
            (fmt_reais_mi(anual.loc[ultimo, "capex_lojas_novas"]), f"investidos em lojas novas em {ultimo}"),
        ])
    else:
        st.subheader("Abertura de lojas")
    c1, c2 = st.columns(2)
    with c1:
        grafico(grafico_barras(ind, [("inauguracoes_petz", "Petz", "Petz"), ("inauguracoes_cobasi", "Cobasi", "Cobasi")],
                               "int", "Inaugurações por trimestre"))
    with c2:
        grafico(grafico_barras(ind, [("capex_lojas_novas", "Lojas novas e hospitais", 0), ("capex_reformas", "Reformas e manutenção", 1),
                                     ("capex_tecnologia", "Tecnologia e digital", 2)], "mi", "CAPEX por tipo (R$ milhões)"))
    grafico(grafico_barras(ind, [("lojas_petz", "Petz", "Petz"), ("lojas_cobasi", "Cobasi", "Cobasi")], "int", "Número de lojas"))

# ============================================================== SOBREPOSIÇÃO
with abas[5]:
    s, cidades = base["sobreposicao"], base["cidades"]
    st.subheader("Onde as duas redes competiam")
    st.markdown('<p class="pc-nota">Poder de mercado no varejo é local: o cliente compara as lojas perto de casa. Por '
                "isso o Cade olhou cidade a cidade e exigiu a venda de lojas em São Paulo.</p>", unsafe_allow_html=True)
    if not s:
        st.info("A planilha carregada não tem a aba Lista de Lojas no formato esperado, então esta análise "
                "não está disponível. Veja Dados e método > Contas da planilha.")
    else:
        destaques([
            (fmt_int(s["cidades_ambas"]), f"cidades com Petz e Cobasi, de {fmt_int(s['cidades_total'])} com lojas do grupo"),
            (fmt_int(s["lojas_em_cidades_ambas"]), f"lojas nessas cidades, de {fmt_int(s['lojas_total'])} no total"),
            (fmt_pct(s["participacao"], 0), "das lojas estão em cidades onde as duas bandeiras disputavam clientes"),
        ])
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("**As 15 cidades com mais lojas das duas bandeiras**")
            grafico(grafico_cidades(cidades))
        with c2:
            st.markdown("**Todas as cidades com as duas bandeiras**")
            st.dataframe(
                cidades[["cidade", "petz", "cobasi", "total"]], hide_index=True, height=480, width="stretch",
                column_config={"cidade": "Cidade", "petz": st.column_config.NumberColumn("Petz", format="%d"),
                               "cobasi": st.column_config.NumberColumn("Cobasi", format="%d"),
                               "total": st.column_config.NumberColumn("Total", format="%d")},
            )

# ============================================================== CAIXA E DÍVIDA
with abas[6]:
    grafico(grafico_linhas(ind, [("caixa_total", "Caixa total", "Grupo"), ("divida_bruta", "Dívida bruta", 1)], "mi",
                           "Caixa total e dívida bruta (R$ milhões)", altura=400))
    liquida = ind["divida_liquida"].dropna()
    if not liquida.empty and (liquida < 0).all():
        situacao = "O grupo tem mais caixa (incluindo aplicações financeiras) do que dívida em todo o período: caixa líquido."
    elif not liquida.empty and liquida.iloc[-1] < 0:
        situacao = (f"No {faixas['ultimo']}, o grupo tem mais caixa (incluindo aplicações financeiras) do que dívida, "
                    "mas isso não vale para todo o período.")
    elif not liquida.empty:
        situacao = f"No {faixas['ultimo']}, a dívida líquida é de {fmt_reais_mi(liquida.iloc[-1])}."
    else:
        situacao = ""
    if pd.Period("2026Q1", freq="Q") in ind.index:
        situacao += " A queda do caixa no 1T26 coincide com a saída de recursos ligada à combinação de negócios."
    st.caption(situacao)
    grafico(grafico_barras(ind, [("fluxo_caixa_operacional", "Fluxo de caixa operacional", "Grupo")], "mi",
                           "Fluxo de caixa operacional (R$ milhões)"))
