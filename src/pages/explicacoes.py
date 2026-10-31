"""Por que a métrica variou? Notícias do período + explicação gerada por IA (Groq)."""
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.indicadores import rotulo_trimestre
from src.util.componentes import barra_lateral_dados, exigir_base
from src.util.estilo import MARINHO, fmt_dias, fmt_int, fmt_pct, fmt_reais_mi
from src.util.extrator_noticias import contexto_para_llm, maiores_variacoes, descrever_variacao
from src.util.graficos import CONFIG, grafico_linhas
from src.util.llm import explicar_variacoes, ia_disponivel, linkar_fontes, separar_por_trimestre

barra_lateral_dados()
base, _ = exigir_base()
ind = base["indicadores"]

# rótulo: (coluna, tipo da variação, formatação, formato do gráfico, empresa buscada, termo da busca)
METRICAS = {
    "Receita líquida": ("receita_liquida", "valor", fmt_reais_mi, "mi", "Petz OR Cobasi", "receita resultado"),
    "Receita bruta Petz": ("receita_bruta_petz", "valor", fmt_reais_mi, "mi", "Petz", "receita resultado"),
    "Receita bruta Cobasi": ("receita_bruta_cobasi", "valor", fmt_reais_mi, "mi", "Cobasi", "receita vendas"),
    "Margem bruta": ("margem_bruta", "taxa", fmt_pct, "pct", "Petz OR Cobasi", "margem bruta resultado"),
    "Margem EBITDA ajustada": ("margem_ebitda", "taxa", fmt_pct, "pct", "Petz OR Cobasi", "EBITDA margem resultado"),
    "Despesas com vendas / receita": ("despesas_vendas_pct", "taxa", fmt_pct, "pct", "Petz OR Cobasi", "despesas resultado"),
    "Lucro líquido": ("lucro_liquido", "valor", fmt_reais_mi, "mi", "Petz OR Cobasi", "lucro resultado"),
    "Prazo com fornecedores": ("prazo_fornecedores", "dias", fmt_dias, "dias", "Petz OR Cobasi", "fornecedores capital de giro"),
    "Vendas mesmas lojas (SSS)": ("sss_consolidado", "taxa", fmt_pct, "pct", "Petz OR Cobasi", "vendas mesmas lojas"),
    "Número de lojas": ("lojas_total", "valor", fmt_int, "int", "Petz OR Cobasi", "lojas abertura fechamento"),
}
COMPARACOES = {"Mesmo trimestre do ano anterior": "ano", "Trimestre anterior": "trimestre"}


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Buscando notícias, pode levar alguns instantes...")
def obter_contexto(serie, empresa, nome, tipo, comparar, top, incluir, termo):
    formatar = METRICAS[nome][2]
    return contexto_para_llm(serie, empresa, nome, formatar=formatar, tipo=tipo, comparar=comparar,
                             top=top, incluir=incluir, termo_busca=termo)


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Gerando explicação...")
def obter_explicacao(empresa, nome, contexto):
    return explicar_variacoes(empresa, nome, contexto)


st.title("Por que a métrica variou?")
st.markdown(
    '<p class="pc-lead">Escolha uma métrica: o app encontra os trimestres com as maiores variações, busca notícias '
    "sobre Petz e Cobasi daquele período e pede a uma IA uma explicação baseada só nessas notícias.</p>",
    unsafe_allow_html=True,
)
st.caption("A explicação é gerada por IA e pode errar. Use-a como ponto de partida e confira sempre as fontes e o "
           "release de resultados do trimestre no RI.")

c1, c2, c3 = st.columns([2, 2, 1])
pos_fusao = st.toggle("Incluir sempre os trimestres depois da fusão", value=True, key="pos_fusao_explicacao")
nome = c1.selectbox("Métrica", list(METRICAS), key="metrica_explicacao")
comparar = COMPARACOES[c2.segmented_control("Comparar com", list(COMPARACOES), default="Mesmo trimestre do ano anterior",
                                            key="comparar_explicacao") or "Mesmo trimestre do ano anterior"]
top = c3.number_input("Trimestres", min_value=1, max_value=5, value=3, key="top_explicacao")
coluna, tipo, formatar, formato_grafico, empresa_busca, termo = METRICAS[nome]
serie = ind[coluna]
incluir = tuple(p for p in serie.index if p >= pd.Period("2026Q1", freq="Q")) if pos_fusao else ()
variacoes = maiores_variacoes(serie, top=int(top), comparar=comparar, tipo=tipo, incluir=incluir)

# gráfico com os trimestres escolhidos destacados
fig = grafico_linhas(ind, [(coluna, nome, "Grupo")], formato_grafico, f"{nome}: trimestres analisados")
fig.add_scatter(x=[v["trimestre"] for v in variacoes], y=[v["valor"] for v in variacoes], mode="markers",
                marker=dict(size=16, color="rgba(0,0,0,0)", line=dict(color=MARINHO, width=2.5)),
                name="Maiores variações", hoverinfo="skip")
fig.update_layout(showlegend=False)
st.plotly_chart(fig, config=CONFIG)

if not variacoes:
    st.info("Não há trimestres suficientes para calcular a variação dessa métrica.")
    st.stop()

chave = (nome, comparar, int(top), incluir)
gerar = st.button("Buscar notícias e gerar explicação", type="primary", icon=":material/auto_awesome:")
if not ia_disponivel():
    st.caption("A chave da IA (GROQ_API_KEY) não está configurada: o botão busca só as notícias. "
               "Veja .streamlit/secrets.toml.example.")
if gerar:
    try:
        contexto, fontes, detalhes = obter_contexto(serie, empresa_busca, nome, tipo, comparar, int(top), incluir, termo)
        explicacao = obter_explicacao(empresa_busca, nome, contexto) if ia_disponivel() else None
        st.session_state["explicacao"] = {"chave": chave, "contexto": contexto, "fontes": fontes,
                                          "detalhes": detalhes, "texto": explicacao}
    except Exception as erro:
        st.error(f"Não foi possível gerar a explicação agora: {erro}")

resultado = st.session_state.get("explicacao")
resultado = resultado if resultado and resultado["chave"] == chave else None
por_trimestre = separar_por_trimestre(resultado["texto"]) if resultado and resultado["texto"] else {}
detalhes = {d["trimestre"]: d for d in resultado["detalhes"]} if resultado else {}

for v in variacoes:
    with st.container(border=True):
        st.markdown(f"#### {v['trimestre']}")
        st.markdown(descrever_variacao(v, nome, formatar, tipo, comparar).replace("$", "\\$") + ".")
        if v["periodo"] < pd.Period("2026Q1", freq="Q"):
            st.caption("Número pro forma: Petz e Cobasi somadas, antes da fusão.")
        if not resultado:
            continue
        d = detalhes.get(v["trimestre"], {})
        texto = por_trimestre.get(v["trimestre"])
        if texto:
            st.markdown(linkar_fontes(texto, resultado["fontes"]).replace("$", "\\$"))
        elif resultado["texto"] is None:
            st.caption("Explicação por IA indisponível (chave não configurada). As notícias encontradas estão abaixo.")
        if d.get("erro"):
            st.warning(f"A busca de notícias falhou: {d['erro']}")
        elif not d.get("noticias"):
            st.caption("Nenhuma notícia sobre Petz ou Cobasi encontrada nesse período.")
        else:
            linhas = []
            for n in d["noticias"]:
                data = n["data"].strftime("%d/%m/%Y") if n.get("data") else "sem data"
                situacao = "texto lido" if n["tem_texto"] else "só o título"
                titulo = n["titulo"].replace("[", "(").replace("]", ")")
                linhas.append(f"- **{n['codigo']}** [{titulo}]({n['link']}) · {n['dominio']} · {data} · {situacao}")
            st.markdown("**Notícias usadas**\n\n" + "\n".join(linhas))

if resultado and resultado["texto"] and not por_trimestre:
    # a IA não seguiu o formato pedido: mostra a resposta inteira
    st.markdown(linkar_fontes(resultado["texto"], resultado["fontes"]))

if resultado:
    with st.expander("Ver o texto enviado para a IA"):
        st.text(resultado["contexto"])
