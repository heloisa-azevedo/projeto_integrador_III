import streamlit as st

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from io import StringIO
import plotly.graph_objects as go

import pandas as pd

def info(data):
    buffer = StringIO()
    data.info(buf=buffer)
    st.markdown(
            """
            <style>
            pre code {
                color: black !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    return st.code(buffer.getvalue(), language="text")

def correlacao(data):
    corr = data.corr(numeric_only=True)
    fig_corr, ax = plt.subplots()
    sns.heatmap(corr,
                annot=True,
                fmt='.2f',
                cmap="coolwarm",
                linewidths=0.5,
                cbar_kws={"shrink": 1},
                annot_kws={"size": 5},
                vmin=-1,
                vmax=1,
                ax=ax)
    plt.xticks(rotation=45, ha='right')
    return fig_corr

def htg(data):
    return data.hist(figsize=(15, 13))

import plotly.graph_objects as go

def linha(lista_dados, x: str, y: str, lista_empresas):
    fig = go.Figure()
    
    for i, (data, empresa) in enumerate(zip(lista_dados, lista_empresas)):
        fig.add_trace(go.Scatter(
            x=data.index, 
            y=data[y], 
            mode='lines+markers',
            name=empresa
        ))

    def chave_trimestre(rotulo):
        rotulo = str(rotulo)
        trimestre, ano = rotulo.split('T')
        return (int(ano), int(trimestre))

    todos_trimestres = set()
    for data in lista_dados:
        todos_trimestres.update(data.index)

    ordem = sorted(todos_trimestres, key=chave_trimestre)
    
    fig.update_layout(
        yaxis_title=f"{y.replace("_", " ")} em R$",
        xaxis_title=x,
        legend_title="Empresas",
        xaxis=dict(
            tickangle=-45,
            type='category',
            categoryorder='array',
            categoryarray=ordem
        ),
        yaxis=dict(
            tickformat=',.2f',
            exponentformat="none"
        ),
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=80)
    )
    
    return fig

#plt.show()