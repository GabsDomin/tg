"""Exporta APENAS agregados para o site estatico (web/data/). Nenhum identificador de paciente.

- municipios.json : indicadores por municipio (taxas suavizadas, acessibilidade relativa, distancia)
- servicos.json   : CAPS AD habilitados (dados publicos do CNES) com pressao relativa R_j
- municipios.geojson : malha simplificada
Contagens absolutas pequenas nao sao publicadas; so taxas suavizadas.
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd

from tg.config import CFG
from tg.indicadores import acessibilidade as ac, oferta as of

SAIDA = CFG.raiz / "web" / "data"
ANO = 2024
CAMADA = "O1"
RAIO = CFG.e2sfca.raio_km


_MIN = {"de", "da", "do", "das", "dos", "e", "em", "a", "o"}
_SIGLAS = {"CAPS", "AD", "II", "III", "IV", "CRAD", "HC", "UBS", "SP", "I"}
_ABREV = {"CENT": "Centro", "AT": "Atenção", "PSIC": "Psicossocial", "ALCOOL": "Álcool", "ATENCAO": "Atenção",
          "PSICOSSOCIAL": "Psicossocial", "PSICOSOCIAL": "Psicossocial", "DROGA": "Droga", "DROGAS": "Drogas",
          "SAO": "São", "JOAO": "João", "ROSA": "Rosa", "ARACATUBA": "Araçatuba", "PARAISOPOLIS": "Paraisópolis"}


def formatar_nome(n):
    """Nomes do CNES vem em caixa alta, sem acento e abreviados: reconstitui uma grafia legivel."""
    pal = str(n).upper().split()
    saida = []
    for i, p in enumerate(pal):
        if p in _SIGLAS:
            saida.append(p)
        elif p in _ABREV:
            saida.append(_ABREV[p])
        elif p.lower() in _MIN and i > 0:
            saida.append(p.lower())
        else:
            saida.append(p.capitalize())
    return " ".join(saida)


def _dump(obj, nome):
    (SAIDA / nome).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def exportar():
    SAIDA.mkdir(parents=True, exist_ok=True)
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")
    pop = pd.read_parquet(CFG.tratado / "populacao.parquet").query("ano == @ANO").set_index("cod_mun6")
    dem = pd.read_parquet(CFG.tratado / "demanda.parquet").query("bloco == 'avaliacao'").set_index("cod_mun6")
    dist = pd.read_parquet(CFG.tratado / "distancias.parquet")
    srv = pd.read_parquet(CFG.tratado / "servicos.parquet")
    srv = srv[(srv["competencia"] == f"{ANO}12") & srv["eh_caps_ad"]]

    # E2SFCA com a oferta de dez/2024 e a demanda do bloco de avaliacao (mesma logica da tabela de acessibilidade)
    normas = of.norma()
    oferta = of.oferta(CAMADA, ANO, normas)
    E = pd.DataFrame({"cod_mun6": mun["cod_mun6"]})
    E["E"] = (E["cod_mun6"].map(dem["taxa_suav_int"]) * E["cod_mun6"].map(pop["pop_15mais"]) / 1e5).values
    fx, ps = ac.pesos_por_raio(RAIO)
    A, R = ac.e2sfca(oferta, E, dist, fx, ps)
    ref = oferta["cap"].sum() / E["E"].sum()
    A_rel = (A / ref).set_axis(E["cod_mun6"])
    R_rel = R / ref

    d_ad = dist[dist["cnes"].isin(set(srv["cnes"]))].groupby("cod_mun6")["km"].min()
    n_ad = srv.groupby("cod_mun6").size()

    linhas = []
    for _, m in mun.iterrows():
        c = m["cod_mun6"]
        linhas.append({
            "c": c, "n": m["nome"], "r": m["nome_regiao"], "la": round(m["lat"], 4), "lo": round(m["lon"], 4),
            "p": int(pop.loc[c, "pop_total"]), "a": round(float(A_rel.get(c, 0)), 3),
            "t": round(float(dem.loc[c, "taxa_suav_int"]), 1), "d": round(float(d_ad.get(c, np.nan)), 1),
            "k": int(n_ad.get(c, 0)),
        })
    _dump(linhas, "municipios.json")

    nomes = mun.set_index("cod_mun6")["nome"]
    sv = []
    for _, s in srv.iterrows():
        sv.append({"id": s["cnes"], "n": formatar_nome(s["nome"]) if isinstance(s["nome"], str) else f"CAPS AD (CNES {s['cnes']})",
                   "m": s["cod_mun6"], "mn": nomes[s["cod_mun6"]], "mo": s["modalidade_ad"],
                   "la": round(float(s["lat"]), 5), "lo": round(float(s["lon"]), 5),
                   "f": round(float(R_rel.get(s["cnes"], 0)), 3)})
    _dump(sv, "servicos.json")

    g = gpd.read_file(CFG.bruto / "malha_sp_municipios.geojson")
    g["c"] = g["codarea"].astype(str).str[:6]
    g["geometry"] = g.geometry.simplify(0.004, preserve_topology=True)
    g[["c", "geometry"]].to_file(SAIDA / "municipios.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)

    meta = {"ano": ANO, "camada": CAMADA, "raio_km": RAIO, "n_municipios": len(linhas), "n_servicos": len(sv),
            "cnes_competencia": f"{ANO}-12", "pesos_referencia": {"proximidade": 0.35, "regiao": 0.15,
                                                                 "adequacao": 0.15, "folga": 0.35}}
    _dump(meta, "meta.json")
    return meta
