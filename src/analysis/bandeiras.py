"""Petz × Cobasi: qual bandeira avançou mais depois da fusão.

A planilha do RI só separa as bandeiras em receita bruta, SSS, lojas, inaugurações e área.
Margens, despesas, lucro e caixa existem apenas para o grupo, então esta comparação
mostra quem passou a vender mais, não quem passou a lucrar mais.
"""
import numpy as np
import pandas as pd

from src.analysis.eventos import TRIMESTRE_FUSAO
from src.analysis.indicadores import LIMIAR_PP, _matriz

BANDEIRAS = ["Petz", "Cobasi"]

# Diferença mínima entre as bandeiras para dizer que uma avançou mais que a outra
# formato "pct": em pontos percentuais; "reais" e "m2": em pontos da variação %
LIMIAR_DIFERENCA = {"pct": LIMIAR_PP, "reais": 0.01, "m2": 0.01}


def com_participacao(ind):
    """Cópia dos indicadores com a fatia de cada bandeira na receita bruta do grupo."""
    total = ind["receita_bruta_petz"] + ind["receita_bruta_cobasi"]
    return ind.assign(participacao_petz=ind["receita_bruta_petz"] / total,
                      participacao_cobasi=ind["receita_bruta_cobasi"] / total)


def _medidas(ind, b, periodos, anteriores):
    """Valores de uma bandeira num conjunto de trimestres. anteriores = os mesmos trimestres um ano antes."""
    d, d_ant = ind.loc[periodos], ind.reindex(anteriores)
    receita = d[f"receita_bruta_{b}"].sum()
    receita_ant = d_ant[f"receita_bruta_{b}"].sum(min_count=len(anteriores))
    total = (d["receita_bruta_petz"] + d["receita_bruta_cobasi"]).sum()
    return {
        "receita": receita,
        "crescimento": receita / receita_ant - 1 if pd.notna(receita_ant) and receita_ant else np.nan,
        "sss": d[f"sss_{b}"].mean(),
        "receita_m2": d[f"receita_m2_{b}"].mean(),
        "participacao": receita / total,
        "inauguracoes": d[f"inauguracoes_{b}"].sum(),
    }


# chave, nome, formato, explicação, entra na contagem de "quem avançou mais"
LINHAS = [
    ("receita", "Receita bruta", "reais",
     "Soma dos trimestres, em R$ milhões. Fica fora do placar porque a variação é o crescimento da linha abaixo.", False),
    ("crescimento", "Crescimento sobre o ano anterior", "pct",
     "Quanto a receita cresceu contra os mesmos trimestres um ano antes. Mostra se a bandeira acelerou.", True),
    ("sss", "Vendas mesmas lojas (SSS)", "pct",
     "Crescimento das vendas nas lojas que já existiam. Separa o ganho de clientes da abertura de lojas.", True),
    ("receita_m2", "Receita por m²", "m2", "Média por trimestre. Mostra quanto cada metro de loja passou a vender.", True),
    ("participacao", "Participação na receita do grupo", "pct",
     "Fatia da bandeira na receita bruta somada das duas. É o sinal mais direto de quem ganhou espaço.", True),
    ("inauguracoes", "Inaugurações", "int",
     "Lojas abertas no período. Não indica benefício: abrir menos lojas pode ser estratégia do grupo.", False),
]


def comparar_bandeiras(ind, antes, depois):
    """Uma linha por indicador, com antes, depois e variação de cada bandeira e quem avançou mais."""
    if not antes or not depois:
        return pd.DataFrame()
    ind = com_participacao(ind)
    vals = {}
    for b in BANDEIRAS:
        chave = b.lower()
        vals[b] = {"antes": _medidas(ind, chave, antes, [p - 4 for p in antes]),
                   "depois": _medidas(ind, chave, depois, antes)}
    linhas = []
    for chave, nome, formato, explica, compara in LINHAS:
        linha = {"chave": chave, "nome": nome, "formato": formato, "explica": explica, "compara": compara}
        for b in BANDEIRAS:
            a, d = vals[b]["antes"][chave], vals[b]["depois"][chave]
            delta = d / a - 1 if formato in ("reais", "m2") and a else d - a
            linha.update({f"{b}_antes": a, f"{b}_depois": d, f"{b}_delta": delta})
        linha["avancou_mais"] = _quem_avancou(linha) if compara else None
        linhas.append(linha)
    return pd.DataFrame(linhas).set_index("chave")


def _quem_avancou(linha):
    dp, dc = linha["Petz_delta"], linha["Cobasi_delta"]
    if pd.isna(dp) or pd.isna(dc):
        return None
    if abs(dp - dc) <= LIMIAR_DIFERENCA[linha["formato"]]:
        return "Empate"
    return "Petz" if dp > dc else "Cobasi"


# ---------------------------------------------------------------- receita contra a tendência
def tendencia_receita(ind, coluna, inicio=TRIMESTRE_FUSAO):
    """Tendência + sazonalidade ajustadas no log da receita antes da fusão (crescimento percentual constante),
    projetadas para todos os trimestres. Mesma matriz da tendência do grupo em indicadores.py."""
    y = np.log(ind[coluna].where(ind[coluna] > 0))
    validos = (ind.index < inicio) & y.notna().values
    if validos.sum() < 6:
        return None
    X = _matriz(ind.index)
    coef, *_ = np.linalg.lstsq(X[validos], y[validos].values, rcond=None)
    return pd.Series(np.exp(X @ coef), index=ind.index, name=coluna)


def receita_contra_tendencia(ind, inicio=TRIMESTRE_FUSAO):
    """Por bandeira: tendências projetadas e diferença média (real ÷ tendência − 1) nos trimestres pós-fusão."""
    pos = ind.index >= inicio
    tendencias, resumo = {}, {}
    for b in BANDEIRAS:
        coluna = f"receita_bruta_{b.lower()}"
        t = tendencia_receita(ind, coluna, inicio)
        if t is None or not pos.any():
            continue
        tendencias[b] = t
        resumo[b] = (ind.loc[pos, coluna] / t[pos] - 1).mean()
    return tendencias, resumo


# ---------------------------------------------------------------- sobreposição por bandeira
def sobreposicao_por_bandeira(lojas):
    """Quantas lojas de cada bandeira ficam em cidades que também têm a outra bandeira."""
    if lojas.empty:
        return {}
    cidade_uf = lojas["cidade"] + "/" + lojas["uf"]
    n_bandeiras = lojas.groupby(cidade_uf)["bandeira"].nunique()
    ambas = cidade_uf.isin(n_bandeiras[n_bandeiras >= 2].index)
    resultado = {}
    for b in BANDEIRAS:
        da_bandeira = lojas["bandeira"].str.casefold() == b.casefold()
        total = int(da_bandeira.sum())
        if total:
            em_ambas = int((da_bandeira & ambas).sum())
            resultado[b] = {"total": total, "em_cidades_ambas": em_ambas, "participacao": em_ambas / total}
    return resultado
