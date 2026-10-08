import asyncio
import io
import re
import unicodedata
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def normalizar(texto):
    """minúsculas e sem acentos (fusão -> fusao)"""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


# A página tem uma <div id="tableN"> por empresa, com um título e uma <table id="tabela_N">.
# Fallback pelo id caso o título não seja reconhecido (ordem: Grupo, Petz, Cobasi).
EMPRESA_POR_TABELA = {"tabela_1": "Fusão", "tabela_2": "Petz", "tabela_3": "Cobasi"}


def empresa_da_tabela(tabela):
    """Descobre a empresa pelo título da seção; se não achar, pelo id da tabela."""
    secao = tabela.find_parent("div", id=re.compile(r"^table\d+$"))
    cabecalho = secao.select_one(".accordion__item__header") if secao else None
    titulo = normalizar(cabecalho.get_text(strip=True)) if cabecalho else ""
    if "grupo" in titulo or ("petz" in titulo and "cobasi" in titulo):
        return "Fusão"
    if "cobasi" in titulo:
        return "Cobasi"
    if "petz" in titulo:
        return "Petz"
    return EMPRESA_POR_TABELA.get(tabela.get("id"))


# 2. MOTOR DE DOWNLOAD (CAPTURA AS PLANILHAS DIRETAMENTE DO SITE)
async def extrair_planilhas_por_ano():
    url_site = "https://ri.petzcobasi.com.br/informacoes-financeiras/planilha-interativa/"
    alvos = ("Petz", "Cobasi", "Fusão")
    links_encontrados = {}
    textos_vistos = set()  # diagnóstico: todos os links de planilha que o site expôs

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url_site, wait_until="networkidle")

        dropdown_contexto = page
        if not await page.locator("select#yearSelect").count():
            for frame in page.frames:
                if "mziq" in frame.url or await frame.locator("select#yearSelect").count():
                    dropdown_contexto = frame
                    break

        await dropdown_contexto.locator("select#yearSelect").wait_for(state="attached", timeout=10000)
        anos = await dropdown_contexto.locator("select#yearSelect").evaluate(
            "select => Array.from(select.options).map(opt => opt.value)"
        )
        anos_validos = sorted([ano for ano in anos if ano.strip().isdigit()], reverse=True)

        for ano in anos_validos:
            if len(links_encontrados) == len(alvos):
                break
            await dropdown_contexto.select_option("select#yearSelect", value=ano)
            await page.wait_for_timeout(3500)

            soup = BeautifulSoup(await dropdown_contexto.content(), "html.parser")
            for tabela in soup.find_all("table", id=re.compile(r"^tabela_\d+$")):
                nome = empresa_da_tabela(tabela)
                links = [
                    a for a in tabela.find_all("a", href=True)
                    if not a["href"].startswith(("#", "javascript"))
                ]
                for a in links:
                    textos_vistos.add(f"{ano} | {tabela.get('id')} | {nome} | {a.get_text(strip=True)}")
                if nome and nome not in links_encontrados and links:
                    links_encontrados[nome] = urljoin(url_site, links[0]["href"])

        await browser.close()

    dados_empresas = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    for empresa, url_planilha in links_encontrados.items():
        try:
            resposta = requests.get(url_planilha, headers=headers, timeout=30)
            resposta.raise_for_status()
            dados_empresas[empresa] = pd.read_excel(io.BytesIO(resposta.content), sheet_name=None)
        except Exception as e:
            print(f"Erro ao ler {empresa}: {e}")
    return dados_empresas


# 3. MOTOR DE LIMPEZA E TRADUÇÃO IFRS
def limpar_planilha_universal(df_bruto, frequencia="trimestral"):
    if df_bruto is None:
        return None
    df = df_bruto.copy()

    df.loc[-1] = df.columns.tolist()
    df.index = df.index + 1
    df = df.sort_index()
    df.columns = range(df.shape[1])

    linha_cabecalho = None
    for idx, row in df.iterrows():
        if any(isinstance(val, str) and re.search(r"^[1-4]T\d{2}|^20\d{2}", str(val).strip()) for val in row):
            linha_cabecalho = idx
            break

    if linha_cabecalho is None:
        return None

    df.columns = df.iloc[linha_cabecalho]
    df = df.iloc[linha_cabecalho + 1:].reset_index(drop=True)

    colunas_alvo, idx_primeira_data = [], -1
    for i, col in enumerate(df.columns):
        col_str = str(col).strip()
        match = (
            re.search(r"^[1-4]T\d{2}", col_str)
            if frequencia == "trimestral"
            else re.search(r"^20\d{2}(?:\.0)?$", col_str)
        )
        if match:
            colunas_alvo.append(col)
        if idx_primeira_data == -1 and re.search(r"^[1-4]T\d{2}|^20\d{2}", col_str):
            idx_primeira_data = i

    colunas_texto = [df.columns[i] for i in range(idx_primeira_data) if df.iloc[:, i].notna().any()]
    if len(colunas_texto) >= 2:
        df = df.rename(columns={colunas_texto[0]: "Conta_PT", colunas_texto[1]: "Conta_EN"})
    elif len(colunas_texto) == 1:
        df = df.rename(columns={colunas_texto[0]: "Conta_PT"})
        df["Conta_EN"] = df["Conta_PT"]
    else:
        return None

    colunas_dados = df[colunas_alvo]
    dados_numericos = colunas_dados.apply(pd.to_numeric, errors="coerce")
    eh_divisao = dados_numericos.isna().all(axis=1) & df["Conta_PT"].notna()

    df["Grupo_Pai"] = None
    df.loc[eh_divisao, "Grupo_Pai"] = df["Conta_PT"]
    df["Grupo_Pai"] = df["Grupo_Pai"].ffill().fillna("Principal")

    df_limpo = df[~eh_divisao].dropna(subset=["Conta_PT"]).copy()

    renames = {}
    for c in colunas_alvo:
        c_str = str(c).strip()
        if frequencia == "anual":
            renames[c] = c_str.replace(".0", "")
        else:
            match = re.search(r"^([1-4]T\d{2})", c_str)
            if match:
                renames[c] = match.group(1)

    df_limpo = df_limpo.rename(columns=renames)
    colunas_alvo_limpas = list(dict.fromkeys([renames.get(c, c) for c in colunas_alvo]))
    return df_limpo[["Grupo_Pai", "Conta_PT", "Conta_EN"] + colunas_alvo_limpas]


# 4. MOTOR DE ANÁLISE DOS 4 PILARES
def montar_modelo_analitico_trimestral(dados_da_empresa):
    dre = limpar_planilha_universal(dados_da_empresa.get("DRE (IAS17)"), "trimestral")
    recon = limpar_planilha_universal(dados_da_empresa.get("Recon. EBITDA"), "trimestral")
    bp = limpar_planilha_universal(dados_da_empresa.get("BP (IAS17)"), "trimestral")
    dfc = limpar_planilha_universal(dados_da_empresa.get("DFC (IAS17)"), "trimestral")
    ops = limpar_planilha_universal(dados_da_empresa.get("Dados Operacionais"), "trimestral")

    def pescar_valores(df, termo_busca_en, regex=False, ocorrencia=0):
        if df is None or "Conta_EN" not in df.columns:
            return pd.Series(dtype=float)
        linha = df[df["Conta_EN"].str.contains(termo_busca_en, case=False, na=False, regex=regex)]
        if not linha.empty and len(linha) > ocorrencia:
            colunas_datas = [c for c in df.columns if c not in ["Grupo_Pai", "Conta_PT", "Conta_EN"]]
            return pd.to_numeric(linha.iloc[ocorrencia][colunas_datas], errors="coerce").fillna(0)
        return pd.Series(dtype=float)

    analise = pd.DataFrame()
    analise["Receita_Bruta"] = pescar_valores(dre, "Gross Revenue")
    analise["Receita_Liquida"] = pescar_valores(dre, "Net Revenue|Net Sales", regex=True)
    analise["EBITDA_Ajustado"] = pescar_valores(recon, "Adjusted EBITDA")
    analise["Lucro_Liquido"] = pescar_valores(dre, "Net Income")

    analise["Caixa_Equivalentes"] = pescar_valores(bp, "Cash and Cash Equivalents")
    analise["Aplicacoes_Financeiras"] = pescar_valores(bp, "Investments")
    analise["Emprestimos_CP"] = pescar_valores(bp, "Loans, Financing", ocorrencia=0)
    analise["Emprestimos_LP"] = pescar_valores(bp, "Loans, Financing", ocorrencia=-1)
    analise["Estoques"] = pescar_valores(bp, "Inventor")

    analise["Fluxo_Caixa_Operacional"] = pescar_valores(dfc, "Operating Activities")

    analise["SSS_Percentual"] = pescar_valores(ops, "Same Store Sales")
    analise["Penetracao_Digital"] = pescar_valores(ops, "Digital Penetration")

    analise["Margem_EBITDA"] = (analise["EBITDA_Ajustado"] / analise["Receita_Liquida"]).fillna(0)
    analise["Divida_Bruta"] = analise["Emprestimos_CP"] + analise["Emprestimos_LP"]
    analise["Caixa_Total"] = analise["Caixa_Equivalentes"] + analise["Aplicacoes_Financeiras"]
    analise["Divida_Liquida"] = analise["Divida_Bruta"] - analise["Caixa_Total"]

    return analise.dropna(how="all").rename_axis("Trimestre")


# 5. EXECUÇÃO MESTRE
async def main():
    print("1/2 Iniciando extração dos dados direto do RI...")
    dados_gerais = await extrair_planilhas_por_ano()

    faltando = [e for e in ("Petz", "Cobasi", "Fusão") if e not in dados_gerais]
    if faltando:
        print(f"Planilhas não carregadas: {faltando}. Seguindo com: {list(dados_gerais)}")
    if not dados_gerais:
        raise RuntimeError("Nenhuma planilha foi carregada.")

    print("2/2 Construindo modelos analíticos (IFRS/IAS17)...")
    analises = {
        nome: montar_modelo_analitico_trimestral(dados)
        for nome, dados in dados_gerais.items()
    }

    return analises


_cache = None


def carregar_analises():
    """Versão síncrona para usar em outros módulos. O scraping roda uma única vez."""
    global _cache
    if _cache is None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            _cache = asyncio.run(main())
        else:
            # Já existe um loop rodando (Jupyter / Interactive Window do VS Code):
            # roda em outra thread, que tem o próprio loop.
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=1) as executor:
                _cache = executor.submit(lambda: asyncio.run(main())).result()
    return _cache


def __getattr__(nome):
    # Permite `from data.dadosPetz import analises` sem rodar o scraping no import do módulo:
    # ele só roda quando `analises` é realmente pedido.
    if nome == "analises":
        return carregar_analises()
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")


if __name__ == "__main__":
    carregar_analises()