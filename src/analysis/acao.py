from pathlib import Path
import numpy as np
import pandas as pd
from src.analysis.eventos import EVENTOS

TICKER_PETZ = "PETZ3.SA"
TICKER_GRUPO = "AUAU3.SA"
TICKER_INDICE = "^BVSP"
ARQUIVO_RESERVA = Path(__file__).resolve().parents[2] / "data" / "raw" / "precos.csv"

JANELA_ESTIMACAO = (-150, -11)   # pregões em relação ao dia do evento
JANELA_EVENTO = (-1, 1)          # pregão anterior, dia do evento e pregão seguinte
DIAS_GRAFICO = 5                 # o gráfico do evento mostra de −5 a +5 pregões
T_CRITICO = 1.96                 # 95% de confiança


def baixar_precos(inicio="2023-06-01"):
    """Preços de fechamento ajustados (por dividendos e desdobramentos). Devolve (DataFrame, origem)."""
    tickers = [TICKER_PETZ, TICKER_GRUPO, TICKER_INDICE]
    try:
        import yfinance as yf

        dados = yf.download(tickers, start=inicio, auto_adjust=True, progress=False)
        precos = dados["Close"] if isinstance(dados.columns, pd.MultiIndex) else dados
        precos = precos.dropna(how="all")
        if TICKER_PETZ not in precos or precos[TICKER_PETZ].dropna().empty:
            raise ValueError("o Yahoo Finance não devolveu os preços da PETZ3")
        origem = "Yahoo Finance (yfinance)"
    except Exception as erro:
        if not ARQUIVO_RESERVA.exists():
            raise RuntimeError(f"não foi possível baixar as cotações ({erro}) e não existe data/raw/precos.csv") from erro
        bruto = pd.read_csv(ARQUIVO_RESERVA, parse_dates=["data"])
        precos = bruto.pivot_table(index="data", columns="ticker", values="fechamento")
        origem = f"arquivo {ARQUIVO_RESERVA.name}"
    precos.index = pd.to_datetime(precos.index)
    if precos.index.tz is not None:
        precos.index = precos.index.tz_localize(None)
    return precos.sort_index(), origem


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