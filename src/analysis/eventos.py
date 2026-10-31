"""Linha do tempo da fusão. Datas conferidas em notícias públicas (Agência Brasil,
Suno, Times Brasil, GiroNews); confirmem nos fatos relevantes do RI antes de entregar."""
import pandas as pd

# Primeiro trimestre com o grupo já combinado (conclusão em 02/01/2026)
TRIMESTRE_FUSAO = pd.Period("2026Q1", freq="Q")

EVENTOS = [
    {"data": "2024-08-15", "rotulo": "ago/24", "titulo": "Anúncio da fusão",
     "texto": "Petz e Cobasi divulgam o acordo para combinar os negócios."},
    {"data": "2025-02-07", "rotulo": "fev/25", "titulo": "Notificação ao Cade",
     "texto": "Começa a análise concorrencial da operação."},
    {"data": "2025-03-14", "rotulo": "mar/25", "titulo": "Aprovação dos acionistas",
     "texto": "Assembleia da Petz aprova a incorporação de ações."},
    {"data": "2025-06-03", "rotulo": "jun/25", "titulo": "Aval da Superintendência",
     "texto": "Área técnica do Cade aprova sem restrições; a Petlove recorre."},
    {"data": "2025-12-10", "rotulo": "dez/25", "titulo": "Tribunal do Cade aprova",
     "texto": "Aprovação condicionada à venda de 26 lojas em São Paulo (cerca de 3,3% da receita combinada)."},
    {"data": "2026-01-02", "rotulo": "jan/26", "titulo": "Fusão concluída",
     "texto": "Ações da Petz são incorporadas; acionistas da Petz ficam com 52,6% e os da Cobasi com 47,4%."},
]

# Eventos marcados nos gráficos (os demais aparecem só na página inicial)
EVENTOS_NOS_GRAFICOS = {"Anúncio da fusão", "Fusão concluída"}
