# Abre uma COPIA do .docx no Word (somente leitura), le a pagina de cada titulo e exporta PDF.
# Uso: powershell -File paginar_word.ps1 <docx> <saida.json> <saida.pdf>
param([string]$Docx, [string]$Json, [string]$Pdf)
$ErrorActionPreference = "Stop"
$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
try {
    $d = $w.Documents.Open((Resolve-Path $Docx).Path, $false, $true)
    $d.Repaginate()
    $out = [ordered]@{}
    foreach ($p in $d.Paragraphs) {
        if ($p.OutlineLevel -le 2) {
            $t = $p.Range.Text.Trim()
            if ($t.Length -gt 0 -and -not $out.Contains($t)) { $out[$t] = [int]$p.Range.Information(1) }
        }
    }
    # "REFERENCIAS" nao e titulo (sem estilo): acha pelo texto
    foreach ($p in $d.Paragraphs) {
        $t = $p.Range.Text.Trim()
        if ($t -eq "REFERÊNCIAS" -and $p.OutlineLevel -gt 2) { $out["REFERÊNCIAS"] = [int]$p.Range.Information(1) }
    }
    $out["__paginas_total"] = [int]$d.ComputeStatistics(2)
    $out | ConvertTo-Json | Out-File -Encoding utf8 $Json
    $pdfPath = [System.IO.Path]::GetFullPath($Pdf)
    $d.ExportAsFixedFormat($pdfPath, 17)
    $d.Close(0)
} finally {
    $w.Quit()
}
