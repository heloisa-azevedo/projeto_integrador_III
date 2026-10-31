"""Baixa a planilha do grupo no RI e grava em data/raw/.

Uso (na raiz do projeto):
    python -m scripts.atualizar_dados                 # baixa do RI (Playwright)
    python -m scripts.atualizar_dados caminho.xlsx    # importa um arquivo já baixado

Depois, confiram 2 ou 3 números com o release de resultados e façam commit de data/raw/.
"""
import sys
from pathlib import Path

from src.data.dadosPetz import ler_planilha_grupo
from src.data.repositorio import atualizar_do_ri, salvar_planilha

if __name__ == "__main__":
    if len(sys.argv) > 1:
        origem = Path(sys.argv[1])
        caminho = salvar_planilha(origem.read_bytes(), origem.name)
    else:
        caminho = atualizar_do_ri()
    dados = ler_planilha_grupo(caminho)
    t = dados["trimestral"]
    print(f"Planilha salva em {caminho}: {len(t)} trimestres ({t.index.min()} a {t.index.max()}), {len(dados['lojas'])} lojas")
    if dados["ausentes"]:
        print("Contas não encontradas:", ", ".join(dados["ausentes"]))
