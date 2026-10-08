# %%
import matplotlib.pyplot as plt
import seaborn as sns

import pandas as pd

# %%
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

#plt.show()