# Use após configurar no roteador o redirecionamento da porta para este computador.
$env:SEPEX_HOST = '0.0.0.0'
$env:SEPEX_ADMIN_LOCAL_ONLY = '1'
if (-not $env:SEPEX_PORT) { $env:SEPEX_PORT = '5000' }
if (-not $env:SEPEX_ADMIN_TOKEN -or -not $env:SEPEX_SECRET_KEY) {
    throw 'Defina SEPEX_ADMIN_TOKEN e SEPEX_SECRET_KEY no ambiente antes de expor o programa à internet.'
}

$ipPublico = $null
try { $ipPublico = (Invoke-RestMethod -Uri 'https://api.ipify.org' -TimeoutSec 5).Trim() }
catch { Write-Warning 'Não foi possível consultar o IP público. Verifique o endereço WAN no roteador.' }

Write-Host 'ABAQUAR · acesso pela internet'
if ($ipPublico) { Write-Host "Endereço externo possível: http://$($ipPublico):$($env:SEPEX_PORT)" }
Write-Host 'O roteador precisa encaminhar a porta TCP escolhida para o IPv4 local deste computador.'
Write-Host 'O firewall também precisa permitir essa porta. Teste a partir de um celular usando dados móveis.'
Write-Host "Administração disponível somente neste computador por http://127.0.0.1:$($env:SEPEX_PORT)"

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
Push-Location $PSScriptRoot
try { & $python servir.py } finally { Pop-Location }
