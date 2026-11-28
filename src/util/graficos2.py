"""
- Distribuição e assimetria (Histogramas)
- Comparação de dispersão e quartis (Boxplots)
- Relação entre faturamento e resultado (Dispersão Receita x Lucro)
- Eficiência operacional vs. rentabilidade (Dispersão EBITDA x Margem)
- Estrutura de endividamento (Dívida Bruta, Caixa Total e Dívida Líquida)
- Liquidez disponível e cobertura de curto prazo
- Variação percentual trimestre a trimestre (QoQ)
- Comparativo entre Margem EBITDA e Margem Líquida
- Crescimento indexado (Base 100)
- Intensidade de capital de giro (Estoques x Receita Líquida)
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np


CORES_EMPRESAS = {
    "Petz": "#1f77b4",     # Azul Petz
    "Cobasi": "#ff7f0e",   # Laranja Cobasi
    "Fusão": "#2ca02c"     # Verde Grupo Integrado
}


def chave_ordenacao_trimestre(t) -> tuple:
    """
    Garante a ordenação cronológica estrita de trimestres (ex.: '1T19', '4T25').
    Evita que '1T23' apareça antes de '2T19' em uma ordenação alfabética comum.
    """
    try:
        t_str = str(t).strip()
        trim = int(t_str[0])
        ano = int(t_str[2:])
        ano_completo = 2000 + ano if ano < 100 else ano
        return (ano_completo, trim)
    except Exception:
        return (9999, 0)


def ordenar_df_cronologico(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna o DataFrame reordenado cronologicamente pelo índice de trimestres."""
    if df is None or df.empty:
        return df
    indices_ordenados = sorted(df.index, key=chave_ordenacao_trimestre)
    return df.reindex(indices_ordenados)


# ==============================================================================
# Gráfico 1 — Histogramas financeiros
# ==============================================================================
def grafico_histogramas_financeiros(df: pd.DataFrame, empresa: str = "Empresa") -> plt.Figure:
    """
    Cria histogramas individuais com curva KDE para 11 variáveis numéricas relevantes,
    permitindo analisar a distribuição dos valores, assimetria, concentração e dispersão.
    """
    df_sorted = ordenar_df_cronologico(df)
    variaveis = [
        ("Receita_Liquida", "Receita Líquida (R$ mil)", "R$ mil"),
        ("EBITDA_Ajustado", "EBITDA Ajustado (R$ mil)", "R$ mil"),
        ("Lucro_Liquido", "Lucro Líquido (R$ mil)", "R$ mil"),
        ("Fluxo_Caixa_Operacional", "Fluxo de Caixa Operacional (R$ mil)", "R$ mil"),
        ("Divida_Bruta", "Dívida Bruta (R$ mil)", "R$ mil"),
        ("Divida_Liquida", "Dívida Líquida (R$ mil)", "R$ mil"),
        ("Caixa_Total", "Caixa Total (R$ mil)", "R$ mil"),
        ("Estoques", "Estoques (R$ mil)", "R$ mil"),
        ("Margem_EBITDA", "Margem EBITDA (%)", "%"),
        ("SSS_Percentual", "SSS - Same Store Sales (%)", "%"),
        ("Penetracao_Digital", "Penetração Digital (%)", "%")
    ]
    
    fig, axes = plt.subplots(4, 3, figsize=(15, 13))
    axes = axes.flatten()
    cor = CORES_EMPRESAS.get(empresa, "#1f77b4")
    
    for idx, (col, rotulo, unidade) in enumerate(variaveis):
        ax = axes[idx]
        if col in df_sorted.columns:
            serie = df_sorted[col].dropna()
            if len(serie) > 0:
                valores = serie * 100 if unidade == "%" else serie
                sns.histplot(valores, kde=True, ax=ax, color=cor, bins=min(8, len(valores)))
                media = valores.mean()
                mediana = valores.median()
                ax.axvline(media, color="#d9534f", linestyle="--", linewidth=1.3, label=f"Média: {media:.1f}")
                ax.axvline(mediana, color="#5cb85c", linestyle=":", linewidth=1.6, label=f"Mediana: {mediana:.1f}")
                ax.set_title(rotulo, fontsize=10, fontweight="bold")
                ax.set_xlabel(unidade, fontsize=8.5)
                ax.set_ylabel("Frequência", fontsize=8.5)
                ax.legend(fontsize=7.5, loc="upper right")
                ax.grid(True, linestyle="--", alpha=0.5)
            else:
                ax.text(0.5, 0.5, f"Dados não disponíveis\npara {empresa}", 
                        ha="center", va="center", color="#777777", fontsize=9.5)
                ax.set_title(rotulo, fontsize=10, fontweight="bold")
                ax.set_xticks([])
                ax.set_yticks([])
        else:
            ax.text(0.5, 0.5, "Variável ausente", ha="center", va="center", color="#777777", fontsize=9.5)
            ax.set_title(rotulo, fontsize=10, fontweight="bold")
            ax.set_xticks([])
            ax.set_yticks([])
            
    # Painel explicativo no último quadrante
    axes[11].axis("off")
    axes[11].text(0.05, 0.5, 
                  f"Distribuição Estatística — {empresa}\n"
                  f"Total de trimestres computados: {len(df_sorted)}\n\n"
                  "• Linha Vermelha (--): Média aritmética\n"
                  "• Linha Verde (..): Mediana (50º percentil)\n"
                  "• Curva contínua: Densidade estimada (KDE)\n"
                  "• Escalas: Valores monetários em R$ mil e taxas em %",
                  fontsize=9.5, verticalalignment="center",
                  bbox=dict(boxstyle="round,pad=0.6", facecolor="#f8f9fa", edgecolor="#ced4da"))
    
    fig.suptitle(f"Gráfico 1 — Histogramas dos Indicadores Financeiros e Operacionais ({empresa})", 
                 fontsize=13, fontweight="bold", y=0.99)
    plt.tight_layout()
    return fig


# ==============================================================================
# Gráfico 2 — Boxplots financeiros
# ==============================================================================
def grafico_boxplots_financeiros(analises: dict, empresas: list = None) -> plt.Figure:
    """
    Compara a dispersão dos 6 principais indicadores financeiros entre as empresas
    (Petz e Cobasi), evidenciando mediana, quartis, amplitude interquartil e outliers.
    """
    if empresas is None:
        empresas = [e for e in ["Petz", "Cobasi"] if e in analises]
        
    indicadores = [
        ("Receita_Liquida", "Receita Líquida (R$ mil)"),
        ("EBITDA_Ajustado", "EBITDA Ajustado (R$ mil)"),
        ("Lucro_Liquido", "Lucro Líquido (R$ mil)"),
        ("Fluxo_Caixa_Operacional", "Fluxo de Caixa Operacional (R$ mil)"),
        ("Divida_Liquida", "Dívida Líquida (R$ mil)"),
        ("Margem_EBITDA", "Margem EBITDA (%)")
    ]
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    
    dados_combinados = []
    for emp in empresas:
        if emp in analises:
            df_temp = analises[emp].copy()
            df_temp["Empresa"] = emp
            df_temp["Trimestre"] = df_temp.index
            dados_combinados.append(df_temp)
            
    df_all = pd.concat(dados_combinados, ignore_index=True) if dados_combinados else pd.DataFrame()
    
    for idx, (col, rotulo) in enumerate(indicadores):
        ax = axes[idx]
        if col in df_all.columns:
            df_col = df_all.dropna(subset=[col]).copy()
            if not df_col.empty:
                if col == "Margem_EBITDA":
                    df_col[col] = df_col[col] * 100
                    
                sns.boxplot(x="Empresa", y=col, hue="Empresa", data=df_col, ax=ax, 
                            palette=CORES_EMPRESAS, width=0.45, legend=False)
                sns.stripplot(x="Empresa", y=col, data=df_col, ax=ax, 
                              color="black", alpha=0.5, jitter=0.15, size=5)
                ax.set_title(rotulo, fontsize=11, fontweight="bold")
                ax.set_xlabel("Empresa", fontsize=9)
                ax.set_ylabel("%" if col == "Margem_EBITDA" else "R$ mil", fontsize=9)
                ax.grid(True, linestyle="--", alpha=0.5)
                
                # Alerta para dívida de Cobasi indisponível
                if col == "Divida_Liquida" and "Cobasi" in empresas:
                    cobasi_dados = df_all[df_all["Empresa"] == "Cobasi"][col].dropna()
                    if cobasi_dados.empty:
                        ax.annotate("Cobasi: dados de empréstimos\ne dívida não discriminados no RI", 
                                    xy=(0.65, 0.75), xycoords="axes fraction",
                                    fontsize=8.5, color="#d9534f",
                                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff3cd", edgecolor="#ffeeba"))
            else:
                ax.text(0.5, 0.5, "Dados não disponíveis", ha="center", va="center", color="gray")
                ax.set_title(rotulo, fontsize=11, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "Indicador ausente", ha="center", va="center", color="gray")
            ax.set_title(rotulo, fontsize=11, fontweight="bold")
            
    fig.suptitle("Gráfico 2 — Boxplots Comparativos de Desempenho Financeiro (Petz vs. Cobasi)", 
                 fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.01, 
             "Nota: A base de dados do RI não contém uma marcação temporal pré/pós união. "
             "Cobasi disponibiliza dados a partir de 2023, enquanto Petz possui série desde 2019. "
             "Valores de Dívida Líquida de Cobasi não foram detalhados na planilha original.",
             ha="center", fontsize=8.5, style="italic", color="#555555")
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    return fig


# ==============================================================================
# Gráfico 3 — Dispersão entre receita líquida e lucro líquido
# ==============================================================================
def grafico_dispersao_receita_lucro(analises: dict, empresas: list = None) -> plt.Figure:
    """
    Scatter plot entre Receita Líquida e Lucro Líquido por empresa, identificando
    períodos onde receitas elevadas não se converteram em lucros correspondentes.
    """
    if empresas is None:
        empresas = [e for e in ["Petz", "Cobasi"] if e in analises]
        
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axhline(0, color="gray", linestyle="--", linewidth=1, label="Lucro Zero (Ponto de Equilíbrio)")
    
    for emp in empresas:
        if emp in analises:
            df_emp = analises[emp].dropna(subset=["Receita_Liquida", "Lucro_Liquido"]).copy()
            if not df_emp.empty:
                cor = CORES_EMPRESAS.get(emp, "#333333")
                ax.scatter(df_emp["Receita_Liquida"], df_emp["Lucro_Liquido"], 
                           color=cor, label=f"{emp} (Trimestres)", s=60, alpha=0.85, edgecolors="white")
                
                # Linha de tendência linear
                if len(df_emp) > 2:
                    p = np.polyfit(df_emp["Receita_Liquida"], df_emp["Lucro_Liquido"], 1)
                    r = np.corrcoef(df_emp["Receita_Liquida"], df_emp["Lucro_Liquido"])[0, 1]
                    x_linha = np.linspace(df_emp["Receita_Liquida"].min(), df_emp["Receita_Liquida"].max(), 50)
                    ax.plot(x_linha, np.polyval(p, x_linha), color=cor, linestyle="-.", linewidth=1.5,
                            label=f"Tendência {emp} (R = {r:.2f})")
                    
                # Anotação de trimestres de destaque (menor lucro e maior receita)
                idx_min = df_emp["Lucro_Liquido"].idxmin()
                idx_max = df_emp["Lucro_Liquido"].idxmax()
                for ponto_idx in set([idx_min, idx_max]):
                    ponto = df_emp.loc[ponto_idx]
                    ax.annotate(f"{emp} {ponto_idx}", 
                                (ponto["Receita_Liquida"], ponto["Lucro_Liquido"]),
                                textcoords="offset points", xytext=(0, 7), ha="center",
                                fontsize=8, color=cor, fontweight="bold")
                    
    ax.set_title("Gráfico 3 — Dispersão entre Receita Líquida e Lucro Líquido", fontsize=12, fontweight="bold")
    ax.set_xlabel("Receita Líquida (R$ mil)", fontsize=10)
    ax.set_ylabel("Lucro Líquido (R$ mil)", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8.5, loc="best")
    plt.tight_layout()
    return fig


# ==============================================================================
# Gráfico 4 — Dispersão entre EBITDA e margem EBITDA
# ==============================================================================
def grafico_dispersao_ebitda_margem(analises: dict, empresas: list = None) -> plt.Figure:
    """
    Relação entre geração operacional absoluta (EBITDA Ajustado) e rentabilidade relativa (Margem EBITDA).
    Permite identificar períodos de ganho ou perda de margem operacional.
    """
    if empresas is None:
        empresas = [e for e in ["Petz", "Cobasi"] if e in analises]
        
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for emp in empresas:
        if emp in analises:
            df_emp = analises[emp].dropna(subset=["EBITDA_Ajustado", "Margem_EBITDA"]).copy()
            if not df_emp.empty:
                cor = CORES_EMPRESAS.get(emp, "#333333")
                margem_pct = df_emp["Margem_EBITDA"] * 100
                ax.scatter(df_emp["EBITDA_Ajustado"], margem_pct,
                           color=cor, label=f"{emp} (Trimestres)", s=60, alpha=0.85, edgecolors="white")
                
                # Linha de mediana de margem
                mediana_m = margem_pct.median()
                ax.axhline(mediana_m, color=cor, linestyle=":", alpha=0.75, 
                           label=f"Mediana Margem {emp}: {mediana_m:.1f}%")
                
                # Anotações dos trimestres extremos
                p_min = df_emp.loc[margem_pct.idxmin()]
                p_max = df_emp.loc[margem_pct.idxmax()]
                ax.annotate(f"{emp} ({margem_pct.idxmin()})", 
                            (p_min["EBITDA_Ajustado"], p_min["Margem_EBITDA"] * 100),
                            textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8, color=cor)
                ax.annotate(f"{emp} ({margem_pct.idxmax()})", 
                            (p_max["EBITDA_Ajustado"], p_max["Margem_EBITDA"] * 100),
                            textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8, color=cor)
                
    ax.set_title("Gráfico 4 — Relação entre EBITDA Ajustado e Margem EBITDA", fontsize=12, fontweight="bold")
    ax.set_xlabel("EBITDA Ajustado (R$ mil)", fontsize=10)
    ax.set_ylabel("Margem EBITDA (%)", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=8.5, loc="best")
    plt.tight_layout()
    return fig


# ==============================================================================
# Gráfico 5 — Comparação entre dívida bruta, caixa total e dívida líquida
# ==============================================================================
def grafico_comparacao_divida(df: pd.DataFrame, empresa: str = "Empresa") -> plt.Figure:
    """
    Compara Dívida Bruta, Caixa Total e Dívida Líquida ao longo do tempo.
    Nota: Dívida Líquida = Dívida Bruta - Caixa Total (não é independente).
    """
    df_sorted = ordenar_df_cronologico(df)
    fig, ax = plt.subplots(figsize=(12, 6))
    
    tem_divida = ("Divida_Bruta" in df_sorted.columns and 
                  df_sorted["Divida_Bruta"].dropna().count() > 0)
    
    trimestres = df_sorted.index.tolist()
    x = np.arange(len(trimestres))
    largura = 0.35
    
    if tem_divida:
        div_bruta = df_sorted["Divida_Bruta"].fillna(0)
        caixa_tot = df_sorted["Caixa_Total"].fillna(0)
        div_liquida = df_sorted["Divida_Liquida"].fillna(0)
        
        ax.bar(x - largura/2, div_bruta, width=largura, label="Dívida Bruta (Empréstimos CP + LP)", color="#d9534f", alpha=0.85)
        ax.bar(x + largura/2, caixa_tot, width=largura, label="Caixa Total (Equivalentes + Aplicações)", color="#5cb85c", alpha=0.85)
        
        ax.plot(x, div_liquida, color="#0275d8", marker="o", linewidth=2.2, label="Dívida Líquida (Dívida Bruta - Caixa)")
        ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
        
        ax.set_xticks(x)
        ax.set_xticklabels(trimestres, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("R$ mil", fontsize=10)
        ax.set_title(f"Gráfico 5 — Estrutura de Endividamento e Posição Financeira ({empresa})", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9, loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.5)
        
        fig.text(0.5, 0.01, 
                 "Nota metodológica: A Dívida Líquida é calculada como Dívida Bruta menos Caixa Total; portanto, não é uma medida independente. "
                 "Valores negativos representam posição de Caixa Líquido (disponibilidades superiores ao endividamento).",
                 ha="center", fontsize=8.5, style="italic", color="#555555")
        plt.tight_layout(rect=[0, 0.04, 1, 1])
    else:
        caixa_tot = df_sorted["Caixa_Total"].fillna(0)
        ax.bar(x, caixa_tot, width=0.5, label="Caixa Total Disponível", color="#5cb85c", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(trimestres, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("R$ mil", fontsize=10)
        ax.set_title(f"Gráfico 5 — Posição de Caixa Total ({empresa})", fontsize=12, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(fontsize=9)
        
        ax.text(0.5, 0.75, 
                f"Atenção: A planilha de RI da {empresa} não divulga os valores discriminados\n"
                "de Empréstimos/Financiamentos no Balanço Patrimonial.\n"
                "Portanto, Dívida Bruta e Dívida Líquida não puderam ser calculadas.",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="#a94442",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#f2dede", edgecolor="#ebccd1"))
        plt.tight_layout()
        
    return fig


# ==============================================================================
# Gráfico 6 — Liquidez e composição da dívida
# ==============================================================================
def grafico_liquidez_composicao_divida(df: pd.DataFrame, empresa: str = "Empresa") -> plt.Figure:
    """
    Compara a composição de ativos líquidos (Caixa vs Aplicações) com o perfil de
    vencimento da dívida (CP vs LP) e calcula o índice de cobertura da dívida de curto prazo.
    """
    df_sorted = ordenar_df_cronologico(df)
    trimestres = df_sorted.index.tolist()
    x = np.arange(len(trimestres))
    
    tem_divida = ("Emprestimos_CP" in df_sorted.columns and 
                  df_sorted["Emprestimos_CP"].dropna().count() > 0)
    
    if tem_divida:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
        
        caixa = df_sorted["Caixa_Equivalentes"].fillna(0)
        aplic = df_sorted["Aplicacoes_Financeiras"].fillna(0)
        emp_cp = df_sorted["Emprestimos_CP"].fillna(0)
        emp_lp = df_sorted["Emprestimos_LP"].fillna(0)
        
        largura = 0.35
        # Painel 1: Composição
        ax1.bar(x - largura/2, caixa, width=largura, label="Caixa e Equivalentes", color="#5cb85c", alpha=0.85)
        ax1.bar(x - largura/2, aplic, width=largura, bottom=caixa, label="Aplicações Financeiras", color="#a3d9a5", alpha=0.85)
        
        ax1.bar(x + largura/2, emp_cp, width=largura, label="Empréstimos Curto Prazo (CP)", color="#d9534f", alpha=0.85)
        ax1.bar(x + largura/2, emp_lp, width=largura, bottom=emp_cp, label="Empréstimos Longo Prazo (LP)", color="#f0ad4e", alpha=0.85)
        
        ax1.set_ylabel("R$ mil", fontsize=10)
        ax1.set_title(f"Gráfico 6 — Liquidez Disponível e Perfil de Vencimento da Dívida ({empresa})", fontsize=12, fontweight="bold")
        ax1.legend(fontsize=8.5, loc="upper left", ncol=2)
        ax1.grid(True, linestyle="--", alpha=0.5)
        
        # Painel 2: Indicador de Cobertura CP
        caixa_total = caixa + aplic
        cobertura_cp = np.where(emp_cp > 0, caixa_total / emp_cp, np.nan)
        
        ax2.plot(x, cobertura_cp, marker="s", color="#337ab7", linewidth=2, label="Cobertura Financeira CP (Caixa Total / Empréstimos CP)")
        ax2.axhline(1.0, color="red", linestyle="--", linewidth=1.2, label="Paridade 1,0x (100% Cobertura)")
        ax2.set_ylabel("Múltiplo (x)", fontsize=10)
        ax2.set_xlabel("Trimestre", fontsize=10)
        ax2.set_xticks(x)
        ax2.set_xticklabels(trimestres, rotation=45, ha="right", fontsize=9)
        ax2.legend(fontsize=8.5, loc="upper left")
        ax2.grid(True, linestyle="--", alpha=0.5)
        
        fig.text(0.5, 0.01, 
                 "Nota: O índice (Caixa Total / Empréstimos CP) é uma aproximação de cobertura financeira imediata da dívida bancária, "
                 "e não um índice completo de Liquidez Corrente (que requer todo o Ativo e Passivo Circulante).",
                 ha="center", fontsize=8.5, style="italic", color="#555555")
        plt.tight_layout(rect=[0, 0.03, 1, 1])
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        caixa = df_sorted["Caixa_Equivalentes"].fillna(0)
        aplic = df_sorted["Aplicacoes_Financeiras"].fillna(0)
        
        ax.bar(x, caixa, width=0.45, label="Caixa e Equivalentes", color="#5cb85c", alpha=0.85)
        ax.bar(x, aplic, width=0.45, bottom=caixa, label="Aplicações Financeiras", color="#a3d9a5", alpha=0.85)
        
        ax.set_xticks(x)
        ax.set_xticklabels(trimestres, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("R$ mil", fontsize=10)
        ax.set_title(f"Gráfico 6 — Composição da Liquidez Disponível ({empresa})", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.5)
        
        ax.text(0.5, 0.75, 
                f"Nota: Dados de Empréstimos CP/LP indisponíveis para {empresa}.\n"
                "O gráfico apresenta a composição das reservas líquidas (Caixa + Aplicações).",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="#8a6d3b",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#fcf8e3", edgecolor="#faebcc"))
        plt.tight_layout()
        
    return fig


# ==============================================================================
# Gráfico 7 — Variação percentual dos indicadores financeiros (QoQ)
# ==============================================================================
def grafico_variacao_percentual_qoq(df: pd.DataFrame, empresa: str = "Empresa") -> plt.Figure:
    """
    Calcula a variação percentual trimestre contra trimestre anterior (QoQ) em ordem
    cronológica estrita, tratando mudanças de sinal e divisões por zero com rigor metodológico.
    """
    df_sorted = ordenar_df_cronologico(df)
    indicadores = [
        ("Receita_Liquida", "Receita Líquida"),
        ("EBITDA_Ajustado", "EBITDA Ajustado"),
        ("Lucro_Liquido", "Lucro Líquido"),
        ("Fluxo_Caixa_Operacional", "Fluxo Caixa Operacional"),
        ("Divida_Liquida", "Dívida Líquida")
    ]
    
    fig, axes = plt.subplots(len(indicadores), 1, figsize=(12, 13), sharex=True)
    trimestres = df_sorted.index.tolist()[1:]
    x = np.arange(len(trimestres))
    
    for idx, (col, rotulo) in enumerate(indicadores):
        ax = axes[idx]
        if col in df_sorted.columns and df_sorted[col].dropna().count() > 1:
            serie = df_sorted[col].values
            var_pct = []
            
            for t in range(1, len(serie)):
                v_ant = serie[t-1]
                v_atual = serie[t]
                
                # Tratamento de denominadores nulos ou mudanças de sinal que tornam a taxa enganosa
                if pd.isna(v_ant) or pd.isna(v_atual) or v_ant == 0:
                    var_pct.append(np.nan)
                elif (v_ant < 0 and v_atual > 0) or (v_ant > 0 and v_atual < 0):
                    var_pct.append(np.nan)
                elif v_ant < 0 and v_atual < 0:
                    var_pct.append(np.nan)
                else:
                    var_pct.append(((v_atual - v_ant) / abs(v_ant)) * 100)
                    
            var_pct = np.array(var_pct)
            cores = ["#5cb85c" if v >= 0 else "#d9534f" for v in np.nan_to_num(var_pct, nan=0)]
            
            ax.bar(x, np.nan_to_num(var_pct, nan=0), width=0.55, color=cores, alpha=0.85)
            ax.axhline(0, color="black", linestyle="-", linewidth=0.8)
            ax.set_ylabel("Var. % QoQ", fontsize=9)
            ax.set_title(f"Variação Trimestral QoQ: {rotulo}", fontsize=10.5, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.5)
            
            validos = var_pct[~np.isnan(var_pct)]
            if len(validos) > 0:
                lim_max = max(10, np.percentile(validos, 95) * 1.3)
                lim_min = min(-10, np.percentile(validos, 5) * 1.3)
                ax.set_ylim(lim_min, lim_max)
        else:
            ax.text(0.5, 0.5, f"Dados insuficientes para variação de {rotulo}", 
                    ha="center", va="center", color="gray", fontsize=9.5)
            ax.set_title(f"Variação Trimestral QoQ: {rotulo}", fontsize=10.5, fontweight="bold")
            ax.set_yticks([])
            
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(trimestres, rotation=45, ha="right", fontsize=9)
    axes[-1].set_xlabel("Trimestre (Comparação com Trimestre Imediatamente Anterior)", fontsize=10)
    
    fig.suptitle(f"Gráfico 7 — Variações Percentuais Trimestre contra Trimestre (QoQ) — {empresa}", 
                 fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.01, 
             "Nota Metodológica: Variações com base nula ou mudanças de sinal (ex.: transição prejuízo/lucro) foram desconsideradas para evitar taxas distorcidas.",
             ha="center", fontsize=8.5, style="italic", color="#555555")
    plt.tight_layout(rect=[0, 0.02, 1, 0.98])
    return fig


# ==============================================================================
# Gráfico 8 — Análise da margem EBITDA e da margem líquida
# ==============================================================================
def grafico_margens_ebitda_liquida(df: pd.DataFrame, empresa: str = "Empresa") -> plt.Figure:
    """
    Compara a rentabilidade operacional (Margem EBITDA) e a rentabilidade líquida final
    (Margem Líquida = Lucro Líquido / Receita Líquida) ao longo dos trimestres.
    """
    df_sorted = ordenar_df_cronologico(df)
    trimestres = df_sorted.index.tolist()
    x = np.arange(len(trimestres))
    largura = 0.38
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    margem_ebitda = (df_sorted["Margem_EBITDA"] * 100).fillna(0)
    margem_liquida = np.where(df_sorted["Receita_Liquida"] > 0, 
                              (df_sorted["Lucro_Liquido"] / df_sorted["Receita_Liquida"]) * 100, 
                              0)
    
    ax.bar(x - largura/2, margem_ebitda, width=largura, label="Margem EBITDA (%)", color="#1f77b4", alpha=0.85)
    ax.bar(x + largura/2, margem_liquida, width=largura, label="Margem Líquida (%)", color="#2ca02c", alpha=0.85)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    
    media_ebitda = margem_ebitda.mean()
    media_liq = pd.Series(margem_liquida).mean()
    ax.axhline(media_ebitda, color="#1f77b4", linestyle=":", alpha=0.8, label=f"Média EBITDA: {media_ebitda:.1f}%")
    ax.axhline(media_liq, color="#2ca02c", linestyle=":", alpha=0.8, label=f"Média Líquida: {media_liq:.1f}%")
    
    ax.set_xticks(x)
    ax.set_xticklabels(trimestres, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Margem sobre Receita Líquida (%)", fontsize=10)
    ax.set_title(f"Gráfico 8 — Comparativo entre Margem EBITDA e Margem Líquida ({empresa})", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.5)
    
    fig.text(0.5, 0.01, 
             "Diferenciação Econômica: A Margem EBITDA reflete o potencial operacional antes de juros, depreciação e impostos. "
             "A Margem Líquida evidencia o retorno final disponível aos acionistas após todos os custos e despesas.",
             ha="center", fontsize=8.5, style="italic", color="#555555")
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    return fig


# ==============================================================================
# Gráfico 9 — Evolução relativa dos indicadores (Base 100)
# ==============================================================================
def grafico_evolucao_relativa_base100(df: pd.DataFrame, empresa: str = "Empresa") -> plt.Figure:
    """
    Normaliza os indicadores financeiros em Base 100 no primeiro período válido,
    permitindo comparar taxas de crescimento relativo sem distorção de escalas monetárias.
    """
    df_sorted = ordenar_df_cronologico(df)
    trimestres = df_sorted.index.tolist()
    
    candidatos = [
        ("Receita_Liquida", "Receita Líquida", "#1f77b4"),
        ("EBITDA_Ajustado", "EBITDA Ajustado", "#ff7f0e"),
        ("Estoques", "Estoques", "#9467bd"),
        ("Fluxo_Caixa_Operacional", "Fluxo Caixa Operacional", "#2ca02c"),
        ("Lucro_Liquido", "Lucro Líquido", "#d62728")
    ]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    series_omitidas = []
    
    for col, rotulo, cor in candidatos:
        if col in df_sorted.columns:
            serie = df_sorted[col].dropna()
            if not serie.empty:
                v_inicial = serie.iloc[0]
                if v_inicial > 0:
                    base100 = (serie / v_inicial) * 100
                    ax.plot(base100.index, base100.values, marker="o", markersize=4, 
                            linewidth=2, label=f"{rotulo} (Base 100 em {serie.index[0]})", color=cor)
                else:
                    series_omitidas.append(f"{rotulo} (base não positiva: {v_inicial:.1f})")
            else:
                series_omitidas.append(f"{rotulo} (série vazia)")
        else:
            series_omitidas.append(f"{rotulo} (não encontrada)")
            
    ax.axhline(100, color="gray", linestyle="--", linewidth=1.2, label="Linha de Referência Base 100")
    ax.set_xticks(range(len(trimestres)))
    ax.set_xticklabels(trimestres, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Índice de Crescimento (Base 100)", fontsize=10)
    ax.set_title(f"Gráfico 9 — Evolução Relativa e Ritmo de Crescimento Base 100 ({empresa})", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.5)
    
    aviso = "Nota Metodológica: O primeiro período válido da série é fixado como 100."
    if series_omitidas:
        aviso += f" Séries desconsideradas da base 100: {', '.join(series_omitidas)}."
    fig.text(0.5, 0.01, aviso, ha="center", fontsize=8, style="italic", color="#555555")
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    return fig


# ==============================================================================
# Gráfico 10 — Relação entre estoques e receita
# ==============================================================================
def grafico_relacao_estoques_receita(analises: dict, empresas: list = None) -> plt.Figure:
    """
    Gráfico duplo: dispersão com trajetória de expansão (Estoques vs. Receita Líquida)
    e evolução temporal da intensidade de capital em estoques (% da Receita Líquida).
    """
    if empresas is None:
        empresas = [e for e in ["Petz", "Cobasi"] if e in analises]
        
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    for emp in empresas:
        if emp in analises:
            df_emp = ordenar_df_cronologico(analises[emp]).dropna(subset=["Receita_Liquida", "Estoques"]).copy()
            if not df_emp.empty:
                cor = CORES_EMPRESAS.get(emp, "#333333")
                # Painel 1: Trajetória
                ax1.plot(df_emp["Receita_Liquida"], df_emp["Estoques"], 
                         color=cor, linestyle=":", alpha=0.6, linewidth=1.5)
                ax1.scatter(df_emp["Receita_Liquida"], df_emp["Estoques"], 
                            color=cor, label=f"{emp}", s=60, edgecolors="white", zorder=3)
                
                ax1.annotate(f"{emp} {df_emp.index[0]}", 
                             (df_emp["Receita_Liquida"].iloc[0], df_emp["Estoques"].iloc[0]),
                             fontsize=8, color=cor, fontweight="bold", textcoords="offset points", xytext=(-5, 7))
                ax1.annotate(f"{emp} {df_emp.index[-1]}", 
                             (df_emp["Receita_Liquida"].iloc[-1], df_emp["Estoques"].iloc[-1]),
                             fontsize=8, color=cor, fontweight="bold", textcoords="offset points", xytext=(5, -10))
                
                # Painel 2: Razão de Estoques sobre Receita
                razao_est = (df_emp["Estoques"] / df_emp["Receita_Liquida"]) * 100
                ax2.plot(razao_est.index, razao_est.values, marker="s", 
                         color=cor, label=f"{emp} (Estoques / Receita)", linewidth=2)
                
    ax1.set_title("Dispersão e Trajetória: Estoques vs. Receita Líquida", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Receita Líquida (R$ mil)", fontsize=10)
    ax1.set_ylabel("Estoques (R$ mil)", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(fontsize=9)
    
    ax2.set_title("Intensidade de Estoque (% da Receita Líquida)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Trimestre", fontsize=10)
    ax2.set_ylabel("Estoques / Receita Líquida (%)", fontsize=10)
    ax2.tick_params(axis="x", rotation=45)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(fontsize=9)
    
    fig.suptitle("Gráfico 10 — Relação entre Estoques e Faturamento", fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.01, 
             "Limitação Metodológica: Como o Custo das Mercadorias Vendidas (CMV) não está individualizado na base de dados tratada, "
             "a razão (Estoques / Receita Líquida) atua como proxy de intensidade de capital, e não como cálculo estrito do Giro de Estoques.",
             ha="center", fontsize=8.5, style="italic", color="#555555")
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    return fig
