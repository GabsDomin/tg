"""tratado/servicos.parquet: CAPS, unidades residenciais e hospitais com leito SUS de saude mental,
por competencia de dezembro (+ atual), com modalidade (habilitacao) e coordenadas validadas.

Codigos conferidos em TAB_CNES (ver config.yaml e docs): TP_UNID 70 = CAPS, 78 = regime residencial;
CODLEITO 47 PSIQUIATRIA, 73/87 SAUDE MENTAL (34 CRONICOS e 84 ACOLHIMENTO NOTURNO nao entram).
"""
import re

import geopandas as gpd
import numpy as np
import pandas as pd

from tg.config import CFG
from tg.leitura.dbc import ler_dbc

TP_CAPS, TP_RESIDENCIAL = "70", "78"
TP_HOSPITALAR = {"05", "07", "15", "62"}   # hospital geral/especializado, unidade mista, hospital-dia
LEITOS_SM = {"47", "73", "87"}

HAB_CAPS = vars(CFG.habilitacoes.caps)
HAB_AD = set(CFG.habilitacoes.ad)
ROTULO_AD = {"0637": "AD IV", "0635": "AD III", "0619": "AD"}  # 0619 = "CAPS ALCOOL E DROGAS" (II presumido)
ORDEM_AD = ["0637", "0635", "0619"]


def nome_parece_ad(nome):
    """Nome sugere CAPS AD. Nao casa 'CAPS ADULTO'."""
    n = " " + re.sub(r"[-./]", " ", str(nome).upper()).replace("A D ", "AD ") + " "
    return bool(re.search(r"CAPSAD|[^A-Z]AD[^A-Z]|ALCOOL|DROGA", n))


def modalidade_ad(codigos):
    for c in ORDEM_AD:
        if c in codigos:
            return ROTULO_AD[c]
    return None


def _habilitacoes(comp):
    hb = ler_dbc(CFG.bruto / "cnes" / "hb" / f"HB{CFG.uf}{comp[2:]}.dbc", ["CNES", "SGRUPHAB", "CMPT_INI", "CMPT_FIM"])
    ini_ok = (hb["CMPT_INI"] == "") | (hb["CMPT_INI"] <= comp)
    fim_ok = (hb["CMPT_FIM"] == "") | (hb["CMPT_FIM"] >= comp)
    hb = hb[ini_ok & fim_ok & hb["SGRUPHAB"].isin(HAB_CAPS)]
    return hb.groupby("CNES")["SGRUPHAB"].apply(lambda s: tuple(sorted(set(s))))


def _servicos_da_competencia(comp):
    base = CFG.bruto / "cnes"
    st = ler_dbc(base / "st" / f"ST{CFG.uf}{comp[2:]}.dbc", ["CNES", "CODUFMUN", "TP_UNID", "VINC_SUS"])
    lt = ler_dbc(base / "lt" / f"LT{CFG.uf}{comp[2:]}.dbc", ["CNES", "CODLEITO", "QT_SUS"])
    lt = lt[lt["CODLEITO"].isin(LEITOS_SM)].assign(QT_SUS=lambda d: pd.to_numeric(d["QT_SUS"], errors="coerce").fillna(0))
    leitos = lt.groupby("CNES")["QT_SUS"].sum().rename("leitos_sm_sus")

    st = st.drop_duplicates("CNES").merge(leitos, on="CNES", how="left")
    st["leitos_sm_sus"] = st["leitos_sm_sus"].fillna(0).astype(int)
    caps = st["TP_UNID"] == TP_CAPS
    resid = st["TP_UNID"] == TP_RESIDENCIAL
    hosp = st["TP_UNID"].isin(TP_HOSPITALAR) & (st["leitos_sm_sus"] > 0)
    st["tipo_servico"] = np.select([caps, resid, hosp], ["caps", "residencial", "hospital_sm"], default="")
    st = st[st["tipo_servico"] != ""].copy()

    hab = _habilitacoes(comp)
    st["habilitacoes"] = st["CNES"].map(hab).apply(lambda t: t if isinstance(t, tuple) else ())
    st["competencia"] = comp
    st["ano"] = int(comp[:4])
    return st.rename(columns={"CODUFMUN": "cod_mun6", "TP_UNID": "tp_unid", "CNES": "cnes"})


def _opendatasus():
    """Nome e coordenadas (jun/2025), unica fonte de lat/long do CNES."""
    arq = CFG.bruto / "opendatasus_cnes_estabelecimentos_jun2025.zip"
    od = pd.read_csv(arq, sep=";", dtype=str, encoding="latin1",
                     usecols=["CO_CNES", "CO_UF", "NO_FANTASIA", "NU_LATITUDE", "NU_LONGITUDE"])
    od = od[od["CO_UF"] == str(CFG.cod_uf)].copy()
    od["cnes"] = od["CO_CNES"].str.zfill(7)
    od["lat0"] = pd.to_numeric(od["NU_LATITUDE"], errors="coerce")
    od["lon0"] = pd.to_numeric(od["NU_LONGITUDE"], errors="coerce")
    od.loc[(od["lat0"] == 0) | (od["lon0"] == 0), ["lat0", "lon0"]] = np.nan  # 0,0 = ausente
    return od.drop_duplicates("cnes")[["cnes", "NO_FANTASIA", "lat0", "lon0"]].rename(columns={"NO_FANTASIA": "nome"})


def _validar_coordenadas(df, mun):
    malha = gpd.read_file(CFG.bruto / "malha_sp_municipios.geojson")
    malha["cod_mun6"] = malha["codarea"].astype(str).str[:6]
    tem = df[["lat0", "lon0"]].notna().all(axis=1)
    pts = gpd.GeoDataFrame(df.loc[tem, ["cnes", "ano", "cod_mun6"]].copy(),
                           geometry=gpd.points_from_xy(df.loc[tem, "lon0"], df.loc[tem, "lat0"]), crs=malha.crs)
    cai = gpd.sjoin(pts, malha[["cod_mun6", "geometry"]], how="left", predicate="within",
                    lsuffix="pt", rsuffix="poly")
    cai = cai[~cai.index.duplicated()]
    df["coord_valida"] = False
    df.loc[cai.index, "coord_valida"] = (cai["cod_mun6_pt"] == cai["cod_mun6_poly"]).values

    cent = mun.set_index("cod_mun6")[["lat", "lon"]]
    usar = df["coord_valida"]
    df["lat"] = np.where(usar, df["lat0"], df["cod_mun6"].map(cent["lat"]))
    df["lon"] = np.where(usar, df["lon0"], df["cod_mun6"].map(cent["lon"]))
    df["origem_coord"] = np.select(
        [usar, tem & ~usar], ["cnes_opendatasus", "centroide_municipio(coord_fora_do_municipio)"],
        default="centroide_municipio(sem_coord)")
    return df.drop(columns=["lat0", "lon0"])


def construir_servicos():
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")
    partes = [_servicos_da_competencia(c) for c in CFG.competencias_cnes]
    df = pd.concat(partes, ignore_index=True)
    df = df.merge(_opendatasus(), on="cnes", how="left")

    df["modalidade_ad"] = df["habilitacoes"].apply(modalidade_ad)
    df["eh_caps_ad"] = (df["tipo_servico"] == "caps") & df["modalidade_ad"].notna()
    df["modalidade"] = np.where(df["tipo_servico"] != "caps", df["tipo_servico"],
                                df["habilitacoes"].apply(lambda t: " + ".join(HAB_CAPS[c] for c in t) or "CAPS sem habilitacao"))
    df["nome_parece_ad"] = df["nome"].apply(lambda n: nome_parece_ad(n) if isinstance(n, str) else False)
    df["habilitacoes"] = df["habilitacoes"].apply(",".join)
    df = _validar_coordenadas(df, mun)
    cols = ["cnes", "competencia", "ano", "cod_mun6", "nome", "tipo_servico", "tp_unid", "modalidade", "modalidade_ad",
            "eh_caps_ad", "nome_parece_ad", "habilitacoes", "leitos_sm_sus", "lat", "lon", "origem_coord", "coord_valida"]
    return df[cols].sort_values(["competencia", "cod_mun6", "cnes"]).reset_index(drop=True)
