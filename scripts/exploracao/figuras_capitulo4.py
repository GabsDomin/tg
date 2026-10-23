"""Figuras do capitulo 4 (PNG, fundo branco, para o .docx). Saida: figuras/cap4_*.png"""
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from tg.config import CFG

SAIDA = CFG.raiz / "figuras"
SAIDA.mkdir(exist_ok=True)
T = CFG.tratado
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

malha = gpd.read_file(CFG.bruto / "malha_sp_municipios.geojson")
malha["cod_mun6"] = malha["codarea"].astype(str).str[:6]
malha["geometry"] = malha.geometry.simplify(0.003, preserve_topology=True)
cl = pd.read_parquet(T / "clusters.parquet")
ac = (pd.read_parquet(T / "acessibilidade.parquet").query("camada == 'O1' and ano in [2023, 2024]")
        .groupby("cod_mun6")["A_r60_rel"].mean().rename("A"))
srv = pd.read_parquet(T / "servicos.parquet").query("competencia == '202412' and eh_caps_ad")
g = malha.merge(cl, on="cod_mun6").merge(ac, on="cod_mun6")

# --- Figura 1: acessibilidade (quintis) com CAPS AD
RAMPA = ["#7f2704", "#d94801", "#fd8d3c", "#fdd0a2", "#fff5eb"]   # escuro = menor acessibilidade
cortes = np.quantile(g["A"], [0.2, 0.4, 0.6, 0.8])
g["q"] = np.digitize(g["A"], cortes)
fig, ax = plt.subplots(figsize=(7.2, 5.2))
g.plot(ax=ax, color=[RAMPA[i] for i in g["q"]], edgecolor="white", linewidth=0.15)
ax.scatter(srv["lon"], srv["lat"], s=9, c="#111", edgecolors="white", linewidths=0.4, zorder=3)
lim = [g["A"].min(), *cortes, g["A"].max()]
ax.legend(handles=[Patch(facecolor=RAMPA[i], edgecolor="#999", label=f"{lim[i]:.2f} a {lim[i + 1]:.2f}") for i in range(5)] +
          [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#111", markersize=6, label="CAPS AD habilitado")],
          title="Acessibilidade relativa (1 = média do estado)", loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=3,
          fontsize=8, title_fontsize=8, frameon=False)
ax.set_axis_off()
fig.savefig(SAIDA / "cap4_mapa_acessibilidade.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# --- Figura 2: tipologia
from tg.clusters.kmeans import ROTULOS
CAT = {1: "#d55e00", 2: "#56b4e9", 3: "#0072b2", 4: "#009e73", 5: "#e6c200"}
fig, ax = plt.subplots(figsize=(7.2, 5.2))
g.plot(ax=ax, color=[CAT[c] for c in g["cluster"]], edgecolor="white", linewidth=0.15)
ax.legend(handles=[Patch(facecolor=CAT[k], edgecolor="#999", label=f"{k}. {ROTULOS[k]} ({(g['cluster'] == k).sum()})") for k in CAT],
          title="Tipologia (K-Means, k = 5)", loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=2,
          fontsize=7.5, title_fontsize=8, frameon=False)
ax.set_axis_off()
fig.savefig(SAIDA / "cap4_mapa_tipologia.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# --- Figura 3: series (internacoes, obitos, CAPS AD)
sih = pd.read_parquet(T / "internacoes.parquet").groupby("ano")["n_internacoes"].sum()
obi = pd.read_parquet(T / "obitos.parquet").groupby("ano")["n_obitos"].sum()
ad = pd.read_parquet(T / "servicos.parquet").query("eh_caps_ad and competencia != '202609'").groupby("ano")["cnes"].size()
fig, ax = plt.subplots(1, 3, figsize=(9.2, 2.9))
for a, s, t, c in ((ax[0], sih, "Internações F10–F19 (SIH/SUS)", "#1f5f8b"), (ax[1], obi, "Óbitos F10–F19 (SIM)", "#a23b3b"),
                   (ax[2], ad, "CAPS AD habilitados (dez.)", "#2f7d4f")):
    a.plot(s.index, s.values, marker="o", color=c)
    a.set_title(t, fontsize=9)
    a.set_xticks(list(s.index))
    a.tick_params(labelsize=8)
    a.grid(alpha=0.25)
    a.set_ylim(0, s.max() * 1.15)
fig.tight_layout()
fig.savefig(SAIDA / "cap4_series.png", dpi=200)
print("ok:", [p.name for p in SAIDA.glob("cap4_*.png")])

m = pd.read_parquet(T / "municipios.parquet")
for n in ("Espírito Santo do Pinhal", "Itapira", "Casa Branca", "Presidente Prudente", "Assis", "Cruzeiro"):
    r = m[m["nome"] == n]
    print(n, "->", r["nome_regiao"].tolist())
