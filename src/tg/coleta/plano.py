"""Lista de arquivos a coletar, derivada de config.yaml."""
from tg.config import CFG

UF = CFG.uf


def arquivos():
    """[(diretorio_remoto, nome, subpasta_destino)]"""
    itens = []
    for comp in CFG.competencias_cnes:
        aamm = comp[2:]
        for tipo in ("ST", "HB", "LT"):
            itens.append((f"{CFG.ftp.cnes}/{tipo}", f"{tipo}{UF}{aamm}.dbc", f"cnes/{tipo.lower()}"))
    itens.append((CFG.ftp.cnes_auxiliar, "TAB_CNES.zip", "cnes"))

    anos = sorted(set(CFG.anos_construcao) | set(CFG.anos_avaliacao))
    for ano in anos:
        aa = str(ano)[2:]
        itens.append((CFG.ftp.sim, f"DO{UF}{ano}.dbc", "sim"))
        for mes in range(1, 13):
            itens.append((CFG.ftp.sih, f"RD{UF}{aa}{mes:02d}.dbc", "sih"))
            itens.append((CFG.ftp.sia, f"PS{UF}{aa}{mes:02d}.dbc", "sia_ps"))
    return itens
