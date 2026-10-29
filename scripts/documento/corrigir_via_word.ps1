# Aplica correcoes pontuais de texto ao rascunho .docx via Word (sem Python), refaz a paginacao e corrige o sumario manual.
# Uso: powershell -File corrigir_via_word.ps1 <docx> <pdf_saida>
param([string]$Docx, [string]$Pdf)
$ErrorActionPreference = "Stop"
$caminho = (Resolve-Path $Docx).Path

# (trecho antigo curto, ate 255 caracteres) -> (texto novo, sem limite)
$trocas = @(
  @{ de = "Segundo o conversor oficial do CNES, o estado possui 62 regiões de saúde, e não 63.";
     para = "O conversor do CNES utilizado lista 62 regiões de saúde para o estado, número que acompanha a atualização do desenho regional pela Comissão Intergestores Bipartite de São Paulo em 2024 [A CONFIRMAR: número e data da deliberação da CIB-SP]; documentos anteriores citam 63." },
  @{ de = "e as menores, na Baixada Santista (16,8), em Sorocaba (19,3) e em Itapetininga (19,7).";
     para = "e as menores, entre as regiões com mais de 50 internações no biênio, na Baixada Santista (16,8), em Sorocaba (19,3) e em Itapetininga (19,7). Duas regiões com menos internações têm taxas ainda menores (Vale do Ribeira, 8,5, e Sul – Barretos, 16,7), mas com números absolutos pequenos." }
)

$w = New-Object -ComObject Word.Application
$w.Visible = $false; $w.DisplayAlerts = 0
try {
  $d = $w.Documents.Open($caminho, $false, $false)
  foreach ($t in $trocas) {
    $r = $d.Content
    $f = $r.Find; $f.ClearFormatting(); $f.Forward = $true; $f.Wrap = 0; $f.MatchCase = $true
    if ($f.Execute($t.de)) { $r.Text = $t.para; Write-Host "trocado: $($t.de.Substring(0,40))..." } else { Write-Host "NAO ENCONTRADO: $($t.de.Substring(0,40))..." }
  }
  # destaca [A CONFIRMAR ...] em amarelo (o texto novo entrou sem formatacao de destaque)
  $r = $d.Content; $f = $r.Find; $f.ClearFormatting(); $f.MatchWildcards = $true; $f.Wrap = 0
  while ($f.Execute("\[A CONFIRMAR*\]")) { $r.HighlightColorIndex = 7; $r.Collapse(0) }

  $d.Repaginate()
  # pagina real de cada titulo (numero exibido)
  $pag = @{}
  foreach ($p in $d.Paragraphs) { if ($p.OutlineLevel -le 2) { $t = $p.Range.Text.Trim(); if ($t -and -not $pag.ContainsKey($t)) { $pag[$t] = [int]$p.Range.Information(1) } } }
  # confere/corrige as linhas do sumario manual:  "titulo<TAB>numero"
  $corrigidos = 0; $conferidos = 0
  foreach ($p in $d.Paragraphs) {
    $txt = $p.Range.Text.TrimEnd("`r", "`a")
    if ($txt -match "^(?<titulo>.+?)\t(?<n>\d+)$" -and $pag.ContainsKey($Matches.titulo)) {
      $conferidos++
      $real = $pag[$Matches.titulo]
      if ([int]$Matches.n -ne $real) {
        $fim = $p.Range.End - 1; $ini = $fim - $Matches.n.Length
        $d.Range($ini, $fim).Text = "$real"; $corrigidos++
        Write-Host "sumario: '$($Matches.titulo)' $($Matches.n) -> $real"
      }
    }
  }
  Write-Host "linhas do sumario conferidas: $conferidos | corrigidas: $corrigidos"
  $d.Save()
  $d.ExportAsFixedFormat([IO.Path]::GetFullPath($Pdf), 17)
  Write-Host ("paginas: " + $d.ComputeStatistics(2))
  $d.Close(0)
} finally { $w.Quit() }
