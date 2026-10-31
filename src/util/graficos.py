"""Gráficos em Plotly com o período pós-fusão sombreado e o anúncio da fusão marcado.
Mesma lógica dos gráficos do painel interativo."""
import pandas as pd
import plotly.graph_objects as go

from src.analysis.eventos import EVENTOS, EVENTOS_NOS_GRAFICOS, TRIMESTRE_FUSAO
from src.analysis.indicadores import rotulo_trimestre
from src.util.estilo import CINZA, COR_EMPRESA, COR_EXTRA, MARINHO, TERRACOTA, TINTA_SUAVE

FORMATOS = {
    "pct": {"tick": ".0%", "hover": ".1%", "sufixo": ""},
    "pct1": {"tick": ".1%", "hover": ".1%", "sufixo": ""},
    "dias": {"tick": ",.0f", "hover": ",.0f", "sufixo": " dias"},
    "mi": {"tick": ",.0f", "hover": ",.0f", "sufixo": " mi"},
    "int": {"tick": ",.0f", "hover": ",.0f", "sufixo": ""},
    "m2": {"tick": ",.0f", "hover": ",.0f", "sufixo": "/m²"},
}
CONFIG = {"displayModeBar": False}


def cor(chave):
    """'Petz', 'Cobasi', 'Grupo', 0..2 (cores extras) ou 'muted'."""
    if chave == "muted":
        return CINZA
    if isinstance(chave, int):
        return COR_EXTRA[chave % len(COR_EXTRA)]
    return COR_EMPRESA.get(chave, MARINHO)


def _layout(fig, titulo, formato, altura=360):
    f = FORMATOS[formato]
    fig.update_layout(
        title=dict(text=titulo, x=0, xanchor="left", font=dict(family="Outfit, Source Sans 3, sans-serif", size=17, color=MARINHO)) if titulo else None,
        height=altura, margin=dict(l=8, r=8, t=56 if titulo else 30, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Figtree, Source Sans 3, sans-serif", color=MARINHO, size=13),
        separators=",.", hovermode="x unified",
        legend=dict(orientation="h", y=-0.14, x=0, title=None, traceorder="normal"),
        hoverlabel=dict(bgcolor="white", font_color=MARINHO),
    )
    fig.update_yaxes(tickformat=f["tick"], ticksuffix=f["sufixo"] if formato in ("dias", "mi") else "",
                     gridcolor="rgba(29,40,88,.08)", zeroline=False)
    fig.update_xaxes(showgrid=False, type="category", tickangle=0)
    return fig


def _eixo(df):
    periodos = pd.period_range(df.index.min(), df.index.max(), freq="Q")
    return periodos, [rotulo_trimestre(p) for p in periodos]


def _marcar_fusao(fig, periodos, rotulos):
    """Sombreia o pós-fusão e marca o anúncio (posição proporcional à data dentro do trimestre)."""
    lista = list(periodos)
    if TRIMESTRE_FUSAO <= periodos[-1]:
        pos = lista.index(TRIMESTRE_FUSAO) if TRIMESTRE_FUSAO in lista else 0
        fig.add_vrect(x0=pos - 0.5, x1=len(lista) - 0.5, fillcolor=TERRACOTA, opacity=0.09, line_width=0, layer="below")
        fig.add_annotation(x=pos - 0.4, y=1, yref="paper", text="Pós-fusão", showarrow=False, xanchor="left",
                           yanchor="top", font=dict(color=TERRACOTA, size=12, family="Figtree, sans-serif"))
    for ev in EVENTOS:
        if ev["titulo"] not in EVENTOS_NOS_GRAFICOS or ev["titulo"] == "Fusão concluída":
            continue
        data = pd.Timestamp(ev["data"])
        p = data.to_period("Q")
        if p not in lista:
            continue
        frac = (data - p.start_time) / (p.end_time - p.start_time)
        x = lista.index(p) - 0.5 + frac
        fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper", line=dict(color=CINZA, width=1, dash="dot"))
        fig.add_annotation(x=x, y=1, yref="paper", text=ev["titulo"], showarrow=False, xanchor="right",
                           yanchor="top", xshift=-4, font=dict(color=TINTA_SUAVE, size=11))
    fig.update_xaxes(categoryorder="array", categoryarray=rotulos, tickvals=[r for r in rotulos if r.startswith("1T")])


def grafico_linhas(df, series, formato, titulo=None, tendencia=None, altura=360):
    """series: lista de (coluna, nome, cor). tendencia: Series projetada (linha pontilhada cinza)."""
    fig = go.Figure()
    periodos, rotulos = _eixo(df)
    valores = pd.concat([df[c] for c, _, _ in series] + ([tendencia] if tendencia is not None else [])).dropna()
    if formato == "pct" and not valores.empty and valores.max() - valores.min() < 0.03:
        formato = "pct1"
    f = FORMATOS[formato]
    hover = f"%{{y:{f['hover']}}}{f['sufixo']}"
    if tendencia is not None:
        fig.add_scatter(x=rotulos, y=tendencia.reindex(periodos), name="Tendência sem fusão", mode="lines",
                        line=dict(color=cor("muted"), width=2.5, dash="dot"), hovertemplate=hover)
    for coluna, nome, c in series:
        s = df[coluna].reindex(periodos)
        pos = [p >= TRIMESTRE_FUSAO for p in periodos]
        fig.add_scatter(x=rotulos, y=s, name=nome, mode="lines+markers", line=dict(color=cor(c), width=2.5),
                        marker=dict(size=[7 if p else 0 for p in pos], color=cor(c)), hovertemplate=hover)
    _layout(fig, titulo, formato, altura)
    _marcar_fusao(fig, periodos, rotulos)
    if len(series) == 1 and tendencia is None:
        fig.update_layout(showlegend=False)
    return fig


def grafico_barras(df, series, formato, titulo=None, altura=360):
    """Barras empilhadas. series: lista de (coluna, nome, cor)."""
    fig = go.Figure()
    periodos, rotulos = _eixo(df)
    f = FORMATOS[formato]
    for coluna, nome, c in series:
        fig.add_bar(x=rotulos, y=df[coluna].reindex(periodos), name=nome, marker_color=cor(c),
                    hovertemplate=f"%{{y:{f['hover']}}}{f['sufixo']}")
    _layout(fig, titulo, formato, altura)
    fig.update_layout(barmode="stack", bargap=0.28)
    if len(series) == 1:
        fig.update_layout(showlegend=False)
    _marcar_fusao(fig, periodos, rotulos)
    return fig


def grafico_cidades(cidades, n=15):
    """Petz à esquerda, Cobasi à direita, nas cidades com mais lojas das duas bandeiras."""
    top = cidades.head(n).iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=top["cidade"], x=-top["petz"], orientation="h", name="Petz", marker_color=cor("Petz"),
                text=top["petz"], textposition="outside", customdata=top["petz"], hovertemplate="%{customdata} lojas")
    fig.add_bar(y=top["cidade"], x=top["cobasi"], orientation="h", name="Cobasi", marker_color=cor("Cobasi"),
                text=top["cobasi"], textposition="outside", hovertemplate="%{x} lojas")
    limite = max(top["petz"].max(), top["cobasi"].max()) * 1.2
    fig.update_layout(
        barmode="relative", height=70 + 28 * len(top), margin=dict(l=8, r=8, t=50, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Figtree, Source Sans 3, sans-serif", color=MARINHO, size=13),
        legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0.5, xanchor="center", title=None), hovermode="y unified",
    )
    fig.update_xaxes(range=[-limite, limite], showticklabels=False, showgrid=False, zeroline=True, zerolinecolor=CINZA)
    fig.update_yaxes(showgrid=False, automargin=True)
    return fig


# ---------------------------------------------------------------- exploração dos dados (versão anterior do grupo)
# Usadas na aba "Exploração dos dados" da página Dados e método.
from io import StringIO

import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st


def info(data):
    """Mostra o resultado de DataFrame.info() como texto."""
    buffer = StringIO()
    data.info(buf=buffer)
    st.markdown("<style>pre code { color: black !important; }</style>", unsafe_allow_html=True)
    return st.code(buffer.getvalue(), language="text")


def correlacao(data):
    corr = data.corr(numeric_only=True)
    fig_corr, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", linewidths=0.5, cbar_kws={"shrink": 1},
                annot_kws={"size": 6}, vmin=-1, vmax=1, ax=ax)
    plt.xticks(rotation=45, ha="right")
    return fig_corr


def htg(data):
    return data.hist(figsize=(15, 13))


def linha(lista_dados, x: str, y: str, lista_empresas):
    """Gráfico de linhas comparando empresas (versão anterior; as páginas novas usam grafico_linhas)."""
    fig = go.Figure()
    for data, empresa in zip(lista_dados, lista_empresas):
        fig.add_trace(go.Scatter(x=data.index, y=data[y], mode="lines+markers", name=empresa))

    def chave_trimestre(rotulo):
        trimestre, ano = str(rotulo).split("T")
        return (int(ano), int(trimestre))

    todos_trimestres = set()
    for data in lista_dados:
        todos_trimestres.update(data.index)
    ordem = sorted(todos_trimestres, key=chave_trimestre)
    nome_y = y.replace("_", " ")
    fig.update_layout(
        yaxis_title=f"{nome_y} em R$", xaxis_title=x, legend_title="Empresas",
        xaxis=dict(tickangle=-45, type="category", categoryorder="array", categoryarray=ordem),
        yaxis=dict(tickformat=",.2f", exponentformat="none"),
        template="plotly_white", margin=dict(l=40, r=40, t=40, b=80),
    )
    return fig
