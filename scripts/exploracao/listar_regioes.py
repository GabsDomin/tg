import pandas as pd

from tg.config import CFG

m = pd.read_parquet(CFG.tratado / "municipios.parquet")
pop = pd.read_parquet(CFG.tratado / "populacao.parquet").query("ano == 2024").set_index("cod_mun6")["pop_total"]
m["pop"] = m["cod_mun6"].map(pop)
r = m.groupby(["regiao_saude", "nome_regiao"]).agg(n=("cod_mun6", "size"), pop=("pop", "sum")).reset_index()
r = r.sort_values("pop", ascending=False)
print(r.to_string(index=False))
print("\nmunicipios por regiao: min", r["n"].min(), "max", r["n"].max(), "| total", r["n"].sum())
grande_sp = ["Alto do Tietê", "Franco da Rocha", "Mananciais", "Rota dos Bandeirantes", "Grande ABC", "São Paulo"]
g = m[m["nome_regiao"].isin(grande_sp)]
print("\nGrande SP candidata:", sorted(g["nome_regiao"].unique()), "| municipios:", len(g), "(a RMSP tem 39) | pop:", int(g["pop"].sum()))
print("tem 'São Paulo' como regiao?", (m["nome_regiao"] == "São Paulo").any(), "| capital em:", m.loc[m["cod_mun6"] == "355030", "nome_regiao"].tolist())
