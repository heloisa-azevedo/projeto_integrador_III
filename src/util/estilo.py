"""Paleta, formatação pt-BR e CSS compartilhados por todas as páginas."""
import math

import streamlit as st

MARINHO = "#1D2858"     # identidade do grupo / pro forma
TERRACOTA = "#C56A3B"   # usado SÓ para marcar o período pós-fusão
CREME = "#F6F4EA"
TINTA_SUAVE = "#5B6283"
CINZA = "#8A8FA3"

COR_EMPRESA = {"Petz": "#4F7CAC", "Cobasi": "#6E9A63", "Grupo": MARINHO, "Pro forma": MARINHO}
# Séries que não são empresas (prazos, tipos de CAPEX). Terracota fica reservada ao pós-fusão.
COR_EXTRA = ["#3E7C7A", "#B08D57", "#7E6BA8"]


# ---------------------------------------------------------------- números pt-BR
def _br(numero, casas):
    texto = f"{numero:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_reais_mil(valor):
    """Planilhas do RI costumam vir em R$ mil. Confiram a unidade na planilha."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    if abs(valor) >= 1_000_000:
        return f"R$ {_br(valor / 1_000_000, 2)} bi"
    return f"R$ {_br(valor / 1_000, 0)} mi"


def fmt_pct(valor, casas=1):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    return f"{_br(valor * 100, casas)}%"


def fmt_dias(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    return f"{_br(valor, 0)} dias"


def fmt_reais_mi(valor):
    """Valores já em R$ milhões (como nos indicadores)."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    if abs(valor) >= 1_000:
        return f"R$ {_br(valor / 1_000, 2)} bi"
    return f"R$ {_br(valor, 0)} mi"


def fmt_int(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "–"
    return _br(valor, 0)


def fmt_valor(valor, formato):
    return {"reais": fmt_reais_mi, "pct": fmt_pct, "dias": fmt_dias, "int": fmt_int}[formato](valor)


def fmt_delta(delta, formato):
    if delta is None or (isinstance(delta, float) and math.isnan(delta)):
        return "–"
    sinal = "+" if delta > 0 else "−" if delta < 0 else "±"
    if formato == "reais":
        return f"{sinal}{_br(abs(delta) * 100, 1)}%"
    if formato == "pct":
        return f"{sinal}{_br(abs(delta) * 100, 1)} p.p."
    return f"{sinal}{_br(abs(delta), 0)} dias"


# ---------------------------------------------------------------- CSS
CSS = f"""
<style>
/* Logo maior na sidebar (a imagem já vem recortada, sem margem sobrando) */
[data-testid="stSidebarHeader"] {{ padding: 1.25rem 1rem 0.5rem; height: auto; }}
[data-testid="stSidebarHeader"] img {{ height: 2.6rem; max-height: none; width: auto; }}

.block-container {{ max-width: 1180px; padding-top: 2.5rem; }}

h1, h2, h3 {{ letter-spacing: -0.015em; }}
.pc-lead {{ font-size: 1.12rem; line-height: 1.6; max-width: 66ch; color: {TINTA_SUAVE}; }}
.pc-nota {{ font-size: 0.9rem; color: {TINTA_SUAVE}; max-width: 75ch; }}

/* ---------- Página inicial: pergunta em destaque ---------- */
.pc-hero {{ padding: 1rem 0 2.25rem; border-bottom: 2px solid {MARINHO}; margin-bottom: 2.5rem; }}
.pc-hero h1 {{
    font-size: clamp(2.3rem, 5vw, 3.9rem); line-height: 1.04; font-weight: 800;
    max-width: 17ch; margin: 0 0 1.25rem; padding: 0;
}}

/* ---------- Linha do tempo (é uma sequência real, por isso numerada por data) ---------- */
.pc-timeline {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 0; margin: 1.5rem 0 0.5rem; }}
.pc-evento {{ position: relative; padding: 1.6rem 1rem 0 0; border-top: 2px solid {MARINHO}; }}
.pc-evento::before {{
    content: ""; position: absolute; top: -7px; left: 0; width: 12px; height: 12px;
    border-radius: 50%; background: {CREME}; border: 2px solid {MARINHO};
}}
.pc-evento.final {{ border-top-color: {TERRACOTA}; }}
.pc-evento.final::before {{ background: {TERRACOTA}; border-color: {TERRACOTA}; }}
.pc-evento .quando {{ font-weight: 700; font-size: 0.85rem; color: {TINTA_SUAVE}; }}
.pc-evento .titulo {{ font-family: Outfit, 'Source Sans 3', 'Source Sans Pro', sans-serif; font-weight: 700; font-size: 1.05rem; margin: 0.15rem 0 0.35rem; }}
.pc-evento .texto {{ font-size: 0.88rem; line-height: 1.45; color: {TINTA_SUAVE}; }}
@media (max-width: 900px) {{
    .pc-timeline {{ grid-template-columns: 1fr; }}
    .pc-evento {{ border-top: none; border-left: 2px solid {MARINHO}; padding: 0 0 1.2rem 1.25rem; }}
    .pc-evento::before {{ top: 0.2rem; left: -7px; }}
    .pc-evento.final {{ border-left-color: {TERRACOTA}; }}
}}

/* ---------- Mecanismos (página inicial) ---------- */
.pc-mecanismos {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 2rem; margin-top: 1rem; }}
@media (max-width: 1200px) {{ .pc-mecanismos {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 640px) {{ .pc-mecanismos {{ grid-template-columns: 1fr; }} }}
.pc-mecanismo {{ border-left: 3px solid {MARINHO}; padding-left: 1rem; }}
.pc-mecanismo h4 {{ margin: 0 0 0.4rem; padding: 0; font-size: 1.1rem; }}
.pc-mecanismo p {{ font-size: 0.92rem; line-height: 1.5; margin: 0 0 0.5rem; }}
.pc-mecanismo .indicador {{ font-weight: 600; color: {TERRACOTA}; }}

/* ---------- Quadro antes × depois (elemento principal da análise) ---------- */
.pc-quadro {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0 1rem; border: none; }}
.pc-quadro th, .pc-quadro td {{ border: none; background: transparent; }}
.pc-quadro th {{
    text-align: right; font-weight: 600; font-size: 0.85rem; color: {TINTA_SUAVE};
    padding: 0 0.75rem 0.6rem; border-bottom: 2px solid {MARINHO} !important;
}}
.pc-quadro th:first-child {{ text-align: left; padding-left: 0; }}
.pc-quadro th.depois {{ color: {TERRACOTA}; }}
.pc-quadro td {{ padding: 0.95rem 0.75rem; border-bottom: 1px solid rgba(29,40,88,.12) !important; vertical-align: top; }}
.pc-quadro td:first-child {{ padding-left: 0; width: 46%; }}
.pc-quadro .nome {{ font-family: Outfit, 'Source Sans 3', 'Source Sans Pro', sans-serif; font-weight: 700; font-size: 1.05rem; }}
.pc-quadro .explica {{ font-size: 0.85rem; line-height: 1.4; color: {TINTA_SUAVE}; margin-top: 0.2rem; max-width: 52ch; }}
.pc-quadro .num {{ text-align: right; font-size: 1.15rem; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.pc-quadro .num.antes {{ color: {TINTA_SUAVE}; }}
.pc-quadro .num.depois {{ font-weight: 700; }}
.pc-delta {{
    display: inline-block; padding: 0.15rem 0.55rem; border-radius: 6px; font-size: 0.95rem;
    font-weight: 700; background: rgba(197,106,59,.13); color: #8E4521;
}}
.pc-delta.neutro {{ background: rgba(138,143,163,.15); color: {TINTA_SUAVE}; font-weight: 600; }}
@media (max-width: 700px) {{ .pc-quadro .explica {{ display: none; }} .pc-quadro .num {{ font-size: 1rem; }} }}

/* ---------- Números de destaque ---------- */
.pc-destaques {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 1.5rem; margin: 0.5rem 0 1.5rem; }}
.pc-destaque .valor {{ font-family: Outfit, 'Source Sans 3', 'Source Sans Pro', sans-serif; font-weight: 800; font-size: 2.4rem; line-height: 1.05; font-variant-numeric: tabular-nums; }}
.pc-destaque .rotulo {{ font-size: 0.88rem; color: {TINTA_SUAVE}; margin-top: 0.3rem; max-width: 26ch; }}

/* ---------- Lista de cuidados ---------- */
.pc-cuidados {{ font-size: 0.92rem; color: {TINTA_SUAVE}; max-width: 80ch; padding-left: 1.2rem; }}
.pc-cuidados li + li {{ margin-top: 0.35rem; }}

/* ---------- Leitura dos mecanismos ---------- */
.pc-leitura {{ display: grid; grid-template-columns: 11rem 1fr; gap: 0.6rem 1.25rem; margin: 0.5rem 0 1.5rem; }}
.pc-leitura .rotulo {{ font-weight: 700; }}
.pc-leitura .rotulo.sim {{ color: #8E4521; }}
.pc-leitura .rotulo.nao, .pc-leitura .rotulo.indef {{ color: {TINTA_SUAVE}; }}
.pc-leitura div {{ font-size: 0.95rem; line-height: 1.45; }}
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)
