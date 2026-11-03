"""Conclusão: leitura dos mecanismos, texto do grupo e limitações."""
from pathlib import Path

import streamlit as st

from src.analysis.indicadores import rotulo_trimestre
from src.util.componentes import barra_lateral_dados, cuidados, exigir_base, leitura, leitura_com_ia, quadro

barra_lateral_dados()
base, _ = exigir_base()

st.title("Conclusão")
st.markdown('<p class="pc-lead">A pergunta do trabalho é se a fusão aumentou o poder de mercado do grupo. '
            "Abaixo, o que cada sinal indica e a resposta do grupo.</p>", unsafe_allow_html=True)

if base["depois"]:
    st.subheader("O que cada sinal indica")
    leitura(base["comparacao"], base["indicadores"], base["depois"])
    periodo = " e ".join(rotulo_trimestre(p) for p in base["depois"])
    st.caption(f"Leitura automática com base em {periodo}, comparados com os mesmos trimestres de um ano antes.")

    st.subheader("Os números por trás da leitura")
    principais = base["comparacao"].loc[["margem_bruta", "despesas_vendas", "despesas_ga", "margem_ebitda", "prazo_fornecedores"]]
    quadro(principais.to_dict("records"),
           [("Antes", "antes", "antes"), ("Depois", "depois", "depois"), ("Variação", "delta", "delta")])

leitura_com_ia(base, "leitura_ia_conclusao")

st.subheader("Resposta do grupo")
st.markdown((Path(__file__).resolve().parents[2] / "content" / "conclusao.md").read_text(encoding="utf-8"))

st.subheader("Limitações")
cuidados(base)
