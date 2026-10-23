"""Os municipios de maior taxa de internacao F1x sao cidades com hospital psiquiatrico?
Hipotese: 'municipio de residencia' = municipio do hospital para pacientes institucionalizados."""
import pandas as pd

from tg.config import CFG

d = pd.read_parquet(CFG.tratado / "demanda.parquet").query("bloco == 'construcao'")
mun = pd.read_parquet(CFG.tratado / "municipios.parquet")[["cod_mun6", "nome"]]
fl = pd.read_parquet(CFG.tratado / "internacoes_fluxo.parquet")
fl = fl[fl["ano"].isin(CFG.anos_construcao)]
sv = pd.read_parquet(CFG.tratado / "servicos.parquet")
sv = sv[(sv["competencia"] == "202212") & (sv["tipo_servico"] == "hospital_sm")]
sih = pd.read_parquet(CFG.tratado / "internacoes.parquet")
sih = sih[sih["ano"].isin(CFG.anos_construcao)]

proprio = fl[fl["cod_mun6"] == fl["mun_internacao"]].groupby("cod_mun6")["n_internacoes"].sum()
total = fl.groupby("cod_mun6")["n_internacoes"].sum()
dias = sih.groupby("cod_mun6").agg(dias=("n_dias", "sum"), n=("n_internacoes", "sum"))
hosp = sv.groupby("cod_mun6").agg(hosp_sm=("cnes", "size"), leitos_sm_sus=("leitos_sm_sus", "sum"))

t = (d.merge(mun, on="cod_mun6").set_index("cod_mun6")
       .join((proprio / total).rename("pct_no_proprio_mun")).join(hosp).join((dias["dias"] / dias["n"]).rename("dias_medios")))
t[["hosp_sm", "leitos_sm_sus"]] = t[["hosp_sm", "leitos_sm_sus"]].fillna(0)
cols = ["nome", "n_int", "taxa_suav_int", "pct_no_proprio_mun", "hosp_sm", "leitos_sm_sus", "dias_medios"]
print("TOP 12 por taxa suavizada:")
print(t.nlargest(12, "taxa_suav_int")[cols].round(2).to_string())

top = t.nlargest(30, "taxa_suav_int")
print(f"\nTop-30: com hospital SM no municipio = {(top['hosp_sm'] > 0).mean():.0%} | "
      f"demais municipios = {(t.drop(top.index)['hosp_sm'] > 0).mean():.0%}")
print(f"Top-30: internados no proprio municipio (mediana) = {top['pct_no_proprio_mun'].median():.0%} | "
      f"demais = {t.drop(top.index)['pct_no_proprio_mun'].median():.0%}")
print(f"Correlacao de Spearman taxa_suav x leitos SM SUS no municipio: "
      f"{t['taxa_suav_int'].corr(t['leitos_sm_sus'], method='spearman'):.2f}")
