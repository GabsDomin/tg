"""tratado/municipios.parquet e tratado/populacao.parquet (IBGE + TAB_CNES)."""
import re
import zipfile

import geopandas as gpd
import pandas as pd

from tg.coleta import ibge
from tg.config import CFG

CRS_METRICO = "EPSG:5880"  # SIRGAS 2000 / Brazil Polyconic (so para ponto representativo)


def tab_cnes():
    """Pasta com TAB_CNES extraido (idempotente). Devolve dados/bruto/cnes/tab_cnes."""
    destino = CFG.bruto / "cnes" / "tab_cnes"
    if not (destino / "CNV").exists():
        with zipfile.ZipFile(CFG.bruto / "cnes" / "TAB_CNES.zip") as z:
            z.extractall(destino)
    return destino


def _regioes_de_saude():
    """cod_mun6 -> (codigo_regiao, nome_regiao), do conversor oficial do CNES."""
    rx = re.compile(r"^\s*\d+\s+(\d{5})\s+(.+?)\s+(\d{6})\s*$")
    linhas = []
    cnv = tab_cnes() / "CNV" / f"{CFG.uf}_regsaud.cnv"
    for ln in cnv.read_text(encoding="latin1").splitlines():
        m = rx.match(ln)
        if m:
            linhas.append({"regiao_saude": m.group(1), "nome_regiao": m.group(2), "cod_mun6": m.group(3)})
    return pd.DataFrame(linhas)


def construir_municipios():
    loc = pd.DataFrame([{"cod_mun7": str(m["id"]), "nome": m["nome"]} for m in ibge.municipios_sp()])
    loc["cod_mun6"] = loc["cod_mun7"].str[:6]

    malha = gpd.read_file(CFG.bruto / "malha_sp_municipios.geojson")
    malha["cod_mun7"] = malha["codarea"].astype(str)
    pts = malha.set_index("cod_mun7").to_crs(CRS_METRICO).geometry.representative_point()
    pts = gpd.GeoSeries(pts, crs=CRS_METRICO).to_crs("EPSG:4326")
    geo = pd.DataFrame({"cod_mun7": pts.index, "lat": pts.y.values, "lon": pts.x.values})

    area = pd.DataFrame(ibge.sidra(4714, 6318, [2022], nome_cache="sidra_4714_area.json"))
    area = area.assign(area_km2=pd.to_numeric(area["valor"], errors="coerce"))[["cod7", "area_km2"]]
    area = area.rename(columns={"cod7": "cod_mun7"})

    df = (loc.merge(geo, on="cod_mun7", how="left")
             .merge(area, on="cod_mun7", how="left")
             .merge(_regioes_de_saude(), on="cod_mun6", how="left"))
    return df.sort_values("cod_mun6").reset_index(drop=True)


def construir_populacao():
    anos = sorted(set(CFG.anos_construcao) | set(CFG.anos_avaliacao))
    est = pd.DataFrame(ibge.sidra(6579, 9324, anos, nome_cache="sidra_6579_estimativas.json"))
    est["pop_total"] = pd.to_numeric(est["valor"], errors="coerce")
    est["ano"] = est["periodo"].astype(int)
    est["fonte_pop"] = "estimativa"

    # A tabela 6579 nao tem 2022 (ano do Censo) nem 2023. 2022 = Censo (tabela 4714);
    # 2023 = interpolacao geometrica 2022-2024. Ha descontinuidade 2021 -> 2022 (projecoes
    # antigas vs. Censo), tratada como limitacao em docs/.
    censo = pd.DataFrame(ibge.sidra(4714, 93, [2022], nome_cache="sidra_4714_pop.json"))
    censo = censo.assign(pop_total=pd.to_numeric(censo["valor"], errors="coerce"), ano=2022,
                         fonte_pop="censo")[["cod7", "ano", "pop_total", "fonte_pop"]]
    p24 = est.loc[est["ano"] == 2024].set_index("cod7")["pop_total"]
    interp = censo.set_index("cod7")["pop_total"].mul(p24).pow(0.5).round().rename("pop_total").reset_index()
    interp = interp.assign(ano=2023, fonte_pop="interpolado")
    est = pd.concat([est[["cod7", "ano", "pop_total", "fonte_pop"]], censo, interp], ignore_index=True)
    est = est[est["ano"].isin(anos)]
    est["cod_mun6"] = est["cod7"].str[:6]

    # Proporcao 15+ do Censo 2022 (tabela 9514), aplicada a todos os anos:
    # nao ha populacao por idade anual por municipio. Aproximacao declarada em docs.
    idade = pd.DataFrame(ibge.sidra(
        9514, 93, [2022], classificacao="2[6794]|286[113635]|287[100362,93070,93084,93085]",
        nome_cache="sidra_9514_idade_0a14.json"))
    idade["v"] = pd.to_numeric(idade["valor"], errors="coerce")
    idade["faixa"] = idade["classif"].str.extract(r"287:(\w+)")
    p = idade.pivot_table(index="cod7", columns="faixa", values="v", aggfunc="sum")
    # 100362 = total; 93070/93084/93085 = 0-4, 5-9, 10-14
    p["prop_15mais"] = 1 - (p["93070"] + p["93084"] + p["93085"]) / p["100362"]
    prop = p["prop_15mais"].rename_axis("cod7").reset_index()
    est = est.merge(prop, on="cod7", how="left")
    est["pop_15mais"] = (est["pop_total"] * est["prop_15mais"]).round()
    return est[["cod_mun6", "ano", "pop_total", "pop_15mais", "prop_15mais", "fonte_pop"]].sort_values(["cod_mun6", "ano"]).reset_index(drop=True)
