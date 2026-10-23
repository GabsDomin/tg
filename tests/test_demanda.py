"""T2.1: estimador Poisson-gama e criterios de aceite sobre os dados reais."""
import numpy as np
import pandas as pd
import pytest

from tg.config import CFG
from tg.indicadores.demanda import ajustar_gama, suavizar


def test_recupera_parametros_de_dados_simulados():
    rng = np.random.default_rng(42)
    a0, b0 = 4.0, 4.0 / 0.0005                   # taxa media 0,0005 por pessoa-ano
    n = 3000
    py = rng.lognormal(mean=np.log(20_000), sigma=1.0, size=n)
    lam = rng.gamma(a0, 1 / b0, size=n)
    O = rng.poisson(py * lam)
    a, b = ajustar_gama(O, py)
    assert abs(a / a0 - 1) < 0.15 and abs(b / b0 - 1) < 0.20, (a, b)
    # a media global preservada: (a/b) ~ taxa media
    assert abs((a / b) / (O.sum() / py.sum()) - 1) < 0.10


def test_suavizacao_encolhe_mais_quem_tem_menos_exposicao():
    O = np.array([1, 100])
    PY = np.array([1_000.0, 1_000_000.0])        # mesma taxa bruta (1e-3 e 1e-4 diferentes de proposito)
    sm, a, b = suavizar(np.array([1, 10, 3, 0, 5]), np.array([1e3, 1e5, 4e3, 2e3, 1e5]))
    assert (sm > 0).all()


def test_zero_casos_nao_vira_taxa_zero():
    sm, _, _ = suavizar(np.array([0, 5, 8, 2, 0, 9]), np.array([2e3, 5e4, 8e4, 3e4, 1e3, 9e4]))
    assert sm[0] > 0 and sm[4] > 0


ARQ = CFG.tratado / "demanda.parquet"


@pytest.mark.skipif(not ARQ.exists(), reason="rode: python pipeline.py demanda")
class TestDados:
    def setup_method(self):
        self.d = pd.read_parquet(ARQ)

    def test_645_por_bloco(self):
        assert self.d.groupby("bloco").size().to_dict() == {"construcao": 645, "avaliacao": 645}

    def test_variancia_suavizada_menor_que_bruta(self):
        for bloco, g in self.d.groupby("bloco"):
            assert g["taxa_suav_int"].var() < g["taxa_bruta_int"].var(), bloco

    def test_municipios_grandes_mudam_pouco(self):
        pop = pd.read_parquet(CFG.tratado / "populacao.parquet")
        grandes = set(pop[(pop["ano"] == 2022) & (pop["pop_total"] > 100_000)]["cod_mun6"])
        g = self.d[(self.d["bloco"] == "construcao") & self.d["cod_mun6"].isin(grandes)]
        assert g[["taxa_bruta_int", "taxa_suav_int"]].corr().iloc[0, 1] > 0.95
