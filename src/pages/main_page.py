"""Página inicial: quem saiu melhor com a fusão, o contexto, os números principais e como a análise foi feita."""
import streamlit as st

from src.analysis.eventos import EVENTOS
from src.analysis.bandeiras import comparar_bandeiras
from src.analysis.indicadores import LIMIAR_PP, faixas_do_periodo, rotulo_periodo, sinal
from src.util.componentes import barra_lateral_dados, destaques, obter_base
from src.util.estilo import fmt_delta, fmt_pct

barra_lateral_dados()

st.markdown(
    """
<div class="pc-hero">
  <h1>Quem saiu melhor com a fusão Petz + Cobasi?</h1>
  <p class="pc-lead">
    A Petz, a Cobasi, as duas ou nenhuma? Em janeiro de 2026, as duas maiores redes de pet shops do Brasil
    passaram a operar como uma só empresa. Este app compara o desempenho antes da fusão (números pro forma,
    como se as empresas já estivessem juntas) com o depois, usando a Planilha Interativa do RI do grupo e as
    cotações da ação na bolsa.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

base, _ = obter_base()
if base is not None and base["depois"]:
    c = base["comparacao"]
    s = base["sobreposicao"]
    st.subheader("Em resumo")
    periodo = rotulo_periodo(base["depois"])
    ano_antes = min(base["antes"]).year
    # o que puxou a margem EBITDA: escolhido pelos números, não escrito à mão
    s_bruta = sinal(c.loc["margem_bruta", "delta"], LIMIAR_PP)
    s_desp = sinal(c.loc["despesas_vendas", "delta"] + c.loc["despesas_ga", "delta"], LIMIAR_PP)
    motivos = (["pela margem bruta"] if s_bruta == 1 else []) + (["pela queda das despesas"] if s_desp == -1 else [])
    rotulo_ebitda = "na margem EBITDA ajustada" + (", puxada " + " e ".join(motivos) if motivos else "")
    rotulo_bruta = {1: "na margem bruta: em alta", 0: "na margem bruta: praticamente estável",
                    -1: "na margem bruta: em queda", None: "na margem bruta"}[s_bruta]
    itens = [
        (fmt_delta(c.loc["receita", "delta"], "reais"), f"de receita líquida no {periodo} contra o mesmo período de {ano_antes}"),
        (fmt_delta(c.loc["margem_ebitda", "delta"], "pct"), rotulo_ebitda),
        (fmt_delta(c.loc["margem_bruta", "delta"], "pct"), rotulo_bruta),
    ]
    if s:  # vazio se a planilha não trouxer a lista de lojas
        itens.append((fmt_pct(s["participacao"], 0), "das lojas ficam em cidades onde Petz e Cobasi disputavam clientes"))
    destaques(itens)

    # placar das bandeiras: mesmos critérios da aba Petz × Cobasi
    comp = comparar_bandeiras(base["indicadores"], base["antes"], base["depois"])
    if not comp.empty:
        placar = comp["avancou_mais"].value_counts()
        n_petz, n_cobasi, n_empate = (int(placar.get(k, 0)) for k in ("Petz", "Cobasi", "Empate"))
        if n_petz > n_cobasi:
            veredito = "Petz um pouco à frente nas vendas"
        elif n_cobasi > n_petz:
            veredito = "Cobasi um pouco à frente nas vendas"
        else:
            veredito = "Empate entre as bandeiras nas vendas"
        destaques([
            (f"Petz {n_petz} × {n_cobasi} Cobasi", f"{veredito}: indicadores em que cada bandeira avançou mais"
                                                  + (f" ({n_empate} {'empatado' if n_empate == 1 else 'empatados'})" if n_empate else "")),
        ])

st.subheader("Como a fusão aconteceu")
eventos_html = "".join(
    f'<div class="pc-evento{" final" if i == len(EVENTOS) - 1 else ""}">'
    f'<div class="quando">{ev["rotulo"]}</div>'
    f'<div class="titulo">{ev["titulo"]}</div>'
    f'<div class="texto">{ev["texto"]}</div></div>'
    for i, ev in enumerate(EVENTOS)
)
st.markdown(f'<div class="pc-timeline">{eventos_html}</div>', unsafe_allow_html=True)

st.write("")
st.subheader("Como vamos responder")
st.markdown(
    '<p class="pc-lead">"Sair melhor" pode significar coisas diferentes, e a resposta pode mudar conforme o '
    "ângulo. Por isso olhamos quatro frentes:</p>",
    unsafe_allow_html=True,
)
st.markdown(
    """
<div class="pc-mecanismos">
  <div class="pc-mecanismo">
    <h4>O grupo</h4>
    <p>O resultado melhorou? Se sim, foi por poder de mercado (preço, fornecedores) ou por eficiência (despesas)?</p>
    <p class="indicador">Margens, despesas e prazos</p>
  </div>
  <div class="pc-mecanismo">
    <h4>Petz × Cobasi</h4>
    <p>Qual bandeira passou a vender mais, contra o próprio histórico e contra a outra?</p>
    <p class="indicador">Crescimento, SSS, receita por m² e participação</p>
  </div>
  <div class="pc-mecanismo">
    <h4>Os acionistas</h4>
    <p>Como a bolsa reagiu a cada marco da fusão? A Cobasi era fechada, então só o lado da Petz pode ser medido.</p>
    <p class="indicador">Retorno anormal da ação PETZ3</p>
  </div>
  <div class="pc-mecanismo">
    <h4>A concorrência local</h4>
    <p>Onde as duas redes disputavam clientes, a fusão eliminou um concorrente direto.</p>
    <p class="indicador">Sobreposição de lojas e inaugurações</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")
anos_pre = faixas_do_periodo(base["indicadores"])["pre_anos"] if base is not None else "antes da fusão"
st.markdown(
    '<p class="pc-nota">Cada trimestre pós-fusão é comparado com o mesmo trimestre do ano anterior, para evitar o '
    f"efeito das datas sazonais, e também com a tendência de {anos_pre} projetada como se não houvesse fusão.</p>",
    unsafe_allow_html=True,
)
c1, c2, c3 = st.columns(3)
c1.page_link("src/pages/analyse.py", label="Ver a análise", icon=":material/insights:")
c2.page_link("src/pages/conclusao.py", label="Ver a conclusão", icon=":material/task_alt:")
c3.page_link("src/pages/metodologia.py", label="Ver dados e método", icon=":material/table_chart:")
