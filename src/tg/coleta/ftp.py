"""Download do FTP do DATASUS com cache por tamanho, retentativas e manifesto."""
import csv
import ftplib
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from tg.config import CFG

HOST = urlparse(CFG.ftp.base).hostname
BASE = urlparse(CFG.ftp.base).path
MANIFESTO = CFG.bruto / "_manifesto.csv"
TENTATIVAS = 3


def _conectar():
    ftp = ftplib.FTP(HOST, timeout=120)
    ftp.login()
    return ftp


def listar(diretorio):
    """{nome: tamanho} de um diretorio remoto (relativo a CFG.ftp.base)."""
    ftp = _conectar()
    try:
        ftp.cwd(f"{BASE}/{diretorio}")
        linhas = []
        ftp.retrlines("LIST", linhas.append)
    finally:
        ftp.quit()
    saida = {}
    for ln in linhas:
        partes = ln.split(None, 3)
        if len(partes) == 4 and partes[2].isdigit():  # formato Windows/IIS: data hora tamanho nome
            saida[partes[3]] = int(partes[2])
    return saida


def _registrar(caminho, tamanho, remoto):
    novo = not MANIFESTO.exists()
    with open(MANIFESTO, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if novo:
            w.writerow(["arquivo", "tamanho_bytes", "origem", "baixado_em"])
        w.writerow([caminho.relative_to(CFG.bruto).as_posix(), tamanho, remoto,
                    datetime.now().isoformat(timespec="seconds")])


def baixar(diretorio, nome, destino_sub, tamanho_remoto=None):
    """Baixa `nome` de `diretorio` para dados/bruto/<destino_sub>/. Pula se o tamanho confere."""
    destino = CFG.bruto / destino_sub
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / nome
    remoto = f"{diretorio}/{nome}"

    if tamanho_remoto is None:
        tamanho_remoto = listar(diretorio).get(nome)
        if tamanho_remoto is None:
            raise FileNotFoundError(remoto)
    if alvo.exists() and alvo.stat().st_size == tamanho_remoto:
        return alvo

    parcial = alvo.with_suffix(alvo.suffix + ".part")
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            ftp = _conectar()
            try:
                ftp.cwd(f"{BASE}/{diretorio}")
                ftp.voidcmd("TYPE I")
                with open(parcial, "wb") as f:
                    ftp.retrbinary(f"RETR {nome}", f.write, blocksize=1 << 16)
            finally:
                try:
                    ftp.quit()
                except Exception:
                    pass
            if parcial.stat().st_size != tamanho_remoto:
                raise IOError(f"tamanho divergente: {parcial.stat().st_size} != {tamanho_remoto}")
            parcial.replace(alvo)
            _registrar(alvo, tamanho_remoto, remoto)
            return alvo
        except Exception as e:
            if tentativa == TENTATIVAS:
                raise
            print(f"  ! {remoto} tentativa {tentativa} falhou ({e}); repetindo")
            time.sleep(5 * tentativa)
