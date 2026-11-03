"""Indicadores, comparação antes × depois, tendência sem fusão e sobreposição de lojas.

Os mesmos cálculos do painel interativo, em pandas. Margens são sempre calculadas
sobre as somas das contas, nunca pela média de percentuais.
"""
import numpy as np
import pandas as pd

from src.analysis.eventos import TRIMESTRE_FUSAO

DIAS_TRIMESTRE = 91

# Limiares para considerar uma mudança relevante (ajustem e justifiquem no trabalho)
LIMIAR_PP = 0.005   # 0,5 ponto percentual
LIMIAR_DIAS = 5


def rotulo_trimestre(periodo):
    return f"{periodo.quarter}T{str(periodo.year)[2:]}"


# ---------------------------------------------------------------- indicadores por trimestre
def calcular_indicadores(contas):
    """Contas brutas da planilha (R$ mil) -> indicadores por trimestre (valores em R$ milhões)."""
    if contas is None or contas.empty:
        return pd.DataFrame()
    c = contas.reindex(pd.period_range(contas.index.min(), contas.index.max(), freq="Q"))
    rl, rb, cmv = c["receita_liquida"], c["receita_bruta"], c["cmv"].abs()
    divida = c["emprestimos_cp"] + c["emprestimos_lp"]
    caixa = c[["caixa", "aplicacoes_cp", "aplicacoes_lp"]].sum(axis=1, min_count=1)

    d = pd.DataFrame(index=c.index)
    d.index.name = "Trimestre"
    d["pro_forma"] = c["pro_forma"]
    for col in ["receita_liquida", "lucro_bruto", "ebitda_ajustado", "lucro_liquido", "fluxo_caixa_operacional"]:
        d[col] = c[col] / 1000
    d["receita_bruta_petz"] = c["receita_bruta_petz"] / 1000
    d["receita_bruta_cobasi"] = c["receita_bruta_cobasi"] / 1000
    d["despesas_vendas"] = c["despesas_vendas"].abs() / 1000
    d["despesas_ga"] = c["despesas_ga"].abs() / 1000

    d["margem_bruta"] = c["lucro_bruto"] / rl
    d["margem_ebitda"] = c["ebitda_ajustado"] / rl
    d["margem_liquida"] = c["lucro_liquido"] / rl
    d["despesas_vendas_pct"] = c["despesas_vendas"].abs() / rl
    d["despesas_ga_pct"] = c["despesas_ga"].abs() / rl

    d["prazo_fornecedores"] = c["fornecedores"] / cmv * DIAS_TRIMESTRE
    d["prazo_estoques"] = c["estoques"] / cmv * DIAS_TRIMESTRE
    d["prazo_recebimento"] = c["contas_receber"] / rb * DIAS_TRIMESTRE
    d["ciclo_caixa"] = d["prazo_estoques"] + d["prazo_recebimento"] - d["prazo_fornecedores"]

    d["divida_bruta"] = divida / 1000
    d["caixa_total"] = caixa / 1000
    d["divida_liquida"] = (divida - caixa) / 1000

    for col in ["sss_petz", "sss_cobasi", "sss_consolidado", "penetracao_digital",
                "lojas_petz", "lojas_cobasi", "inauguracoes_petz", "inauguracoes_cobasi"]:
        d[col] = c[col]
    d["lojas_total"] = c["lojas_petz"] + c["lojas_cobasi"]
    d["receita_m2_petz"] = c["receita_bruta_petz"] * 1000 / c["area_petz_m2"]
    d["receita_m2_cobasi"] = c["receita_bruta_cobasi"] * 1000 / c["area_cobasi_m2"]
    for col in ["capex_lojas_novas", "capex_reformas", "capex_tecnologia", "capex_total"]:
        d[col] = c[col] / 1000

    d["cresc_petz"] = d["receita_bruta_petz"].pct_change(4, fill_method=None)
    d["cresc_cobasi"] = d["receita_bruta_cobasi"].pct_change(4, fill_method=None)
    d["cresc_receita_liquida"] = d["receita_liquida"].pct_change(4, fill_method=None)
    return d.replace([np.inf, -np.inf], np.nan)


# ---------------------------------------------------------------- antes × depois
# formato: "reais" (variação %), "pct" (variação em p.p.), "dias" (variação em dias)
COMPARACOES = [
    {"chave": "receita", "nome": "Receita líquida", "formato": "reais",
     "explica": "Tamanho do negócio no período."},
    {"chave": "margem_bruta", "nome": "Margem bruta", "formato": "pct",
     "explica": "Se sobe, o grupo vende mais caro ou compra mais barato. É o sinal mais direto de poder de mercado."},
    {"chave": "despesas_vendas", "nome": "Despesas com vendas / receita", "formato": "pct",
     "explica": "Custo de operar as lojas e os canais. Se cai, há ganho de eficiência."},
    {"chave": "despesas_ga", "nome": "Despesas G&A / receita", "formato": "pct",
     "explica": "Sede, áreas de apoio e gestão. É onde a sinergia de juntar duas empresas costuma aparecer."},
    {"chave": "margem_ebitda", "nome": "Margem EBITDA ajustada", "formato": "pct",
     "explica": "Resultado operacional sem itens não recorrentes. Junta preço, compras e despesas."},
    {"chave": "prazo_fornecedores", "nome": "Prazo com fornecedores", "formato": "dias",
     "explica": "Se aumenta, o grupo passou a pagar fornecedores mais tarde: poder de barganha na compra."},
    {"chave": "prazo_estoques", "nome": "Dias de estoque", "formato": "dias",
     "explica": "Quanto tempo o estoque leva para girar."},
]

_MEDIDAS = {
    "receita": lambda d: d["receita_liquida"].sum(),
    "margem_bruta": lambda d: d["lucro_bruto"].sum() / d["receita_liquida"].sum(),
    "despesas_vendas": lambda d: d["despesas_vendas"].sum() / d["receita_liquida"].sum(),
    "despesas_ga": lambda d: d["despesas_ga"].sum() / d["receita_liquida"].sum(),
    "margem_ebitda": lambda d: d["ebitda_ajustado"].sum() / d["receita_liquida"].sum(),
    "prazo_fornecedores": lambda d: d["prazo_fornecedores"].mean(),
    "prazo_estoques": lambda d: d["prazo_estoques"].mean(),
}


def periodos_comparacao(df, inicio=TRIMESTRE_FUSAO):
    """'Depois' = o primeiro ano após a fusão (até 4 trimestres publicados).
    'Antes' = os MESMOS trimestres um ano antes, todos anteriores à fusão (neutraliza a sazonalidade).
    Limitar ao primeiro ano evita que, a partir de 2027, o 'antes' caia em trimestres já pós-fusão."""
    depois = [p for p in df.index if inicio <= p < inicio + 4 and pd.notna(df.loc[p, "receita_liquida"])]
    antes = [p - 4 for p in depois if (p - 4) in df.index]
    return antes, depois


def comparar_antes_depois(df):
    antes, depois = periodos_comparacao(df)
    linhas = []
    for spec in COMPARACOES:
        v_antes = _MEDIDAS[spec["chave"]](df.loc[antes]) if antes else np.nan
        v_depois = _MEDIDAS[spec["chave"]](df.loc[depois]) if depois else np.nan
        delta = v_depois / v_antes - 1 if spec["formato"] == "reais" else v_depois - v_antes
        linhas.append({**spec, "antes": v_antes, "depois": v_depois, "delta": delta})
    return pd.DataFrame(linhas).set_index("chave"), antes, depois


# ---------------------------------------------------------------- tendência sem fusão
METRICAS_TENDENCIA = {
    "margem_bruta": ("Margem bruta", "pct"),
    "despesas_vendas_pct": ("Despesas com vendas / receita", "pct"),
    "despesas_ga_pct": ("Despesas G&A / receita", "pct"),
    "margem_ebitda": ("Margem EBITDA ajustada", "pct"),
    "prazo_fornecedores": ("Prazo com fornecedores", "dias"),
    "prazo_estoques": ("Dias de estoque", "dias"),
}


def _matriz(indice):
    """Constante, tendência linear e sazonalidade (dummies de 2T, 3T e 4T)."""
    t = np.arange(len(indice))
    q = np.array([p.quarter for p in indice])
    return np.column_stack([np.ones(len(indice)), t, q == 2, q == 3, q == 4]).astype(float)


def tendencia_sem_fusao(df, inicio=TRIMESTRE_FUSAO):
    """Ajusta tendência + sazonalidade por mínimos quadrados nos trimestres antes da fusão
    e projeta para todos os trimestres. Devolve {metrica: Series com a tendência}."""
    pre = df.index < inicio
    X = _matriz(df.index)
    tendencias = {}
    for metrica in METRICAS_TENDENCIA:
        y = df[metrica]
        validos = pre & y.notna().values
        if validos.sum() < 6:
            continue
        coef, *_ = np.linalg.lstsq(X[validos], y[validos].values, rcond=None)
        tendencias[metrica] = pd.Series(X @ coef, index=df.index, name=metrica)
    return tendencias


def resumo_tendencia(df, tendencias, inicio=TRIMESTRE_FUSAO):
    """Média dos trimestres pós-fusão: real, tendência e diferença."""
    pos = df.index >= inicio
    linhas = []
    for metrica, (nome, formato) in METRICAS_TENDENCIA.items():
        if metrica not in tendencias:
            continue
        real, tend = df.loc[pos, metrica].mean(), tendencias[metrica][pos].mean()
        linhas.append({"metrica": metrica, "nome": nome, "formato": formato,
                       "tendencia": tend, "real": real, "diferenca": real - tend})
    return pd.DataFrame(linhas).set_index("metrica") if linhas else pd.DataFrame()


# ---------------------------------------------------------------- expansão
def expansao_anual(df):
    """Inaugurações e CAPEX por ano (2026 = semestre disponível)."""
    anos = pd.Series([p.year for p in df.index], index=df.index)
    agrupado = pd.DataFrame({
        "inauguracoes": df["inauguracoes_petz"] + df["inauguracoes_cobasi"],
        "capex_total": df["capex_total"],
        "capex_lojas_novas": df["capex_lojas_novas"],
    }).groupby(anos).sum(min_count=1)
    ultimo = df.index.max()
    agrupado.index = [f"{ultimo.quarter * 3}M{str(a)[2:]}" if a == ultimo.year and ultimo.quarter < 4 else str(a)
                      for a in agrupado.index]
    return agrupado


# ---------------------------------------------------------------- sobreposição geográfica
def sobreposicao_cidades(lojas):
    """Lojas de cada bandeira por cidade, só nas cidades com Petz e Cobasi."""
    if lojas.empty:
        return pd.DataFrame(columns=["cidade", "uf", "petz", "cobasi", "total"])
    l = lojas.assign(cidade_uf=lojas["cidade"] + "/" + lojas["uf"])
    tabela = l.pivot_table(index=["cidade_uf", "uf"], columns="bandeira", values="cidade", aggfunc="count", fill_value=0)
    tabela = tabela.reindex(columns=["Petz", "Cobasi"], fill_value=0).reset_index()
    tabela.columns = ["cidade", "uf", "petz", "cobasi"]
    tabela = tabela[(tabela["petz"] > 0) & (tabela["cobasi"] > 0)].copy()
    tabela["total"] = tabela["petz"] + tabela["cobasi"]
    return tabela.sort_values(["total", "cidade"], ascending=[False, True]).reset_index(drop=True)


def sobreposicao_resumo(lojas):
    if lojas.empty:
        return {}
    cidade_uf = lojas["cidade"] + "/" + lojas["uf"]
    bandeiras = lojas.groupby(cidade_uf)["bandeira"].nunique()
    ambas = set(bandeiras[bandeiras >= 2].index)
    lojas_ambas = int(cidade_uf.isin(ambas).sum())
    return {"cidades_total": len(bandeiras), "cidades_ambas": len(ambas), "lojas_total": len(lojas),
            "lojas_em_cidades_ambas": lojas_ambas, "participacao": lojas_ambas / len(lojas)}


# ---------------------------------------------------------------- leitura da hipótese
def leitura_hipotese(comparacao):
    """Classifica cada mecanismo. É uma leitura de apoio: a conclusão final
    deve ser escrita pelo grupo, com as limitações."""
    despesas = comparacao.loc["despesas_vendas", "delta"] + comparacao.loc["despesas_ga", "delta"]
    s_desp = sinal(despesas, LIMIAR_PP)
    # (sinal() está definida no fim do arquivo)
    return {
        "preco_ou_compra": sinal(comparacao.loc["margem_bruta", "delta"], LIMIAR_PP),
        "fornecedores": sinal(comparacao.loc["prazo_fornecedores", "delta"], LIMIAR_DIAS),
        "sinergia": None if s_desp is None else -s_desp,
    }


# ---------------------------------------------------------------- textos montados a partir dos dados
def rotulo_periodo(trimestres):
    """[1T26, 2T26] -> '1º semestre de 2026'; [1T26..3T26] -> 'nove primeiros meses de 2026'; etc."""
    if not trimestres:
        return ""
    anos = {p.year for p in trimestres}
    quarters = sorted(p.quarter for p in trimestres)
    if len(anos) == 1 and quarters == list(range(1, len(quarters) + 1)):
        ano = anos.pop()
        return {1: f"1º trimestre de {ano}", 2: f"1º semestre de {ano}",
                3: f"nove primeiros meses de {ano}", 4: f"ano de {ano}"}[len(quarters)]
    return f"{rotulo_trimestre(min(trimestres))} a {rotulo_trimestre(max(trimestres))}"


def faixas_do_periodo(df, inicio=TRIMESTRE_FUSAO):
    """Textos sobre os períodos presentes nos dados (para não deixar trimestres escritos à mão)."""
    pre = [p for p in df.index if p < inicio]
    pos = [p for p in df.index if p >= inicio]
    junta = lambda ps: " e ".join(rotulo_trimestre(p) for p in ps) if len(ps) <= 2 else \
        f"{rotulo_trimestre(ps[0])} a {rotulo_trimestre(ps[-1])}"
    return {
        "pre": f"{rotulo_trimestre(pre[0])} a {rotulo_trimestre(pre[-1])}" if pre else "",
        "pre_anos": f"{pre[0].year}–{pre[-1].year}" if pre else "",
        "pos": junta(pos),
        "n_pos": len(pos),
        "n_total": len(df.index),
        "ultimo": rotulo_trimestre(df.index.max()),
    }


def sinal(valor, limiar):
    if valor is None or pd.isna(valor):
        return None
    return 1 if valor > limiar else -1 if valor < -limiar else 0


def anos_completos(df):
    """Anos com os 4 trimestres na planilha."""
    contagem = pd.Series([p.year for p in df.index]).value_counts()
    return sorted(int(a) for a, n in contagem.items() if n == 4)


def prazo_ja_alto_antes(df, depois, limiar=LIMIAR_DIAS, inicio=TRIMESTRE_FUSAO):
    """True se os dois trimestres logo antes da fusão já tinham prazo com fornecedores
    no nível do pós-fusão: nesse caso, o aumento pode não ser efeito da fusão."""
    ultimos_pre = [p for p in df.index if p < inicio][-2:]
    if not ultimos_pre or not depois:
        return False
    return df.loc[ultimos_pre, "prazo_fornecedores"].mean() >= df.loc[depois, "prazo_fornecedores"].mean() - limiar
