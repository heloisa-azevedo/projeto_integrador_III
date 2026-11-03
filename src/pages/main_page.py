"""Página inicial: a pergunta, o contexto da fusão, os números principais e como a análise foi feita."""
import streamlit as st

from src.analysis.eventos import EVENTOS
from src.analysis.indicadores import LIMIAR_PP, faixas_do_periodo, rotulo_periodo, sinal
from src.util.componentes import barra_lateral_dados, destaques, obter_base
from src.util.estilo import fmt_delta, fmt_pct

barra_lateral_dados()

st.markdown(
    """
<div class="pc-hero">
  <h1>A fusão Petz + Cobasi aumentou o poder de mercado do grupo?</h1>
  <p class="pc-lead">
    Em janeiro de 2026, as duas maiores redes de pet shops do Brasil passaram a operar como uma só empresa.
    Este app usa a Planilha Interativa publicada no RI do grupo para comparar o desempenho antes da fusão
    (números pro forma, como se as empresas já estivessem juntas) com o do grupo combinado depois dela.
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
    '<p class="pc-lead">Margem maior depois de uma fusão pode ter causas diferentes. '
    "Para separar poder de mercado de simples ganho de eficiência, olhamos quatro sinais:</p>",
    unsafe_allow_html=True,
)
st.markdown(
    """
<div class="pc-mecanismos">
  <div class="pc-mecanismo">
    <h4>Preço e custo de compra</h4>
    <p>Com menos concorrência, o grupo pode vender mais caro ou negociar produtos mais baratos.</p>
    <p class="indicador">Margem bruta</p>
  </div>
  <div class="pc-mecanismo">
    <h4>Força com fornecedores</h4>
    <p>Um comprador maior consegue pagar os fornecedores com prazos mais longos.</p>
    <p class="indicador">Prazo médio de pagamento</p>
  </div>
  <div class="pc-mecanismo">
    <h4>Sinergia de custos</h4>
    <p>Juntar sede, logística e lojas reduz despesas. Isso aumenta a margem sem envolver poder de mercado.</p>
    <p class="indicador">Despesas sobre a receita</p>
  </div>
  <div class="pc-mecanismo">
    <h4>Menos disputa local</h4>
    <p>Onde as duas redes competiam, a fusão elimina um concorrente direto e reduz a pressão para abrir lojas.</p>
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
c1, c2 = st.columns(2)
c1.page_link("src/pages/analyse.py", label="Ver a análise", icon=":material/insights:")
c2.page_link("src/pages/metodologia.py", label="Ver dados e método", icon=":material/table_chart:")
