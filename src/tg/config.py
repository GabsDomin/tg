"""Le config.yaml e expoe caminhos do projeto."""
from pathlib import Path
from types import SimpleNamespace

import yaml

RAIZ = Path(__file__).resolve().parents[2]


def _ns(obj):
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in obj.items()})
    return obj


def carregar(caminho=RAIZ / "config.yaml"):
    with open(caminho, encoding="utf-8") as f:
        cfg = _ns(yaml.safe_load(f))
    cfg.raiz = RAIZ
    cfg.bruto = RAIZ / "dados" / "bruto"
    cfg.tratado = RAIZ / "dados" / "tratado"
    cfg.publicar = RAIZ / "dados" / "publicar"
    return cfg


CFG = carregar()
