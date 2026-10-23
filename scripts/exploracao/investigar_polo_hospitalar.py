"""Os municipios de maior taxa de internacao se concentram numa regiao, enviando pacientes a hospitais-polo?"""
import pandas as pd

from tg.config import CFG

d = pd.read_parquet(CFG.tratado / "demanda.parquet").query("bloco == 'construcao'")
m = pd.read_parquet(CFG.tratado / "municipios.parquet")[["cod_mun6", "nome", "regiao_saude", "nome_regiao"]]
fl = pd.read_parquet(CFG.tratado / "internacoes_fluxo.parquet")
fl = fl[fl["ano"].isin(CFG.anos_construcao)]
nome = m.set_index("cod_mun6")["nome"]

t = d.merge(m, on="cod_mun6")
top = t.nlargest(30, "taxa_suav_int")
print("Regioes de saude do top-30 de taxa (n municipios):")
print(top.groupby("nome_regiao").size().sort_values(ascending=False).head(5).to_string())

print("\nPara onde vao as internacoes de residentes de cidades de alta taxa SEM hospital:")
for cod in ("355290", "355390", "354810", "352380", "354830"):
    x = fl[fl["cod_mun6"] == cod].groupby("mun_internacao")["n_internacoes"].sum().sort_values(ascending=False)
    destinos = ", ".join(f"{nome.get(k, k)} {int(v)}" for k, v in x.head(2).items())
    print(f"  {nome[cod]:<24} total {int(x.sum()):>4} -> {destinos}")
