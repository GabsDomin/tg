"""Inspeciona o arquivo de habilitacoes do CNES (HB) para os CAPS de SP."""
import os
import sys
import pandas as pd
from dbfread import DBF
from pyreaddbc import dbc2dbf

BRUTOS = "dados/bruto"


def read_dbc(caminho):
    """Descompacta .dbc -> .dbf (uma vez) e le como DataFrame."""
    dbf = caminho[:-4] + ".dbf"
    if not os.path.exists(dbf):
        dbc2dbf(caminho, dbf)
    return pd.DataFrame(iter(DBF(dbf, encoding="latin1", char_decode_errors="replace")))


hb = read_dbc(f"{BRUTOS}/HBSP2609.dbc")
st = read_dbc(f"{BRUTOS}/STSP2609.dbc")

print("HB colunas:", list(hb.columns), "| linhas:", len(hb))
print("ST colunas:", list(st.columns)[:40], "| linhas:", len(st))

caps = st[st["TP_UNID"].astype(str).str.strip() == "70"]
print("\nCAPS (tipo 70) no ST set/2026:", len(caps), "| municipios:", caps["CODUFMUN"].nunique())

hb_caps = hb[hb["CNES"].isin(caps["CNES"])]
print("\nHabilitacoes presentes nos CAPS (SGRUPHAB):")
print(hb_caps["SGRUPHAB"].value_counts().to_string())
sys.stdout.flush()
