import json

import pandas as pd

from tg.avaliacao import experimento as ex, referencia as rf

pd.set_option("display.width", 220)
d = rf.construir_pares()
r = ex.rodar(d)
print(f"consultas: {r['n_consultas']} (dev {r['n_dev']} / teste {r['n_teste']})")
print("pesos calibrados (dev):", r["pesos"], "| NDCG@5 dev =", round(r["ndcg_dev"], 3))
print("pesos hibrido:", r["pesos_hibrido"])
print("\n== TESTE ==");  print(r["tabela"].round(3).to_string(index=False))
print("\ndiferenca de NDCG@5 vs 'so distancia' [IC95% bootstrap pareado]:")
for n, (m, lo, hi) in r["diffs"].items():
    print(f"  {n:<36} {m:+.3f} [{lo:+.3f}, {hi:+.3f}]")
print("\n== ABLACAO (recalibrada no dev; teste) =="); print(r["ablacao"].round(3).to_string(index=False))
print("\n== ESTRATOS (teste) =="); print(r["estratos"].round(3).to_string(index=False))
print("\n== 50 divisoes repetidas (NDCG@5 medio no teste, dp) ==")
for k, (m, s) in r["repeticoes"].items():
    print(f"  {k:<32} {m:.3f} (dp {s:.3f})")
r["tabela"].to_csv("dados/tratado/avaliacao_referencia_tabela.csv", index=False)
r["ablacao"].to_csv("dados/tratado/avaliacao_referencia_ablacao.csv", index=False)
