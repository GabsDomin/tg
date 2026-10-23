"""Acrescenta 'geral_baselines' ao avaliar_busca.mjs (medias gerais das baselines, para a pagina de avaliacao)."""
from pathlib import Path

p = Path(__file__).with_name("avaliar_busca.mjs")
t = p.read_text(encoding="utf-8")
if "geral_baselines" not in t:
    t = t.replace(
        "const acInt = { n: interp.length,",
        "const geralBase = {};\nfor (const b of [\"bm25\", \"necessidade\", \"hibrido\"]) { const L = todos.filter((l) => l[b]); geralBase[b] = { n: L.length, ndcg: media(L.map((l) => l[b].ndcg)) }; }\nconst acInt = { n: interp.length,",
    )
    t = t.replace("por_escopo: tabela, geral, diferencas: dif,", "por_escopo: tabela, geral, geral_baselines: geralBase, diferencas: dif,")
    p.write_text(t, encoding="utf-8")
print("ok", "geral_baselines" in t)
