"""Monta o rascunho, pagina com o Word, atualiza o sumario manual e repete ate estabilizar.

Uso: python -I scripts/documento/fechar_documento.py <original.docx> <saida.docx> <pasta_tmp>
Requer Word instalado (automacao COM). O original nunca e alterado.
"""
import json
import subprocess
import sys
from pathlib import Path

import fitz  # PyMuPDF

RAIZ = Path(__file__).resolve().parents[2]
orig, saida, tmp = sys.argv[1], sys.argv[2], Path(sys.argv[3])
tmp.mkdir(parents=True, exist_ok=True)
PS = RAIZ / "scripts" / "documento" / "paginar_word.ps1"
paginas_json = tmp / "paginas.json"


def montar(paginas):
    arg = [str(paginas_json)] if paginas is not None else []
    if paginas is not None:
        paginas_json.write_text(json.dumps(paginas, ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, "-I", str(RAIZ / "scripts/documento/montar_docx.py"), orig, saida, *arg], check=True)


def paginar():
    bruto, pdf = tmp / "bruto.json", tmp / "doc.pdf"
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS), saida, str(bruto), str(pdf)], check=True)
    dados = json.loads(bruto.read_text(encoding="utf-8-sig"))
    d = fitz.open(str(pdf))
    intro = ref = None
    for i, pg in enumerate(d, 1):
        linhas = [l.strip() for l in pg.get_text().splitlines()]
        if intro is None and "1 INTRODUÇÃO" in linhas and i > 5:
            intro = i
        if "REFERÊNCIAS" in linhas and i > 5:
            ref = i
    novos = {k: v for k, v in dados.items() if k[:2] in ("4 ", "4.", "5 ")}
    novos["REFERÊNCIAS"] = ref - (intro - 5)           # numero exibido = fisico - (fisico_da_intro - 5)
    return novos, dados["__paginas_total"]


atual = None
for volta in range(4):
    montar(atual)
    novos, total = paginar()
    print(f"volta {volta}: {total} paginas | cap.4 p.{novos['4 ANÁLISES E RESULTADOS']} | cap.5 p.{novos['5 CONSIDERAÇÕES FINAIS']} | refs p.{novos['REFERÊNCIAS']}")
    if novos == atual:
        print("sumario estavel")
        break
    atual = novos
else:
    print("AVISO: sumario nao estabilizou em 4 voltas")
