"""Caracterizacao socioeconomica dos clusters: Kruskal-Wallis, tamanho de efeito (epsilon^2) e Dunn/Holm.

epsilon^2 = H / (n - 1) (aproximacao usual para Kruskal-Wallis). p global ajustado por Holm
ENTRE as variaveis; Dunn pareado ajustado por Holm dentro de cada variavel.
Resultados descritivos/associativos: NAO indicam causalidade.
"""
import numpy as np
import pandas as pd
import scikit_posthocs as sp
from scipy.stats import kruskal
from statsmodels.stats.multitest import multipletests  # noqa: F401  (scikit-posthocs depende de statsmodels)

VARS_SOCIO = ["renda_mediana", "anos_estudo", "analfabetismo_pct", "esgoto_rede_pct", "densidade_hab_km2"]


def _iqr(x):
    q = x.quantile([.25, .5, .75])
    return f"{q[.5]:,.1f} ({q[.25]:,.1f}–{q[.75]:,.1f})"


def caracterizar(df, socio=VARS_SOCIO):
    linhas, pareados = [], {}
    for v in socio:
        d = df[["cluster", v]].dropna()
        grupos = [g[v].values for _, g in d.groupby("cluster")]
        H, p = kruskal(*grupos)
        n = len(d)
        linhas.append({"variavel": v, "n": n, "ausentes": int(df[v].isna().sum()), "H": H, "p": p, "epsilon2": H / (n - 1),
                       **{f"cluster_{k}": _iqr(g[v]) for k, g in d.groupby("cluster")}})
        pareados[v] = sp.posthoc_dunn(d, val_col=v, group_col="cluster", p_adjust="holm")
    t = pd.DataFrame(linhas)
    from statsmodels.stats.multitest import multipletests
    t["p_holm"] = multipletests(t["p"], method="holm")[1]
    return t, pareados
