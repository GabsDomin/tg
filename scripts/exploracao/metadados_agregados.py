"""Mostra variaveis e classificacoes (com categorias) de agregados SIDRA, para escolher ids sem chutar."""
import sys

import requests

for ag in sys.argv[1:]:
    m = requests.get(f"https://servicodados.ibge.gov.br/api/v3/agregados/{ag}/metadados", timeout=60).json()
    print(f"\n== {ag}: {m['nome'][:110]}")
    print("   periodos:", m["periodicidade"]["inicio"], "-", m["periodicidade"]["fim"], "| niveis:", m["nivelTerritorial"]["Administrativo"])
    for v in m["variaveis"]:
        print(f"   var {v['id']}: {v['nome'][:90]} [{v['unidade']}]")
    for c in m["classificacoes"]:
        cats = c["categorias"]
        amostra = "; ".join(f"{x['id']}={x['nome'][:34]}" for x in cats[:8])
        print(f"   classif {c['id']} {c['nome'][:40]} ({len(cats)} cat.): {amostra}")
