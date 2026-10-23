"""Converte a saida do paginar_word.ps1 em paginas.json (so itens novos do sumario)."""
import json
import sys

bruto = json.load(open(sys.argv[1], encoding="utf-8-sig"))
referencias = int(sys.argv[3])
novos = {k: v for k, v in bruto.items() if k[:2] in ("4 ", "4.", "5 ")}
novos["REFERÊNCIAS"] = referencias
json.dump(novos, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(novos), "itens")
