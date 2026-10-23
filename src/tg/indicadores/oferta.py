"""Oferta em camadas (ARQUITETURA 5.2) e capacidade por modalidade.

O1 estrita : CAPS AD habilitado (0619/0635/0637)                       [decisao D1/D2: padrao]
O2 ampliada: O1 + CAPS com nome de AD mas sem habilitacao (cap. = norma AD)
O3 efetiva : O1 + CAPS I/II/III/i com producao F1x observada (cap. = F1x mediano do proprio servico)

A capacidade de cada CAPS AD e a NORMA DA MODALIDADE (mediana empirica de pacientes/mes), nao a
producao individual: producao individual mede o que o servico ja faz, e usa-la como oferta
faria a demanda "reconhecida" depender da oferta.
"""
import numpy as np
import pandas as pd

from tg.config import CFG

ANOS_NORMA = [2019, 2022]          # fora do vale pandemico 2020-21
CAMADAS = ("O1", "O2", "O3")


def capacidade_modalidade():
    """Mediana de pacientes unicos/mes por modalidade de CAPS AD, nos meses de ANOS_NORMA."""
    s = pd.read_parquet(CFG.tratado / "servicos.parquet")
    c = pd.read_parquet(CFG.tratado / "raas_carga.parquet")
    c = c[c["ano"].isin(ANOS_NORMA)]
    ad = s[s["eh_caps_ad"]][["cnes", "ano", "modalidade_ad"]]
    j = c.merge(ad, on=["cnes", "ano"], how="inner")
    tab = j.groupby("modalidade_ad")["pacientes_unicos"].agg(
        n_obs="size", n_servicos=lambda x: 0, mediana="median", p25=lambda x: x.quantile(.25), p75=lambda x: x.quantile(.75))
    tab["n_servicos"] = j.groupby("modalidade_ad")["cnes"].nunique()
    return tab.reset_index()


def norma():
    """{modalidade_ad: capacidade (pacientes/mes)}. 'AD IV' sem observacao em 2019-22: assume AD III (marcado)."""
    t = capacidade_modalidade().set_index("modalidade_ad")["mediana"].to_dict()
    t.setdefault("AD IV", t.get("AD III"))
    return t


def oferta(camada, ano, normas=None):
    """DataFrame [cnes, cod_mun6, cap] da camada, na competencia de dezembro de `ano`."""
    normas = normas or norma()
    comp = f"{ano}12"
    s = pd.read_parquet(CFG.tratado / "servicos.parquet")
    s = s[(s["competencia"] == comp) & (s["tipo_servico"] == "caps")].copy()
    s["cap"] = s["modalidade_ad"].map(normas)
    o1 = s[s["eh_caps_ad"]]
    if camada == "O1":
        sel = o1
    elif camada == "O2":
        extra = s[~s["eh_caps_ad"] & s["nome_parece_ad"]].assign(cap=normas["AD"])
        sel = pd.concat([o1, extra])
    elif camada == "O3":
        c = pd.read_parquet(CFG.tratado / "raas_carga.parquet")
        f1 = c[c["ano"] == ano].groupby("cnes")["pacientes_f1x"].median().rename("cap_f1x")
        outros = s[~s["eh_caps_ad"]].merge(f1, left_on="cnes", right_index=True, how="inner")
        outros = outros[outros["cap_f1x"] > 0].assign(cap=lambda d: d["cap_f1x"])
        sel = pd.concat([o1, outros])
    else:
        raise ValueError(camada)
    return sel[["cnes", "cod_mun6", "cap"]].reset_index(drop=True)
