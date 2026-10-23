import re

import streamlit as st
from groq import Groq

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
MODELO = st.secrets.get("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM = """Você é um analista financeiro explicando resultados de empresas do varejo \
para quem está começando. Receberá a variação de uma métrica por trimestre e notícias \
do período. Cada notícia tem um código entre colchetes, como [F1], [F2].

Regras:
- Responda em português do Brasil.
- Para cada trimestre, explique em 2 a 4 frases simples por que a métrica subiu ou caiu.
- Use SOMENTE as notícias fornecidas.
- Cite a fonte pelo CÓDIGO da notícia, exatamente como [F1] ou [F2], logo após a frase \
que ela sustenta. Nunca escreva URLs nem invente códigos.
- Se nenhuma notícia explicar a variação, diga que não encontrou explicação, sem inventar.
- Não afirme causa como certa; use "possivelmente", "segundo a notícia" quando couber."""


def explicar_variacoes(empresa: str, coluna: str, contexto: str) -> str:
    resp = client.chat.completions.create(
        model=MODELO,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Empresa: {empresa}\nMétrica: {coluna}\n\n{contexto}"},
        ],
    )
    return resp.choices[0].message.content


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