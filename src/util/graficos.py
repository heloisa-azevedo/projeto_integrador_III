# %%
from src.util.data.dadosPetz import analises

import matplotlib.pyplot as plt
import seaborn as sns

import pandas as pd

# %%
def correlacao(data):
    corr = data.corr(numeric_only=True)
    plt.figure(figsize=(20, 18))
    return sns.heatmap(corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1)

def htg(data):
    return data.hist(figsize=(15, 13))

#%%

for _, analise in analises.items():
    
    correlacao(analise)
    htg(analise)
    

plt.show()