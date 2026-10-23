"""Criterios de aceite da T1.1 (municipios e populacao)."""
import pandas as pd
import pytest

from tg.coleta import ibge
from tg.config import CFG

MUN = CFG.tratado / "municipios.parquet"
POP = CFG.tratado / "populacao.parquet"
pytestmark = pytest.mark.skipif(not (MUN.exists() and POP.exists()), reason="rode: python pipeline.py territorio")


def test_645_municipios_unicos_e_regiao_preenchida():
    m = pd.read_parquet(MUN)
    assert len(m) == 645 and m["cod_mun6"].is_unique
    assert m["regiao_saude"].notna().all()
    assert m[["lat", "lon", "area_km2"]].notna().all().all()


def test_coordenadas_dentro_de_sp():
    m = pd.read_parquet(MUN)
    assert m["lat"].between(-25.4, -19.7).all() and m["lon"].between(-53.2, -44.1).all()


def test_populacao_2022_bate_com_censo():
    p = pd.read_parquet(POP)
    est = p.loc[p["ano"] == 2022, "pop_total"].sum()
    censo = sum(float(r["valor"]) for r in ibge.sidra(4714, 93, [2022], nome_cache="sidra_4714_pop.json"))
    assert abs(est / censo - 1) < 0.01, (est, censo)


def test_populacao_cobre_todos_os_anos_e_municipios():
    p = pd.read_parquet(POP)
    assert len(p) == 645 * 6
    assert p[["pop_total", "pop_15mais"]].notna().all().all()
    assert p["prop_15mais"].between(0.5, 1).all()
