"""As associacoes socioeconomicas dos clusters sobrevivem ao controle por porte populacional?"""
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

from tg.config import CFG

cl = pd.read_parquet(CFG.tratado / "clusters.parquet")
ce = pd.read_parquet(CFG.tratado / "censo.parquet")
d = cl.merge(ce, on="cod_mun6")
d["lpop"] = np.log(d["pop_2024"])


def parcial(x, y, z):
    rx, ry, rz = (rankdata(v) for v in (x, y, z))
    res = lambda a: a - np.polyval(np.polyfit(rz, a, 1), rz)
    return spearmanr(res(rx), res(ry))


print("Spearman de 'acesso' (E2SFCA) com cada variavel: bruta | parcial controlando log(populacao)")
for v in ("renda_mediana", "anos_estudo", "analfabetismo_pct", "esgoto_rede_pct", "densidade_hab_km2"):
    b = spearmanr(d["acesso"], d[v])
    p = parcial(d["acesso"].values, d[v].values, d["lpop"].values)
    print(f"  {v:<20} bruta {b[0]:+.2f} (p={b[1]:.1e}) | parcial {p[0]:+.2f} (p={p[1]:.1e})")

print("\nSpearman de 'taxa_int' (internacao) com cada variavel: bruta | parcial")
for v in ("renda_mediana", "anos_estudo", "analfabetismo_pct", "esgoto_rede_pct"):
    b = spearmanr(d["taxa_int"], d[v])
    p = parcial(d["taxa_int"].values, d[v].values, d["lpop"].values)
    print(f"  {v:<20} bruta {b[0]:+.2f} | parcial {p[0]:+.2f} (p={p[1]:.1e})")

print("\nDentro dos municipios pequenos (< 15 mil hab.), grupo 2 (sem registro) x grupo 3 (tratados fora):")
peq = d[(d["pop_2024"] < 15000) & d["cluster"].isin([2, 3])]
for v in ("renda_mediana", "anos_estudo", "analfabetismo_pct"):
    a, b = (peq[peq["cluster"] == k][v] for k in (2, 3))
    print(f"  {v:<20} mediana g2={a.median():.1f} (n={len(a)}) | g3={b.median():.1f} (n={len(b)})")

print("\nDunn/Holm: pares de clusters com p ajustado >= 0,05 (NAO distinguiveis):")
for v in ("renda_mediana", "anos_estudo", "analfabetismo_pct", "esgoto_rede_pct", "densidade_hab_km2"):
    m = pd.read_csv(CFG.tratado / f"clusters_dunn_{v}.csv", index_col=0)
    m.columns = m.columns.astype(int)
    nd = [f"{i}-{j}" for i in m.index for j in m.columns if i < j and m.loc[i, j] >= 0.05]
    print(f"  {v:<20}", nd or "todos distinguiveis")
