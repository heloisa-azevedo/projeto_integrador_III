"""Previsão do semestre seguinte com regressão linear simples.

Cada série (feature) tem o seu próprio modelo: valor = a + b · t, em que t é o tempo.
Os coeficientes são estimados por mínimos quadrados com todo o histórico da série.
O modelo não considera sazonalidade nem a fusão: ele só prolonga a reta do histórico.
"""
import numpy as np
import pandas as pd

HORIZONTE_TRIMESTRES = 2   # um semestre
HORIZONTE_MESES = 6        # o mesmo semestre, para a série diária da ação
MINIMO_PONTOS = 6


def _reta(t, y):
    """Mínimos quadrados com uma variável. Devolve (a, b)."""
    b, a = np.polyfit(t, y, 1)
    return a, b


def _r2(y, ajustado):
    total = ((y - y.mean()) ** 2).sum()
    return 1 - ((y - ajustado) ** 2).sum() / total if total > 0 else np.nan


# ---------------------------------------------------------------- séries trimestrais
def prever_trimestres(serie, horizonte=HORIZONTE_TRIMESTRES):
    """serie: Series com PeriodIndex trimestral. Devolve um dict ou None se houver poucos dados.

    previsao:     Series com os `horizonte` trimestres depois do último índice
    r2:           quanto da variação do histórico a reta explica
    erro_modelo:  erro absoluto médio ao esconder os últimos trimestres e prevê-los
    erro_ingenuo: o mesmo erro repetindo o mesmo trimestre do ano anterior (referência)
    """
    y = serie.dropna().astype(float)
    if len(y) < MINIMO_PONTOS:
        return None
    origem = serie.index.min().ordinal
    t = np.array([p.ordinal - origem for p in y.index], dtype=float)
    a, b = _reta(t, y.values)

    futuros = pd.period_range(serie.index.max() + 1, periods=horizonte, freq=serie.index.freq)
    t_futuro = np.array([p.ordinal - origem for p in futuros], dtype=float)
    previsao = pd.Series(a + b * t_futuro, index=futuros, name=serie.name)

    erro_modelo = erro_ingenuo = np.nan
    if len(y) - horizonte >= MINIMO_PONTOS:
        a_t, b_t = _reta(t[:-horizonte], y.values[:-horizonte])
        teste = y.iloc[-horizonte:]
        erro_modelo = np.abs(teste.values - (a_t + b_t * t[-horizonte:])).mean()
        anterior = serie.reindex(teste.index - 4)
        if anterior.notna().all():
            erro_ingenuo = np.abs(teste.values - anterior.values).mean()

    return {"previsao": previsao, "intercepto": a, "inclinacao": b, "r2": _r2(y.values, a + b * t),
            "erro_modelo": erro_modelo, "erro_ingenuo": erro_ingenuo, "n": len(y)}


# ---------------------------------------------------------------- série diária (ação e índice)
def prever_diario(serie, meses=HORIZONTE_MESES):
    """serie: Series com DatetimeIndex (um valor por pregão). Prevê os dias úteis dos próximos `meses`.
    A referência do erro é repetir a última cotação conhecida."""
    y = serie.dropna().astype(float)
    if len(y) < 60:
        return None
    dias = lambda datas: ((datas - y.index[0]) / pd.Timedelta(days=1)).to_numpy(dtype=float)
    t = dias(y.index)
    a, b = _reta(t, y.values)

    ultimo = y.index[-1]
    futuros = pd.bdate_range(ultimo + pd.Timedelta(days=1), ultimo + pd.DateOffset(months=meses))
    previsao = pd.Series(a + b * dias(futuros), index=futuros, name=serie.name)

    erro_modelo = erro_ingenuo = np.nan
    treino = np.asarray(y.index <= ultimo - pd.DateOffset(months=meses))
    if treino.sum() >= 60 and (~treino).any():
        a_t, b_t = _reta(t[treino], y.values[treino])
        erro_modelo = np.abs(y.values[~treino] - (a_t + b_t * t[~treino])).mean()
        erro_ingenuo = np.abs(y.values[~treino] - y.values[treino][-1]).mean()

    return {"previsao": previsao, "intercepto": a, "inclinacao": b, "r2": _r2(y.values, a + b * t),
            "erro_modelo": erro_modelo, "erro_ingenuo": erro_ingenuo, "n": len(y)}
