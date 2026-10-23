"""T2.2/T2.3 sobre os dados reais."""
import pandas as pd
import pytest

from tg.config import CFG

ARQ = CFG.tratado / "acessibilidade.parquet"
pytestmark = pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py acessibilidade")


def test_cobertura_completa():
    a = pd.read_parquet(ARQ)
    assert len(a) == 3 * 6 * 645
    assert set(a["camada"]) == {"O1", "O2", "O3"}


def test_acessibilidade_nao_negativa_e_sem_nulos():
    a = pd.read_parquet(ARQ)
    cols = [c for c in a.columns if c.startswith("A_r") or c.startswith("S_")]
    assert (a[cols] >= 0).all().all() and a[cols].notna().all().all()


def test_camadas_sao_aninhadas_na_oferta():
    """Mais camadas = mais oferta: S(O1) <= S(O2) e S(O1) <= S(O3) em cada municipio-ano."""
    a = pd.read_parquet(ARQ).pivot_table(index=["cod_mun6", "ano"], columns="camada", values="S_r60")
    assert (a["O1"] <= a["O2"] + 1e-9).all() and (a["O1"] <= a["O3"] + 1e-9).all()


def test_ica_municipal_zero_onde_nao_ha_caps_ad():
    a = pd.read_parquet(ARQ).query("camada == 'O1' and ano == 2022")
    s = pd.read_parquet(CFG.tratado / "servicos.parquet").query("competencia == '202212' and eh_caps_ad")
    sem = set(a["cod_mun6"]) - set(s["cod_mun6"])
    assert (a[a["cod_mun6"].isin(sem)]["ICA"].fillna(0) == 0).all()
