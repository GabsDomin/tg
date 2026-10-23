"""Imagem de pre-visualizacao (Open Graph) 1200x630: mapa da tipologia + titulo. Saida: web/og.png"""
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from tg.config import CFG

malha = gpd.read_file(CFG.bruto / "malha_sp_municipios.geojson")
malha["cod_mun6"] = malha["codarea"].astype(str).str[:6]
malha["geometry"] = malha.geometry.simplify(0.004, preserve_topology=True)
cl = pd.read_parquet(CFG.tratado / "clusters.parquet")
g = malha.merge(cl[["cod_mun6", "cluster"]], on="cod_mun6")
CAT = {1: "#d55e00", 2: "#56b4e9", 3: "#0072b2", 4: "#009e73", 5: "#e6c200"}

fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor="#1b2024")
ax = fig.add_axes([0.46, 0.04, 0.52, 0.92])
g.plot(ax=ax, color=[CAT[c] for c in g["cluster"]], edgecolor="#1b2024", linewidth=0.2)
ax.set_axis_off()
fig.text(0.05, 0.80, "Desertos de cuidado em", color="#e8eaeb", fontsize=30, fontweight="bold")
fig.text(0.05, 0.71, "álcool e outras drogas", color="#e8eaeb", fontsize=30, fontweight="bold")
fig.text(0.05, 0.60, "Estado de São Paulo · 645 municípios", color="#9aa5ab", fontsize=17)
fig.text(0.05, 0.40, "Motor de busca + mapa", color="#6fb1dc", fontsize=22, fontweight="bold")
fig.text(0.05, 0.33, "Onde há CAPS AD, onde falta\ne para onde encaminhar.", color="#e8eaeb", fontsize=17, linespacing=1.5)
fig.text(0.05, 0.08, "Versão preliminar · TG FATEC Santana de Parnaíba", color="#9aa5ab", fontsize=13)
fig.savefig(CFG.raiz / "web" / "og.png", facecolor=fig.get_facecolor())
print("ok", (CFG.raiz / "web" / "og.png").stat().st_size // 1024, "KB")
