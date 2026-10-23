"""Pacientes F10-F19 atendidos em CAPS que NAO sao AD (SIA/PS dez/2024)."""
import pandas as pd
from dbfread import DBF

ps = pd.DataFrame(iter(DBF("dados/bruto/sia_ps/PSSP2412.dbf", encoding="latin1",
                           char_decode_errors="replace")))
caps = pd.read_csv("dados/tratado/caps_sp_202609.csv", sep=";", dtype=str).set_index("CNES")
caps["grupo"] = caps["modalidade_ad"].fillna(caps["habilitacao_desc"]).fillna("(sem habilitacao)")

f1x = ps[ps["CIDPRI"].str.match(r"F1[0-9]", na=False)].copy()
f1x["grupo"] = f1x["CNES_EXEC"].map(caps["grupo"]).fillna("(nao e CAPS tipo 70)")
pac = f1x.groupby("grupo")["CNS_PAC"].nunique().sort_values(ascending=False)
print(f"pacientes unicos F10-F19 em dez/2024: {f1x['CNS_PAC'].nunique()}")
print((pac.to_frame("pacientes").assign(pct=lambda d: (100 * d.pacientes / d.pacientes.sum()).round(1))).to_string())

mun_ad = set(caps.loc[caps["modalidade_ad"].notna(), "CODUFMUN"])
sem = f1x[f1x["MUNPAC"].str[:2].eq("35") & ~f1x["MUNPAC"].isin(mun_ad)]
print(f"\nresidentes de municipios SEM CAPS AD atendidos por F10-F19 em algum CAPS: "
      f"{sem['CNS_PAC'].nunique()} pacientes, de {sem['MUNPAC'].nunique()} municipios")
