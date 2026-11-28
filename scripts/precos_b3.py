"""Monta data/raw/precos.csv com as cotações oficiais da B3 (séries históricas COTAHIST).

Uso (na raiz do projeto):
    python -m scripts.precos_b3                      # baixa 2023 até o ano atual do site da B3
    python -m scripts.precos_b3 COTAHIST_A2024.ZIP   # ou usa arquivos já baixados (um ou mais)

Os arquivos ficam em: https://www.b3.com.br > Market Data e Índices > Séries Históricas (cotações históricas, anual).
Cada arquivo anual tem algumas dezenas de MB; o download pode demorar.

O que o script grava:
    PETZ3.SA   Petz, até o fim da negociação (dez/2025)
    AUAU3.SA   Grupo Petz Cobasi, desde jan/2026
    BOVA11.SA  ETF que replica o Ibovespa. O índice em si não está no COTAHIST; o app usa o BOVA11
               como aproximação do Ibovespa se o Yahoo Finance não devolver o ^BVSP.

Atenção: o COTAHIST traz o preço de fechamento sem ajuste por dividendos (o Yahoo ajusta). Num dia de
dividendo a ação cai pelo valor pago, o que pode aparecer como retorno anormal negativo naquele dia.
Depois de gerar, façam commit de data/raw/precos.csv: é ele que o Streamlit Cloud vai usar.
"""
import io
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

CODIGOS = {"PETZ3": "PETZ3.SA", "AUAU3": "AUAU3.SA", "BOVA11": "BOVA11.SA"}
URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP"
DESTINO = Path(__file__).resolve().parents[1] / "data" / "raw" / "precos.csv"


def ler_cotahist(conteudo_zip):
    """Lê um ZIP do COTAHIST e devolve as linhas dos códigos de interesse.
    Layout oficial (posições contadas a partir de 1): tipo de registro 1-2, data 3-10, código BDI 11-12,
    código de negociação 13-24, preço de fechamento 109-121 (com 2 casas decimais implícitas)."""
    linhas = []
    with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
        for nome in z.namelist():
            with z.open(nome) as arquivo:
                for bruta in arquivo:
                    if bruta[:2] != b"01":                     # 00 = cabeçalho, 99 = rodapé
                        continue
                    codigo = bruta[12:24].decode("latin-1").strip()
                    if codigo not in CODIGOS or bruta[10:12] != b"02":   # 02 = lote padrão
                        continue
                    linhas.append({
                        "data": pd.to_datetime(bruta[2:10].decode(), format="%Y%m%d").date(),
                        "ticker": CODIGOS[codigo],
                        "fechamento": int(bruta[108:121]) / 100,
                    })
    return linhas


def main(arquivos):
    if arquivos:
        conteudos = [(str(a), Path(a).read_bytes()) for a in arquivos]
    else:
        conteudos = []
        for ano in range(2023, date.today().year + 1):
            print(f"Baixando COTAHIST {ano}...")
            resposta = requests.get(URL.format(ano=ano), timeout=300, headers={"User-Agent": "Mozilla/5.0"})
            resposta.raise_for_status()
            conteudos.append((f"COTAHIST_A{ano}", resposta.content))

    linhas = []
    for nome, conteudo in conteudos:
        novas = ler_cotahist(conteudo)
        print(f"{nome}: {len(novas)} cotações encontradas")
        linhas += novas
    if not linhas:
        sys.exit("Nenhuma cotação de PETZ3, AUAU3 ou BOVA11 encontrada nos arquivos.")

    tabela = pd.DataFrame(linhas).drop_duplicates(["data", "ticker"]).sort_values(["ticker", "data"])
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(DESTINO, index=False)
    for ticker, grupo in tabela.groupby("ticker"):
        print(f"{ticker}: {len(grupo)} pregões, de {grupo['data'].min()} a {grupo['data'].max()}")
    print(f"Gravado em {DESTINO}")


if __name__ == "__main__":
    main(sys.argv[1:])