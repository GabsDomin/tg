"""SIM (DO): obitos com causa basica F10-F19, por municipio de RESIDENCIA (CODMUNRES).

Os arquivos DOSPaaaa sao por UF de residencia. Ano = ano de DTOBITO (ddmmaaaa).
IDADE (3 digitos): 1o digito = unidade (4 anos, 5 = 100+ anos), demais = valor.
O CID de 3 digitos fica na tabela: F17 (tabaco) pesa ~21% dos obitos F1x em 2024 e
permite analise de sensibilidade sem tabaco.
"""
import numpy as np
import pandas as pd

from tg.config import CFG
from tg.leitura.dbc import ler_dbc
from tg.tratamento.sih import faixa

COLS = ["DTOBITO", "CODMUNRES", "SEXO", "IDADE", "CAUSABAS"]


def _anos(idade):
    s = idade.str.zfill(3)
    unidade, valor = s.str[0], pd.to_numeric(s.str[1:], errors="coerce").fillna(0)
    return np.select([unidade == "4", unidade == "5"], [valor, 100 + valor], default=0.0)


def construir_obitos():
    partes = []
    for ano in sorted(set(CFG.anos_construcao) | set(CFG.anos_avaliacao)):
        d = ler_dbc(CFG.bruto / "sim" / f"DO{CFG.uf}{ano}.dbc", COLS)
        f = d[d["CAUSABAS"].str.match(r"F1\d", na=False)].copy()
        f["ano"] = pd.to_numeric(f["DTOBITO"].str[-4:], errors="coerce").astype("Int64")
        f["cod_mun6"] = f["CODMUNRES"]
        f["sexo"] = f["SEXO"].map({"1": "M", "2": "F"}).fillna("I")
        f["faixa_etaria"] = faixa(_anos(f["IDADE"]))
        f["cid3"] = f["CAUSABAS"].str[:3]
        partes.append(f)
    df = pd.concat(partes, ignore_index=True)
    df = df[df["cod_mun6"].str.startswith(str(CFG.cod_uf))]
    chaves = ["cod_mun6", "ano", "sexo", "faixa_etaria", "cid3"]
    return df.groupby(chaves).size().rename("n_obitos").reset_index()
