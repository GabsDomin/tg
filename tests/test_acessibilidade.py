"""T2.3: E2SFCA verificado em um caso de brinquedo calculado a mao."""
import numpy as np
import pandas as pd

from tg.indicadores.acessibilidade import e2sfca, ica_municipal, peso


def test_peso_por_faixas():
    w = peso([5, 15, 16, 30, 31, 60, 61], [15, 30, 60], [1.0, 0.5, 0.25])
    assert w.tolist() == [1.0, 1.0, 0.5, 0.5, 0.25, 0.25, 0.0]


def test_e2sfca_caso_de_brinquedo():
    # Municipios X, Y, Z. Servicos s1 (em X, cap 100) e s2 (em Z, cap 50).
    # Distancias (km): X-s1 0 | Y-s1 10 | Z-s1 40 | X-s2 40 | Y-s2 30 | Z-s2 0
    # Faixas ate 15 (w=1) e ate 45 (w=0.5).
    dist = pd.DataFrame({"cod_mun6": list("XYZXYZ"), "cnes": ["s1"] * 3 + ["s2"] * 3,
                         "km": [0, 10, 40, 40, 30, 0]})
    oferta = pd.DataFrame({"cnes": ["s1", "s2"], "cap": [100.0, 50.0]})
    dem = pd.DataFrame({"cod_mun6": list("XYZ"), "E": [10.0, 20.0, 10.0]})
    A, R = e2sfca(oferta, dem, dist, [15, 45], [1.0, 0.5])
    # passo 1: s1 -> 10*1 + 20*1 + 10*0.5 = 35 ; R1 = 100/35
    #          s2 -> 10*0.5 + 20*0.5 + 10*1 = 25 ; R2 = 50/25 = 2
    assert np.isclose(R["s1"], 100 / 35) and np.isclose(R["s2"], 2.0)
    # passo 2: A_X = R1*1 + R2*0.5 ; A_Y = R1*1 + R2*0.5 ; A_Z = R1*0.5 + R2*1
    assert np.isclose(A["X"], 100 / 35 + 1.0) and np.isclose(A["Y"], 100 / 35 + 1.0)
    assert np.isclose(A["Z"], 50 / 35 + 2.0)


def test_servico_sem_demanda_no_raio_nao_gera_R_infinito():
    dist = pd.DataFrame({"cod_mun6": ["X"], "cnes": ["s"], "km": [100.0]})
    A, R = e2sfca(pd.DataFrame({"cnes": ["s"], "cap": [10.0]}), pd.DataFrame({"cod_mun6": ["X"], "E": [5.0]}),
                  dist, [15], [1.0])
    assert R["s"] == 0.0 or "s" not in R.index
    assert A["X"] == 0.0


def test_ica_municipal():
    of = pd.DataFrame({"cnes": ["a"], "cod_mun6": ["X"], "cap": [30.0]})
    dem = pd.DataFrame({"cod_mun6": ["X", "Y"], "E": [10.0, 5.0]})
    ica = ica_municipal(of, dem)
    assert ica["X"] == 3.0 and ica["Y"] == 0.0
