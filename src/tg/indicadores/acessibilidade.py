"""Acessibilidade espacial E2SFCA (Enhanced Two-Step Floating Catchment Area) e ICA municipal.

Passo 1: R_j = cap_j / sum_m E_m * w(d_mj)      (pressao potencial do servico j)
Passo 2: A_m = sum_j R_j * w(d_mj)              (acessibilidade do municipio m)
w e um decaimento por faixas de distancia. A_m so tem leitura RELATIVA (razao a media estadual).

NAO citar autores sem confirmar a referencia (ver CLAUDE.md: Luo e Wang 2003 / Luo e Qi 2009 a confirmar).
"""
import numpy as np
import pandas as pd

from tg.config import CFG


def pesos_por_raio(raio_km):
    """Faixas e pesos do config, reescalonando as faixas proporcionalmente ao raio (sensibilidade)."""
    fx = np.array(CFG.e2sfca.faixas_km, float) * raio_km / CFG.e2sfca.raio_km
    return fx, np.array(CFG.e2sfca.pesos, float)


def peso(km, faixas, pesos):
    km = np.asarray(km, float)
    w = np.zeros_like(km)
    for lim, p in reversed(list(zip(faixas, pesos))):
        w = np.where(km <= lim, p, w)
    return w


def e2sfca(oferta, demanda, dist, faixas, pesos):
    """oferta [cnes, cap]; demanda [cod_mun6, E]; dist [cod_mun6, cnes, km]. Retorna serie A por cod_mun6."""
    d = dist.merge(oferta[["cnes", "cap"]], on="cnes").merge(demanda[["cod_mun6", "E"]], on="cod_mun6")
    d["w"] = peso(d["km"], faixas, pesos)
    d = d[d["w"] > 0]
    denom = (d["E"] * d["w"]).groupby(d["cnes"]).sum()
    cap = oferta.set_index("cnes")["cap"]
    R = (cap / denom).where(denom > 0, 0.0).rename("R")          # sem demanda no raio: R = 0
    d = d.merge(R, left_on="cnes", right_index=True)
    A = (d["R"] * d["w"]).groupby(d["cod_mun6"]).sum()
    return A.reindex(demanda["cod_mun6"]).fillna(0.0).rename("A"), R


def acessibilidade_oferta(oferta, dist, faixas, pesos, municipios):
    """Indice de OFERTA pura (sem demanda): S_m = sum_j cap_j * w(d_mj). Controle da validacao externa."""
    d = dist.merge(oferta[["cnes", "cap"]], on="cnes")
    d["w"] = peso(d["km"], faixas, pesos)
    S = (d["cap"] * d["w"]).groupby(d["cod_mun6"]).sum()
    return S.reindex(municipios).fillna(0.0).rename("S")


def ica_municipal(oferta, demanda):
    """Baseline prometido no documento: capacidade no proprio municipio / demanda esperada."""
    cap = oferta.groupby("cod_mun6")["cap"].sum()
    d = demanda.set_index("cod_mun6")["E"]
    return (cap.reindex(d.index).fillna(0.0) / d.where(d > 0)).rename("ICA")


def construir_acessibilidade():
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")["cod_mun6"]
    pop = pd.read_parquet(CFG.tratado / "populacao.parquet")
    dem = pd.read_parquet(CFG.tratado / "demanda.parquet")
    dist = pd.read_parquet(CFG.tratado / "distancias.parquet")
    from tg.indicadores import oferta as of
    normas = of.norma()
    blocos = {**{a: "construcao" for a in CFG.anos_construcao}, **{a: "avaliacao" for a in CFG.anos_avaliacao}}
    raios = CFG.e2sfca.raios_sensibilidade_km

    linhas = []
    for camada in of.CAMADAS:
        for ano, bloco in blocos.items():
            of_ = of.oferta(camada, ano, normas)
            taxa = dem[dem["bloco"] == bloco].set_index("cod_mun6")["taxa_suav_int"]
            py = pop[pop["ano"] == ano].set_index("cod_mun6")["pop_15mais"]
            E = pd.DataFrame({"cod_mun6": mun.values})
            E["E"] = (E["cod_mun6"].map(taxa) * E["cod_mun6"].map(py) / 1e5).values
            out = pd.DataFrame({"cod_mun6": mun.values})
            for r in raios:
                fx, ps = pesos_por_raio(r)
                A, _ = e2sfca(of_, E, dist, fx, ps)
                out[f"A_r{r}"] = A.values
            fx, ps = pesos_por_raio(CFG.e2sfca.raio_km)
            out["S_r60"] = acessibilidade_oferta(of_, dist, fx, ps, out["cod_mun6"]).values
            out["ICA"] = ica_municipal(of_, E).reindex(out["cod_mun6"]).values
            out["E"] = E["E"].values
            ref = of_["cap"].sum() / E["E"].sum()           # razao estadual capacidade/demanda
            for r in raios:
                out[f"A_r{r}_rel"] = out[f"A_r{r}"] / ref
            out["camada"], out["ano"] = camada, ano
            linhas.append(out)
    return pd.concat(linhas, ignore_index=True)
