"""Peças reaproveitadas pelas páginas: carregamento dos dados, barra lateral e quadros."""
import html
import pandas as pd
import streamlit as st

from src.analysis.indicadores import (LIMIAR_DIAS, LIMIAR_PP, faixas_do_periodo, leitura_hipotese, prazo_ja_alto_antes,
                                      rotulo_periodo, rotulo_trimestre)
from src.data.repositorio import montar_base, planilha_atual
from src.util.estilo import fmt_delta, fmt_valor
from src.util.extrator_noticias import contexto_para_resumo, periodo_do_trimestre
from src.util.llm import ia_disponivel, linkar_fontes, numeros_fora_do_contexto, resumir_com_noticias


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
        1: "O prazo de pagamento aumentou, o que é consistente com maior poder de barganha.",
        0: "O prazo de pagamento ficou estável.",
        -1: "O prazo de pagamento diminuiu."}),
    "sinergia": ("Sinergia de custos", {
        1: "As despesas caíram em relação à receita: parte da melhora do resultado vem de eficiência.",
        0: "As despesas ficaram estáveis em relação à receita.",
        -1: "As despesas subiram, provavelmente com custos de integração."}),
}


def leitura(comparacao, ind=None, depois=()):
    """Frases escolhidas por regras a partir dos números (mesmos dados -> mesmas frases)."""
    estado = leitura_hipotese(comparacao)
    classes = {1: "sim", 0: "nao", -1: "nao", None: "indef"}
    corpo = ""
    for chave, (rotulo, frases) in TEXTOS_LEITURA.items():
        s = estado[chave]
        frase = frases.get(s, "Sem dados suficientes para avaliar.")
        if chave == "fornecedores" and s == 1 and ind is not None and prazo_ja_alto_antes(ind, list(depois)):
            frase += (" Mas o prazo já estava nesse nível nos dois trimestres anteriores à fusão, então parte do "
                      "aumento pode não ser efeito dela. Veja a aba Capital de giro.")
        corpo += f'<div class="rotulo {classes[s]}">{rotulo}</div><div>{html.escape(frase)}</div>'
    st.markdown(f'<div class="pc-leitura">{corpo}</div>', unsafe_allow_html=True)


# Observações escritas à mão a partir de uma planilha específica.
# Atualizem a lista e o trimestre de referência quando revisarem com o release de resultados.
OBSERVACOES_REFERENCIA = "2T26"
OBSERVACOES = [
    "A margem EBITDA já tinha saltado no 2T25, antes da fusão. Parte da melhora pode ter outras causas ou ser efeito de antecipação.",
    "A lista de lojas do 2T26 ainda tem 520 unidades: a venda das 26 lojas exigida pelo Cade não aparece nesses dados.",
    "No 2T26 há resultado não recorrente positivo e equivalência patrimonial negativa, e no 1T26 o intangível sobe com a "
    "combinação de negócios. Esses itens devem ser explicados com o release de resultados.",
]


def cuidados(base):
    """Limitações gerais (montadas a partir dos dados) + observações escritas à mão, com o trimestre de referência."""
    f = faixas_do_periodo(base["indicadores"])
    n = len(base["depois"])
    gerais = [
        f"O histórico pro forma ({f['pre']}) foi montado pela própria companhia; o trabalho deve citar essa fonte.",
        f"A comparação usa {n} {'trimestre' if n == 1 else 'trimestres'} depois da fusão: as diferenças são indícios, "
        "não provas estatísticas. Ela também não isola fatores externos, como juros, inflação e o desempenho do varejo.",
    ]
    if f["n_pos"] > 4:
        gerais.append("O quadro Antes × depois usa só o primeiro ano após a fusão; os trimestres seguintes aparecem "
                      "nos gráficos e na comparação com a tendência.")
    st.markdown('<ul class="pc-cuidados">' + "".join(f"<li>{html.escape(c)}</li>" for c in gerais) + "</ul>",
                unsafe_allow_html=True)
    st.markdown(f"**Observações sobre os dados do {OBSERVACOES_REFERENCIA}**")
    if f["ultimo"] != OBSERVACOES_REFERENCIA:
        st.caption(f"A planilha atual vai até o {f['ultimo']}: estas observações foram escritas com os dados do "
                   f"{OBSERVACOES_REFERENCIA} e precisam ser revisadas (OBSERVACOES em src/util/componentes.py).")
    st.markdown('<ul class="pc-cuidados">' + "".join(f"<li>{html.escape(c)}</li>" for c in OBSERVACOES) + "</ul>",
                unsafe_allow_html=True)


# ---------------------------------------------------------------- parágrafo da IA com notícias
def _linhas_numeros(base):
    """Frases com os números já formatados, que vão para a IA (ela não pode inventar outros)."""
    c, t = base["comparacao"], base["resumo_tendencia"]
    periodo = rotulo_periodo(base["depois"])
    antes = " e ".join(rotulo_trimestre(p) for p in base["antes"])
    depois = " e ".join(rotulo_trimestre(p) for p in base["depois"])
    linhas = [f"Período depois da fusão: {periodo} ({depois}), comparado com o mesmo período um ano antes ({antes}, pro forma)."]
    for chave, r in c.iterrows():
        linhas.append(f"{r['nome']}: {fmt_valor(r['antes'], r['formato'])} antes e {fmt_valor(r['depois'], r['formato'])} "
                      f"depois ({fmt_delta(r['delta'], r['formato'])}).")
    for chave, r in t.iterrows():
        linhas.append(f"{r['nome']} contra a tendência sem fusão: real {fmt_valor(r['real'], r['formato'])}, tendência "
                      f"{fmt_valor(r['tendencia'], r['formato'])} (diferença de {fmt_delta(r['diferenca'], r['formato'])}).")
    s = base["sobreposicao"]
    if s:
        linhas.append(f"Lojas em cidades com as duas bandeiras: {s['lojas_em_cidades_ambas']} de {s['lojas_total']} "
                      f"({fmt_valor(s['participacao'], 'pct')}).")
    return linhas


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Buscando notícias do período...")
def _contexto_resumo(linhas, data_ini, data_fim):
    return contexto_para_resumo(list(linhas), data_ini, data_fim)


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Gerando a leitura com IA...")
def _texto_resumo(contexto):
    return resumir_com_noticias(contexto)


def leitura_com_ia(base, chave_botao):
    """Parágrafo de interpretação: números do app + notícias pós-fusão, escrito pela IA (sob demanda)."""
    st.subheader("Leitura com notícias")
    st.caption("Parágrafo escrito por IA a partir dos números acima e de notícias do período pós-fusão. "
               "Pode conter erros: confira as fontes. Os números e as frases acima não dependem da IA.")
    if not base["depois"]:
        return
    linhas = tuple(_linhas_numeros(base))
    data_ini, _ = periodo_do_trimestre(min(base["depois"]))
    _, data_fim = periodo_do_trimestre(max(base["depois"]))
    versao = hash(linhas)  # muda quando os números mudam: a leitura antiga deixa de aparecer

    if st.button("Gerar leitura com notícias", icon=":material/auto_awesome:", key=chave_botao):
        try:
            contexto, fontes, noticias, erro = _contexto_resumo(linhas, data_ini, data_fim)
            texto = _texto_resumo(contexto) if ia_disponivel() else None
            st.session_state["leitura_ia"] = {"versao": versao, "contexto": contexto, "fontes": fontes,
                                              "noticias": noticias, "erro": erro, "texto": texto}
        except Exception as e:
            st.error(f"Não foi possível gerar a leitura agora: {e}")
    if not ia_disponivel():
        st.caption("A chave da IA (GROQ_API_KEY) não está configurada: o botão busca só as notícias.")

    r = st.session_state.get("leitura_ia")
    if not r or r["versao"] != versao:
        return
    with st.container(border=True):
        if r["texto"]:
            st.markdown(linkar_fontes(r["texto"], r["fontes"]).replace("$", "\\$"))
            fora = numeros_fora_do_contexto(r["texto"], r["contexto"])
            if fora:
                st.warning("A IA escreveu números que não estão nos dados enviados: " + ", ".join(fora) +
                           ". Confira antes de usar este parágrafo.")
        if r["erro"]:
            st.warning(f"A busca de notícias falhou: {r['erro']}")
        elif not r["noticias"]:
            st.caption("Nenhuma notícia sobre Petz ou Cobasi encontrada no período.")
        else:
            itens = []
            for n in r["noticias"]:
                data = n["data"].strftime("%d/%m/%Y") if n.get("data") else "sem data"
                titulo = n["titulo"].replace("[", "(").replace("]", ")")
                situacao = "texto lido" if n["tem_texto"] else "só o título"
                itens.append(f"- **{n['codigo']}** [{titulo}]({n['link']}) · {n['dominio']} · {data} · {situacao}")
            st.markdown("**Notícias usadas**\n\n" + "\n".join(itens))
        with st.expander("Ver o texto enviado para a IA"):
            st.text(r["contexto"])
