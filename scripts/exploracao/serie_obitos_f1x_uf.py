"""Serie 2018-2022 de obitos F10-F19 (TabNet SIM) em varias UFs, para saber se a quebra
2019->2020 de SP e local ou nacional."""
import re
from urllib.parse import urlencode

import requests


def consultar(uf, anos=("18", "19", "20", "21", "22")):
    url = f"http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/obt10{uf}.def"
    campos = [("Linha", "Ano_do_Óbito"), ("Coluna", "--Não-Ativa--"), ("Incremento", "Óbitos_p/Residênc")]
    campos += [("Arquivos", f"obt{uf.lower()}{a}.dbf") for a in anos]
    campos += [("SGrupo_CID-10", "55"), ("formato", "prn"), ("mostre", "Mostra")]
    r = requests.post(url, data=urlencode(campos, encoding="latin1"), timeout=300,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.encoding = "latin1"
    out = {}
    for ln in r.text.splitlines():
        m = re.match(r'^"?(\d{4})"?;"?([\d.]+)"?', ln.strip())
        if m:
            out[int(m.group(1))] = int(m.group(2).replace(".", ""))
    return out


import time

for uf in ("SP", "RJ", "MG", "RS", "BR"):
    for tentativa in range(4):
        try:
            print(uf, consultar(uf), flush=True)
            break
        except Exception as e:
            time.sleep(8 * (tentativa + 1))
    else:
        print(uf, "falhou apos 4 tentativas")
    time.sleep(5)
