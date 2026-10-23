"""Metricas de ranqueamento por consulta: NDCG@k, MRR, P@k. Empates: ordem por menor km (determinista)."""
import numpy as np


def ordenar(scores, desempate):
    """indices em ordem decrescente de score; empate resolvido por `desempate` crescente."""
    return np.lexsort((desempate, -np.asarray(scores, float)))


def dcg(rels, k):
    r = np.asarray(rels, float)[:k]
    return float(((2 ** r - 1) / np.log2(np.arange(2, len(r) + 2))).sum())


def ndcg_at_k(rels_ordenadas, rels_todas, k):
    ideal = dcg(sorted(rels_todas, reverse=True), k)
    return dcg(rels_ordenadas, k) / ideal if ideal > 0 else 0.0


def mrr(rels_ordenadas):
    for i, r in enumerate(rels_ordenadas, 1):
        if r > 0:
            return 1.0 / i
    return 0.0


def precision_at_k(rels_ordenadas, k):
    r = np.asarray(rels_ordenadas)[:k]
    return float((r > 0).sum() / k)


def avaliar_consulta(rels, scores, desempate, k=5):
    o = ordenar(scores, desempate)
    r = np.asarray(rels)[o]
    return {"ndcg": ndcg_at_k(r, rels, k), "mrr": mrr(r), "p": precision_at_k(r, k)}
