"""tratado/distancias.parquet: distancia haversine (km) do ponto representativo de cada municipio
a cada servico (CNES), ate RAIO_MAX_KM. Limitacao declarada: distancia em linha reta, nao por estrada."""
import numpy as np
import pandas as pd

from tg.config import CFG

RAIO_MAX_KM = 200.0
R_TERRA_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia em km; aceita arrays com broadcasting."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * R_TERRA_KM * np.arcsin(np.sqrt(a))


def construir_distancias():
    mun = pd.read_parquet(CFG.tratado / "municipios.parquet")
    s = pd.read_parquet(CFG.tratado / "servicos.parquet")
    # coordenada de cada CNES: a da competencia mais recente em que aparece
    serv = s.sort_values("competencia").drop_duplicates("cnes", keep="last")[["cnes", "lat", "lon"]].reset_index(drop=True)

    d = haversine_km(mun["lat"].values[:, None], mun["lon"].values[:, None],
                     serv["lat"].values[None, :], serv["lon"].values[None, :])
    i, j = np.where(d <= RAIO_MAX_KM)
    out = pd.DataFrame({"cod_mun6": mun["cod_mun6"].values[i], "cnes": serv["cnes"].values[j],
                        "km": d[i, j].round(2)})
    return out
