"""Criterios de aceite da T1.5 e a regra de privacidade (nenhum identificador em dados/tratado)."""
import pandas as pd
import pytest

from tg.config import CFG

CARGA = CFG.tratado / "raas_carga.parquet"
SERV = CFG.tratado / "servicos.parquet"


@pytest.mark.skipif(not (CARGA.exists() and SERV.exists()), reason="rode: python pipeline.py raas servicos")
def test_dez2024_reproduz_exploracao():
    """Exploracao (inspecionar_fluxos.py): 23.309 pacientes unicos em CAPS AD habilitados (set/2026).
    Aqui soma-se por CAPS, entao um paciente em 2 CAPS conta 2x: tolera +3%."""
    ad = set(pd.read_parquet(SERV).query("competencia == '202609' and eh_caps_ad")["cnes"])
    c = pd.read_parquet(CARGA).query("ano == 2024 and mes == 12")
    soma = c[c["cnes"].isin(ad)]["pacientes_unicos"].sum()
    assert 23309 * 0.99 <= soma <= 23309 * 1.03, soma


@pytest.mark.skipif(not CARGA.exists(), reason="rode: python pipeline.py raas")
def test_f1x_nunca_excede_total():
    c = pd.read_parquet(CARGA)
    assert (c["pacientes_f1x"] <= c["pacientes_unicos"]).all()


def test_nenhuma_tabela_tratada_tem_coluna_proibida():
    proibidas = {c.upper() for c in CFG.colunas_proibidas_publicar}
    for arq in CFG.tratado.glob("*.parquet"):
        cols = {c.upper() for c in pd.read_parquet(arq).columns}
        assert not (cols & proibidas), (arq.name, cols & proibidas)
