"""Demanda estimada por municipio: taxa de internacao F10-F19 suavizada por Bayes empirico.

Modelo Poisson-gama: O_i ~ Poisson(PY_i * lambda_i), lambda_i ~ Gamma(forma=a, taxa=b).
a e b sao estimados por maxima verossimilhanca marginal (binomial negativa). A media
a posteriori (O_i + a) / (PY_i + b) encolhe taxas de municipios pequenos em direcao a media estadual.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln

from tg.config import CFG

POR = 100_000


def _nll(theta, O, PY):
    a, b = np.exp(theta)
    ll = (gammaln(O + a) - gammaln(a) - gammaln(O + 1)
          + a * np.log(b / (b + PY)) + O * np.log(PY / (b + PY)))
    return -ll.sum()


def ajustar_gama(O, PY):
    """(a, b) por maxima verossimilhanca marginal. Inicia pelo metodo dos momentos."""
    O, PY = np.asarray(O, float), np.asarray(PY, float)
    ok = PY > 0
    O, PY = O[ok], PY[ok]
    m = O.sum() / PY.sum()
    # variancia das taxas brutas menos a parte de Poisson (m/PY), ponderada por PY
    taxas = O / PY
    v = np.average((taxas - m) ** 2, weights=PY) - m * len(O) / PY.sum()
    v = max(v, 1e-12)
    b0 = m / v
    a0 = m * b0
    res = minimize(_nll, np.log([a0, b0]), args=(O, PY), method="Nelder-Mead",
                   options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 2000})
    if not res.success:
        raise RuntimeError(f"ajuste Poisson-gama nao convergiu: {res.message}")
    return tuple(np.exp(res.x))


def suavizar(O, PY, a=None, b=None):
    """Media a posteriori da taxa (por pessoa-ano). Retorna (taxa_suavizada, a, b)."""
    O, PY = np.asarray(O, float), np.asarray(PY, float)
    if a is None:
        a, b = ajustar_gama(O, PY)
    return (O + a) / (PY + b), a, b


def construir_demanda():
    pop = pd.read_parquet(CFG.tratado / "populacao.parquet")
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")[["cod_mun6"]]
    blocos = {"construcao": CFG.anos_construcao, "avaliacao": CFG.anos_avaliacao}
    fontes = {"int": ("internacoes.parquet", "n_internacoes"), "obito": ("obitos.parquet", "n_obitos")}

    saida = []
    for bloco, anos in blocos.items():
        py = (pop[pop["ano"].isin(anos)].groupby("cod_mun6")["pop_15mais"].sum().rename("pessoas_ano"))
        base = mun.merge(py, on="cod_mun6", how="left")
        for sigla, (arq, col) in fontes.items():
            d = pd.read_parquet(CFG.tratado / arq)
            n = d[d["ano"].isin(anos)].groupby("cod_mun6")[col].sum().rename("n")
            t = base.merge(n, on="cod_mun6", how="left").fillna({"n": 0})
            sm, a, b = suavizar(t["n"], t["pessoas_ano"])
            base[f"n_{sigla}"] = t["n"].values
            base[f"taxa_bruta_{sigla}"] = (t["n"] / t["pessoas_ano"] * POR).values
            base[f"taxa_suav_{sigla}"] = sm * POR
            base[f"gama_a_{sigla}"], base[f"gama_b_{sigla}"] = a, b
        # robustez: caudas controladas por polos hospitalares (ver ARQUITETURA A22)
        base["taxa_suav_int_w99"] = base["taxa_suav_int"].clip(upper=base["taxa_suav_int"].quantile(0.99))
        base["bloco"] = bloco
        saida.append(base)
    return pd.concat(saida, ignore_index=True)
