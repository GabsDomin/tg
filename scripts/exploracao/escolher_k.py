"""Avalia k=3..8 (silhueta, inercia, estabilidade por bootstrap) e imprime o perfil de cada solucao."""
import pandas as pd

from tg.clusters import kmeans as km

f = km.construir_features()
print("features sem nulos:", f[km.VARS].notna().all().all(), "| n =", len(f))
print(f[km.VARS].describe(percentiles=[.5, .9]).round(2).T.to_string(), "\n")
Z, _ = km.matriz(f)
tab = km.avaliar_k(Z)
print(tab.round(3).to_string(index=False))
f.to_parquet("dados/tratado/_features_kmeans.parquet", index=False)
