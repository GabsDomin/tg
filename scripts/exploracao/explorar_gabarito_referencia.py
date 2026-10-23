"""Tamanho e qualidade do conjunto de consultas da porta de referencia."""
import pandas as pd

from tg.avaliacao import referencia as rf

d = rf.construir_pares()
q = d.groupby("origem")
print("consultas (municipios de origem):", d["origem"].nunique())
print("candidatos por consulta: mediana", int(q.size().median()), "| min", int(q.size().min()), "| max", int(q.size().max()))
print("servicos relevantes por consulta (rel>0): mediana", int(q["rel"].apply(lambda x: (x > 0).sum()).median()),
      "| consultas com 1 so relevante:", int((q["rel"].apply(lambda x: (x > 0).sum()) == 1).sum()))
print("distribuicao de rel (pares):", d["rel"].value_counts().sort_index().to_dict())
print("consultas com historico 2019-22 ao servico relevante:", int((q.apply(lambda g: ((g["rel"] > 0) & (g["hist"] > 0)).any())).sum()),
      "| sem historico (cold-start):", int((~q.apply(lambda g: ((g["rel"] > 0) & (g["hist"] > 0)).any())).sum()))
# o servico MAIS PROXIMO e o relevante?
prox = d.loc[d.groupby("origem")["km"].idxmin()]
print("o servico mais proximo tem rel>0 em", f"{(prox['rel'] > 0).mean():.0%}", "das consultas; rel mediano do mais proximo:", prox["rel"].median())
print("pacientes 2023-24 em servicos a <=150 km vs todos os candidatos: ver cobertura abaixo")
