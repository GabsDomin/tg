"""Avaliacao da PORTA DE REFERENCIA contra fluxos observados (SIA/PS 2023-24).

Consulta  : municipio de origem SEM CAPS AD habilitado em dez/2022 e com >=1 paciente F1x tratado em
            algum CAPS AD candidato em 2023-24.
Candidatos: CAPS AD habilitados em dez/2022 a ate RAIO_KM do origem.
Relevancia: pacientes F1x unicos origem->servico em 2023-24, em faixas (0 / 1-4 / 5-19 / 20+) -> 0..3.
Atributos : calculados SO com dados de 2019-2022 (nada de 2023-24 entra no ranking).

Tabela devolvida (uma linha por par origem-servico candidato):
  origem, cnes, km, proximidade, mesma_regiao, adequacao, folga, abertura, pop_destino,
  hist (pacientes origem->servico 2019-22), n_av (2023-24), rel (0..3)
"""
import numpy as np
import pandas as pd

from tg.config import CFG
from tg.indicadores import acessibilidade as ac, oferta as of

RAIO_KM = 150.0
ANO_REF = 2022
FAIXAS = [(0, 0), (1, 4), (5, 19), (20, 10**9)]
COMPONENTES = ["proximidade", "mesma_regiao", "adequacao", "folga", "abertura"]


def faixa_relevancia(n):
    for g, (lo, hi) in enumerate(FAIXAS):
        if lo <= n <= hi:
            return g
    return 0


def _pct(s):
    """posto percentil em (0,1]"""
    return s.rank(method="average", pct=True)


def atributos_servicos(ano_ref=ANO_REF, anos_hist=None, bloco="construcao"):
    """Atributos de cada CAPS AD (dez/`ano_ref`) calculados com dados de `anos_hist` (padrao: 2019-22).

    Avaliacao: ano_ref=2022, anos_hist=2019-22, bloco='construcao'.
    Producao (site): ano_ref=2024, anos_hist=2019-24, bloco='avaliacao' (dados mais recentes)."""
    anos_hist = list(CFG.anos_construcao) if anos_hist is None else list(anos_hist)
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")
    srv = pd.read_parquet(CFG.tratado / "servicos.parquet")
    srv = srv[(srv["competencia"] == f"{ano_ref}12") & srv["eh_caps_ad"]].copy()
    dist = pd.read_parquet(CFG.tratado / "distancias.parquet")
    fl = pd.read_parquet(CFG.tratado / "raas_fluxos.parquet")
    pop = pd.read_parquet(CFG.tratado / "populacao.parquet")
    dem = pd.read_parquet(CFG.tratado / "demanda.parquet").query("bloco == @bloco").set_index("cod_mun6")

    normas = of.norma()
    oferta = of.oferta("O1", ano_ref, normas)
    E = pd.DataFrame({"cod_mun6": mun["cod_mun6"]})
    py = pop[pop["ano"] == ano_ref].set_index("cod_mun6")["pop_15mais"]
    E["E"] = (E["cod_mun6"].map(dem["taxa_suav_int"]) * E["cod_mun6"].map(py) / 1e5).values
    fx, ps = ac.pesos_por_raio(CFG.e2sfca.raio_km)
    _, R = ac.e2sfca(oferta, E, dist, fx, ps)

    sv = srv.set_index("cnes")[["cod_mun6", "modalidade_ad"]].rename(columns={"cod_mun6": "mun_servico"})
    sv["regiao_servico"] = sv["mun_servico"].map(mun.set_index("cod_mun6")["regiao_saude"])
    sv["adequacao"] = sv["modalidade_ad"].map(normas) / max(normas[m] for m in sv["modalidade_ad"].unique())
    sv["folga"] = _pct(R.reindex(sv.index).fillna(0))

    h = fl[fl["ano"].isin(anos_hist) & fl["cnes"].isin(sv.index)].copy()
    h["fora"] = h["cod_mun6"] != h["cnes"].map(sv["mun_servico"])
    tot = h.groupby("cnes")["pacientes_f1x"].sum().reindex(sv.index).fillna(0)
    fora = h[h["fora"]].groupby("cnes")["pacientes_f1x"].sum().reindex(sv.index).fillna(0)
    sv["abertura"] = _pct((fora + 1) / (tot + 2))      # fracao de pacientes de fora, suavizada (Laplace)
    sv["pop_destino"] = sv["mun_servico"].map(pop[pop["ano"] == ano_ref].set_index("cod_mun6")["pop_total"])
    return sv, h


def construir_pares():
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")
    dist = pd.read_parquet(CFG.tratado / "distancias.parquet")
    fl = pd.read_parquet(CFG.tratado / "raas_fluxos.parquet")
    sv, h = atributos_servicos()
    reg = mun.set_index("cod_mun6")["regiao_saude"]

    gold = (fl[fl["ano"].isin(CFG.anos_avaliacao) & fl["cnes"].isin(sv.index)]
            .groupby(["cod_mun6", "cnes"])["pacientes_f1x"].sum().rename("n_av").reset_index())
    hist = h.groupby(["cod_mun6", "cnes"])["pacientes_f1x"].sum().rename("hist").reset_index()

    com_ad = set(sv["mun_servico"])
    origens = sorted(set(gold["cod_mun6"]) - com_ad)

    d = dist[dist["cod_mun6"].isin(origens) & dist["cnes"].isin(sv.index) & (dist["km"] <= RAIO_KM)].copy()
    d = d.rename(columns={"cod_mun6": "origem"}).merge(sv, left_on="cnes", right_index=True)
    d["proximidade"] = 1 - d["km"] / RAIO_KM
    d["mesma_regiao"] = (d["origem"].map(reg).values == d["regiao_servico"].values).astype(float)
    d = (d.merge(gold.rename(columns={"cod_mun6": "origem"}), on=["origem", "cnes"], how="left")
          .merge(hist.rename(columns={"cod_mun6": "origem"}), on=["origem", "cnes"], how="left"))
    d[["n_av", "hist"]] = d[["n_av", "hist"]].fillna(0).astype(int)
    d["rel"] = d["n_av"].map(faixa_relevancia)
    # consultas utilizaveis: ao menos um servico relevante ENTRE os candidatos a <= RAIO_KM
    ok = d.groupby("origem")["rel"].max() > 0
    d = d[d["origem"].isin(ok[ok].index)].reset_index(drop=True)
    return d
