"""Ação na bolsa: reação da PETZ3 aos eventos da fusão (estudo de evento) e desempenho do grupo depois dela.

Preços do Yahoo Finance pela biblioteca yfinance:
    PETZ3.SA  Petz, negociada até o fim de 2025
    AUAU3.SA  Grupo Petz Cobasi, negociado desde janeiro de 2026 (1 ação nova para cada ação da Petz)
    ^BVSP     Ibovespa, usado para descontar o movimento do mercado

O Yahoo pode não ter mais o histórico da PETZ3 (ela deixou de ser negociada) ou bloquear acessos vindos do
Streamlit Cloud. O que faltar é completado por data/raw/precos.csv (colunas: data, ticker, fechamento),
que o script scripts/precos_b3.py monta com as cotações oficiais da B3.

Estudo de evento (modelo de mercado):
1. Com os retornos diários de 150 a 11 pregões antes do evento, estima-se o comportamento normal da ação:
   retorno_ação = α + β × retorno_Ibovespa.
2. Retorno anormal = retorno real − retorno esperado pelo modelo.
3. Soma-se o retorno anormal na janela do evento (do pregão anterior ao seguinte) e compara-se com a
   oscilação normal da ação: estatística t acima de 1,96 (em módulo) indica reação fora do comum.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.analysis.eventos import EVENTOS

TICKER_PETZ = "PETZ3.SA"
TICKER_GRUPO = "AUAU3.SA"
TICKER_INDICE = "^BVSP"
TICKER_INDICE_ALTERNATIVO = "BOVA11.SA"   # ETF do Ibovespa, usado se o índice não estiver disponível
ARQUIVO_RESERVA = Path(__file__).resolve().parents[2] / "data" / "raw" / "precos.csv"

JANELA_ESTIMACAO = (-150, -11)   # pregões em relação ao dia do evento
JANELA_EVENTO = (-1, 1)          # pregão anterior, dia do evento e pregão seguinte
DIAS_GRAFICO = 5                 # o gráfico do evento mostra de −5 a +5 pregões
T_CRITICO = 1.96                 # 95% de confiança


def _do_yahoo(tickers, inicio):
    """Preços do Yahoo Finance; colunas vazias são descartadas (ticker sem histórico ou download bloqueado)."""
    import yfinance as yf

    dados = yf.download(tickers, start=inicio, auto_adjust=True, progress=False)
    if dados.empty:
        return pd.DataFrame()
    precos = dados["Close"] if isinstance(dados.columns, pd.MultiIndex) else dados[["Close"]].rename(columns={"Close": tickers[0]})
    return precos.dropna(axis=1, how="all").dropna(how="all")


def _do_arquivo():
    """data/raw/precos.csv (colunas data, ticker, fechamento), gerado por scripts/precos_b3.py ou à mão."""
    if not ARQUIVO_RESERVA.exists():
        return pd.DataFrame()
    bruto = pd.read_csv(ARQUIVO_RESERVA, parse_dates=["data"])
    return bruto.pivot_table(index="data", columns="ticker", values="fechamento")


def baixar_precos(inicio="2023-06-01"):
    """Junta as duas fontes: o Yahoo Finance traz o que conseguir e o arquivo completa o que faltar.
    Assim o arquivo só precisa ter a PETZ3, se for ela que o Yahoo não tiver mais. Devolve (DataFrame, origem)."""
    tickers = [TICKER_PETZ, TICKER_GRUPO, TICKER_INDICE]
    try:
        yahoo = _do_yahoo(tickers, inicio)
        erro_yahoo = None
    except Exception as erro:
        yahoo, erro_yahoo = pd.DataFrame(), erro
    arquivo = _do_arquivo()

    colunas, origens = {}, []
    for t in tickers:
        if t in yahoo and yahoo[t].notna().any():
            colunas[t] = yahoo[t]
            origens.append(f"{t.replace('.SA', '')}: Yahoo Finance")
        elif t in arquivo and arquivo[t].notna().any():
            colunas[t] = arquivo[t]
            origens.append(f"{t.replace('.SA', '')}: {ARQUIVO_RESERVA.name}")

    if TICKER_INDICE not in colunas:
        for fonte, nome in ((yahoo, "Yahoo Finance"), (arquivo, ARQUIVO_RESERVA.name)):
            if TICKER_INDICE_ALTERNATIVO in fonte and fonte[TICKER_INDICE_ALTERNATIVO].notna().any():
                colunas[TICKER_INDICE] = fonte[TICKER_INDICE_ALTERNATIVO]
                origens.append(f"Ibovespa aproximado pelo BOVA11: {nome}")
                break

    faltando = [t.replace(".SA", "") for t in (TICKER_PETZ, TICKER_INDICE) if t not in colunas]
    if faltando:
        motivo = f"o Yahoo Finance falhou ({erro_yahoo})" if erro_yahoo else "o Yahoo Finance não devolveu essas cotações"
        dica = ("rode python -m scripts.precos_b3 para criar data/raw/precos.csv" if not ARQUIVO_RESERVA.exists()
                else f"elas também não estão em data/raw/{ARQUIVO_RESERVA.name}")
        raise RuntimeError(f"faltam as cotações de {', '.join(faltando)}: {motivo}; {dica}")

    precos = pd.DataFrame(colunas)
    precos.index = pd.to_datetime(precos.index)
    if precos.index.tz is not None:
        precos.index = precos.index.tz_localize(None)
    precos = precos[precos.index >= pd.Timestamp(inicio)].sort_index()
    return precos, "; ".join(origens)


def serie_do_grupo(precos):
    """Uma série só: PETZ3 até o fim da negociação e AUAU3 depois (1 ação nova por ação da Petz).
    Não inclui o dinheiro pago aos acionistas da Petz na conclusão, então subestima o retorno de quem tinha PETZ3."""
    petz = precos.get(TICKER_PETZ, pd.Series(dtype=float)).dropna()
    grupo = precos.get(TICKER_GRUPO, pd.Series(dtype=float)).dropna()
    if not petz.empty:
        grupo = grupo[grupo.index > petz.index.max()]
    return pd.concat([petz, grupo]).sort_index()


def base_100(serie, inicio):
    s = serie[serie.index >= pd.Timestamp(inicio)].dropna()
    return s / s.iloc[0] * 100 if not s.empty else s


def estudo_de_evento(precos, data_evento, acao=TICKER_PETZ, indice=TICKER_INDICE):
    """Retorno anormal da ação em torno de uma data. Devolve (resumo, janela) ou (None, None)."""
    retornos = np.log(precos[[acao, indice]]).diff().dropna()
    datas = retornos.index
    pos = datas.searchsorted(pd.Timestamp(data_evento))   # primeiro pregão na data ou depois
    ini, fim = pos + JANELA_ESTIMACAO[0], pos + JANELA_ESTIMACAO[1]
    if ini < 0 or pos + JANELA_EVENTO[1] >= len(datas):
        return None, None

    estimacao = retornos.iloc[ini:fim + 1]
    beta, alfa = np.polyfit(estimacao[indice], estimacao[acao], 1)
    sigma = (estimacao[acao] - (alfa + beta * estimacao[indice])).std(ddof=2)

    janela = retornos.iloc[max(pos - DIAS_GRAFICO, 0):pos + DIAS_GRAFICO + 1].copy()
    janela["dia"] = np.arange(len(janela)) + (max(pos - DIAS_GRAFICO, 0) - pos)
    janela["anormal"] = janela[acao] - (alfa + beta * janela[indice])
    janela["anormal_acumulado"] = janela["anormal"].cumsum()

    no_evento = janela[(janela["dia"] >= JANELA_EVENTO[0]) & (janela["dia"] <= JANELA_EVENTO[1])]
    car = no_evento["anormal"].sum()
    t = car / (sigma * np.sqrt(len(no_evento)))
    dia0 = janela[janela["dia"] == 0].iloc[0]
    resumo = {
        "pregao": datas[pos].date(),
        "retorno_dia": np.exp(dia0[acao]) - 1,
        "indice_dia": np.exp(dia0[indice]) - 1,
        "retorno_anormal": np.exp(car) - 1,
        "t": t,
        "significativo": abs(t) > T_CRITICO,
        "beta": beta,
    }
    return resumo, janela


def tabela_eventos(precos):
    """Estudo de evento para cada marco da fusão marcado com estudo_evento."""
    linhas, janelas = [], {}
    for ev in EVENTOS:
        if not ev.get("estudo_evento"):
            continue
        resumo, janela = estudo_de_evento(precos, ev["data"])
        if resumo is None:
            continue
        linhas.append({"evento": ev["titulo"], **resumo})
        janelas[ev["titulo"]] = janela
    return pd.DataFrame(linhas), janelas