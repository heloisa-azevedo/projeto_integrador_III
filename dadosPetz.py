# %%
import io
import re
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import nest_asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
nest_asyncio.apply()

# %%
# 2. MOTOR DE DOWNLOAD (CAPTURA AS PLANILHAS DIRETAMENTE DO SITE)
async def extrair_planilhas_por_ano():
    url_site = "https://ri.petzcobasi.com.br/informacoes-financeiras/planilha-interativa/"
    alvos = {"Petz": "[petz]", "Cobasi": "[cobasi]", "Fusão": "[grupo]"}
    links_encontrados = {}

    async with async_playwright() as p:z
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
        anos = await dropdown_contexto.locator("select#yearSelect").evaluate("select => Array.from(select.options).map(opt => opt.value)")
        anos_validos = sorted([ano for ano in anos if ano.strip().isdigit()], reverse=True)

        for ano in anos_validos:
            if len(links_encontrados) == len(alvos): break
            await dropdown_contexto.select_option("select#yearSelect", value=ano)
            await page.wait_for_timeout(3500)

            soup = BeautifulSoup(await dropdown_contexto.content(), 'html.parser')
            for link in soup.find_all('a', href=True):
                texto_link = link.get_text(strip=True).lower()
                if "planilha" in texto_link and "[" in texto_link:
                    for nome, ident in alvos.items():
                        if ident in texto_link and nome not in links_encontrados:
                            url_final = link['href']
                            if url_final.startswith('/'): url_final = "https://ri.petzcobasi.com.br" + url_final
                            if not url_final.startswith('http'): url_final = "https://ri.petzcobasi.com.br/" + url_final.lstrip('../')
                            links_encontrados[nome] = url_final

        await browser.close()

    dados_empresas = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    for empresa, url_planilha in links_encontrados.items():
        try:
            resposta = requests.get(url_planilha, headers=headers)
            dados_empresas[empresa] = pd.read_excel(io.BytesIO(resposta.content), sheet_name=None)
        except Exception as e:
            print(f"Erro ao ler {empresa}: {e}")
    return dados_empresas


# 3. MOTOR DE LIMPEZA E TRADUÇÃO IFRS
def limpar_planilha_universal(df_bruto, frequencia='trimestral'):
    if df_bruto is None: return None
    df = df_bruto.copy()

    df.loc[-1] = df.columns.tolist()
    df.index = df.index + 1
    df = df.sort_index()
    df.columns = range(df.shape[1])

    linha_cabecalho = None
    for idx, row in df.iterrows():
        if any(isinstance(val, str) and re.search(r'^[1-4]T\d{2}|^20\d{2}', str(val).strip()) for val in row):
            linha_cabecalho = idx
            break

    if linha_cabecalho is None: return None

    df.columns = df.iloc[linha_cabecalho]
    df = df.iloc[linha_cabecalho+1:].reset_index(drop=True)

    colunas_alvo, idx_primeira_data = [], -1
    for i, col in enumerate(df.columns):
        col_str = str(col).strip()
        match = re.search(r'^[1-4]T\d{2}', col_str) if frequencia == 'trimestral' else re.search(r'^20\d{2}(?:\.0)?$', col_str)
        if match:
            colunas_alvo.append(col)
        if idx_primeira_data == -1 and re.search(r'^[1-4]T\d{2}|^20\d{2}', col_str):
            idx_primeira_data = i

    colunas_texto = [df.columns[i] for i in range(idx_primeira_data) if df.iloc[:, i].notna().any()]
    if len(colunas_texto) >= 2:
        df = df.rename(columns={colunas_texto[0]: "Conta_PT", colunas_texto[1]: "Conta_EN"})
    elif len(colunas_texto) == 1:
        df = df.rename(columns={colunas_texto[0]: "Conta_PT"})
        df['Conta_EN'] = df['Conta_PT']
    else: return None

    colunas_dados = df[colunas_alvo]
    dados_numericos = colunas_dados.apply(pd.to_numeric, errors='coerce')
    eh_divisao = dados_numericos.isna().all(axis=1) & df['Conta_PT'].notna()

    df['Grupo_Pai'] = None
    df.loc[eh_divisao, 'Grupo_Pai'] = df['Conta_PT']
    df['Grupo_Pai'] = df['Grupo_Pai'].ffill().fillna("Principal")

    df_limpo = df[~eh_divisao].dropna(subset=['Conta_PT']).copy()

    renames = {}
    for c in colunas_alvo:
        c_str = str(c).strip()
        if frequencia == 'anual': renames[c] = c_str.replace('.0', '')
        else:
            match = re.search(r'^([1-4]T\d{2})', c_str)
            if match: renames[c] = match.group(1)

    df_limpo = df_limpo.rename(columns=renames)
    colunas_alvo_limpas = list(dict.fromkeys([renames.get(c, c) for c in colunas_alvo]))
    return df_limpo[['Grupo_Pai', 'Conta_PT', 'Conta_EN'] + colunas_alvo_limpas]


# 4. MOTOR DE ANÁLISE DOS 4 PILARES
def montar_modelo_analitico_trimestral(dados_da_empresa):
    dre = limpar_planilha_universal(dados_da_empresa.get('DRE (IAS17)'), 'trimestral')
    recon = limpar_planilha_universal(dados_da_empresa.get('Recon. EBITDA'), 'trimestral')
    bp = limpar_planilha_universal(dados_da_empresa.get('BP (IAS17)'), 'trimestral')
    dfc = limpar_planilha_universal(dados_da_empresa.get('DFC (IAS17)'), 'trimestral')
    ops = limpar_planilha_universal(dados_da_empresa.get('Dados Operacionais'), 'trimestral')

    def pescar_valores(df, termo_busca_en, regex=False, ocorrencia=0):
        if df is None or 'Conta_EN' not in df.columns: return pd.Series(dtype=float)
        linha = df[df['Conta_EN'].str.contains(termo_busca_en, case=False, na=False, regex=regex)]
        if not linha.empty and len(linha) > ocorrencia:
            colunas_datas = [c for c in df.columns if c not in ['Grupo_Pai', 'Conta_PT', 'Conta_EN']]
            return pd.to_numeric(linha.iloc[ocorrencia][colunas_datas], errors='coerce').fillna(0)
        return pd.Series(dtype=float)

    analise = pd.DataFrame()
    analise['Receita_Bruta'] = pescar_valores(dre, 'Gross Revenue')
    analise['Receita_Liquida'] = pescar_valores(dre, 'Net Revenue|Net Sales', regex=True)
    analise['EBITDA_Ajustado'] = pescar_valores(recon, 'Adjusted EBITDA')
    analise['Lucro_Liquido'] = pescar_valores(dre, 'Net Income')

    analise['Caixa_Equivalentes'] = pescar_valores(bp, 'Cash and Cash Equivalents')
    analise['Aplicacoes_Financeiras'] = pescar_valores(bp, 'Investments')
    analise['Emprestimos_CP'] = pescar_valores(bp, 'Loans, Financing', ocorrencia=0)
    analise['Emprestimos_LP'] = pescar_valores(bp, 'Loans, Financing', ocorrencia=-1)
    analise['Estoques'] = pescar_valores(bp, 'Inventor')

    analise['Fluxo_Caixa_Operacional'] = pescar_valores(dfc, 'Operating Activities')

    analise['SSS_Percentual'] = pescar_valores(ops, 'Same Store Sales')
    analise['Penetracao_Digital'] = pescar_valores(ops, 'Digital Penetration')

    analise['Margem_EBITDA'] = (analise['EBITDA_Ajustado'] / analise['Receita_Liquida']).fillna(0)
    analise['Divida_Bruta'] = analise['Emprestimos_CP'] + analise['Emprestimos_LP']
    analise['Caixa_Total'] = analise['Caixa_Equivalentes'] + analise['Aplicacoes_Financeiras']
    analise['Divida_Liquida'] = analise['Divida_Bruta'] - analise['Caixa_Total']

    return analise.dropna(how='all').rename_axis('Trimestre')


# 5. EXECUÇÃO MESTRE
try:
    print("🌐 1/2 Iniciando extração dos dados direto do RI...")
    dados_gerais = await extrair_planilhas_por_ano()

    print("🚀 2/2 Construindo modelos analíticos (IFRS/IAS17)...")
    analise_petz_tri = montar_modelo_analitico_trimestral(dados_gerais['Petz'])
    analise_cobasi_tri = montar_modelo_analitico_trimestral(dados_gerais['Cobasi'])
    analise_fusao_tri = montar_modelo_analitico_trimestral(dados_gerais['Fusão'])

    print("\n✅ Concluído com sucesso! \n")

    print("--- VISÃO ANALÍTICA: PETZ (Últimos 6 Trimestres) ---")
    display(analise_petz_tri.tail(6))

    print("\n--- VISÃO ANALÍTICA: COBASI (Últimos 6 Trimestres) ---")
    display(analise_cobasi_tri.tail(6))

    print("\n--- VISÃO ANALÍTICA: FUSÃO (Últimos 6 Trimestres) ---")
    display(analise_fusao_tri.tail(6))

except Exception as e:
    print(f"❌ Erro na execução: {e}")

# %%
# Correlação PETZ
corr_petz = analise_petz_tri.corr(numeric_only=True)
plt.figure(figsize=(20, 18))
sns.heatmap(corr_petz, annot=True, cmap="coolwarm", vmin=-1, vmax=1)

analise_petz_tri.hist(figsize=(15, 13))

plt.show()
# %%
# Correlação Cobasi

corr_cobasi = analise_cobasi_tri.corr(numeric_only=True)
plt.figure(figsize=(20, 18))
sns.heatmap(corr_cobasi, annot=True, cmap="coolwarm", vmin=-1, vmax=1)

analise_cobasi_tri.hist(figsize=(15, 13))

plt.show()
# %%
# Correlação Fusão
#FUSAO
corr_fusao = analise_fusao_tri.corr(numeric_only=True)
plt.figure(figsize=(20, 18))
sns.heatmap(corr_fusao, annot=True, cmap="coolwarm", vmin=-1, vmax=1)

analise_fusao_tri.hist(figsize=(15, 13))

plt.show()