"""Consultas ao IBGE (localidades, SIDRA via API v3, malha) com cache JSON em dados/bruto/ibge/."""
import json

import requests

from tg.config import CFG

API = "https://servicodados.ibge.gov.br/api"
PASTA = CFG.bruto / "ibge"


def _get_json(url, nome_cache):
    PASTA.mkdir(parents=True, exist_ok=True)
    arq = PASTA / nome_cache
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    arq.write_text(r.text, encoding="utf-8")
    return r.json()


def municipios_sp():
    return _get_json(f"{API}/v1/localidades/estados/{CFG.cod_uf}/municipios", "localidades_sp.json")


def sidra(agregado, variavel, periodos, classificacao=None, nome_cache=None):
    """Valores municipais de SP. `classificacao`: ex. '287[93070,93084]|2[6794]'.
    Retorna lista de dicts {cod7, periodo, classif, valor(str)}."""
    per = "|".join(str(p) for p in periodos)
    url = (f"{API}/v3/agregados/{agregado}/periodos/{per}/variaveis/{variavel}"
           f"?localidades=N6[N3[{CFG.cod_uf}]]")
    if classificacao:
        url += f"&classificacao={classificacao}"
    dados = _get_json(url, nome_cache or f"sidra_{agregado}_{variavel}.json")
    linhas = []
    for var in dados:
        for res in var["resultados"]:
            classif = "|".join(f"{c['id']}:{k}" for c in res["classificacoes"] for k in c["categoria"])
            for s in res["series"]:
                cod7 = s["localidade"]["id"]
                for p, v in s["serie"].items():
                    linhas.append({"cod7": cod7, "periodo": p, "classif": classif, "valor": v})
    return linhas
