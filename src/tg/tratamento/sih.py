"""SIH/SUS (RD): internacoes por transtornos F10-F19 (DIAG_PRINC), por municipio de RESIDENCIA.

Decisoes (dicionario TAB_SIH, CNV/IDENT.CNV e SEXO.CNV):
- IDENT 1 = AIH normal  -> conta como internacao.
- IDENT 5 = longa permanencia (AIH reemitida todo mes para o mesmo paciente) -> NAO conta como
  internacao; fica em coluna propria (n_aih_longa) para nao ser perdida nem triplicada.
- Ano = ano da competencia de processamento (ANO_CMPT).
- Residentes fora de SP sao excluidos (contagem registrada).
"""
import numpy as np
import pandas as pd

from tg.config import CFG
from tg.leitura.dbc import ler_dbc

COLS = ["ANO_CMPT", "MES_CMPT", "IDENT", "N_AIH", "MUNIC_RES", "MUNIC_MOV", "SEXO", "COD_IDADE",
        "IDADE", "DIAG_PRINC", "DIAS_PERM", "MORTE"]
FAIXAS = [(0, 14, "0-14"), (15, 24, "15-24"), (25, 34, "25-34"), (35, 44, "35-44"), (45, 59, "45-59"), (60, 200, "60+")]


def idade_anos(cod, idade):
    """COD_IDADE: 2=dias, 3=meses, 4=anos, 5=100+ anos (valor = anos alem de 100)."""
    v = pd.to_numeric(idade, errors="coerce")
    return np.select([cod == "4", cod == "5"], [v, 100 + v], default=0.0)


def faixa(anos):
    rot = np.full(len(anos), "ignorada", dtype=object)
    for lo, hi, nome in FAIXAS:
        rot[(anos >= lo) & (anos <= hi)] = nome
    return rot


def _mes(caminho):
    df = ler_dbc(caminho, COLS)
    f = df[df["DIAG_PRINC"].str.match(r"F1\d", na=False)].copy()
    f["residente_sp"] = f["MUNIC_RES"].str.startswith(str(CFG.cod_uf))
    exclu = int((~f["residente_sp"]).sum())
    f = f[f["residente_sp"]].copy()
    f["cod_mun6"] = f["MUNIC_RES"]
    f["mun_internacao"] = f["MUNIC_MOV"]
    f["ano"] = f["ANO_CMPT"].astype(int)
    f["sexo"] = f["SEXO"].map({"1": "M", "2": "F", "3": "F"}).fillna("I")
    f["faixa_etaria"] = faixa(idade_anos(f["COD_IDADE"], f["IDADE"]))
    f["cid3"] = f["DIAG_PRINC"].str[:3]
    f["dias"] = pd.to_numeric(f["DIAS_PERM"], errors="coerce").fillna(0)
    f["obito"] = (f["MORTE"] == "1").astype(int)
    f["normal"] = f["IDENT"] == "1"
    f["longa"] = f["IDENT"] == "5"
    return f, exclu


def construir_internacoes():
    chaves = ["cod_mun6", "ano", "sexo", "faixa_etaria", "cid3"]
    agregados, fluxos, excluidos = [], [], 0
    anos = sorted(set(CFG.anos_construcao) | set(CFG.anos_avaliacao))
    for ano in anos:
        for mes in range(1, 13):
            arq = CFG.bruto / "sih" / f"RD{CFG.uf}{str(ano)[2:]}{mes:02d}.dbc"
            f, exc = _mes(arq)
            excluidos += exc
            n = f[f["normal"]]
            g = n.groupby(chaves).agg(n_internacoes=("N_AIH", "size"), n_dias=("dias", "sum"),
                                      n_obitos_hosp=("obito", "sum")).reset_index()
            lg = f[f["longa"]].groupby(chaves).agg(n_aih_longa=("N_AIH", "size")).reset_index()
            agregados.append(g.merge(lg, on=chaves, how="outer"))
            fluxos.append(n.groupby(["cod_mun6", "mun_internacao", "ano"]).size().rename("n_internacoes").reset_index())
            print(f"  {ano}-{mes:02d}: {len(n)} internacoes F1x (+{int(f['longa'].sum())} AIH longa perm.)", flush=True)
    base = pd.concat(agregados, ignore_index=True)
    base = base.groupby(chaves, as_index=False).sum(numeric_only=True).fillna(0)
    for c in ("n_internacoes", "n_dias", "n_obitos_hosp", "n_aih_longa"):
        base[c] = base[c].astype(int)
    fl = pd.concat(fluxos, ignore_index=True).groupby(["cod_mun6", "mun_internacao", "ano"], as_index=False)["n_internacoes"].sum()
    return base, fl, excluidos
