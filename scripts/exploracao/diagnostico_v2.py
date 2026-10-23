"""
DIAGNOSTICO v2 - CAPS em SP com dado estruturado (CNES set/2026)

Substitui o diagnostico_viabilidade.py, que dependia da API (inacessivel)
e inferia modalidade pelo nome. Aqui:
  - estabelecimentos: ST (FTP DATASUS, competencia 2026-09)
  - modalidade:       HB (habilitacoes vigentes), codigos conferidos em
                      TAB_CNES/DBF/HABILITA.DBF
  - nome e coordenadas: cnes_estabelecimentos.csv do OpenDataSUS (jun/2025)
  - validacao geografica: malha municipal IBGE (API v3)

Uso:  .venv\\Scripts\\python.exe -I scripts\\exploracao\\diagnostico_v2.py  (a partir da pasta TG)
"""

import os
import re
import pandas as pd
import geopandas as gpd
from dbfread import DBF
from pyreaddbc import dbc2dbf

BRUTOS = "dados/bruto"
COMPETENCIA = "202609"

# conferidos em HABILITA.DBF (TAB_CNES out/2026)
HAB_CAPS = {
    "0616": "CAPS I", "0617": "CAPS II", "0618": "CAPS III",
    "0619": "CAPS AD", "0620": "CAPS i", "0635": "CAPS AD III",
    "0637": "CAPS AD IV",
}
HAB_AD = {"0619", "0635", "0637"}


def read_dbc(caminho):
    """Descompacta .dbc -> .dbf (uma vez) e le como DataFrame."""
    dbf = caminho[:-4] + ".dbf"
    if not os.path.exists(dbf):
        dbc2dbf(caminho, dbf)
    return pd.DataFrame(iter(DBF(dbf, encoding="latin1", char_decode_errors="replace")))


def nome_parece_ad(nome):
    """Regex corrigida: nao casa com 'CAPS ADULTO'."""
    n = " " + re.sub(r"[-./]", " ", str(nome).upper()).replace("A D ", "AD ") + " "
    return bool(re.search(r"CAPSAD|[^A-Z]AD[^A-Z]|ALCOOL|DROGA", n))


def modalidade_ad(codigos):
    if "0637" in codigos:
        return "AD IV"
    if "0635" in codigos:
        return "AD III"
    if "0619" in codigos:
        return "AD II"
    return None


# ----------------------------------------------------------------------
st = read_dbc(f"{BRUTOS}/STSP2609.dbc")
caps = st[st["TP_UNID"].astype(str).str.strip() == "70"][["CNES", "CODUFMUN", "REGSAUDE"]].copy()

hb = read_dbc(f"{BRUTOS}/HBSP2609.dbc")
fim = hb["CMPT_FIM"].astype(str).str.strip()
hb = hb[(fim == "") | (fim >= COMPETENCIA)]  # so habilitacoes vigentes
hb = hb[hb["SGRUPHAB"].isin(HAB_CAPS)]
cods = hb.groupby("CNES")["SGRUPHAB"].apply(set)

caps["habilitacoes"] = caps["CNES"].map(cods).apply(lambda s: s if isinstance(s, set) else set())
caps["habilitacao_desc"] = caps["habilitacoes"].apply(lambda s: " + ".join(sorted(HAB_CAPS[c] for c in s)))
caps["modalidade_ad"] = caps["habilitacoes"].apply(modalidade_ad)

od = pd.read_csv(f"{BRUTOS}/opendatasus_cnes_estabelecimentos_jun2025.zip", sep=";", dtype=str,
                 encoding="latin1", usecols=["CO_CNES", "CO_UF", "NO_FANTASIA", "NU_LATITUDE", "NU_LONGITUDE"])
od = od[od["CO_UF"] == "35"]
od["CNES"] = od["CO_CNES"].str.zfill(7)
caps = caps.merge(od[["CNES", "NO_FANTASIA", "NU_LATITUDE", "NU_LONGITUDE"]], on="CNES", how="left")
caps["nome_parece_ad"] = caps["NO_FANTASIA"].apply(lambda n: nome_parece_ad(n) if pd.notna(n) else None)

print("=" * 70)
print(f"CAPS (tipo 70) em SP, competencia {COMPETENCIA}: {len(caps)} em {caps['CODUFMUN'].nunique()} municipios")
print("=" * 70)

print("\nCombinacoes de habilitacao vigente:")
print(caps["habilitacao_desc"].replace("", "(nenhuma habilitacao CAPS)").value_counts().to_string())

ad = caps[caps["modalidade_ad"].notna()]
print(f"\nCAPS AD habilitados: {len(ad)} em {ad['CODUFMUN'].nunique()} municipios "
      f"| capital: {(ad['CODUFMUN'] == '355030').sum()}")
print(ad["modalidade_ad"].value_counts().to_string())

print("\nNome x habilitacao (onde ha nome):")
cx = caps[caps["nome_parece_ad"].notna()]
print(pd.crosstab(cx["nome_parece_ad"].map({True: "nome diz AD", False: "nome nao diz AD"}),
                  cx["modalidade_ad"].notna().map({True: "habilitado AD", False: "nao habilitado AD"})).to_string())
divergentes = cx[cx["nome_parece_ad"] & cx["modalidade_ad"].isna()]
print(f"\nNome diz AD mas sem habilitacao AD ({len(divergentes)}):")
for _, r in divergentes.iterrows():
    print(f"  {r['CNES']} {r['CODUFMUN']} {str(r['NO_FANTASIA'])[:45]:<45} hab: {r['habilitacao_desc'] or '-'}")
print(f"\nCAPS do ST sem correspondencia no arquivo de jun/2025 (novos, sem nome/coord): "
      f"{caps['NO_FANTASIA'].isna().sum()}")

# ----------------------------------------------------------------------
print("\n" + "=" * 70)
print("VALIDACAO GEOGRAFICA: a coordenada cai dentro do municipio declarado?")
print("=" * 70)
malha = gpd.read_file(f"{BRUTOS}/malha_sp_municipios.geojson")
malha["CODUFMUN"] = malha["codarea"].astype(str).str[:6]

geo = caps.dropna(subset=["NU_LATITUDE", "NU_LONGITUDE"]).copy()
pts = gpd.GeoDataFrame(geo, geometry=gpd.points_from_xy(geo["NU_LONGITUDE"].astype(float),
                                                         geo["NU_LATITUDE"].astype(float)), crs=malha.crs)
cai = gpd.sjoin(pts, malha[["CODUFMUN", "geometry"]], how="left", predicate="within", rsuffix="malha")
geo["mun_da_coordenada"] = cai["CODUFMUN_malha"].values
geo["coord_ok"] = geo["mun_da_coordenada"] == geo["CODUFMUN"]
caps = caps.merge(geo[["CNES", "mun_da_coordenada", "coord_ok"]], on="CNES", how="left")

for rot, sub in (("todos os CAPS", geo), ("CAPS AD", geo[geo["modalidade_ad"].notna()])):
    ok = sub["coord_ok"].sum()
    print(f"  {rot:<14} {ok}/{len(sub)} dentro do municipio declarado ({100 * ok / len(sub):.1f}%)")
erros = geo[~geo["coord_ok"]]
print(f"\nCoordenadas fora do municipio declarado ({len(erros)}):")
for _, r in erros.iterrows():
    print(f"  {r['CNES']} declarado {r['CODUFMUN']} -> cai em {r['mun_da_coordenada']}  {str(r['NO_FANTASIA'])[:40]}")

caps["habilitacoes"] = caps["habilitacoes"].apply(lambda s: ",".join(sorted(s)))
caps.to_csv("dados/tratado/caps_sp_202609.csv", sep=";", index=False, encoding="utf-8")
print("\nsalvo em dados/tratado/caps_sp_202609.csv")
