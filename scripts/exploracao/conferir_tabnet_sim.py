"""Confere obitos F10-F19 (residencia, SP) contra o TabNet de mortalidade (CID-10).

Filtro Grupo CID-10 = 55 (F10-F19); linha = ano do obito; medida = obitos por residencia.
Uso: python -I scripts/exploracao/conferir_tabnet_sim.py
"""
import re
from urllib.parse import urlencode

import pandas as pd
import requests

from tg.config import CFG

URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/obt10SP.def"
anos = sorted(set(CFG.anos_construcao) | set(CFG.anos_avaliacao))

campos = [("Linha", "Ano_do_Óbito"), ("Coluna", "--Não-Ativa--"), ("Incremento", "Óbitos_p/Residênc")]
campos += [("Arquivos", f"obtsp{str(a)[2:]}.dbf") for a in anos]
campos += [("SGrupo_CID-10", "55"), ("formato", "prn"), ("mostre", "Mostra")]

r = requests.post(URL, data=urlencode(campos, encoding="latin1"), timeout=300,
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
r.encoding = "latin1"
tn = {}
for ln in r.text.splitlines():
    m = re.match(r'^"?(\d{4})"?;"?([\d.]+)"?', ln.strip())
    if m:
        tn[int(m.group(1))] = int(m.group(2).replace(".", ""))
if not tn:
    print(r.text[:1500])
    raise SystemExit("nao consegui extrair a tabela")

meu = pd.read_parquet(CFG.tratado / "obitos.parquet").groupby("ano")["n_obitos"].sum()
cmp = pd.DataFrame({"tabnet": pd.Series(tn), "meu": meu})
cmp["dif_%"] = ((cmp["meu"] / cmp["tabnet"] - 1) * 100).round(2)
print(cmp.to_string())
