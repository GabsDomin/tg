"""Leitura rapida de .dbc do DATASUS (dbc -> dbf temporario -> numpy), so as colunas pedidas."""
import os
import struct
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from pyreaddbc import dbc2dbf


def _campos(dbf):
    """Parse do cabecalho dBase III: (n_registros, tam_cabecalho, tam_registro, [(nome, tam)])."""
    with open(dbf, "rb") as f:
        cab = f.read(32)
        n, tam_cab, tam_reg = struct.unpack("<xxxxIHH", cab[:12])
        campos = []
        while True:
            d = f.read(32)
            if not d or d[0] == 0x0D:
                break
            nome = d[:11].split(b"\x00")[0].decode("latin1").strip()
            campos.append((nome, d[16]))
    return n, tam_cab, tam_reg, campos


def ler_dbc(caminho, colunas=None):
    """DataFrame de strings (latin1, sem espacos nas pontas). Conversao de tipo fica a cargo de quem chama."""
    caminho = Path(caminho)
    with tempfile.TemporaryDirectory() as tmp:
        dbf = os.path.join(tmp, caminho.stem + ".dbf")
        dbc2dbf(str(caminho), dbf)
        n, tam_cab, tam_reg, campos = _campos(dbf)
        dtype = [("_del", "S1")] + [(nome, f"S{tam}") for nome, tam in campos]
        assert np.dtype(dtype).itemsize == tam_reg, "layout de registro inconsistente"
        alvo = [c for c, _ in campos] if colunas is None else list(colunas)
        faltam = set(alvo) - {c for c, _ in campos}
        if faltam:
            raise KeyError(f"colunas ausentes em {caminho.name}: {sorted(faltam)}")
        bruto = np.fromfile(dbf, dtype=dtype, count=n, offset=tam_cab)
    df = pd.DataFrame({c: pd.Series(bruto[c]).str.decode("latin1").str.strip() for c in alvo})
    return df[bruto["_del"] != b"*"].reset_index(drop=True)
