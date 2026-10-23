"""
Busca notícias sobre uma empresa em um portal, extrai link + título
e depois acessa cada link para extrair o texto da matéria.

Dependências:
    pip install requests beautifulsoup4 lxml trafilatura
(trafilatura é opcional, mas dá um texto bem mais limpo)
"""
import calendar
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

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


def _buscar_rss(cfg, consulta, limite):
    r = _get(cfg["url"].format(q=quote_plus(consulta)))
    soup = BeautifulSoup(r.content, "xml")
    resultados = []
    for item in soup.find_all("item")[:limite]:
        titulo = item.find("title")
        link = item.find("link")
        data = item.find("pubDate")
        if titulo and link:
            resultados.append({
                "titulo": titulo.get_text(strip=True),
                "link": link.get_text(strip=True),   # resolvido só depois do filtro
                "data": _parse_data(data.get_text(strip=True)) if data else None,
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
                    max_chars: int = 4000):
    """
    empresa (+ termo) -> busca no portal -> extrai (titulo, link) -> acessa o link
    -> extrai o texto.

    termo:            palavras extras da busca (ex.: "receita bruta 3º trimestre 2024")
    data_ini/data_fim: restringem o período das notícias
    max_chars:        corta o texto de cada matéria (controla o uso de tokens da LLM)

    Retorna: [{"titulo", "link", "data", "texto"}, ...]
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
    noticias = buscar(cfg, consulta, limite * 3 if (data_ini or data_fim) else limite)

    # filtro de data (necessário no Bing; reforço no Google). Sem data = mantém.
    def no_periodo(n):
        d = n.get("data")
        return d is None or ((not data_ini or d >= data_ini) and (not data_fim or d <= data_fim))

    noticias = [n for n in noticias if no_periodo(n)][:limite]

    for n in noticias:
        n["link"] = _resolver_link(n["link"])
        if extrair:
            try:
                n["texto"] = extrair_texto(n["link"])[:max_chars]
            except Exception as e:  # site bloqueou, timeout, paywall...
                n["texto"] = ""
                n["erro"] = str(e)
            time.sleep(pausa)  # educado com os servidores

    return noticias


# ---------------------------------------------------------------------------
# Camada para a LLM: dataframe (índice = trimestre "nTYY", 1 coluna = parâmetro)
# -> trimestres com maior variação -> notícias do período -> texto de contexto
# ---------------------------------------------------------------------------
def periodo_do_trimestre(rotulo: str, dias_apos: int = 75):
    """'3T24' -> (01/07/2024, 30/09/2024 + dias_apos).
    A janela vai além do fim do trimestre porque o balanço sai ~30-60 dias depois."""
    tri, ano = str(rotulo).upper().strip().split("T")
    tri, ano = int(tri), 2000 + int(ano)
    ini = date(ano, 3 * tri - 2, 1)
    fim = date(ano, 3 * tri, calendar.monthrange(ano, 3 * tri)[1])
    return ini, fim + timedelta(days=dias_apos)


def maiores_variacoes(df, coluna=None, top: int = 3):
    """Devolve os `top` trimestres com maior variação % em relação ao anterior."""
    serie = df[coluna] if coluna else (df.iloc[:, 0] if hasattr(df, "columns") else df)
    var = serie.pct_change() * 100
    anterior = serie.shift(1)
    sel = var.abs().sort_values(ascending=False).dropna().head(top).index
    return [
        {"trimestre": t, "valor": float(serie[t]), "anterior": float(anterior[t]),
         "variacao_pct": float(var[t])}
        for t in sorted(sel, key=lambda r: tuple(reversed(str(r).upper().split("T"))))
    ]


def contexto_para_llm(df, empresa: str, coluna: str = None, top: int = 3,
                      noticias_por_trimestre: int = 3, portal: str = "google",
                      termo_busca: str = None, max_chars: int = 2000,
                      retornar_fontes: bool = False):
    """
    Monta o texto que vai para a LLM: para cada variação relevante, o que mudou
    e as notícias do período. Cada notícia recebe um código único ([F1], [F2]...).

    retornar_fontes=True -> devolve (texto, fontes), com fontes = {"F1": {"titulo","link"}, ...}
    Isso permite trocar os códigos citados pela LLM por hiperlinks (ver llm.linkar_fontes).
    """
    nome = coluna or (df.columns[0] if hasattr(df, "columns") else df.name)
    termo_param = termo_busca or str(nome).replace("_", " ").lower()
    blocos, fontes = [], {}

    for v in maiores_variacoes(df, coluna, top):
        ini, fim = periodo_do_trimestre(v["trimestre"])
        tri, ano = str(v["trimestre"]).upper().split("T")
        try:
            noticias = buscar_noticias(
                empresa, portal=portal, limite=noticias_por_trimestre,
                termo=f"{termo_param} {tri}º trimestre 20{ano}",
                data_ini=ini, data_fim=fim, max_chars=max_chars,
            )
        except Exception as e:
            noticias = []
            blocos.append(f"(erro na busca de notícias de {v['trimestre']}: {e})")

        sentido = "ALTA" if v["variacao_pct"] > 0 else "QUEDA"
        bloco = [f"## {v['trimestre']} — {nome}: {v['anterior']:,.2f} -> {v['valor']:,.2f} "
                 f"({sentido} de {abs(v['variacao_pct']):.1f}% vs trimestre anterior)"]
        if not noticias:
            bloco.append("Nenhuma notícia encontrada para este período.")
        for n in noticias:
            codigo = f"F{len(fontes) + 1}"
            fontes[codigo] = {"titulo": n["titulo"], "link": n["link"]}
            bloco.append(f"[{codigo}] {n['titulo']} ({n.get('data') or 's/ data'})\n"
                         f"    {n['link']}\n    {n.get('texto') or '(texto indisponível)'}")
        blocos.append("\n".join(bloco))

    texto = "\n\n".join(blocos)
    return (texto, fontes) if retornar_fontes else texto