"""Validacao externa do E2SFCA SEM o vies mecanico de persistencia da demanda.

Problema: A_m (2019-22) leva E_m (demanda do proprio municipio) no denominador; como a demanda
persiste (2019-22 -> 2023-24), uma correlacao negativa A_m x internacao futura apareceria mesmo que
a oferta nao tivesse efeito algum. Controles:
  (a) correlacao PARCIAL: tira de ambos o efeito da demanda do bloco anterior (persistencia);
  (b) indice de OFERTA pura S_m (sem demanda): se S_m nao se associa, o resultado de A_m e mecanico.
"""
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

from tg.config import CFG

ac = pd.read_parquet(CFG.tratado / "acessibilidade.parquet")
dem = pd.read_parquet(CFG.tratado / "demanda.parquet")
pop22 = pd.read_parquet(CFG.tratado / "populacao.parquet").query("ano == 2022").set_index("cod_mun6")["pop_total"]


def media_bloco(camada, col):
    x = ac[(ac["camada"] == camada) & ac["ano"].isin(CFG.anos_construcao)]
    return x.groupby("cod_mun6")[col].mean()


def parcial(x, y, z):
    """Spearman parcial de x e y controlando z (residuos de postos)."""
    rx, ry, rz = (rankdata(v) for v in (x, y, z))
    def res(a):
        b = np.polyfit(rz, a, 1)
        return a - np.polyval(b, rz)
    return spearmanr(res(rx), res(ry))


y_av = dem[dem["bloco"] == "avaliacao"].set_index("cod_mun6")["taxa_suav_int"]
y_co = dem[dem["bloco"] == "construcao"].set_index("cod_mun6")["taxa_suav_int"]
y_av_w = dem[dem["bloco"] == "avaliacao"].set_index("cod_mun6")["taxa_suav_int_w99"]
y_co_w = dem[dem["bloco"] == "construcao"].set_index("cod_mun6")["taxa_suav_int_w99"]
ob_av = dem[dem["bloco"] == "avaliacao"].set_index("cod_mun6")["taxa_suav_obito"]
ob_co = dem[dem["bloco"] == "construcao"].set_index("cod_mun6")["taxa_suav_obito"]

print("persistencia da demanda (Spearman taxa 2019-22 x 2023-24): int =",
      round(spearmanr(y_co, y_av)[0], 2), "| obito =", round(spearmanr(ob_co, ob_av)[0], 2), "\n")

for camada in ("O1", "O2", "O3"):
    A = media_bloco(camada, "A_r60")
    S = media_bloco(camada, "S_r60")
    print(f"--- camada {camada}  (municipios com A>0: {(A > 0).sum()}, S>0: {(S > 0).sum()})")
    for rot, y, y0 in (("internacao", y_av, y_co), ("internacao w99", y_av_w, y_co_w), ("obito", ob_av, ob_co)):
        i = A.index
        bruta_A = spearmanr(A, y.reindex(i))
        par_A = parcial(A.values, y.reindex(i).values, y0.reindex(i).values)
        bruta_S = spearmanr(S, y.reindex(i))
        par_S = parcial(S.values, y.reindex(i).values, y0.reindex(i).values)
        print(f"  {rot:<15} A: bruta {bruta_A[0]:+.2f} (p={bruta_A[1]:.3f}) parcial {par_A[0]:+.2f} (p={par_A[1]:.3f})"
              f" | S(oferta): bruta {bruta_S[0]:+.2f} parcial {par_S[0]:+.2f} (p={par_S[1]:.3f})")

print("\nsensibilidade ao raio (Spearman entre rankings de A, O1, media 2019-22):")
a30, a60, a90 = (media_bloco("O1", f"A_r{r}") for r in (30, 60, 90))
print(f"  30x60 {spearmanr(a30, a60)[0]:.3f} | 60x90 {spearmanr(a60, a90)[0]:.3f} | 30x90 {spearmanr(a30, a90)[0]:.3f}")

print("\nmunicipios acima de 20 mil hab. (parcial, O1, r60):")
grandes = pop22[pop22 > 20000].index.intersection(media_bloco("O1", "A_r60").index)
A = media_bloco("O1", "A_r60").reindex(grandes)
r = parcial(A.values, y_av.reindex(grandes).values, y_co.reindex(grandes).values)
print(f"  n={len(grandes)}  parcial A x internacao: {r[0]:+.2f} (p={r[1]:.3f})")

print("\nrelacao A_rel (1 = media estadual), O1, r60, media 2019-22:")
rel = media_bloco("O1", "A_r60_rel")
print("  municipios com A_rel < 0,5:", int((rel < 0.5).sum()), "| < 1:", int((rel < 1).sum()), "| = 0:", int((rel == 0).sum()))
