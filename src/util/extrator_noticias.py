"""
Busca notícias sobre uma empresa em um portal, extrai link + título
e depois acessa cada link para extrair o texto da matéria.

Dependências:
    pip install requests beautifulsoup4 lxml trafilatura googlenewsdecoder
(trafilatura é opcional, mas dá um texto bem mais limpo)

Mudanças desta versão:
- filtro de relevância: só ficam notícias que citam Petz ou Cobasi (antes vinham matérias de outras empresas);
- a variação pode ser comparada com o mesmo trimestre do ano anterior (padrão), como no resto do app;
- margens e prazos variam em pontos percentuais / dias, não em %;
- o contexto da LLM não usa mais títulos Markdown (##) e os números saem no formato brasileiro;
- contexto_para_llm devolve também os dados estruturados, para a página mostrar as fontes organizadas.
"""
import calendar
import time
import unicodedata
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Termos que uma notícia precisa citar (no título ou no texto) para ser usada
TERMOS_RELEVANCIA = ("petz", "cobasi")

# ---------------------------------------------------------------------------
# Portais de busca. Para usar outro site, basta adicionar uma entrada aqui.
#   tipo "rss":  só precisa da URL (com {q} no lugar da busca)
#   tipo "html": precisa dos seletores CSS do item, título e link
# ---------------------------------------------------------------------------
PORTAIS = {
    # Google Notícias: aceita operadores after:/before:, então serve para
    # trimestres antigos. (pip install googlenewsdecoder para resolver os links)
    "google": {
        "tipo": "rss",
        "url": "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    },
    # Bing: só devolve notícias recentes, bom para o trimestre atual
    "bing": {
        "tipo": "rss",
        "url": "https://www.bing.com/news/search?q={q}&format=rss&setlang=pt-BR&cc=BR",
    },
    # Exemplo de portal HTML (ajuste a URL e os seletores inspecionando o site):
    "exemplo_html": {
        "tipo": "html",
        "url": "https://www.site-de-noticias.com.br/busca?q={q}",
        "item": "article",          # seletor de cada resultado
        "titulo": "h2 a",           # seletor do título dentro do item
        "link": "h2 a",             # seletor do <a> com href dentro do item
    },
}


def _get(url, timeout=15):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r


def _limpar_link_bing(link):
    """O RSS do Bing devolve um redirecionador; o link real está no parâmetro 'url'."""
    qs = parse_qs(urlparse(link).query)
    return qs["url"][0] if "url" in qs else link


def _resolver_link(link):
    """Resolve os redirecionadores do Bing e do Google Notícias para a URL real."""
    if "news.google.com" in link:
        try:
            from googlenewsdecoder import gnewsdecoder
            r = gnewsdecoder(link, interval=1)
            if r.get("status"):
                return r["decoded_url"]
        except Exception:
            pass
        return link
    return _limpar_link_bing(link)


def _parse_data(texto):
    try:
        d = parsedate_to_datetime(texto)
        return d.date() if d else None
    except Exception:
        return None


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def e_relevante(noticia, termos=TERMOS_RELEVANCIA):
    """True se o título ou o texto cita algum dos termos (sem acento, sem maiúsculas)."""
    alvo = _normalizar(f"{noticia.get('titulo', '')} {noticia.get('texto', '')[:3000]}")
    return any(t in alvo for t in termos)


def dominio(link):
    host = urlparse(link).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _buscar_rss(cfg, consulta, limite):
    r = _get(cfg["url"].format(q=quote_plus(consulta)))
    soup = BeautifulSoup(r.content, "xml")
    resultados = []
    for item in soup.find_all("item")[:limite]:
        titulo = item.find("title")
        link = item.find("link")
        data = item.find("pubDate")
        fonte = item.find("source")
        if titulo and link:
            resultados.append({
                "titulo": titulo.get_text(strip=True),
                "link": link.get_text(strip=True),   # resolvido só depois do filtro
                "data": _parse_data(data.get_text(strip=True)) if data else None,
                "veiculo": fonte.get_text(strip=True) if fonte else "",
            })
    return resultados


def _buscar_html(cfg, empresa, limite):
    url = cfg["url"].format(q=quote_plus(empresa))
    soup = BeautifulSoup(_get(url).text, "lxml")
    resultados = []
    for item in soup.select(cfg["item"])[:limite]:
        t = item.select_one(cfg["titulo"])
        a = item.select_one(cfg["link"])
        if t and a and a.get("href"):
            resultados.append({
                "titulo": t.get_text(strip=True),
                "link": urljoin(url, a["href"]),
            })
    return resultados


def extrair_texto(url):
    """Acessa a URL da notícia e devolve apenas o texto principal."""
    html = _get(url).text

    # 1) trafilatura (melhor opção, remove menus, propagandas, etc.)
    try:
        import trafilatura
        texto = trafilatura.extract(html, include_comments=False, include_tables=False)
        if texto:
            return texto
    except ImportError:
        pass

    # 2) fallback: junta os <p> do <article> (ou da página inteira)
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    area = soup.find("article") or soup
    paragrafos = [p.get_text(" ", strip=True) for p in area.find_all("p")]
    return "\n\n".join(p for p in paragrafos if len(p) > 40)


def buscar_noticias(empresa: str, portal: str = "google", limite: int = 10,
                    extrair: bool = True, pausa: float = 1.0, termo: str = "",
                    data_ini: date = None, data_fim: date = None,
                    max_chars: int = 4000, termos_relevancia=TERMOS_RELEVANCIA):
    """
    empresa (+ termo) -> busca no portal -> extrai (titulo, link) -> acessa o link
    -> extrai o texto -> mantém só as notícias que citam os termos de relevância.

    termo:             palavras extras da busca (ex.: "receita resultado")
    data_ini/data_fim: restringem o período das notícias
    max_chars:         corta o texto de cada matéria (controla o uso de tokens da LLM)
    termos_relevancia: None desliga o filtro

    Retorna: [{"titulo", "link", "data", "veiculo", "texto", "tem_texto"}, ...]
    Se uma matéria falhar, o erro fica em "erro" e o loop continua.
    """
    cfg = PORTAIS[portal]
    consulta = f"{empresa} {termo}".strip()
    if portal == "google":
        if data_ini:
            consulta += f" after:{data_ini.isoformat()}"
        if data_fim:
            consulta += f" before:{data_fim.isoformat()}"

    buscar = _buscar_rss if cfg["tipo"] == "rss" else _buscar_html
    # pede mais resultados do que o necessário, porque o filtro de relevância descarta parte
    candidatas = buscar(cfg, consulta, limite * 4)

    # filtro de data (necessário no Bing; reforço no Google). Sem data = mantém.
    def no_periodo(n):
        d = n.get("data")
        return d is None or ((not data_ini or d >= data_ini) and (not data_fim or d <= data_fim))

    candidatas = [n for n in candidatas if no_periodo(n)]
    # primeiro passa só pelo título: evita baixar matérias que claramente não são da empresa
    if termos_relevancia:
        candidatas.sort(key=lambda n: not e_relevante(n, termos_relevancia))

    noticias = []
    for n in candidatas:
        if len(noticias) >= limite:
            break
        n["link"] = _resolver_link(n["link"])
        n["texto"] = ""
        if extrair:
            try:
                n["texto"] = extrair_texto(n["link"])[:max_chars]
            except Exception as e:  # site bloqueou, timeout, paywall...
                n["erro"] = str(e)
            time.sleep(pausa)  # educado com os servidores
        n["tem_texto"] = len(n["texto"]) > 200
        if termos_relevancia and not e_relevante(n, termos_relevancia):
            continue
        noticias.append(n)

    return noticias


# ---------------------------------------------------------------------------
# Camada para a LLM: série por trimestre -> trimestres com maior variação
# -> notícias do período -> texto de contexto + dados estruturados
# ---------------------------------------------------------------------------
def _rotulo(trimestre):
    """Period('2024Q3') ou '3T24' -> '3T24'."""
    if isinstance(trimestre, pd.Period):
        return f"{trimestre.quarter}T{str(trimestre.year)[2:]}"
    return str(trimestre).upper().strip()


def periodo_do_trimestre(rotulo, dias_apos: int = 75):
    """'3T24' -> (01/07/2024, 30/09/2024 + dias_apos).
    A janela vai além do fim do trimestre porque o balanço sai ~30-60 dias depois."""
    tri, ano = _rotulo(rotulo).split("T")
    tri, ano = int(tri), 2000 + int(ano)
    ini = date(ano, 3 * tri - 2, 1)
    fim = date(ano, 3 * tri, calendar.monthrange(ano, 3 * tri)[1])
    return ini, fim + timedelta(days=dias_apos)


def maiores_variacoes(serie, top: int = 3, comparar: str = "ano", tipo: str = "valor", incluir=()):
    """Os `top` trimestres com maior variação (mais os trimestres de `incluir`, se houver).

    serie:    índice em ordem cronológica e sem buracos (Period ou rótulos 'nTYY')
    comparar: "ano" = mesmo trimestre do ano anterior (tira a sazonalidade); "trimestre" = anterior
    tipo:     "valor" -> variação em %; "taxa" -> diferença em pontos percentuais; "dias" -> diferença em dias
    incluir:  trimestres que entram sempre (ex.: os pós-fusão), desde que tenham variação calculável
    """
    if hasattr(serie, "columns"):  # aceita DataFrame de uma coluna, como na versão anterior
        serie = serie.iloc[:, 0]
    defasagem = 4 if comparar == "ano" else 1
    anterior = serie.shift(defasagem)
    variacao = serie / anterior - 1 if tipo == "valor" else serie - anterior
    escolhidos = set(variacao.abs().dropna().sort_values(ascending=False).head(top).index)
    escolhidos |= {t for t in incluir if t in variacao.index and pd.notna(variacao[t])}
    indice = list(serie.index)
    return [
        {"trimestre": _rotulo(t), "base": _rotulo(indice[indice.index(t) - defasagem]),
         "valor": float(serie[t]), "anterior": float(anterior[t]), "variacao": float(variacao[t]),
         "periodo": t}
        for t in sorted(escolhidos, key=indice.index)
    ]


def descrever_variacao(v, nome, formatar, tipo, comparar):
    """Frase da variação, montada pelo código (e não pela IA)."""
    if tipo == "valor":
        quanto = f"{abs(v['variacao']) * 100:.1f}".replace(".", ",") + "%"
    elif tipo == "taxa":
        quanto = f"{abs(v['variacao']) * 100:.1f}".replace(".", ",") + " p.p."
    else:
        quanto = f"{abs(v['variacao']):.0f} dias"
    sentido = "alta" if v["variacao"] > 0 else "queda"
    base = "o mesmo trimestre do ano anterior" if comparar == "ano" else "o trimestre anterior"
    return (f"{nome}: {formatar(v['anterior'])} em {v['base']} → {formatar(v['valor'])} em {v['trimestre']} "
            f"({sentido} de {quanto} sobre {base})")


def contexto_para_llm(serie, empresa: str, nome: str, formatar=str, tipo: str = "valor",
                      comparar: str = "ano", top: int = 3, incluir=(), noticias_por_trimestre: int = 3,
                      portal: str = "google", termo_busca: str = "resultado", max_chars: int = 2000,
                      trimestre_fusao="1T26"):
    """
    Monta o texto que vai para a LLM: para cada variação relevante, o que mudou
    e as notícias do período. Cada notícia recebe um código único ([F1], [F2]...).

    Retorna (texto, fontes, detalhes):
      fontes   = {"F1": {"titulo", "link"}, ...}  -> usado por llm.linkar_fontes
      detalhes = lista com cada variação e suas notícias, para a página mostrar organizado
    """
    tri_f, ano_f = _rotulo(trimestre_fusao).split("T")
    blocos, fontes, detalhes = [], {}, []

    for v in maiores_variacoes(serie, top, comparar, tipo, incluir):
        ini, fim = periodo_do_trimestre(v["trimestre"])
        tri, ano = v["trimestre"].split("T")
        pro_forma = (int(ano), int(tri)) < (int(ano_f), int(tri_f))
        erro = None
        try:
            noticias = buscar_noticias(
                empresa, portal=portal, limite=noticias_por_trimestre,
                termo=f"{termo_busca} {tri}º trimestre 20{ano}",
                data_ini=ini, data_fim=fim, max_chars=max_chars,
            )
        except Exception as e:
            noticias, erro = [], str(e)

        frase = descrever_variacao(v, nome, formatar, tipo, comparar)
        bloco = [f"TRIMESTRE {v['trimestre']}", frase]
        if pro_forma:
            bloco.append("Atenção: antes de 2026 os números são pro forma (Petz e Cobasi somadas, antes da fusão).")
        if erro:
            bloco.append(f"(erro na busca de notícias: {erro})")
        elif not noticias:
            bloco.append("Nenhuma notícia sobre Petz ou Cobasi encontrada para este período.")

        usadas = []
        for n in noticias:
            codigo = f"F{len(fontes) + 1}"
            fontes[codigo] = {"titulo": n["titulo"], "link": n["link"]}
            situacao = "texto lido" if n["tem_texto"] else "só o título (texto indisponível)"
            bloco.append(f"[{codigo}] {n['titulo']} ({n.get('data') or 's/ data'}, {dominio(n['link'])}; {situacao})")
            if n["tem_texto"]:
                bloco.append(n["texto"])
            usadas.append({**n, "codigo": codigo, "dominio": dominio(n["link"])})

        blocos.append("\n".join(bloco))
        detalhes.append({**v, "frase": frase, "pro_forma": pro_forma, "noticias": usadas, "erro": erro})

    return "\n\n".join(blocos), fontes, detalhes
