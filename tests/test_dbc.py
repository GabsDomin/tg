"""ler_dbc deve reproduzir o dbfread (referencia) e respeitar a selecao de colunas."""
import pandas as pd
import pytest
from dbfread import DBF

from tg.config import CFG
from tg.leitura.dbc import ler_dbc

HB = CFG.bruto / "HBSP2609.dbc"
pytestmark = pytest.mark.skipif(not HB.exists(), reason="dado bruto ausente")


def test_igual_ao_dbfread():
    ref = pd.DataFrame(iter(DBF(str(HB.with_suffix(".dbf")), encoding="latin1", char_decode_errors="replace")))
    ref = ref.astype(str).apply(lambda s: s.str.strip())
    meu = ler_dbc(HB)
    assert list(meu.columns) == list(ref.columns)
    assert len(meu) == len(ref)
    for c in ("CNES", "CODUFMUN", "SGRUPHAB", "CMPT_FIM"):
        assert (meu[c].fillna("").values == ref[c].replace({"None": ""}).values).all(), c


def test_selecao_de_colunas():
    df = ler_dbc(HB, colunas=["CNES", "SGRUPHAB"])
    assert list(df.columns) == ["CNES", "SGRUPHAB"]


def test_coluna_inexistente():
    with pytest.raises(KeyError):
        ler_dbc(HB, colunas=["NAO_EXISTE"])
