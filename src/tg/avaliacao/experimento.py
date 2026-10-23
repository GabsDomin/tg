"""Experimento da porta de referencia: baselines, sistema com pesos calibrados, ablacao, bootstrap.

Protocolo
- Consultas divididas ao acaso em DESENVOLVIMENTO (calibra pesos) e TESTE (so reporta), 50/50, semente fixa.
- Robustez: 50 divisoes repetidas (media do NDCG@5 no teste).
- Sistema = soma ponderada de componentes em [0,1]; pesos escolhidos em grade (passo 0,1, soma 1) no DEV.
- IC 95% da diferenca de NDCG@5 sistema - baseline por bootstrap pareado sobre as consultas de teste.
"""
import itertools

import numpy as np
import pandas as pd

from tg.avaliacao import metricas as mt
from tg.avaliacao.referencia import COMPONENTES

K = 5
SEMENTE = 20261023
PASSO = 0.1


def _grupos(d):
    """lista de dicts por consulta com arrays alinhados."""
    out = []
    for o, g in d.groupby("origem"):
        out.append({"origem": o, "rel": g["rel"].values, "km": g["km"].values, "X": g[COMPONENTES].values,
                    "hist": g["hist"].values, "pop": g["pop_destino"].values})
    return out


def grade_pesos(n, passo=PASSO):
    m = int(round(1 / passo))
    for c in itertools.product(range(m + 1), repeat=n - 1):
        if sum(c) <= m:
            yield np.array(list(c) + [m - sum(c)]) / m


def _metricas(grupos, scorer):
    r = [mt.avaliar_consulta(g["rel"], scorer(g), g["km"], K) for g in grupos]
    return pd.DataFrame(r)


def baselines():
    return {
        "so distancia": lambda g: -g["km"],
        "so populacao do destino": lambda g: g["pop"],
        "so mesma regiao (depois distancia)": lambda g: g["X"][:, COMPONENTES.index("mesma_regiao")],
        "persistencia (fluxo 2019-22)": lambda g: g["hist"],
    }


def sistema(pesos, comps=COMPONENTES):
    idx = [COMPONENTES.index(c) for c in comps]
    w = np.asarray(pesos, float)
    return lambda g: g["X"][:, idx] @ w


def hibrido(pesos):
    """sistema + historico (log, normalizado por consulta) como 6o componente."""
    def f(g):
        h = np.log1p(g["hist"]); h = h / h.max() if h.max() > 0 else h
        return g["X"] @ pesos[:-1] + pesos[-1] * h
    return f


def calibrar(grupos, comps=COMPONENTES, usar_hist=False):
    n = len(comps) + (1 if usar_hist else 0)
    melhor, w_melhor = -1, None
    for w in grade_pesos(n):
        scorer = hibrido(w) if usar_hist else sistema(w, comps)
        v = _metricas(grupos, scorer)["ndcg"].mean()
        if v > melhor + 1e-12:
            melhor, w_melhor = v, w
    return w_melhor, melhor


def dividir(grupos, semente=SEMENTE):
    rng = np.random.default_rng(semente)
    idx = rng.permutation(len(grupos))
    meio = len(grupos) // 2
    return [grupos[i] for i in idx[:meio]], [grupos[i] for i in idx[meio:]]


def bootstrap_diff(a, b, n=2000, semente=SEMENTE):
    rng = np.random.default_rng(semente)
    d = np.asarray(a) - np.asarray(b)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n)]
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def rodar(d):
    G = _grupos(d)
    dev, teste = dividir(G)
    res = {"n_consultas": len(G), "n_dev": len(dev), "n_teste": len(teste)}

    w, ndcg_dev = calibrar(dev)
    res["pesos"] = dict(zip(COMPONENTES, w.round(2)))
    res["ndcg_dev"] = ndcg_dev

    linhas, por_consulta = [], {}
    cand = {**baselines(), "SISTEMA (pesos calibrados)": sistema(w)}
    wh, _ = calibrar(dev, usar_hist=True)
    cand["SISTEMA + historico"] = hibrido(wh)
    res["pesos_hibrido"] = dict(zip(COMPONENTES + ["hist"], wh.round(2)))
    for nome, sc in cand.items():
        m = _metricas(teste, sc)
        por_consulta[nome] = m["ndcg"].values
        linhas.append({"metodo": nome, "NDCG@5": m["ndcg"].mean(), "MRR": m["mrr"].mean(), "P@5": m["p"].mean()})
    res["tabela"] = pd.DataFrame(linhas)

    base = "so distancia"
    res["diffs"] = {n: bootstrap_diff(por_consulta[n], por_consulta[base]) for n in por_consulta if n != base}

    # ablacao: remove um componente por vez e RECALIBRA no dev (justo: os demais pesos se reajustam)
    abl = []
    for c in COMPONENTES:
        comps = [x for x in COMPONENTES if x != c]
        wc, _ = calibrar(dev, comps)
        m = _metricas(teste, sistema(wc, comps))
        abl.append({"sem": c, "NDCG@5": m["ndcg"].mean(), "MRR": m["mrr"].mean(), "P@5": m["p"].mean()})
    res["ablacao"] = pd.DataFrame(abl)

    # estratos no teste: com historico x cold-start
    quente = [g for g in teste if ((g["rel"] > 0) & (g["hist"] > 0)).any()]
    frio = [g for g in teste if not ((g["rel"] > 0) & (g["hist"] > 0)).any()]
    est = []
    for rot, gs in (("com historico", quente), ("cold-start", frio)):
        for nome, sc in cand.items():
            est.append({"estrato": rot, "n": len(gs), "metodo": nome, "NDCG@5": _metricas(gs, sc)["ndcg"].mean()})
    res["estratos"] = pd.DataFrame(est)

    # robustez: 50 divisoes repetidas
    rep = {n: [] for n in ("so distancia", "persistencia (fluxo 2019-22)", "SISTEMA (pesos calibrados)")}
    for s in range(50):
        dv, ts = dividir(G, semente=1000 + s)
        wr, _ = calibrar(dv)
        for nome, sc in (("so distancia", baselines()["so distancia"]), ("persistencia (fluxo 2019-22)", baselines()["persistencia (fluxo 2019-22)"]),
                         ("SISTEMA (pesos calibrados)", sistema(wr))):
            rep[nome].append(_metricas(ts, sc)["ndcg"].mean())
    res["repeticoes"] = {k: (float(np.mean(v)), float(np.std(v))) for k, v in rep.items()}
    return res
