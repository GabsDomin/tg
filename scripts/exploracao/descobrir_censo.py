"""Quais agregados do Censo 2022 existem em nivel municipal (N6) e tratam de renda, escolaridade,
saneamento, raca/cor, urbanizacao? Lista para escolha manual; nada e assumido."""
import re
import unicodedata

import requests

API = "https://servicodados.ibge.gov.br/api/v3/agregados"
r = requests.get(API, params={"periodo": "2022", "nivel": "N6"}, timeout=120)
r.raise_for_status()
import sys
pat = re.compile(sys.argv[1] if len(sys.argv) > 1 else r"renda|rendimento|esgot|saneament|abastecimento|coleta de lixo|banheiro|favela|gini|urbana", re.I)


def sem_acento(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


vistos = set()
for grupo in r.json():
    for a in grupo["agregados"]:
        nome = a["nome"]
        if a["id"] not in vistos and pat.search(sem_acento(nome)) and "Censo" in grupo["nome"]:
            vistos.add(a["id"])
            print(f"{a['id']:>6}  {nome[:120]}")
print(len(vistos), "agregados")
