"""Fluxo intermunicipal em CAPS AD (SIA/PS dez/2024): quem atende quem de fora?"""
import pandas as pd
from dbfread import DBF

ps = pd.DataFrame(iter(DBF("dados/bruto/sia_ps/PSSP2412.dbf", encoding="latin1",
                           char_decode_errors="replace")))
caps = pd.read_csv("dados/tratado/caps_sp_202609.csv", sep=";", dtype=str)
ad = caps[caps["modalidade_ad"].notna()].set_index("CNES")
mun_com_ad = set(ad["CODUFMUN"])

sub = ps[ps["CNES_EXEC"].isin(ad.index)].copy()
sub["mun_caps"] = sub["CNES_EXEC"].map(ad["CODUFMUN"])
fora = sub[sub["MUNPAC"] != sub["mun_caps"]]
fora_sp = fora[fora["MUNPAC"].str[:2] == "35"]

print(f"pacientes unicos (CNS) em CAPS AD: {sub['CNS_PAC'].nunique()}")
print(f"pacientes unicos de outro municipio: {fora['CNS_PAC'].nunique()}")
orig_sem = set(fora_sp["MUNPAC"]) - mun_com_ad
print(f"municipios SP SEM CAPS AD que aparecem como origem: {len(orig_sem)} de {645 - len(mun_com_ad)}")
print(f"CAPS AD que recebem algum paciente de fora: {fora['CNES_EXEC'].nunique()}")

print("\nTop destinos (pacientes unicos de fora / total):")
tot = sub.groupby("CNES_EXEC")["CNS_PAC"].nunique()
de_fora = fora.groupby("CNES_EXEC")["CNS_PAC"].nunique().sort_values(ascending=False).head(12)
for cnes, n in de_fora.items():
    print(f"  {ad.loc[cnes, 'NO_FANTASIA'][:42]:<42} {n:>4} / {tot[cnes]:>5}  ({fora[fora['CNES_EXEC']==cnes]['MUNPAC'].nunique()} mun. origem)")

print("\nPacientes unicos por CAPS AD no mes, por modalidade (mediana / p90):")
pac = tot.rename("pac").to_frame().join(ad["modalidade_ad"])
print(pac.groupby("modalidade_ad")["pac"].describe(percentiles=[.5, .9])[["count", "50%", "90%"]].to_string())
