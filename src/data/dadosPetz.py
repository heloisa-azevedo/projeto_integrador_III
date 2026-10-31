import asyncio
import io
import re
import os
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


# 1. LANÇADOR DE NAVEGADOR (funciona na nuvem e no Windows)
async def lancar_navegador(p):
    """
    - Streamlit Cloud (Linux): usa o Chromium instalado pelo packages.txt.
    - Windows/local: tenta Edge, depois Chrome, depois o Chromium do Playwright
      (o último só funciona se `python -m playwright install chromium` tiver sido executado).
    """
    caminho_chromium = "/usr/bin/chromium"
    if os.path.exists(caminho_chromium):
        return await p.chromium.launch(
            headless=True,
            executable_path=caminho_chromium,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

    ultimo_erro = None
    for canal in ("msedge", "chrome", None):
        try:
            if canal:
                return await p.chromium.launch(headless=True, channel=canal)
            return await p.chromium.launch(headless=True)
        except Exception as e:
            ultimo_erro = e
    raise ultimo_erro


# 2. MOTOR DE DOWNLOAD (CAPTURA AS PLANILHAS DIRETAMENTE DO SITE)
URL_SITE = "https://ri.petzcobasi.com.br/informacoes-financeiras/planilha-interativa/"


async def encontrar_links_planilhas():
    """Abre a página do RI, percorre os anos do seletor e devolve {empresa: url da planilha}."""
    alvos = ("Petz", "Cobasi", "Fusão")
    links_encontrados = {}

    async with async_playwright() as p:
        browser = await lancar_navegador(p)
        page = await browser.new_page()
        await page.goto(URL_SITE, wait_until="networkidle")

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
                if nome and nome not in links_encontrados and links:
                    links_encontrados[nome] = urljoin(URL_SITE, links[0]["href"])

        await browser.close()
    return links_encontrados


def baixar_planilha(url_planilha):
    """Baixa uma planilha e devolve os bytes do .xlsx."""
    resposta = requests.get(url_planilha, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resposta.raise_for_status()
    return resposta.content


async def extrair_planilhas_por_ano():
    """Mantida por compatibilidade: devolve {empresa: {aba: DataFrame}}."""
    dados_empresas = {}
    for empresa, url_planilha in (await encontrar_links_planilhas()).items():
        try:
            dados_empresas[empresa] = pd.read_excel(io.BytesIO(baixar_planilha(url_planilha)), sheet_name=None)
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


# 4. EXTRAÇÃO DAS CONTAS DA PLANILHA DO GRUPO
# A planilha do Grupo Petz Cobasi tem uma única coluna de nomes, em português.
# De 1T23 a 4T25 os trimestres são pro forma ("1T23 PF*"); depois, o grupo combinado.
# Padrões começam com ^ para não confundir, por exemplo, "Lucro Líquido" com "Lucro Líquido Ajustado".
# Formato: coluna destino -> (aba, padrão, ocorrência)
CONTAS = {
    "receita_bruta":           ("DRE (IAS17)", r"^Receita Bruta de Vendas", 0),
    "receita_bruta_petz":      ("DRE (IAS17)", r"^Receita Bruta Petz", 0),
    "receita_bruta_cobasi":    ("DRE (IAS17)", r"^Receita Bruta Cobasi", 0),
    "receita_liquida":         ("DRE (IAS17)", r"^Receita L[ií]quida", 0),
    "cmv":                     ("DRE (IAS17)", r"^Custo das Mercadorias", 0),
    "lucro_bruto":             ("DRE (IAS17)", r"^Lucro Bruto", 0),
    "despesas_vendas":         ("DRE (IAS17)", r"^Com Vendas", 0),
    "despesas_ga":             ("DRE (IAS17)", r"^Gerais", 0),
    "ebitda_ajustado":         ("DRE (IAS17)", r"^EBITDA Ajustado", 0),
    "lucro_liquido":           ("DRE (IAS17)", r"^Lucro L[ií]quido do Exerc[ií]cio$", 0),
    "caixa":                   ("BP (IAS17)", r"^Caixa e Equivalentes", 0),
    "aplicacoes_cp":           ("BP (IAS17)", r"^Aplica[cç][oõ]es Financeiras", 0),
    "aplicacoes_lp":           ("BP (IAS17)", r"^Aplica[cç][oõ]es Financeiras", 1),
    "contas_receber":          ("BP (IAS17)", r"^Contas a Receber", 0),
    "estoques":                ("BP (IAS17)", r"^Estoques", 0),
    "fornecedores":            ("BP (IAS17)", r"^Fornecedores$", 0),
    "emprestimos_cp":          ("BP (IAS17)", r"^Empr[eé]stimos", 0),
    "emprestimos_lp":          ("BP (IAS17)", r"^Empr[eé]stimos", 1),
    "fluxo_caixa_operacional": ("DFC (IAS17)", r"^Fluxo de Caixa Operacional", 0),
    "lojas_petz":              ("Dados Operacionais", r"^N[uú]mero de Lojas Petz", 0),
    "lojas_cobasi":            ("Dados Operacionais", r"^N[uú]mero de Lojas Cobasi", 0),
    "inauguracoes_petz":       ("Dados Operacionais", r"^N[uú]mero de Inaugura[cç][oõ]es Petz", 0),
    "inauguracoes_cobasi":     ("Dados Operacionais", r"^N[uú]mero de Inaugura[cç][oõ]es Cobasi", 0),
    "area_petz_m2":            ("Dados Operacionais", r"^[ÁA]rea de Lojas Petz", 0),
    "area_cobasi_m2":          ("Dados Operacionais", r"^[ÁA]rea de Lojas Cobasi", 0),
    "sss_petz":                ("Dados Operacionais", r"^Same Store Sales.*Petz", 0),
    "sss_cobasi":              ("Dados Operacionais", r"^Same Store Sales.*Cobasi", 0),
    "sss_consolidado":         ("Dados Operacionais", r"^Same Store Sales.*Consolidado", 0),
    "penetracao_digital":      ("Dados Operacionais", r"^Penetra[cç][aã]o Digital", 0),
    "capex_lojas_novas":       ("Investimentos | CAPEX", r"^Novas Lojas", 0),
    "capex_reformas":          ("Investimentos | CAPEX", r"^Reformas", 0),
    "capex_tecnologia":        ("Investimentos | CAPEX", r"^Tecnologia", 0),
    "capex_total":             ("Investimentos | CAPEX", r"^Investimentos Totais", 0),
}

COLUNAS_META = ["Grupo_Pai", "Conta_PT", "Conta_EN"]
TRIMESTRE_FUSAO = pd.Period("2026Q1", freq="Q")


def trimestre_para_periodo(rotulo):
    """'1T24' -> Period('2024Q1'). Texto não ordena trimestres corretamente."""
    rotulo = str(rotulo).strip()
    return pd.Period(f"20{rotulo[2:4]}Q{rotulo[0]}", freq="Q")


def pescar_valores(df, padrao, ocorrencia=0):
    """Devolve a linha da conta como série numérica indexada por trimestre.
    Valores ausentes ficam NaN (antes viravam 0 e criavam quedas falsas nos gráficos)."""
    if df is None:
        return pd.Series(dtype=float)
    nomes = df["Conta_PT"].astype(str).str.replace("\xa0", " ").str.strip()
    linhas = df[nomes.str.contains(padrao, case=False, na=False, regex=True)]
    if len(linhas) <= ocorrencia:
        return pd.Series(dtype=float)
    colunas_datas = [c for c in df.columns if c not in COLUNAS_META]
    serie = pd.to_numeric(linhas.iloc[ocorrencia][colunas_datas], errors="coerce")
    serie.index = [trimestre_para_periodo(c) for c in serie.index]
    return serie[~serie.index.duplicated()]


def montar_trimestral(abas):
    """Recebe {aba: DataFrame} da planilha do grupo e devolve uma tabela por trimestre
    com as contas brutas (R$ mil) e a lista de contas que não foram encontradas."""
    limpas = {}
    colunas, ausentes = {}, []
    for destino, (aba, padrao, ocorrencia) in CONTAS.items():
        if aba not in limpas:
            limpas[aba] = limpar_planilha_universal(abas.get(aba), "trimestral")
        serie = pescar_valores(limpas[aba], padrao, ocorrencia)
        if serie.dropna().empty:
            ausentes.append(f"{destino} ({aba})")
        colunas[destino] = serie
    # pd.DataFrame(dict) une os índices de todas as séries
    tabela = pd.DataFrame(colunas).sort_index().dropna(how="all")
    tabela.index.name = "Trimestre"
    tabela.insert(0, "pro_forma", tabela.index < TRIMESTRE_FUSAO)
    return tabela, ausentes


# Nome normalizado da coluna na planilha -> nome usado no app
COLUNAS_LOJAS = {
    "bandeira": "bandeira", "marca": "bandeira", "loja": "codigo", "codigo": "codigo", "nome da loja": "nome",
    "inauguracao": "inauguracao", "data de inauguracao": "inauguracao", "trim. inaug.": "trimestre_inauguracao",
    "area (m2)": "area_m2", "area (m²)": "area_m2", "area": "area_m2", "cidade": "cidade", "municipio": "cidade",
    "uf": "uf", "estado": "uf", "regiao": "regiao",
}


def _aba(abas, nome):
    """Encontra a aba ignorando maiúsculas, acentos e espaços nas pontas."""
    alvo = normalizar(nome).strip()
    for chave, df in abas.items():
        if normalizar(str(chave)).strip() == alvo:
            return df
    return None


def montar_lojas(abas):
    """Aba 'Lista de Lojas': uma linha por loja (sem endereço).
    Tolera cabeçalho fora da primeira linha e variações nos nomes das colunas.
    Se a aba não existir ou não tiver bandeira e cidade, devolve uma tabela vazia
    (a análise de sobreposição fica indisponível, o resto do app funciona)."""
    vazia = pd.DataFrame(columns=["bandeira", "cidade", "uf"])
    bruto = _aba(abas, "Lista de Lojas")
    if bruto is None or bruto.empty:
        return vazia

    # o cabeçalho pode não estar na 1ª linha: procura a linha que tem "Bandeira" e "Cidade"
    tabela = pd.concat([bruto.columns.to_frame().T.set_axis(bruto.columns, axis=1), bruto], ignore_index=True)
    linha_cab = None
    for i, linha in tabela.head(15).iterrows():
        nomes = {normalizar(str(v)).strip() for v in linha if pd.notna(v)}
        if {"bandeira", "cidade"} <= nomes or {"marca", "cidade"} <= nomes:
            linha_cab = i
            break
    if linha_cab is None:
        return vazia

    cabecalho = [COLUNAS_LOJAS.get(normalizar(str(v)).strip(), normalizar(str(v)).strip()) for v in tabela.iloc[linha_cab]]
    lojas = tabela.iloc[linha_cab + 1:].copy()
    lojas.columns = cabecalho
    lojas = lojas.loc[:, ~lojas.columns.duplicated()]
    lojas = lojas.dropna(subset=["bandeira", "cidade"])
    lojas["bandeira"] = lojas["bandeira"].astype(str).str.strip()
    lojas["cidade"] = lojas["cidade"].astype(str).str.strip()
    lojas["uf"] = lojas["uf"].astype(str).str.strip().str.upper() if "uf" in lojas.columns else ""
    if "codigo" in lojas.columns:  # mistura números (Cobasi) e textos (Petz)
        lojas["codigo"] = lojas["codigo"].astype(str)
    if "inauguracao" in lojas.columns:
        lojas["inauguracao"] = pd.to_datetime(lojas["inauguracao"], errors="coerce").dt.date
    if "area_m2" in lojas.columns:
        lojas["area_m2"] = pd.to_numeric(lojas["area_m2"], errors="coerce")
    colunas = [c for c in ["bandeira", "codigo", "nome", "inauguracao", "trimestre_inauguracao", "area_m2", "cidade", "uf", "regiao"]
               if c in lojas.columns]
    return lojas[colunas].reset_index(drop=True)


def ler_planilha_grupo(origem):
    """origem: caminho do .xlsx, bytes ou arquivo enviado pelo Streamlit."""
    if isinstance(origem, (bytes, bytearray)):
        origem = io.BytesIO(origem)
    abas = pd.read_excel(origem, sheet_name=None)
    trimestral, ausentes = montar_trimestral(abas)
    lojas = montar_lojas(abas)
    if lojas.empty:
        ausentes.append("lista de lojas (aba Lista de Lojas)")
    return {"trimestral": trimestral, "lojas": lojas, "ausentes": ausentes}


# 5. EXECUÇÃO MESTRE
async def baixar_planilha_grupo():
    """Encontra no RI a planilha do grupo combinado e devolve seus bytes."""
    links = await encontrar_links_planilhas()
    if "Fusão" not in links:
        raise RuntimeError(f"Planilha do grupo não encontrada no RI. Links achados: {list(links)}")
    return baixar_planilha(links["Fusão"])


def carregar_planilha_do_ri():
    """Versão síncrona para usar em outros módulos (o Streamlit não roda async diretamente)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(baixar_planilha_grupo())
    else:
        # Já existe um loop rodando (Jupyter / Interactive Window do VS Code):
        # roda em outra thread, que tem o próprio loop.
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(baixar_planilha_grupo())).result()


if __name__ == "__main__":
    dados = ler_planilha_grupo(carregar_planilha_do_ri())
    print(dados["trimestral"].tail())
