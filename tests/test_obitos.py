"""T1.4: totais anuais contra o TabNet de mortalidade (consulta de 23/10/2026; diferenca 0,0%).
scripts/exploracao/conferir_tabnet_sim.py -- Grupo CID-10 55 (F10-F19), obitos por residencia, SP."""
import pandas as pd
import pytest

from tg.config import CFG

ARQ = CFG.tratado / "obitos.parquet"
TABNET = {2019: 1015, 2020: 1749, 2021: 1722, 2022: 1510, 2023: 1402, 2024: 1379}
pytestmark = pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py obitos")


def test_total_anual_bate_com_tabnet():
    por_ano = pd.read_parquet(ARQ).groupby("ano")["n_obitos"].sum()
    for ano, ref in TABNET.items():
        assert abs(por_ano[ano] / ref - 1) < 0.02, ano


def test_so_f10_a_f19():
    assert set(pd.read_parquet(ARQ)["cid3"]) <= {f"F1{i}" for i in range(10)}
