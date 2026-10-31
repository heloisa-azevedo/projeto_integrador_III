"""Peças reaproveitadas pelas páginas: carregamento dos dados, barra lateral e quadros."""
import html
import pandas as pd
import streamlit as st

from src.analysis.indicadores import LIMIAR_DIAS, LIMIAR_PP, leitura_hipotese
from src.data.repositorio import montar_base, planilha_atual
from src.util.estilo import fmt_delta, fmt_valor


# ---------------------------------------------------------------- dados
@st.cache_data(ttl=60 * 60 * 24, show_spinner="Buscando dados no RI, pode levar alguns instantes...")
def _baixar_do_ri():
    """Como na versão original: baixa do RI e guarda por 24 h.
    Devolve (bytes, None) ou (None, erro). A falha também fica guardada,
    para o app não tentar de novo (e ficar lento) a cada clique; o botão Buscar no RI força nova tentativa."""
    from src.data import dadosPetz
    try:
        return dadosPetz.carregar_planilha_do_ri(), None
    except Exception as erro:
        return None, str(erro)


@st.cache_data(show_spinner="Calculando os indicadores...")
def _montar(origem, versao):
    # versao entra na chave do cache: dados novos invalidam o resultado anterior
    return montar_base(origem)


def obter_base():
    """1º: planilha baixada do RI. 2º (se o download ou a leitura falharem): planilha salva em data/raw."""
    conteudo, erro = _baixar_do_ri()
    if conteudo is not None:
        try:
            base = _montar(conteudo, "ri")
            st.session_state.pop("aviso_ri", None)
            return base, "baixada automaticamente do RI"
        except Exception as e:  # a planilha mudou de formato: não derruba o app
            erro = f"a planilha baixada não pôde ser lida ({type(e).__name__}: {e})"
    caminho = planilha_atual()
    if caminho is None:
        return None, None
    st.session_state["aviso_ri"] = erro
    return _montar(str(caminho), caminho.stat().st_mtime), f"{caminho.name} (cópia salva no projeto)"


def exigir_base():
    """Para a página com uma orientação se não houver dados de nenhuma das duas fontes."""
    base, origem = obter_base()
    if base is None:
        st.info("Não foi possível usar a planilha do RI, e não há cópia em data/raw/. "
                "Tente o botão Buscar no RI na barra lateral.", icon=":material/cloud_off:")
        st.stop()
    return base, origem


def barra_lateral_dados():
    with st.sidebar:
        if st.session_state.get("aviso_ri"):
            st.caption("Não foi possível usar a planilha do RI agora; o app está usando a cópia salva no projeto.")
            with st.expander("Detalhes"):
                st.caption(st.session_state["aviso_ri"])
        if st.button("Buscar no RI", icon=":material/refresh:", width="stretch"):
            _baixar_do_ri.clear()   # força nova tentativa
            _montar.clear()
            st.session_state.pop("aviso_ri", None)
            st.rerun()


# ---------------------------------------------------------------- quadros
def quadro(linhas, colunas):
    """linhas: lista de dicts com nome, explica (opcional), formato e os valores.
    colunas: [(rótulo, chave, tipo)] com tipo 'antes', 'depois' ou 'delta'."""
    cab = "".join(f'<th class="{"depois" if tipo == "depois" else ""}">{html.escape(rot)}</th>' for rot, _, tipo in colunas)
    corpo = []
    for l in linhas:
        celulas = []
        for _, chave, tipo in colunas:
            v = l[chave]
            if tipo == "delta":
                limiar = LIMIAR_DIAS if l["formato"] == "dias" else LIMIAR_PP if l["formato"] == "pct" else 0
                classe = "pc-delta" if pd.notna(v) and abs(v) > limiar else "pc-delta neutro"
                celulas.append(f'<td class="num"><span class="{classe}">{fmt_delta(v, l["formato"])}</span></td>')
            else:
                celulas.append(f'<td class="num {tipo}">{fmt_valor(v, l["formato"])}</td>')
        explica = f'<div class="explica">{html.escape(l["explica"])}</div>' if l.get("explica") else ""
        corpo.append(f'<tr><td><div class="nome">{html.escape(l["nome"])}</div>{explica}</td>{"".join(celulas)}</tr>')
    st.markdown(f'<table class="pc-quadro"><thead><tr><th>Indicador</th>{cab}</tr></thead>'
                f'<tbody>{"".join(corpo)}</tbody></table>', unsafe_allow_html=True)


def legenda_limiares():
    st.caption(f"Variações menores que {f'{LIMIAR_PP * 100:.1f}'.replace('.', ',')} p.p. ou {LIMIAR_DIAS} dias "
               "aparecem sem destaque e contam como estabilidade.")


def destaques(itens):
    """itens: lista de (valor formatado, rótulo)."""
    blocos = "".join(f'<div class="pc-destaque"><div class="valor">{html.escape(v)}</div>'
                     f'<div class="rotulo">{html.escape(r)}</div></div>' for v, r in itens)
    st.markdown(f'<div class="pc-destaques">{blocos}</div>', unsafe_allow_html=True)


TEXTOS_LEITURA = {
    "preco_ou_compra": ("Preço e custo de compra", {
        1: "A margem bruta subiu: o grupo vende mais caro ou compra mais barato.",
        0: "A margem bruta ficou praticamente estável: não há sinal claro de poder de preço.",
        -1: "A margem bruta caiu: não há sinal de poder de preço."}),
    "fornecedores": ("Força com fornecedores", {
        1: "O prazo de pagamento aumentou, o que é consistente com maior poder de barganha. "
           "O prazo já estava alto no fim de 2025, então vale olhar a aba Capital de giro.",
        0: "O prazo de pagamento ficou estável.",
        -1: "O prazo de pagamento diminuiu."}),
    "sinergia": ("Sinergia de custos", {
        1: "As despesas caíram em relação à receita: a maior parte da melhora do EBITDA vem de eficiência.",
        0: "As despesas ficaram estáveis em relação à receita.",
        -1: "As despesas subiram, provavelmente com custos de integração."}),
}


def leitura(comparacao):
    estado = leitura_hipotese(comparacao)
    classes = {1: "sim", 0: "nao", -1: "nao", None: "indef"}
    corpo = ""
    for chave, (rotulo, frases) in TEXTOS_LEITURA.items():
        s = estado[chave]
        corpo += (f'<div class="rotulo {classes[s]}">{rotulo}</div>'
                  f'<div>{frases.get(s, "Sem dados suficientes para avaliar.")}</div>')
    st.markdown(f'<div class="pc-leitura">{corpo}</div>', unsafe_allow_html=True)


CUIDADOS = [
    "A margem EBITDA já tinha saltado no 2T25, antes da fusão. Parte da melhora pode ter outras causas ou ser efeito de antecipação.",
    "A lista de lojas ainda tem 520 unidades: a venda das 26 lojas exigida pelo Cade não aparece nos dados do 2T26.",
    "No 2T26 há resultado não recorrente positivo e equivalência patrimonial negativa, e no 1T26 o intangível sobe com a "
    "combinação de negócios. Esses itens devem ser explicados com o release de resultados.",
    "O histórico pro forma (1T23 a 4T25) foi montado pela própria companhia; o trabalho deve citar essa fonte.",
    "Com só dois trimestres depois da fusão, as diferenças são indícios, não provas estatísticas. A comparação também "
    "não isola fatores externos, como juros, inflação e o desempenho do varejo como um todo.",
]


def cuidados():
    st.markdown('<ul class="pc-cuidados">' + "".join(f"<li>{html.escape(c)}</li>" for c in CUIDADOS) + "</ul>",
                unsafe_allow_html=True)
