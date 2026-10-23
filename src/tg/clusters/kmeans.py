"""K-Means sobre indicadores ASSISTENCIAIS (variaveis socioeconomicas ficam fora: so caracterizam).

Periodo: bloco de avaliacao (2023-2024), a situacao mais recente. Variaveis (log1p + z-score):
  acesso        : acessibilidade E2SFCA relativa (O1, raio 60 km, media 2023-24)
  dist_ad       : km ao CAPS AD habilitado mais proximo (dez/2024)
  taxa_int      : internacao F10-F19 suavizada (/100 mil 15+)
  taxa_obito    : obito F10-F19 suavizado (/100 mil 15+)   [sinal secundario: quebra de regime em 2020]
  atend_caps    : pacientes F1x atendidos em qualquer CAPS por 100 mil 15+ (atendimento realizado)
  frac_fora     : fracao desses pacientes atendida em CAPS de OUTRO municipio
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from tg.config import CFG

# Rotulos PROPOSTOS (interpretacao dos perfis em docs/resultados_clusters.md), validos para k=5 e a
# ordenacao por acesso mediano. tests/test_clusters.py falha se uma nova execucao mudar o sentido dos grupos.
ROTULOS = {
    1: "Polos médios sob pressão",
    2: "Pequenos sem atendimento registrado em CAPS",
    3: "Pequenos que dependem de CAPS de outro município",
    4: "Grandes centros com boa oferta",
    5: "Médios com acesso alto e baixa internação",
}
VARS = ["acesso", "dist_ad", "taxa_int", "taxa_obito", "atend_caps", "frac_fora"]
SEMENTE = 20261023


def construir_features():
    anos = CFG.anos_avaliacao
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")[["cod_mun6", "nome", "regiao_saude", "nome_regiao"]]
    dem = pd.read_parquet(CFG.tratado / "demanda.parquet").query("bloco == 'avaliacao'").set_index("cod_mun6")
    ac = pd.read_parquet(CFG.tratado / "acessibilidade.parquet").query("camada == 'O1' and ano in @anos")
    pop = pd.read_parquet(CFG.tratado / "populacao.parquet")
    srv = pd.read_parquet(CFG.tratado / "servicos.parquet")
    dist = pd.read_parquet(CFG.tratado / "distancias.parquet")
    fl = pd.read_parquet(CFG.tratado / "raas_fluxos.parquet").query("ano in @anos")

    f = mun.set_index("cod_mun6").copy()
    f["acesso"] = ac.groupby("cod_mun6")["A_r60_rel"].mean()
    ad24 = set(srv.query("competencia == '202412' and eh_caps_ad")["cnes"])
    f["dist_ad"] = dist[dist["cnes"].isin(ad24)].groupby("cod_mun6")["km"].min()
    f["taxa_int"] = dem["taxa_suav_int"]
    f["taxa_obito"] = dem["taxa_suav_obito"]

    cnes_mun = srv.sort_values("competencia").drop_duplicates("cnes", keep="last").set_index("cnes")["cod_mun6"]
    fl = fl.assign(mun_servico=fl["cnes"].map(cnes_mun)).dropna(subset=["mun_servico"])
    tot = fl.groupby("cod_mun6")["pacientes_f1x"].sum()
    fora = fl[fl["cod_mun6"] != fl["mun_servico"]].groupby("cod_mun6")["pacientes_f1x"].sum()
    py = pop[pop["ano"].isin(anos)].groupby("cod_mun6")["pop_15mais"].sum()
    f["atend_caps"] = (tot / py * 1e5).reindex(f.index).fillna(0)
    f["frac_fora"] = (fora.reindex(tot.index).fillna(0) / tot).reindex(f.index).fillna(0)
    f["pop_2024"] = pop[pop["ano"] == 2024].set_index("cod_mun6")["pop_total"]
    return f.reset_index()


def matriz(f):
    X = np.log1p(f[VARS].clip(lower=0))
    X["frac_fora"] = f["frac_fora"]                 # ja esta em [0,1]
    return StandardScaler().fit_transform(X), StandardScaler


def avaliar_k(Z, ks=range(3, 9), n_boot=100):
    rng = np.random.default_rng(SEMENTE)
    linhas = []
    for k in ks:
        km = KMeans(n_clusters=k, n_init=20, random_state=SEMENTE).fit(Z)
        sil = silhouette_score(Z, km.labels_)
        rotulos = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(Z), len(Z))
            rotulos.append(KMeans(n_clusters=k, n_init=5, random_state=int(rng.integers(1e9))).fit(Z[idx]).predict(Z))
        pares = [adjusted_rand_score(rotulos[i], rotulos[i + 1]) for i in range(0, n_boot - 1, 2)]
        linhas.append({"k": k, "inercia": km.inertia_, "silhueta": sil, "ari_medio": float(np.mean(pares)),
                       "menor_cluster": int(np.bincount(km.labels_).min())})
    return pd.DataFrame(linhas)


def ajustar(f, k):
    Z, _ = matriz(f)
    km = KMeans(n_clusters=k, n_init=50, random_state=SEMENTE).fit(Z)
    out = f.copy()
    # ordena clusters do "pior" ao "melhor" acesso, para rotulos estaveis e legiveis
    ordem = out.assign(c=km.labels_).groupby("c")["acesso"].median().sort_values().index.tolist()
    out["cluster"] = pd.Series(km.labels_).map({c: i + 1 for i, c in enumerate(ordem)}).values
    return out
