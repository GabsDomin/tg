"""Grafico de funil: taxa x exposicao, bruta vs suavizada (bloco de construcao)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tg.config import CFG

d = pd.read_parquet(CFG.tratado / "demanda.parquet")
pop = pd.read_parquet(CFG.tratado / "populacao.parquet")
mun = pd.read_parquet(CFG.tratado / "municipios.parquet")[["cod_mun6", "nome"]]
py = pop[pop["ano"].isin(CFG.anos_construcao)].groupby("cod_mun6")["pop_15mais"].sum()
g = d[d["bloco"] == "construcao"].merge(mun, on="cod_mun6")
g["py"] = g["cod_mun6"].map(py)

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for a, col, tit in ((ax[0], "taxa_bruta_int", "Taxa bruta"), (ax[1], "taxa_suav_int", "Taxa suavizada (Bayes empírico)")):
    a.scatter(g["py"], g[col], s=8, alpha=.5, color="#2b6cb0")
    a.axhline(g["n_int"].sum() / g["py"].sum() * 1e5, color="#c53030", lw=1, ls="--", label="média estadual")
    a.set_xscale("log"); a.set_xlabel("pessoas-ano (15+), 2019–2022"); a.set_title(tit); a.grid(alpha=.2)
ax[0].set_ylabel("internações F10–F19 por 100 mil hab. 15+ por ano")
ax[0].legend(frameon=False)
fig.tight_layout()
(CFG.raiz / "figuras").mkdir(exist_ok=True)
fig.savefig(CFG.raiz / "figuras" / "funil_demanda_construcao.png", dpi=150)

print("taxa estadual (por 100k 15+/ano):", round(g["n_int"].sum() / g["py"].sum() * 1e5, 1))
print("municipios com 0 internacoes no bloco:", int((g["n_int"] == 0).sum()))
print("bruta  : min/mediana/max =", g["taxa_bruta_int"].agg(["min", "median", "max"]).round(1).tolist())
print("suav.  : min/mediana/max =", g["taxa_suav_int"].agg(["min", "median", "max"]).round(1).tolist())
print("\nmaiores taxas suavizadas:")
print(g.nlargest(8, "taxa_suav_int")[["nome", "n_int", "taxa_bruta_int", "taxa_suav_int"]].round(1).to_string(index=False))
