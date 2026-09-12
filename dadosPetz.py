# %%
import io
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
# %%
def extrair_petz_com_bs4():
    url_site = "https://ri.petzcobasi.com.br/informacoes-financeiras/planilha-interativa/"
    
    # 1. Usamos o Playwright apenas para carregar o JavaScript e mudar o ano
    with sync_playwright() as p:
        print("Abrindo o navegador em segundo plano...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Acessando o site de RI da PetzCobasi...")
        page.goto(url_site, wait_until="networkidle")
        
        # Seleciona o ano de 2025 no dropdown HTML que você mapeou
        print("Selecionando o ano de 2025...")
        page.select_option("select#yearSelect", value="2025")
        
        # Pausa de 3 segundos para dar tempo ao JavaScript do site gerar a tabela_2 na tela
        page.wait_for_timeout(3000)
        
        # Captura o HTML completo já modificado e renderizado pelo navegador
        html_renderizado = page.content()
        browser.close()
        
    print("Navegador fechado. Iniciando análise do HTML com BeautifulSoup...")
    
    # 2. Alimentamos o BeautifulSoup com o HTML capturado
    soup = BeautifulSoup(html_renderizado, 'html.parser')
    
    # Busca a tabela específica que você nos enviou pelo ID
    tabela = soup.find('table', id='tabela_2')
    if not tabela:
        raise Exception("Erro: A tabela 'tabela_2' não foi encontrada no HTML renderizado. Verifique se o ano possui dados disponíveis.")
        
    # Procura pelo link (<a>) que possui o texto da Petz dentro da tabela_2
    link_elemento = None
    for link in tabela.find_all('a', href=True):
        if "[Petz]" in link.get_text():
            link_elemento = link
            break
            
    if not link_elemento:
        raise Exception("Erro: O link contendo '[Petz]' não foi encontrado dentro da tabela_2.")
        
    url_planilha = link_elemento['href']
    print(f"Link da planilha localizado com sucesso: {url_planilha}")
    
    # 3. Faz o download do arquivo diretamente para a memória RAM por requisição HTTP
    print("Baixando os dados do Excel diretamente para a memória...")
    headers = {"User-Agent": "Mozilla/5.0"}
    resposta_excel = requests.get(url_planilha, headers=headers)
    
    # 4. Processa os bytes do arquivo Excel usando o Pandas
    print("Carregando tabelas no Pandas...")
    bytes_io = io.BytesIO(resposta_excel.content)
    
    # O sheet_name=None força o Pandas a ler TODAS as abas internas do arquivo Excel
    todas_as_abas = pd.read_excel(bytes_io, sheet_name=None)
    lista_abas = list(todas_as_abas.keys())
    dfDRE = todas_as_abas[lista_abas[2]]
    dfRecon = todas_as_abas[lista_abas[4]]
    dfBP = todas_as_abas[lista_abas[6]]
    dfDFC = todas_as_abas[lista_abas[8]]
    dfDO = todas_as_abas[lista_abas[9]]
    return todas_as_abas, dfDRE, dfRecon, dfBP, dfDFC, dfDO

if __name__ == "__main__":
    try:
        dados_abas = extrair_petz_com_bs4()
        lista_abas = list(dados_abas.keys())
        print(f"Abas carregadas na memória RAM: {lista_abas}")
        
        # Exibe as primeiras 5 linhas da primeira aba como teste de validação dos dados
        if lista_abas:
            primeira_aba = lista_abas[0]
            print(f"\n--- Visualizando cabeçalho da aba: {primeira_aba} ---")
            print(dados_abas[primeira_aba].head(5))
            
    except Exception as e:
        print(f"\n❌ Falha durante o processo de raspagem: {e}")


