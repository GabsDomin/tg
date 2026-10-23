"""T2.4/T2.5: os rotulos so valem se o perfil dos grupos continuar o mesmo."""
import numpy as np
import pandas as pd
import pytest

from tg.clusters import kmeans as km
from tg.config import CFG

ARQ = CFG.tratado / "clusters.parquet"
pytestmark = pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py clusters")


@pytest.fixture(scope="module")
def c():
    return pd.read_parquet(ARQ)


def test_645_municipios_5_grupos_nenhum_minusculo(c):
    assert len(c) == 645 and set(c["cluster"]) == {1, 2, 3, 4, 5}
    assert c["cluster"].value_counts().min() >= 30


def test_perfil_confere_com_os_rotulos(c):
    med = c.groupby("cluster")[km.VARS + ["pop_2024"]].median()
    assert med.loc[2, "atend_caps"] == 0                      # sem atendimento registrado em CAPS
    assert med.loc[3, "frac_fora"] >= 0.9                     # tratados em CAPS de outro municipio
    assert med.loc[2, "pop_2024"] < 20_000 and med.loc[3, "pop_2024"] < 20_000
    assert med.loc[4, "pop_2024"] > 80_000 and med.loc[4, "dist_ad"] < 15   # grandes centros, CAPS perto
    assert med.loc[1, "taxa_int"] > med.loc[5, "taxa_int"]    # polos pressionados x baixa internacao
    assert med.loc[5, "acesso"] > med.loc[1, "acesso"]


def test_reproducivel():
    a = km.ajustar(km.construir_features(), 5)
    b = km.ajustar(km.construir_features(), 5)
    assert (a["cluster"].values == b["cluster"].values).all()


def test_features_sem_nulos():
    f = km.construir_features()
    assert f[km.VARS].notna().all().all() and np.isfinite(f[km.VARS]).all().all()


CEN = CFG.tratado / "censo.parquet"


@pytest.mark.skipif(not CEN.exists(), reason="rode: python pipeline.py censo")
def test_censo_completo_e_plausivel():
    d = pd.read_parquet(CEN)
    assert len(d) == 645 and d.drop(columns="cod_mun6").notna().all().all()
    assert d["analfabetismo_pct"].between(0, 25).all() and d["anos_estudo"].between(3, 15).all()
