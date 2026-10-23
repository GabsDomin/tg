"""Numeros descritivos do capitulo 4 (objetivo 2 e resposta a pergunta de pesquisa). Tudo reproduzivel."""
import numpy as np
import pandas as pd

from tg.config import CFG

pd.set_option("display.width", 200)
T = CFG.tratado
sih = pd.read_parquet(T / "internacoes.parquet")
obi = pd.read_parquet(T / "obitos.parquet")
pop = pd.read_parquet(T / "populacao.parquet")
mun = pd.read_parquet(T / "municipios.parquet")
srv = pd.read_parquet(T / "servicos.parquet")
dist = pd.read_parquet(T / "distancias.parquet")
cl = pd.read_parquet(T / "clusters.parquet")
dem = pd.read_parquet(T / "demanda.parquet")

print("== A. PERFIL DA DEMANDA (internacoes F10-F19, IDENT 1, 2019-2024) ==")
tot = sih["n_internacoes"].sum()
print("total internacoes:", tot, "| AIH longa permanencia (separadas):", sih["n_aih_longa"].sum())
print("por sexo (%):", (sih.groupby("sexo")["n_internacoes"].sum() / tot * 100).round(1).to_dict())
print("por faixa etaria (%):", (sih.groupby("faixa_etaria")["n_internacoes"].sum() / tot * 100).round(1).to_dict())
print("por CID (%):", (sih.groupby("cid3")["n_internacoes"].sum() / tot * 100).round(1).sort_values(ascending=False).head(6).to_dict())
sx = sih.pivot_table(index="faixa_etaria", columns="sexo", values="n_internacoes", aggfunc="sum")
print("homens por mulher, por faixa:", (sx["M"] / sx["F"]).round(1).to_dict())
print("dias medios de internacao (IDENT 1):", round(sih["n_dias"].sum() / tot, 1), "| obito hospitalar (%):", round(sih["n_obitos_hosp"].sum() / tot * 100, 1))
print("serie anual:", sih.groupby("ano")["n_internacoes"].sum().to_dict())

print("\n== obitos F10-F19 ==")
to = obi["n_obitos"].sum()
print("total:", to, "| por sexo (%):", (obi.groupby("sexo")["n_obitos"].sum() / to * 100).round(1).to_dict())
print("por CID (%):", (obi.groupby("cid3")["n_obitos"].sum() / to * 100).round(1).sort_values(ascending=False).head(4).to_dict())
print("por faixa (%):", (obi.groupby("faixa_etaria")["n_obitos"].sum() / to * 100).round(1).to_dict())

print("\n== B. GEOGRAFIA (2023-24, taxa bruta por 100 mil 15+) ==")
a = sih[sih["ano"].isin(CFG.anos_avaliacao)].groupby("cod_mun6")["n_internacoes"].sum()
py = pop[pop["ano"].isin(CFG.anos_avaliacao)].groupby("cod_mun6")["pop_15mais"].sum()
g = mun.set_index("cod_mun6").join(a.rename("n")).join(py.rename("py")).fillna({"n": 0})
reg = g.groupby("nome_regiao").agg(n=("n", "sum"), py=("py", "sum"))
reg["taxa"] = reg["n"] / reg["py"] * 1e5 / 2 * 2 / 1  # por 100 mil pessoas-ano
reg["taxa"] = reg["n"] / reg["py"] * 1e5
print("estado:", round(g["n"].sum() / g["py"].sum() * 1e5, 1))
print("maiores taxas regionais:"); print(reg.sort_values("taxa", ascending=False).head(5)[["n", "taxa"]].round(1).to_string())
print("menores taxas regionais:"); print(reg[reg["n"] > 50].sort_values("taxa").head(3)[["n", "taxa"]].round(1).to_string())
top10 = g.nlargest(10, "n")["n"].sum() / g["n"].sum()
print("os 10 municipios com mais internacoes concentram (%):", round(top10 * 100, 1))
print("municipios com 0 internacoes em 2023-24:", int((g["n"] == 0).sum()))

print("\n== C. OFERTA (CAPS AD habilitados) ==")
ad = srv[srv["eh_caps_ad"]]
print(ad.groupby("ano").agg(n=("cnes", "size"), municipios=("cod_mun6", "nunique")).T.to_string())
d24 = ad[ad["competencia"] == "202412"]
print("modalidades dez/2024:", d24["modalidade_ad"].value_counts().to_dict())
p24 = pop[pop["ano"] == 2024].set_index("cod_mun6")["pop_total"]
com = set(d24["cod_mun6"])
dmin = dist[dist["cnes"].isin(set(d24["cnes"]))].groupby("cod_mun6")["km"].min()
P = p24.sum()
print(f"populacao 2024: {P:,.0f}")
print("vive em municipio COM CAPS AD (%):", round(p24[p24.index.isin(com)].sum() / P * 100, 1))
for k in (30, 60):
    print(f"vive a mais de {k} km do CAPS AD mais proximo (%):", round(p24[dmin.reindex(p24.index) > k].sum() / P * 100, 1),
          "| municipios:", int((dmin > k).sum()))
sem = len(mun) - len(com)
print("municipios sem CAPS AD habilitado:", sem, f"({sem / 645 * 100:.0f}%) | populacao neles (%):", round(p24[~p24.index.isin(com)].sum() / P * 100, 1))

print("\n== D. 'DESERTO' OPERACIONAL (provisorio) ==")
c = cl.set_index("cod_mun6")
ac = pd.read_parquet(T / "acessibilidade.parquet").query("camada == 'O1' and ano in [2023, 2024]").groupby("cod_mun6")["A_r60_rel"].mean()
c["A"] = ac
q20 = c["A"].quantile(0.2)
mediana_int = c["taxa_int"].median()
desert = c[(c["A"] <= q20) & (c["taxa_int"] >= mediana_int)]
print(f"criterio: acessibilidade relativa no quintil inferior (<= {q20:.2f}) E taxa de internacao suavizada >= mediana ({mediana_int:.0f}/100 mil)")
print("municipios:", len(desert), "| populacao 2024:", f"{desert['pop_2024'].sum():,.0f}", f"({desert['pop_2024'].sum() / P * 100:.1f}% do estado)")
print("por tipologia:", desert["cluster"].value_counts().sort_index().to_dict())
print("regioes com mais desertos:", desert.groupby("nome_regiao").size().sort_values(ascending=False).head(6).to_dict())
print("os 12 mais populosos:"); print(desert.nlargest(12, "pop_2024")[["nome", "nome_regiao", "pop_2024", "A", "taxa_int"]].round(2).to_string())
print("\nsem CAPS AD E acessibilidade = 0 (sem oferta em 60 km): ", int((c["A"] == 0).sum()), "municipios; pop:", f"{c[c['A'] == 0]['pop_2024'].sum():,.0f}")
