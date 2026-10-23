"""Site estatico: so agregados, sem identificadores, e tamanho compativel com a hospedagem."""
import json

import pytest

from tg.config import CFG

DATA = CFG.raiz / "web" / "data"
pytestmark = pytest.mark.skipif(not (DATA / "municipios.json").exists(), reason="rode: python pipeline.py publicar")


def _chaves(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(k.upper()); _chaves(v, acc)
    elif isinstance(obj, list):
        for v in obj[:50]:
            _chaves(v, acc)
    return acc


@pytest.mark.parametrize("nome", ["municipios.json", "servicos.json", "meta.json"])
def test_sem_colunas_proibidas(nome):
    proibidas = {c.upper() for c in CFG.colunas_proibidas_publicar}
    d = json.loads((DATA / nome).read_text(encoding="utf-8"))
    assert not (_chaves(d) & proibidas)


def test_nao_publica_contagens_absolutas_de_pacientes():
    d = json.loads((DATA / "municipios.json").read_text(encoding="utf-8"))
    assert set(d[0]) == {"c", "n", "r", "la", "lo", "p", "a", "t", "d", "k", "g"}   # so taxas e indices


def test_645_municipios_e_acentos_preservados():
    d = json.loads((DATA / "municipios.json").read_text(encoding="utf-8"))
    assert len(d) == 645
    assert any("ã" in m["n"] or "é" in m["n"] or "ç" in m["n"] for m in d)


def test_pasta_pequena():
    total = sum(f.stat().st_size for f in (CFG.raiz / "web").rglob("*") if f.is_file())
    assert total < 5 * 1024 * 1024
