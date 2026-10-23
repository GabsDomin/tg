"""T1.6: sanidade da distancia."""
import numpy as np
import pandas as pd
import pytest

from tg.config import CFG
from tg.tratamento.distancias import haversine_km


def test_haversine_conhecido():
    # Sao Paulo (Se) -> Rio de Janeiro (Centro): ~358 km em linha reta
    d = haversine_km(-23.55, -46.63, -22.91, -43.17)
    assert 350 < float(d) < 365


def test_haversine_zero_e_simetria():
    assert float(haversine_km(-23.5, -46.6, -23.5, -46.6)) == 0.0
    a = haversine_km(-23.5, -46.6, -22.0, -47.0)
    b = haversine_km(-22.0, -47.0, -23.5, -46.6)
    assert np.isclose(a, b)


ARQ = CFG.tratado / "distancias.parquet"


@pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py distancias")
def test_santana_de_parnaiba_para_capital():
    d = pd.read_parquet(ARQ)
    s = pd.read_parquet(CFG.tratado / "servicos.parquet")
    # servicos da capital (355030): o mais proximo de Santana de Parnaiba (353440)
    cnes_capital = set(s.loc[s["cod_mun6"] == "355030", "cnes"])
    km = d[(d["cod_mun6"] == "353440") & d["cnes"].isin(cnes_capital)]["km"].min()
    assert 5 < km < 45, km


@pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py distancias")
def test_sem_distancia_negativa_e_dentro_do_raio():
    d = pd.read_parquet(ARQ)
    assert (d["km"] >= 0).all() and (d["km"] <= 200).all()
