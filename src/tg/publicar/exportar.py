"""Exporta APENAS agregados para o site estatico (web/data/). Nenhum identificador de paciente.

- municipios.json : indicadores por municipio (taxas suavizadas, acessibilidade relativa, distancia, tipologia)
- regioes.json    : agregados por regiao de saude
- servicos.json   : CAPS AD habilitados (dados publicos do CNES) com folga e abertura
- municipios.geojson : malha simplificada
- meta.json       : rotulos, pesos de referencia calibrados, datas

Tambem gera, FORA do site (dados/tratado/), o conjunto de avaliacao da busca com separacao temporal:
o motor ve atributos de 2019-2022; o gabarito usa 2023-2024.
Contagens absolutas pequenas nao sao publicadas; so taxas e agregados regionais.
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd

from tg.clusters.kmeans import ROTULOS
from tg.config import CFG
from tg.indicadores import acessibilidade as ac, oferta as of

SAIDA = CFG.raiz / "web" / "data"
ANO = 2024
CAMADA = "O1"
RAIO = CFG.e2sfca.raio_km
GRANDE_SP = ["Alto do Tietê", "Franco da Rocha", "Mananciais", "Rota dos Bandeirantes", "Grande ABC", "São Paulo"]  # 39 municipios (RMSP)
LITORAL = ["Baixada Santista", "Litoral Norte"]

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


def _dump(obj, nome, pasta=SAIDA):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def indicadores(anos, bloco, ano_ref):
    """Indicadores municipais para um bloco temporal. Indice: cod_mun6."""
    T = CFG.tratado
    mun = pd.read_parquet(T / "municipios.parquet").set_index("cod_mun6")
    pop = pd.read_parquet(T / "populacao.parquet")
    dem = pd.read_parquet(T / "demanda.parquet").query("bloco == @bloco").set_index("cod_mun6")
    acs = pd.read_parquet(T / "acessibilidade.parquet").query("camada == 'O1' and ano in @anos")
    srv = pd.read_parquet(T / "servicos.parquet").query("competencia == @comp and eh_caps_ad", local_dict={"comp": f"{ano_ref}12"})
    dist = pd.read_parquet(T / "distancias.parquet")
    sih = pd.read_parquet(T / "internacoes.parquet")

    f = pd.DataFrame(index=mun.index)
    f["a"] = acs.groupby("cod_mun6")["A_r60_rel"].mean().reindex(f.index)
    f["t"] = dem["taxa_suav_int"]
    f["d"] = dist[dist["cnes"].isin(set(srv["cnes"]))].groupby("cod_mun6")["km"].min()
    f["k"] = srv.groupby("cod_mun6").size().reindex(f.index).fillna(0).astype(int)
    f["p"] = pop[pop["ano"] == ano_ref].set_index("cod_mun6")["pop_total"]
    f["py"] = pop[pop["ano"].isin(anos)].groupby("cod_mun6")["pop_15mais"].sum()
    f["n"] = sih[sih["ano"].isin(anos)].groupby("cod_mun6")["n_internacoes"].sum().reindex(f.index).fillna(0)
    # "deserto de cuidado" operacional (cap. 4.7): acessibilidade no quintil inferior E internacao >= mediana
    f["dz"] = ((f["a"] <= f["a"].quantile(0.2)) & (f["t"] >= f["t"].median())).astype(int)
    f["nome"], f["ri"], f["r"] = mun["nome"], mun["regiao_saude"], mun["nome_regiao"]
    f["la"], f["lo"] = mun["lat"], mun["lon"]
    f["gs"] = f["r"].isin(GRANDE_SP).astype(int)
    f["lit"] = f["r"].isin(LITORAL).astype(int)
    return f


def regioes(f):
    """Agregados por regiao de saude a partir dos indicadores municipais."""
    g = f.groupby(["ri", "r"])
    r = g.agg(p=("p", "sum"), nm=("nome", "size"), k=("k", "sum"), sem=("k", lambda s: int((s == 0).sum())),
              dz=("dz", "sum"), n=("n", "sum"), py=("py", "sum"), gs=("gs", "max"), lit=("lit", "max"),
              la=("la", "mean"), lo=("lo", "mean")).reset_index()
    r["t"] = r["n"] / r["py"] * 1e5
    r["a"] = [np.average(f[f["ri"] == ri]["a"], weights=f[f["ri"] == ri]["p"]) for ri in r["ri"]]
    return r


def _mun_json(f, cl):
    out = []
    for c, m in f.iterrows():
        out.append({"c": c, "n": m["nome"], "r": m["r"], "ri": m["ri"], "la": round(m["la"], 4), "lo": round(m["lo"], 4),
                    "p": int(m["p"]), "a": round(float(m["a"]), 3), "t": round(float(m["t"]), 1),
                    "d": round(float(m["d"]), 1) if pd.notna(m["d"]) else None, "k": int(m["k"]),
                    "g": int(cl[c]), "dz": int(m["dz"]), "gs": int(m["gs"]), "lit": int(m["lit"])})
    return out


def _reg_json(r):
    return [{"ri": x["ri"], "n": x["r"], "p": int(x["p"]), "nm": int(x["nm"]), "k": int(x["k"]), "sem": int(x["sem"]), "dz": int(x["dz"]),
             "t": round(float(x["t"]), 1), "a": round(float(x["a"]), 3), "gs": int(x["gs"]), "lit": int(x["lit"]),
             "la": round(float(x["la"]), 4), "lo": round(float(x["lo"]), 4)} for _, x in r.iterrows()]


def exportar():
    T = CFG.tratado
    f = indicadores(list(CFG.anos_avaliacao), "avaliacao", ANO)
    cl = pd.read_parquet(T / "clusters.parquet").set_index("cod_mun6")["cluster"]
    mun_j = _mun_json(f, cl)
    _dump(mun_j, "municipios.json")
    _dump(_reg_json(regioes(f)), "regioes.json")

    dist = pd.read_parquet(T / "distancias.parquet")
    pop = pd.read_parquet(T / "populacao.parquet").query("ano == @ANO").set_index("cod_mun6")
    dem = pd.read_parquet(T / "demanda.parquet").query("bloco == 'avaliacao'").set_index("cod_mun6")
    srv = pd.read_parquet(T / "servicos.parquet")
    srv = srv[(srv["competencia"] == f"{ANO}12") & srv["eh_caps_ad"]]

    normas = of.norma()
    oferta = of.oferta(CAMADA, ANO, normas)
    E = pd.DataFrame({"cod_mun6": f.index})
    E["E"] = (E["cod_mun6"].map(dem["taxa_suav_int"]) * E["cod_mun6"].map(pop["pop_15mais"]) / 1e5).values
    fx, ps = ac.pesos_por_raio(RAIO)
    _, R = ac.e2sfca(oferta, E, dist, fx, ps)
    ref = oferta["cap"].sum() / E["E"].sum()
    R_rel = R / ref

    from tg.avaliacao import referencia as rf
    attrs, _ = rf.atributos_servicos(ano_ref=ANO, anos_hist=range(2019, ANO + 1), bloco="avaliacao")
    pesos = json.loads((T / "pesos_referencia.json").read_text(encoding="utf-8"))

    nomes = f["nome"]
    regs = f["r"]
    sv = []
    for _, s in srv.iterrows():
        sv.append({"id": s["cnes"], "n": formatar_nome(s["nome"]) if isinstance(s["nome"], str) else f"CAPS AD (CNES {s['cnes']})",
                   "m": s["cod_mun6"], "mn": nomes[s["cod_mun6"]], "r": regs[s["cod_mun6"]], "mo": s["modalidade_ad"],
                   "la": round(float(s["lat"]), 5), "lo": round(float(s["lon"]), 5),
                   "f": round(float(R_rel.get(s["cnes"], 0)), 3), "ab": round(float(attrs["abertura"].get(s["cnes"], 0.5)), 3)})
    _dump(sv, "servicos.json")

    g = gpd.read_file(CFG.bruto / "malha_sp_municipios.geojson")
    g["c"] = g["codarea"].astype(str).str[:6]
    g["geometry"] = g.geometry.simplify(0.004, preserve_topology=True)
    g[["c", "geometry"]].to_file(SAIDA / "municipios.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)

    meta = {"clusters": {str(k): v for k, v in ROTULOS.items()}, "ano": ANO, "camada": CAMADA, "raio_km": RAIO,
            "n_municipios": len(mun_j), "n_servicos": len(sv), "cnes_competencia": f"{ANO}-12",
            "grande_sp": GRANDE_SP, "litoral": LITORAL,
            "pesos_referencia": {"proximidade": pesos["pesos"]["proximidade"], "regiao": pesos["pesos"]["mesma_regiao"],
                                 "abertura": pesos["pesos"]["abertura"]},
            "avaliacao": {"n_consultas": pesos["n_consultas"]},
            "n_desertos": int(f["dz"].sum()), "pop_desertos": int(f.loc[f["dz"] == 1, "p"].sum())}
    _dump(meta, "meta.json")
    ref = T / "avaliacao_referencia.json"
    if ref.exists():                                  # avaliacao da porta de referencia (pipeline avaliacao_referencia)
        (SAIDA / "avaliacao_referencia.json").write_text(ref.read_text(encoding="utf-8"), encoding="utf-8")
    return meta


def exportar_avaliacao_busca():
    """Dados para avaliar a busca SEM circularidade: o motor usa 2019-22 (dez/2022); o gabarito usa 2023-24 (dez/2024)."""
    T = CFG.tratado
    ent = indicadores(list(CFG.anos_construcao), "construcao", 2022)      # o que o motor ve
    res = indicadores(list(CFG.anos_avaliacao), "avaliacao", 2024)        # desfecho (gabarito)
    cl = pd.read_parquet(T / "clusters.parquet").set_index("cod_mun6")["cluster"]
    srv = pd.read_parquet(T / "servicos.parquet")
    nomes = ent["nome"]

    def servicos(comp):
        s = srv[(srv["competencia"] == comp) & srv["eh_caps_ad"]]
        return [{"id": x["cnes"], "n": formatar_nome(x["nome"]) if isinstance(x["nome"], str) else f"CAPS AD (CNES {x['cnes']})",
                 "m": x["cod_mun6"], "mn": nomes[x["cod_mun6"]], "r": ent.loc[x["cod_mun6"], "r"], "mo": x["modalidade_ad"],
                 "la": round(float(x["lat"]), 5), "lo": round(float(x["lon"]), 5), "f": 1.0, "ab": 0.5} for _, x in s.iterrows()]

    dados = {"motor": {"municipios": _mun_json(ent, cl), "regioes": _reg_json(regioes(ent)), "servicos": servicos("202212")},
             "gabarito": {"municipios": _mun_json(res, cl), "regioes": _reg_json(regioes(res)), "servicos": servicos("202412")}}
    _dump(dados, "avaliacao_busca_dados.json", pasta=T)
    return {k: {kk: len(vv) for kk, vv in v.items()} for k, v in dados.items()}
