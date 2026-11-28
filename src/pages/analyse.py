"""Análise antes × depois da fusão: as mesmas sete seções do painel interativo."""
import pandas as pd
import streamlit as st

from src.analysis.indicadores import anos_completos, faixas_do_periodo, rotulo_trimestre
from src.util.componentes import (barra_lateral_dados, cuidados, destaques, exigir_base, leitura, leitura_com_ia,
                                  legenda_limiares, quadro)
from src.analysis.bandeiras import (com_participacao, comparar_bandeiras, receita_contra_tendencia, sobreposicao_por_bandeira)
from src.util.estilo import fmt_int, fmt_pct, fmt_reais_mi, fmt_delta, fmt_valor
from src.util.graficos import CONFIG, grafico_barras, grafico_cidades, grafico_linhas, grafico_acao, grafico_retorno_anormal
from src.util.graficobolha import grafico_bolhas_lojas
from src.analysis.acao import TICKER_INDICE, base_100, baixar_precos, serie_do_grupo, tabela_eventos

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


abas = st.tabs(["Resumo", "Crescimento", "Margens", "Capital de giro", "Expansão", "Sobreposição", "Caixa e dívida", "Bolsa", "Petz × Cobasi"])



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

    if not base["lojas"].empty and "area_m2" in base["lojas"].columns:
        grafico(grafico_bolhas_lojas(base["lojas"], "Lojas Petz e Cobasi no Brasil (tamanho = área em m²)"))
        st.caption("Cada bolha é uma loja, segundo a aba Lista de Lojas. Lojas da mesma cidade aparecem espalhadas "
                   "em volta da sede do município; a posição dentro da cidade é ilustrativa.")


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

# ============================================================== BOLSA
@st.cache_data(ttl=60 * 60 * 12, show_spinner="Baixando cotações...")
def _cotacoes():
    return baixar_precos()


with abas[7]:
    st.subheader("Como a bolsa reagiu à fusão")
    st.markdown('<p class="pc-nota">A Cobasi era uma empresa fechada, então só dá para medir a reação do lado da Petz. '
                "Para cada marco da fusão, comparamos o retorno da ação com o que seria esperado pelo movimento do "
                "Ibovespa naqueles dias (estudo de evento).</p>", unsafe_allow_html=True)
    try:
        precos, origem_precos = _cotacoes()
    except Exception as erro:
        st.info(f"As cotações não estão disponíveis agora: {erro}.", icon=":material/cloud_off:")
    else:
        grupo = base_100(serie_do_grupo(precos), "2024-01-01")
        indice = base_100(precos[TICKER_INDICE], "2024-01-01")
        grafico(grafico_acao(grupo, indice, "Ação da Petz/grupo contra o Ibovespa (base 100 em jan/24)"))
        st.caption("Até dez/25: PETZ3. Desde jan/26: AUAU3 (uma ação nova para cada ação da Petz). O dinheiro pago aos "
                   f"acionistas da Petz na conclusão não está incluído na linha. Fonte: {origem_precos}.")

        tabela, janelas = tabela_eventos(precos)
        if tabela.empty:
            st.info("Não há cotações suficientes em torno dos eventos para o estudo de evento.")
        else:
            st.markdown("**Reação a cada marco da fusão**")
            exibir = pd.DataFrame({
                "Evento": tabela["evento"],
                "Pregão": tabela["pregao"],
                "PETZ3 no dia": tabela["retorno_dia"] * 100,
                "Ibovespa no dia": tabela["indice_dia"] * 100,
                "Retorno anormal (−1 a +1)": tabela["retorno_anormal"] * 100,
                "Estatística t": tabela["t"],
                "Fora do comum?": tabela["significativo"].map({True: "Sim", False: "Não"}),
            })
            st.dataframe(exibir, hide_index=True, width="stretch", column_config={
                "Pregão": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "PETZ3 no dia": st.column_config.NumberColumn(format="%+.1f%%"),
                "Ibovespa no dia": st.column_config.NumberColumn(format="%+.1f%%"),
                "Retorno anormal (−1 a +1)": st.column_config.NumberColumn(format="%+.1f%%"),
                "Estatística t": st.column_config.NumberColumn(format="%.2f"),
            })
            st.caption("Retorno anormal: quanto a ação variou além do esperado pelo Ibovespa, somando o pregão anterior, "
                       "o do evento e o seguinte. \"Fora do comum\" quando a estatística t passa de 1,96 em módulo (95% de "
                       "confiança), ou seja, a variação foi maior do que a ação costumava oscilar.")

            escolhido = st.selectbox("Ver o evento em detalhe", list(janelas), key="evento_bolsa")
            grafico(grafico_retorno_anormal(janelas[escolhido]))
            st.caption("Barras: retorno anormal de cada pregão (escuras: os três pregões somados na tabela). "
                       "Linha: retorno anormal acumulado desde 5 pregões antes do evento.")



# ============================================================== PETZ × COBASI
def _fmt_bandeira(valor, formato):
    if formato == "m2":
        return "–" if pd.isna(valor) else f"R$ {fmt_int(valor)}/m²"
    return fmt_valor(valor, formato)


def _fmt_delta_bandeira(delta, formato):
    if formato == "m2":
        return fmt_delta(delta, "reais")
    if formato == "int":
        if pd.isna(delta):
            return "–"
        return ("+" if delta > 0 else "−" if delta < 0 else "±") + fmt_int(abs(delta))
    return fmt_delta(delta, formato)


def quadro_bandeiras(comp):
    """Variação de cada bandeira (antes → depois embaixo) e quem avançou mais."""
    import html as _html
    cab = "".join(f"<th>{t}</th>" for t in ["Petz", "Cobasi", "Avançou mais"])
    corpo = []
    for _, l in comp.iterrows():
        celulas = []
        for b in ["Petz", "Cobasi"]:
            d = l[f"{b}_delta"]
            destaque = pd.notna(d) and (abs(d) > 0.005 if l["formato"] == "pct" else d != 0)
            classe = "pc-delta" if destaque else "pc-delta neutro"
            de_para = f'{_fmt_bandeira(l[f"{b}_antes"], l["formato"])} → {_fmt_bandeira(l[f"{b}_depois"], l["formato"])}'
            celulas.append(f'<td class="num"><span class="{classe}">{_fmt_delta_bandeira(d, l["formato"])}</span>'
                           f'<div class="explica" style="text-align:right">{_html.escape(de_para)}</div></td>')
        quem = l["avancou_mais"]
        celulas.append(f'<td class="num">{_html.escape(quem) if isinstance(quem, str) and quem else "–"}</td>')
        corpo.append(f'<tr><td><div class="nome">{_html.escape(l["nome"])}</div>'
                     f'<div class="explica">{_html.escape(l["explica"])}</div></td>{"".join(celulas)}</tr>')
    st.markdown(f'<table class="pc-quadro"><thead><tr><th>Indicador</th>{cab}</tr></thead>'
                f'<tbody>{"".join(corpo)}</tbody></table>', unsafe_allow_html=True)


with abas[8]:
    st.subheader("Qual bandeira se beneficiou mais?")
    st.markdown('<p class="pc-nota">A planilha do RI separa Petz e Cobasi só em receita, vendas mesmas lojas, lojas, '
                "inaugurações e área. Margens, despesas e lucro existem apenas para o grupo. Por isso esta aba mostra "
                "<b>qual bandeira passou a vender mais</b> depois da fusão, não qual passou a lucrar mais.</p>",
                unsafe_allow_html=True)
    if not base["depois"]:
        st.info("Ainda não há trimestres publicados depois da fusão na planilha carregada.")
    else:
        comp = comparar_bandeiras(ind, base["antes"], base["depois"])
        txt_antes = " e ".join(rotulo_trimestre(p) for p in base["antes"])
        txt_depois = " e ".join(rotulo_trimestre(p) for p in base["depois"])

        # ---- placar
        contagem = comp["avancou_mais"].value_counts()
        n_petz, n_cobasi, n_empate = (int(contagem.get(k, 0)) for k in ["Petz", "Cobasi", "Empate"])
        destaques([
            (fmt_int(n_petz), "indicadores em que a Petz avançou mais"),
            (fmt_int(n_cobasi), "indicadores em que a Cobasi avançou mais"),
            (fmt_int(n_empate), "indicadores praticamente empatados"),
        ])

        st.subheader("Antes × depois, por bandeira")
        st.markdown(f'<p class="pc-nota">Depois = <b>{txt_depois}</b>; antes = <b>{txt_antes}</b>, os mesmos trimestres '
                    "um ano antes. O crescimento \"antes\" compara com mais um ano para trás. Diferenças entre as "
                    "bandeiras menores que 0,5 p.p. (ou 1 p.p. nas variações em %) contam como empate.</p>",
                    unsafe_allow_html=True)
        quadro_bandeiras(comp)

        # ---- real × tendência
        st.subheader("Receita contra a tendência de cada bandeira")
        tend_b, gap_b = receita_contra_tendencia(ind)
        if tend_b:
            st.markdown(f'<p class="pc-nota">Tendência e sazonalidade da receita bruta de {faixas["pre"]}, projetadas '
                        "como se a fusão não tivesse acontecido. Quem ficou mais acima da linha pontilhada cresceu mais "
                        "do que o próprio histórico indicava.</p>", unsafe_allow_html=True)
            destaques([(fmt_delta(gap_b[b], "reais"), f"receita da {b} acima da tendência (média pós-fusão)")
                       for b in gap_b])
            c1, c2 = st.columns(2)
            for coluna_st, b in zip([c1, c2], ["Petz", "Cobasi"]):
                if b in tend_b:
                    with coluna_st:
                        grafico(grafico_linhas(ind, [(f"receita_bruta_{b.lower()}", "Real", b)], "mi",
                                               f"Receita bruta {b}: real × tendência (R$ milhões)",
                                               tendencia=tend_b[b]))
        else:
            st.info("Não há trimestres suficientes antes da fusão para estimar a tendência.")

        # ---- participação
        st.subheader("Quem ganhou espaço dentro do grupo")
        grafico(grafico_linhas(com_participacao(ind), [("participacao_cobasi", "Cobasi", "Cobasi")], "pct",
                               "Participação da Cobasi na receita bruta do grupo", altura=380))
        st.caption("O restante é a Petz. Se a linha sobe no período sombreado, a Cobasi ganhou espaço depois da fusão; "
                   "se desce, quem ganhou foi a Petz.")

        # ---- sobreposição
        sob = sobreposicao_por_bandeira(base["lojas"])
        if sob:
            st.subheader("Quem mais disputava clientes com a outra")
            itens = []
            for b, v in sob.items():
                itens.append((fmt_pct(v["participacao"], 0),
                              f"das lojas {b} ({v['em_cidades_ambas']} de {v['total']}) ficam em cidades com a outra bandeira"))
            destaques(itens)
            mais_exposta = max(sob, key=lambda b: sob[b]["participacao"])
            st.caption(f"A {mais_exposta} é, proporcionalmente, a bandeira mais exposta à antiga concorrência. Se a fusão "
                       "reduziu a disputa local, ela é a que mais poderia se beneficiar. A planilha não traz receita por "
                       "loja, então não dá para medir isso diretamente.")

        # ---- leitura
        st.subheader("O que os números sugerem")
        ganhou = {b: [l["nome"].lower() for _, l in comp.iterrows() if l["avancou_mais"] == b] for b in ["Petz", "Cobasi"]}
        frases = []
        for b in ["Petz", "Cobasi"]:
            if ganhou[b]:
                frases.append(f"A {b} avançou mais em: {', '.join(ganhou[b])}.")
        if n_petz == n_cobasi:
            frases.append("Nenhuma bandeira se destaca com clareza: as duas melhoraram em ritmos parecidos.")
        else:
            lider = "Petz" if n_petz > n_cobasi else "Cobasi"
            frases.append(f"Pelos indicadores de venda, a {lider} parece ter se beneficiado um pouco mais, "
                          "mas a diferença deve ser lida com cautela.")
        st.markdown(" ".join(frases))

        st.subheader("Cuidados na interpretação")
        n = len(base["depois"])
        st.markdown(
            "- **Margem e lucro não podem ser atribuídos a uma bandeira**: a planilha só traz esses números para o grupo.\n"
            "- **Não há receita por loja**, então não dá para testar se as lojas em cidades com as duas bandeiras "
            "melhoraram mais que as demais.\n"
            f"- **Só {n} {'trimestre' if n == 1 else 'trimestres'} depois da fusão**: as diferenças são indícios, "
            "não provas estatísticas.\n"
            "- **\"Quem se beneficiou\" também pode ser lido como quais acionistas ganharam** (os da Petz ou os donos da "
            "Cobasi). Isso depende da relação de troca das ações e da cotação, que não estão nesta planilha."
        )

