$bytes = Get-Content -Path .\start-dev.ps1 -Encoding Byte -TotalCount 3
$hex = $bytes | ForEach-Object { '{0:X2}' -f $_ }
Write-Host "First 3 bytes: $($hex -join ' ')"
if ($hex[0] -eq 'EF' -and $hex[1] -eq 'BB' -and $hex[2] -eq 'BF') {
    Write-Host "UTF-8 BOM detected - OK!" -ForegroundColor Green
} else {
    Write-Host "No BOM found" -ForegroundColor Red
}
