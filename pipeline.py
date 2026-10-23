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
