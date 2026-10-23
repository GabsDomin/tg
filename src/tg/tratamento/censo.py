"""Variaveis socioeconomicas do Censo 2022 por municipio (SIDRA). Usadas SO para caracterizar clusters.

Tabelas (conferidas nos metadados em 23/10/2026; categoria 'Total' em todas as demais classificacoes):
  6805  var 1000381  % domicilios com esgoto por 'Rede geral ou pluvial' (classif 11558 = 72110)
  10289 var 13537    rendimento nominal mensal MEDIANO de todos os trabalhos, 14+ (R$)
  10062 var 13285    media de anos de estudo, 11+
  10135 var 10267    taxa de analfabetismo, 15+ (%)
Valores suprimidos pelo IBGE ('-', '...', 'X') viram NaN e sao contados.
"""
import numpy as np
import pandas as pd

from tg.coleta import ibge
from tg.config import CFG

TOTAIS = "2[6794]|86[95251]"
TABELAS = {
    "esgoto_rede_pct": (6805, 1000381, "11558[72110]"),
    "renda_mediana": (10289, 13537, TOTAIS),
    "anos_estudo": (10062, 13285, "58[95253]|" + TOTAIS),
    "analfabetismo_pct": (10135, 10267, "58[95253]|" + TOTAIS + "|839[46583]"),
}


def _tabela(nome, agregado, variavel, classif):
    d = pd.DataFrame(ibge.sidra(agregado, variavel, [2022], classificacao=classif, nome_cache=f"sidra_{agregado}_{variavel}.json"))
    d[nome] = pd.to_numeric(d["valor"], errors="coerce")
    d["cod_mun6"] = d["cod7"].str[:6]
    assert d["cod_mun6"].is_unique, f"{nome}: mais de uma linha por municipio (classificacao incompleta?)"
    return d.set_index("cod_mun6")[nome]


def construir_censo():
    cols = [_tabela(n, *a) for n, a in TABELAS.items()]
    c = pd.concat(cols, axis=1)
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet").set_index("cod_mun6")
    pop = pd.read_parquet(CFG.tratado / "populacao.parquet").query("ano == 2022").set_index("cod_mun6")["pop_total"]
    c["densidade_hab_km2"] = pop / mun["area_km2"]
    return c.reindex(mun.index).reset_index()
