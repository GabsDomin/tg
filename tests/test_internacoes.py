"""Criterios de aceite da T1.3: totais anuais contra o TabNet oficial (consulta de 23/10/2026).

TabNet SIH/SUS, por local de residencia, SP, ano de processamento, Internacoes,
Lista Morb CID-10 = 133 + 134 (F10-F19). Script: scripts/exploracao/conferir_tabnet_sih.py
"""
import pandas as pd
import pytest

from tg.config import CFG

ARQ = CFG.tratado / "internacoes.parquet"
TABNET = {2019: 19414, 2020: 15435, 2021: 15071, 2022: 17293, 2023: 22369, 2024: 24821}
pytestmark = pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py internacoes")


def test_total_anual_bate_com_tabnet_em_2pct():
    por_ano = pd.read_parquet(ARQ).groupby("ano")["n_internacoes"].sum()
    for ano, ref in TABNET.items():
        assert abs(por_ano[ano] / ref - 1) < 0.02, ano


def test_so_f10_a_f19_e_so_residentes_de_sp():
    d = pd.read_parquet(ARQ)
    assert set(d["cid3"]) <= {f"F1{i}" for i in range(10)}
    assert d["cod_mun6"].str.startswith("35").all()


def test_longa_permanencia_separada_das_internacoes():
    d = pd.read_parquet(ARQ)
    assert d["n_aih_longa"].sum() > 0 and (d["n_internacoes"] >= 0).all()
