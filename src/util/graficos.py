import streamlit as st

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from io import StringIO

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

def linha(data, x:str, y:str, empresa=None, data2=None, empresa2=None):
    fig_lin, ax = plt.subplots()
    sns.lineplot(x=x, y=y, data=data, ax=ax, label=empresa)
    if data2 is not None:
        sns.lineplot(x=x, y=y, data=data2, ax=ax, label=empresa2)
        plt.legend(title= "Empresas", loc= "upper left")

    formatter = ticker.ScalarFormatter()
    formatter.set_scientific(False)
    ax.yaxis.set_major_formatter(formatter)

    plt.ylabel(f"{y} em R$")
    
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout() 
    return fig_lin

#plt.show()