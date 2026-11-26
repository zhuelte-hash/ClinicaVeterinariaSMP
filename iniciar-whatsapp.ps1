$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
$configure = Join-Path $PSScriptRoot 'backend\scripts\configure_manual_whatsapp.py'
$launcher = Join-Path $PSScriptRoot 'backend\scripts\start_manual_app.py'
$index = Join-Path $PSScriptRoot 'frontend\dist\browser\index.html'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Falta el entorno Python. Ejecuta primero la instalacion de dependencias del backend.'
}
if (-not (Test-Path -LiteralPath $index)) {
    throw 'Falta compilar el frontend. Ejecuta npm run build desde la carpeta frontend.'
}

& $python $configure
if ($LASTEXITCODE -ne 0) { throw 'No se pudo configurar WhatsApp manual.' }

$temporary = Join-Path ([System.IO.Path]::GetTempPath()) 'opencode'
if (-not (Test-Path -LiteralPath $temporary)) {
    New-Item -ItemType Directory -Path $temporary | Out-Null
}
$session = Join-Path $temporary ('whatsapp-' + [Guid]::NewGuid().ToString('N'))
Write-Host 'Aplicacion: http://localhost:8000/inicio'
Write-Host 'Conserva esta ventana abierta mientras pruebas WhatsApp. Para detener: Ctrl+C.'
& $python $launcher --session $session
if ($LASTEXITCODE -ne 0) { throw 'No se pudo mantener iniciada la aplicacion. Revisa el mensaje anterior.' }
