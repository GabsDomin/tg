"""Orquestrador. Uso: python pipeline.py <etapa> [<etapa> ...]   (etapas idempotentes)"""
import sys

ETAPAS = {}


def etapa(nome):
    def deco(fn):
        ETAPAS[nome] = fn
        return fn
    return deco


@etapa("coleta")
def coleta():
    from tg.coleta import ftp, plano
    itens = plano.arquivos()
    tamanhos = {}
    for d in sorted({d for d, _, _ in itens}):
        tamanhos[d] = ftp.listar(d)
    for i, (d, n, sub) in enumerate(itens, 1):
        tam = tamanhos[d].get(n)
        if tam is None:
            print(f"[{i}/{len(itens)}] AUSENTE no FTP: {d}/{n}")
            continue
        ftp.baixar(d, n, sub, tamanho_remoto=tam)
        print(f"[{i}/{len(itens)}] ok {sub}/{n}", flush=True)


@etapa("territorio")
def territorio():
    from tg.config import CFG
    from tg.tratamento import municipios
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    m = municipios.construir_municipios()
    m.to_parquet(CFG.tratado / "municipios.parquet", index=False)
    p = municipios.construir_populacao()
    p.to_parquet(CFG.tratado / "populacao.parquet", index=False)
    print(f"municipios: {len(m)} | regioes de saude: {m['regiao_saude'].nunique()} | populacao: {len(p)} linhas")


@etapa("servicos")
def servicos():
    from tg.config import CFG
    from tg.tratamento import servicos as s
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    df = s.construir_servicos()
    df.to_parquet(CFG.tratado / "servicos.parquet", index=False)
    print(df.groupby(["competencia", "tipo_servico"]).size().unstack(fill_value=0).to_string())


@etapa("internacoes")
def internacoes():
    from tg.config import CFG
    from tg.tratamento import sih
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    base, fluxo, exc = sih.construir_internacoes()
    base.to_parquet(CFG.tratado / "internacoes.parquet", index=False)
    fluxo.to_parquet(CFG.tratado / "internacoes_fluxo.parquet", index=False)
    print(base.groupby("ano")[["n_internacoes", "n_aih_longa"]].sum().to_string())
    print(f"residentes fora de SP excluidos (registros F1x): {exc}")


@etapa("obitos")
def obitos():
    from tg.config import CFG
    from tg.tratamento import sim
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    df = sim.construir_obitos()
    df.to_parquet(CFG.tratado / "obitos.parquet", index=False)
    print(df.groupby("ano")["n_obitos"].sum().to_string())


@etapa("raas")
def raas():
    from tg.config import CFG
    from tg.tratamento import sia_ps
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    carga, fluxos = sia_ps.construir_raas()
    carga.to_parquet(CFG.tratado / "raas_carga.parquet", index=False)
    fluxos.to_parquet(CFG.tratado / "raas_fluxos.parquet", index=False)
    print(f"raas_carga: {len(carga)} linhas | raas_fluxos: {len(fluxos)} linhas")


@etapa("distancias")
def distancias():
    from tg.config import CFG
    from tg.tratamento import distancias as dist
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    df = dist.construir_distancias()
    df.to_parquet(CFG.tratado / "distancias.parquet", index=False)
    print(f"distancias: {len(df)} pares municipio-servico ate {dist.RAIO_MAX_KM:.0f} km")


@etapa("demanda")
def demanda():
    from tg.config import CFG
    from tg.indicadores import demanda as dm
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    df = dm.construir_demanda()
    df.to_parquet(CFG.tratado / "demanda.parquet", index=False)
    r = df.groupby("bloco")[["gama_a_int", "gama_b_int", "gama_a_obito", "gama_b_obito"]].first()
    print(r.round(3).to_string())


@etapa("acessibilidade")
def acessibilidade():
    from tg.config import CFG
    from tg.indicadores import acessibilidade as ac, oferta as of
    CFG.tratado.mkdir(parents=True, exist_ok=True)
    cap = of.capacidade_modalidade()
    cap.to_csv(CFG.tratado / "capacidade_modalidade.csv", index=False)
    print(cap.round(1).to_string(index=False))
    df = ac.construir_acessibilidade()
    df.to_parquet(CFG.tratado / "acessibilidade.parquet", index=False)
    print(f"acessibilidade: {len(df)} linhas (3 camadas x 6 anos x 645 municipios)")


def main(args):
    if not args or args[0] not in ETAPAS and args[0] != "tudo":
        print("etapas:", ", ".join(ETAPAS))
        return 1
    for nome in (ETAPAS if args[0] == "tudo" else args):
        print(f"== {nome} ==")
        ETAPAS[nome]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
