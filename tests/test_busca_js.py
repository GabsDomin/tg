"""Roda os testes do motor de busca (JavaScript) com o Node, para ter um unico comando de teste."""
import shutil
import subprocess

import pytest

from tg.config import CFG

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None or not (CFG.raiz / "web" / "data" / "regioes.json").exists(), reason="node ou web/data ausentes")


def test_motor_de_busca_js():
    r = subprocess.run([NODE, "--test", str(CFG.raiz / "scripts" / "busca" / "testes_motor.mjs")], capture_output=True, text=True, encoding="utf-8", cwd=CFG.raiz)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1500:]
