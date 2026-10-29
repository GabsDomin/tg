"""Os numeros escritos no texto dos capitulos e nos docs de resultados batem com os dados publicados?

Roda scripts/exploracao/auditar_numeros.mjs (Node). Se um numero do texto divergir dos dados, o teste falha.
Precisa dos CSV de dados/tratado (nao versionados): sem eles, o teste e ignorado.
"""
import shutil
import subprocess

import pytest

from tg.config import CFG

NODE = shutil.which("node")
NECESSARIOS = [CFG.tratado / "clusters_perfil.csv", CFG.tratado / "capacidade_modalidade.csv", CFG.tratado / "clusters_socioeconomico.csv",
               CFG.raiz / "web" / "data" / "municipios.json"]
pytestmark = pytest.mark.skipif(NODE is None or not all(p.exists() for p in NECESSARIOS), reason="node ou dados tratados ausentes")


def test_numeros_do_texto_batem_com_os_dados():
    r = subprocess.run([NODE, str(CFG.raiz / "scripts" / "exploracao" / "auditar_numeros.mjs")], capture_output=True, text=True, encoding="utf-8", cwd=CFG.raiz)
    falhas = [ln for ln in r.stdout.splitlines() if ln.startswith("FALHA")]
    assert r.returncode == 0 and not falhas, "\n".join(falhas) or r.stderr[-1500:]
