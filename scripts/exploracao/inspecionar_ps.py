"""Inspeciona o SIA/PS (RAAS psicossocial): da para ver fluxo residencia -> CAPS?"""
import os
import pandas as pd
from dbfread import DBF
from pyreaddbc import dbc2dbf

ARQ = "dados/bruto/sia_ps/PSSP2412.dbc"
dbf = ARQ[:-4] + ".dbf"
if not os.path.exists(dbf):
    dbc2dbf(ARQ, dbf)
ps = pd.DataFrame(iter(DBF(dbf, encoding="latin1", char_decode_errors="replace")))
print("colunas:", list(ps.columns))
print("linhas:", len(ps))

caps = pd.read_csv("dados/tratado/caps_sp_202609.csv", sep=";", dtype=str)
ad = set(caps.loc[caps["modalidade_ad"].notna(), "CNES"])
col_cnes = next(c for c in ps.columns if c.startswith("CNES"))
col_res = next((c for c in ps.columns if c in ("MUNPAC", "MUN_PAC", "MUNIC_PAC", "MUNPCN")), None)
print(f"\ncoluna CNES: {col_cnes} | coluna residencia: {col_res}")
sub = ps[ps[col_cnes].isin(ad)]
print(f"registros em CAPS AD habilitados: {len(sub)} | CAPS AD com producao: {sub[col_cnes].nunique()}/{len(ad)}")
if col_res:
    mun_caps = caps.set_index("CNES")["CODUFMUN"]
    fora = (sub[col_res] != sub[col_cnes].map(mun_caps)).mean()
    print(f"fracao de atendimentos AD a residentes de OUTRO municipio: {100 * fora:.1f}%")
    print(f"municipios de residencia distintos atendidos em CAPS AD: {sub[col_res].nunique()}")
diag = next((c for c in ps.columns if "CID" in c), None)
if diag:
    print(f"\n{diag} em CAPS AD (top):")
    print(sub[diag].str[:3].value_counts().head(8).to_string())
