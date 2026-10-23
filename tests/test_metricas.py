"""Metricas conferidas com valores calculados a mao (e contra o sklearn)."""
import numpy as np
import pytest

from tg.avaliacao import metricas as mt


def test_dcg_manual():
    # rels [3,2,0]: (2^3-1)/log2(2) + (2^2-1)/log2(3) + 0 = 7 + 3/1.58496 = 8.89279
    assert mt.dcg([3, 2, 0], 3) == pytest.approx(7 + 3 / np.log2(3))


def test_ndcg_ordem_ideal_e_pior():
    rels = [0, 1, 3, 0]
    ideal = sorted(rels, reverse=True)
    assert mt.ndcg_at_k(ideal, rels, 4) == pytest.approx(1.0)
    pior = [0, 0, 1, 3]
    assert mt.ndcg_at_k(pior, rels, 4) < 1.0


def test_ndcg_contra_sklearn_com_relevancia_binaria():
    """sklearn usa ganho LINEAR (rel); aqui o ganho e 2^rel-1. Coincidem so para rel em {0,1}."""
    sklearn = pytest.importorskip("sklearn.metrics")
    rels = np.array([0, 1, 1, 0, 1])
    scores = np.array([0.1, 0.5, 0.4, 0.9, 0.3])
    o = mt.ordenar(scores, np.arange(5))
    assert mt.ndcg_at_k(rels[o], rels, 5) == pytest.approx(sklearn.ndcg_score([rels], [scores], k=5))


def test_ganho_exponencial_pesa_mais_o_muito_relevante():
    # ordem ruim com rel [1, 3]: ganho exp = (1 + 7/log2(3)) vs ideal (7 + 1/log2(3))
    ruim = mt.ndcg_at_k([1, 3], [1, 3], 2)
    assert ruim == pytest.approx((1 + 7 / np.log2(3)) / (7 + 1 / np.log2(3)))


def test_mrr_e_precisao():
    assert mt.mrr([0, 0, 2, 1]) == pytest.approx(1 / 3)
    assert mt.mrr([0, 0, 0]) == 0.0
    assert mt.precision_at_k([1, 0, 2, 0, 0], 5) == pytest.approx(2 / 5)


def test_desempate_determinista_por_menor_km():
    scores = [1.0, 1.0, 1.0]
    km = [30, 10, 20]
    assert mt.ordenar(scores, km).tolist() == [1, 2, 0]


def test_ndcg_sem_relevante_e_zero():
    assert mt.ndcg_at_k([0, 0], [0, 0], 2) == 0.0
