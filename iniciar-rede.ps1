# Execute no computador que hospeda o programa, após instalar as dependências.
$env:SEPEX_HOST = '0.0.0.0'
if (-not $env:SEPEX_PORT) { $env:SEPEX_PORT = '5000' }

$enderecos = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.|0\.)' -and $_.PrefixOrigin -ne 'WellKnown' } |
    Select-Object -ExpandProperty IPAddress -Unique

Write-Host 'ABAQUAR · acesso na rede local'
Write-Host 'Use no celular conectado à mesma rede Wi-Fi:'
foreach ($endereco in $enderecos) { Write-Host "  http://$($endereco):$($env:SEPEX_PORT)" }
if (-not $enderecos) { Write-Host '  Nenhum IPv4 de rede foi encontrado. Verifique a conexão do computador.' }
Write-Host "No próprio computador: http://127.0.0.1:$($env:SEPEX_PORT)"
Write-Host 'Se o celular não abrir, confira o firewall e o isolamento entre clientes da rede Wi-Fi.'

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
Push-Location $PSScriptRoot
try { & $python run.py } finally { Pop-Location }
