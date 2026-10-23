"""SIA/SUS PS (RAAS psicossocial): carga dos servicos e fluxos residencia -> servico.

NAO e medida de demanda (so existe onde ha servico); ver ARQUITETURA, principio 3.
CNS_PAC e usado apenas em memoria para contar pacientes unicos. Nenhuma saida o contem.
"""
import pandas as pd

from tg.config import CFG
from tg.leitura.dbc import ler_dbc

COLS = ["CNES_EXEC", "MUNPAC", "CNS_PAC", "CIDPRI"]


def construir_raas():
    carga, fluxos = [], []
    anos = sorted(set(CFG.anos_construcao) | set(CFG.anos_avaliacao))
    for ano in anos:
        tripla_ano = []
        for mes in range(1, 13):
            d = ler_dbc(CFG.bruto / "sia_ps" / f"PS{CFG.uf}{str(ano)[2:]}{mes:02d}.dbc", COLS)
            d = d[d["CNS_PAC"] != ""].copy()
            d["f1x"] = d["CIDPRI"].str.match(r"F1\d", na=False)
            g = d.groupby("CNES_EXEC").agg(pacientes_unicos=("CNS_PAC", "nunique"), n_registros=("CNS_PAC", "size")).reset_index()
            gf = d[d["f1x"]].groupby("CNES_EXEC")["CNS_PAC"].nunique().rename("pacientes_f1x").reset_index()
            c = g.merge(gf, on="CNES_EXEC", how="left").fillna({"pacientes_f1x": 0})
            c["ano"], c["mes"] = ano, mes
            carga.append(c)
            tripla_ano.append(d[["MUNPAC", "CNES_EXEC", "CNS_PAC", "f1x"]].drop_duplicates())
        t = pd.concat(tripla_ano, ignore_index=True).drop_duplicates()
        tot = t.groupby(["MUNPAC", "CNES_EXEC"])["CNS_PAC"].nunique().rename("pacientes_unicos")
        f1 = t[t["f1x"]].groupby(["MUNPAC", "CNES_EXEC"])["CNS_PAC"].nunique().rename("pacientes_f1x")
        fl = pd.concat([tot, f1], axis=1).fillna(0).astype(int).reset_index()
        fl["ano"] = ano
        fluxos.append(fl)
        print(f"  {ano}: {len(fl)} pares residencia-servico", flush=True)
    carga = pd.concat(carga, ignore_index=True).rename(columns={"CNES_EXEC": "cnes"})
    carga["pacientes_f1x"] = carga["pacientes_f1x"].astype(int)
    fluxos = pd.concat(fluxos, ignore_index=True).rename(columns={"CNES_EXEC": "cnes", "MUNPAC": "cod_mun6"})
    return carga, fluxos
