$path = Resolve-Path '.\start-dev.ps1'
$content = Get-Content -Path $path -Raw -Encoding UTF8
$utf8bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($path.Path, $content, $utf8bom)
Write-Host "UTF-8 BOM added to start-dev.ps1"
