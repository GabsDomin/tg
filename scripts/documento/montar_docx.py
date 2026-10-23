"""Monta o RASCUNHO dos capitulos 4 e 5 numa COPIA do TG (o original nao e alterado).

Uso: python -I scripts/documento/montar_docx.py <original.docx> <saida.docx> [paginas.json]

- Copia os paragrafos-modelo do proprio documento (corpo, Heading2, entrada do sumario), entao a
  formatacao (Arial 12, 1,5, recuo 1,25 cm, justificado) segue o padrao existente.
- Insere tabelas (Arial 9, bordas horizontais) e figuras PNG (word/media) com legenda acima e fonte abaixo.
- Trechos "[A CONFIRMAR: ...]" saem destacados em amarelo.
- paginas.json (opcional): {"4 ANÁLISES E RESULTADOS": 16, "4.1 ...": 16, ...} para atualizar o sumario manual.
"""
import json
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent))
from conteudo_cap4_cap5 import CAP4, CAP5  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
FIGURAS = RAIZ / "figuras"
LARGURA_UTIL = 9071            # DXA: 11906 - 1701 - 1134
EMU_CM = 360000

ARIAL = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="Arial"/>'


def run(t, sz=24, bold=False, destaque=False):
    rpr = f'{ARIAL}<w:b w:val="{1 if bold else 0}"/><w:i w:val="0"/><w:sz w:val="{sz}"/>' + ('<w:highlight w:val="yellow"/>' if destaque else "")
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(t)}</w:t></w:r>'


def runs(texto, sz=24, bold=False):
    """quebra em trechos, destacando [A CONFIRMAR: ...]"""
    partes = re.split(r"(\[A CONFIRMAR[^\]]*\])", texto)
    return "".join(run(p, sz, bold, destaque=p.startswith("[A CONFIRMAR")) for p in partes if p)


def p_corpo(t):
    return ('<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto" w:before="0" w:after="0"/><w:ind w:firstLine="709"/>'
            f'<w:jc w:val="both"/></w:pPr>{runs(t)}</w:p>')


def p_h2(t):
    return ('<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:keepNext/><w:widowControl/><w:jc w:val="left"/></w:pPr>'
            f'{run(t, 24, True)}</w:p>')


def p_legenda(t, keep=True):
    # "Tabela 1 - titulo" com o rotulo em negrito
    m = re.match(r"^((?:Tabela|Figura) \d+ –)(.*)$", t)
    corpo = run(m.group(1), 20, True) + run(m.group(2), 20) if m else run(t, 20)
    return ('<w:p><w:pPr>' + ('<w:keepNext/>' if keep else '') +
            '<w:spacing w:line="240" w:lineRule="auto" w:before="240" w:after="80"/><w:jc w:val="left"/></w:pPr>' + corpo + '</w:p>')


def p_fonte(t):
    return ('<w:p><w:pPr><w:spacing w:line="240" w:lineRule="auto" w:before="60" w:after="240"/><w:jc w:val="left"/></w:pPr>'
            f'{run(t, 20)}</w:p>')


def celula(t, w, header=False, esquerda=False, manter=True):
    """manter=True: o paragrafo fica na mesma pagina da linha seguinte (tabela nao se parte)"""
    shd = '<w:shd w:val="clear" w:color="auto" w:fill="E7E6E6"/>' if header else ""
    jc = "left" if esquerda else "center"
    keep = "<w:keepNext/>" if manter else ""
    return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}<w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr>{keep}<w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/><w:jc w:val="{jc}"/></w:pPr>'
            f'{run(t, 18, header)}</w:p></w:tc>')


def tabela(cab, linhas, larg):
    assert sum(larg) == LARGURA_UTIL, f"larguras somam {sum(larg)} (esperado {LARGURA_UTIL}): {cab}"
    assert all(len(l) == len(cab) for l in linhas), cab
    borda = 'w:val="single" w:sz="4" w:space="0" w:color="808080"'
    x = (f'<w:tbl><w:tblPr><w:tblW w:w="{LARGURA_UTIL}" w:type="dxa"/><w:jc w:val="center"/>'
         f'<w:tblBorders><w:top {borda}/><w:bottom {borda}/><w:insideH w:val="single" w:sz="2" w:space="0" w:color="BFBFBF"/></w:tblBorders>'
         '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
         '<w:tblGrid>' + "".join(f'<w:gridCol w:w="{w}"/>' for w in larg) + "</w:tblGrid>")
    x += '<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' + "".join(celula(c, w, True, i == 0) for i, (c, w) in enumerate(zip(cab, larg))) + "</w:tr>"
    for k, l in enumerate(linhas):
        ultima = k == len(linhas) - 1
        x += '<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(
            celula(c, w, False, i == 0, manter=not ultima) for i, (c, w) in enumerate(zip(l, larg))) + "</w:tr>"
    return x + "</w:tbl>"


def dimensoes_png(caminho):
    with open(caminho, "rb") as f:
        cab = f.read(24)
    assert cab[:8] == b"\x89PNG\r\n\x1a\n", caminho
    return struct.unpack(">II", cab[16:24])


def figura_xml(rid, docpr_id, arquivo, largura_cm):
    w_px, h_px = dimensoes_png(FIGURAS / arquivo)
    cx = int(largura_cm * EMU_CM)
    cy = int(cx * h_px / w_px)
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    return ('<w:p><w:pPr><w:keepNext/><w:spacing w:line="240" w:lineRule="auto" w:before="0" w:after="0"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{docpr_id}" name="Figura {docpr_id}" descr="{escape(arquivo)}"/>'
            f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="{A}" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            f'<a:graphic xmlns:a="{A}"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="0" name="{escape(arquivo)}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


def renderizar(itens, midias):
    out = []
    for it in itens:
        k = it[0]
        if k == "p":
            out.append(p_corpo(it[1]))
        elif k == "h2":
            out.append(p_h2(it[1]))
        elif k == "tabela":
            _, n, titulo, cab, linhas, larg, fonte = it
            out += [p_legenda(f"Tabela {n} – {titulo}"), tabela(cab, linhas, larg), p_fonte(fonte)]
        elif k == "figura":
            _, arq, n, titulo, larg_cm, fonte = it
            rid = f"rIdFig{n}"
            midias.append((rid, arq))
            out += [p_legenda(f"Figura {n} – {titulo}"), figura_xml(rid, 900 + n, arq, larg_cm), p_fonte(fonte)]
        else:
            raise ValueError(k)
    return "".join(out)


def paragrafo_h1(xml, texto):
    """posicao final do paragrafo Heading1 com o texto (corpo, nao sumario)"""
    for m in re.finditer(r"<w:p>(?:(?!</w:p>).)*?w:pStyle w:val=\"Heading1\"(?:(?!</w:p>).)*?</w:p>", xml, flags=re.S):
        if texto in m.group(0):
            return m.end()
    raise LookupError(texto)


def atualizar_sumario(xml, paginas):
    """acrescenta 4.1..4.9 ao sumario manual e atualiza numeros dos itens novos"""
    modelo = re.search(r"<w:p><w:pPr><w:tabs>(?:(?!</w:p>).)*?<w:t>1\.1 Justificativa</w:t><w:tab/><w:t>\d+</w:t></w:r></w:p>", xml, flags=re.S).group(0)

    def entrada(txt, pg):
        return modelo.replace("<w:t>1.1 Justificativa</w:t>", f"<w:t>{escape(txt)}</w:t>").replace("<w:t>5</w:t></w:r>", f"<w:t>{pg}</w:t></w:r>")

    subs = [it[1] for it in CAP4 if it[0] == "h2"]
    # 1) acrescenta subsecoes apos a entrada "4 ANALISES"
    m = re.search(r"<w:p><w:pPr><w:tabs>(?:(?!</w:p>).)*?<w:t>4 ANÁLISES E RESULTADOS</w:t><w:tab/><w:t>\d+</w:t></w:r></w:p>", xml, flags=re.S)
    novas = "".join(entrada(t, paginas.get(t, "")) for t in subs)
    xml = xml[:m.end()] + novas + xml[m.end():]
    # 2) atualiza numeros dos itens 4, 5 e REFERENCIAS
    for t in ("4 ANÁLISES E RESULTADOS", "5 CONSIDERAÇÕES FINAIS", "REFERÊNCIAS"):
        if t in paginas:
            xml = re.sub(rf"(<w:t>{re.escape(t)}</w:t><w:tab/><w:t>)\d+(</w:t>)", rf"\g<1>{paginas[t]}\g<2>", xml, count=1)
    return xml


def main(orig, saida, paginas=None):
    paginas = json.loads(Path(paginas).read_text(encoding="utf-8")) if paginas else {}
    zin = zipfile.ZipFile(orig)
    partes = {n: zin.read(n) for n in zin.namelist()}
    ordem = list(zin.namelist())
    xml = partes["word/document.xml"].decode("utf-8")

    midias = []
    c4, c5 = renderizar(CAP4, midias), renderizar(CAP5, midias)
    i4 = paragrafo_h1(xml, "4 ANÁLISES E RESULTADOS")
    xml = xml[:i4] + c4 + xml[i4:]
    # A quebra de pagina solta do original (paragrafo vazio entre o cap. 4 e o 5) gera pagina em branco quando o
    # texto termina no fim da pagina. Troca por "quebra antes" no titulo do cap. 5 (nao depende do layout).
    quebra = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    k = xml.find(quebra, i4 + len(c4) - 1)
    assert k != -1 and k < xml.find("5 CONSIDERAÇÕES FINAIS</w:t></w:r></w:p>", i4 + len(c4)), "quebra do cap. 4 nao encontrada"
    xml = xml[:k] + xml[k + len(quebra):]
    h5 = re.search(r'<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:keepNext/>(?=<w:widowControl/><w:jc w:val="left"/></w:pPr><w:r>(?:(?!</w:p>).)*?5 CONSIDERAÇÕES FINAIS)', xml, flags=re.S)
    xml = xml[:h5.end()] + "<w:pageBreakBefore/>" + xml[h5.end():]
    i5 = paragrafo_h1(xml, "5 CONSIDERAÇÕES FINAIS")
    xml = xml[:i5] + c5 + xml[i5:]
    xml = atualizar_sumario(xml, paginas)
    partes["word/document.xml"] = xml.encode("utf-8")

    rels = partes["word/_rels/document.xml.rels"].decode("utf-8")
    novas = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{arq}"/>'
                    for rid, arq in midias)
    partes["word/_rels/document.xml.rels"] = rels.replace("</Relationships>", novas + "</Relationships>").encode("utf-8")
    ct = partes["[Content_Types].xml"].decode("utf-8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default Extension=\"rels\"", '<Default Extension="png" ContentType="image/png"/><Default Extension="rels"', 1)
    partes["[Content_Types].xml"] = ct.encode("utf-8")
    for _, arq in midias:
        partes[f"word/media/{arq}"] = (FIGURAS / arq).read_bytes()
        ordem.append(f"word/media/{arq}")

    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in ordem:
            zout.writestr(n, partes[n])
    print(f"ok: {saida} | {len(CAP4)} blocos no cap. 4, {len(CAP5)} no cap. 5, {len(midias)} figuras")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
