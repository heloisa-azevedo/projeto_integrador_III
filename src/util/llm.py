"""Explicação das variações com IA (Groq).

A chave fica em .streamlit/secrets.toml (nunca no Git):
    GROQ_API_KEY = "..."
    GROQ_MODEL = "openai/gpt-oss-120b"   # opcional

Mudanças desta versão:
- o cliente só é criado na hora de usar: sem a chave, o app abre normalmente e só esta função fica indisponível;
- o prompt pede uma explicação por trimestre, começando por **nTYY**, sem títulos Markdown,
  e trata notícias com "só o título" com mais cuidado;
- separar_por_trimestre() divide a resposta para cada trimestre aparecer no seu cartão.
"""
import re

import streamlit as st

MODELO_PADRAO = "openai/gpt-oss-120b"

SYSTEM = """Você é um analista financeiro explicando resultados de empresas do varejo \
para quem está começando. Receberá a variação de uma métrica por trimestre e notícias \
do período. Cada notícia tem um código entre colchetes, como [F1], [F2].

Contexto: Petz e Cobasi se fundiram em janeiro de 2026. Antes disso, os números são pro forma \
(as duas empresas somadas); depois, são do grupo combinado.

Regras:
- Responda em português do Brasil.
- Para cada trimestre, escreva um parágrafo que comece exatamente com o trimestre em negrito, \
como **2T25**:, e explique em 2 a 4 frases simples por que a métrica subiu ou caiu.
- Não use títulos, cabeçalhos (#) nem listas. Não repita os números da variação, eles já aparecem na tela.
- Use SOMENTE as notícias fornecidas.
- Cite a fonte pelo CÓDIGO da notícia, exatamente como [F1] ou [F2], logo após a frase \
que ela sustenta. Nunca escreva URLs nem invente códigos.
- Notícias marcadas como "só o título" não bastam sozinhas para afirmar uma causa: deixe isso claro.
- Se a notícia fala de só uma das empresas, diga de qual (Petz ou Cobasi).
- Se nenhuma notícia explicar a variação, diga que não encontrou explicação nas notícias, sem inventar.
- Não afirme causa como certa; use "possivelmente", "segundo a notícia" quando couber."""


def _segredo(nome, padrao=None):
    try:
        return st.secrets.get(nome, padrao)
    except Exception:  # sem arquivo secrets.toml
        return padrao


def ia_disponivel() -> bool:
    return bool(_segredo("GROQ_API_KEY"))


def explicar_variacoes(empresa: str, coluna: str, contexto: str) -> str:
    from groq import Groq  # import tardio: o app funciona mesmo sem o pacote configurado

    client = Groq(api_key=_segredo("GROQ_API_KEY"))
    resp = client.chat.completions.create(
        model=_segredo("GROQ_MODEL", MODELO_PADRAO),
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Empresa: {empresa}\nMétrica: {coluna}\n\n{contexto}"},
        ],
    )
    return resp.choices[0].message.content


def separar_por_trimestre(texto: str) -> dict:
    """'**2T25**: ... **3T25**: ...' -> {'2T25': '...', '3T25': '...'}. Vazio se a IA não seguir o formato."""
    partes = re.split(r"\*\*\s*([1-4]T\d{2})\s*\*\*\s*:?", texto or "")
    return {partes[i].upper(): partes[i + 1].strip() for i in range(1, len(partes) - 1, 2) if partes[i + 1].strip()}


def linkar_fontes(texto: str, fontes: dict) -> str:
    def hiperlink(codigo):
        f = fontes.get(codigo)
        if not f:
            return codigo
        titulo = f["titulo"].replace("[", "(").replace("]", ")")
        return f"[{titulo}]({f['link']})"

    def trocar(m):
        return "(" + "; ".join(hiperlink(c) for c in re.findall(r"F\d+", m.group(0))) + ")"

    return re.sub(r"\[\s*F\d+(?:\s*[,;]\s*F\d+)*\s*\]", trocar, texto)
