"""Criterios de aceite da T1.2 (servicos)."""
import pandas as pd
import pytest

from tg.config import CFG
from tg.tratamento.servicos import modalidade_ad, nome_parece_ad

ARQ = CFG.tratado / "servicos.parquet"


@pytest.mark.parametrize("nome,esperado", [
    ("CAPS ADULTO III MOOCA", False),            # armadilha: 'CAPS ADULTO' nao e AD
    ("CAPS ADULTO II JACANA DR LEONIDIO", False),
    ("CAPS AD III PARAISOPOLIS", True),
    ("CAPSAD EMBU", True),
    ("CAPS A D CENTRO PSICOSSOCIAL ALCOOL E DROGAS", True),
    ("CENTRO DE ATENCAO PSICOSSOCIAL ALCOOL E DROGAS", True),
    ("CAPS III AD ESPACO FERNANDO RAMOS", True),
    ("CAPS INFANTOJUVENIL II", False),
])
def test_nome_parece_ad(nome, esperado):
    assert nome_parece_ad(nome) is esperado


def test_modalidade_ad_precedencia():
    assert modalidade_ad(("0618", "0637")) == "AD IV"
    assert modalidade_ad(("0635",)) == "AD III"
    assert modalidade_ad(("0619",)) == "AD"
    assert modalidade_ad(("0618", "0620")) is None


@pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py servicos")
class TestTabela:
    def setup_method(self):
        self.s = pd.read_parquet(ARQ)

    def test_reproduz_achado_a2(self):
        ad = self.s[(self.s.competencia == "202609") & self.s.eh_caps_ad]
        assert len(ad) == 123 and ad["cod_mun6"].nunique() == 83

    def test_toda_linha_tem_coordenada_e_origem(self):
        assert self.s[["lat", "lon", "origem_coord"]].notna().all().all()

    def test_caps_ad_sempre_tem_modalidade(self):
        assert self.s.loc[self.s.eh_caps_ad, "modalidade_ad"].notna().all()

    def test_todas_as_competencias_presentes(self):
        assert set(self.s.competencia) == set(CFG.competencias_cnes)

    def test_chave_unica_por_competencia(self):
        assert not self.s.duplicated(["competencia", "cnes"]).any()
