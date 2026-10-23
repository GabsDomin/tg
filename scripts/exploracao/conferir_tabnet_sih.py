"""Confere o total anual de internacoes F10-F19 (residencia, SP) contra o TabNet oficial.

Consulta: Morbidade Hospitalar do SUS, por local de RESIDENCIA, SP, linha = Ano processamento,
medida = Internacoes, filtro Lista Morb CID-10 = 133 (F10) + 134 (F11-F19).
Uso: python -I scripts/exploracao/conferir_tabnet_sih.py
"""
import re
from urllib.parse import urlencode

import pandas as pd
import requests

from tg.config import CFG

URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/nrSP.def"
anos = sorted(set(CFG.anos_construcao) | set(CFG.anos_avaliacao))

campos = [("Linha", "Ano_processamento"), ("Coluna", "--Não-Ativa--"), ("Incremento", "Internações")]
campos += [("Arquivos", f"nrsp{str(a)[2:]}{m:02d}.dbf") for a in anos for m in range(1, 13)]
campos += [("SLista_Morb__CID-10", "133"), ("SLista_Morb__CID-10", "134")]
campos += [("formato", "prn"), ("mostre", "Mostra")]

r = requests.post(URL, data=urlencode(campos, encoding="latin1"), timeout=300,
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
r.encoding = "latin1"
texto = r.text
print("HTTP", r.status_code, "| tamanho", len(texto))

tn = {}
for ln in texto.splitlines():
    m = re.match(r'^"?(\d{4})"?;"?([\d.]+)"?', ln.strip())
    if m:
        tn[int(m.group(1))] = int(m.group(2).replace(".", ""))
if not tn:
    print(texto[:1500])
    raise SystemExit("nao consegui extrair a tabela; veja a resposta acima")

meu = pd.read_parquet(CFG.tratado / "internacoes.parquet").groupby("ano")["n_internacoes"].sum()
cmp = pd.DataFrame({"tabnet": pd.Series(tn), "meu": meu})
cmp["dif_%"] = ((cmp["meu"] / cmp["tabnet"] - 1) * 100).round(2)
print(cmp.to_string())
