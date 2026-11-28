"""Linha do tempo da fusão. Datas conferidas em notícias públicas (InfoMoney, Suno, Genial, Agência Brasil,
Times Brasil, Forbes); confirmem nos fatos relevantes do RI antes de entregar."""
import pandas as pd

# Primeiro trimestre com o grupo já combinado (conclusão em 02/01/2026)
TRIMESTRE_FUSAO = pd.Period("2026Q1", freq="Q")

# estudo_evento: entra no estudo de evento da ação PETZ3 (aba Bolsa).
# A data é a do fato relevante; se foi divulgado fora do pregão, o primeiro pregão seguinte é o "dia 0".
EVENTOS = [
    {"data": "2024-04-19", "rotulo": "abr/24", "titulo": "Anúncio da fusão", "estudo_evento": True,
     "texto": "Petz e Cobasi assinam um memorando de entendimentos para combinar os negócios."},
    {"data": "2024-08-16", "rotulo": "ago/24", "titulo": "Acordo assinado", "estudo_evento": True,
     "texto": "As empresas assinam o acordo de associação que define os termos da fusão."},
    {"data": "2025-02-07", "rotulo": "fev/25", "titulo": "Notificação ao Cade", "estudo_evento": False,
     "texto": "Começa a análise concorrencial da operação."},
    {"data": "2025-03-14", "rotulo": "mar/25", "titulo": "Aprovação dos acionistas", "estudo_evento": True,
     "texto": "Assembleia da Petz aprova a incorporação de ações."},
    {"data": "2025-06-03", "rotulo": "jun/25", "titulo": "Aval da Superintendência", "estudo_evento": True,
     "texto": "Área técnica do Cade aprova sem restrições; a Petlove recorre."},
    {"data": "2025-12-10", "rotulo": "dez/25", "titulo": "Tribunal do Cade aprova", "estudo_evento": True,
     "texto": "Aprovação condicionada à venda de 26 lojas em São Paulo (cerca de 3,3% da receita combinada)."},
    {"data": "2026-01-02", "rotulo": "jan/26", "titulo": "Fusão concluída", "estudo_evento": False,
     "texto": "O grupo passa a ser negociado como AUAU3; acionistas da Petz ficam com 52,6% e recebem R$ 320,8 mi em dinheiro."},
]

# Eventos marcados nos gráficos trimestrais (os demais aparecem só na página inicial e na aba Bolsa)
EVENTOS_NOS_GRAFICOS = {"Anúncio da fusão", "Fusão concluída"}