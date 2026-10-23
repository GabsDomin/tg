"""Conjunto de consultas da porta de referencia: sem vazamento temporal e com o tamanho documentado."""
import json

import numpy as np
import pandas as pd
import pytest

from tg.avaliacao import experimento as ex, referencia as rf
from tg.config import CFG

pytestmark = pytest.mark.skipif(not (CFG.tratado / "raas_fluxos.parquet").exists(), reason="rode o pipeline antes")


@pytest.fixture(scope="module")
def pares():
    return rf.construir_pares()


def test_219_consultas_e_toda_consulta_tem_relevante(pares):
    assert pares["origem"].nunique() == 219
    assert (pares.groupby("origem")["rel"].max() > 0).all()


def test_origens_nao_tem_caps_ad_proprio(pares):
    srv = pd.read_parquet(CFG.tratado / "servicos.parquet").query("competencia == '202212' and eh_caps_ad")
    assert not set(pares["origem"]) & set(srv["cod_mun6"])


def test_candidatos_dentro_do_raio_e_componentes_em_0_1(pares):
    assert (pares["km"] <= rf.RAIO_KM).all()
    assert pares[rf.COMPONENTES].min().min() >= 0 and pares[rf.COMPONENTES].max().max() <= 1.0 + 1e-9


def test_atributos_de_servico_nao_usam_2023_24():
    """abertura/folga de avaliacao (ano_ref=2022) devem ser identicos se os fluxos de 2023-24 mudarem."""
    sv, h = rf.atributos_servicos()
    assert set(h["ano"]) <= set(CFG.anos_construcao)


def test_grade_de_pesos_soma_um():
    ws = list(ex.grade_pesos(5))
    assert len(ws) == 1001 and all(abs(w.sum() - 1) < 1e-9 for w in ws)


def test_pesos_de_producao_gravados_e_validos():
    arq = CFG.tratado / "pesos_referencia.json"
    if not arq.exists():
        pytest.skip("rode: python pipeline.py avaliacao_referencia")
    p = json.loads(arq.read_text(encoding="utf-8"))
    assert abs(sum(p["pesos"].values()) - 1) < 1e-9 and p["n_consultas"] == 219
