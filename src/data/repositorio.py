"""De onde vêm os dados do app.

O app lê a Planilha Interativa do grupo salva em data/raw/ (a mais recente pelo nome).
Ela pode chegar de três jeitos:
1. Versionada no Git (é o que vai para a apresentação: não depende do site do RI).
2. Enviada pela barra lateral do app.
3. Baixada do RI pelo scraping (botão "Buscar no RI" ou scripts/atualizar_dados.py).
"""
from datetime import datetime
from pathlib import Path

from src.analysis.indicadores import (calcular_indicadores, comparar_antes_depois, expansao_anual, resumo_tendencia,
                                      sobreposicao_cidades, sobreposicao_resumo, tendencia_sem_fusao)
from src.data.dadosPetz import ler_planilha_grupo

PASTA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"


def planilha_atual():
    """Caminho da planilha mais recente em data/raw (ou None)."""
    arquivos = sorted(PASTA_RAW.glob("*.xlsx"), key=lambda p: (p.stat().st_mtime, p.name))
    return arquivos[-1] if arquivos else None


def salvar_planilha(conteudo, nome=None):
    """Grava os bytes de uma planilha em data/raw e devolve o caminho."""
    PASTA_RAW.mkdir(parents=True, exist_ok=True)
    nome = nome or f"planilha_interativa_{datetime.now():%Y%m%d_%H%M}.xlsx"
    caminho = PASTA_RAW / nome
    caminho.write_bytes(conteudo)
    return caminho


def atualizar_do_ri():
    """Roda o scraping (Playwright), valida e grava a planilha do grupo."""
    from src.data import dadosPetz  # import tardio: Playwright só é carregado se precisar
    conteudo = dadosPetz.carregar_planilha_do_ri()
    dados = ler_planilha_grupo(conteudo)  # valida antes de salvar
    if dados["trimestral"].empty:
        raise RuntimeError("A planilha baixada não tem os trimestres esperados.")
    return salvar_planilha(conteudo)


def montar_base(origem):
    """Lê a planilha e calcula tudo que as páginas usam."""
    dados = ler_planilha_grupo(origem)
    ind = calcular_indicadores(dados["trimestral"])
    tendencias = tendencia_sem_fusao(ind)
    comparacao, antes, depois = comparar_antes_depois(ind)
    return {
        "contas": dados["trimestral"],
        "indicadores": ind,
        "comparacao": comparacao,
        "antes": antes,
        "depois": depois,
        "tendencias": tendencias,
        "resumo_tendencia": resumo_tendencia(ind, tendencias),
        "anual": expansao_anual(ind),
        "lojas": dados["lojas"],
        "cidades": sobreposicao_cidades(dados["lojas"]),
        "sobreposicao": sobreposicao_resumo(dados["lojas"]),
        "ausentes": dados["ausentes"],
    }
