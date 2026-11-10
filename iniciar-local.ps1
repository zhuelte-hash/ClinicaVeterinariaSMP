param([switch]$SinWorker)

$ErrorActionPreference = 'Stop'
$backend = Join-Path $PSScriptRoot 'backend'
$frontend = Join-Path $PSScriptRoot 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath (Join-Path $backend '.env'))) {
    throw 'Falta backend/.env. Configura DATABASE_URL con tu conexion a Neon y SECRET_KEY.'
}
if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) {
    throw 'El puerto 8000 esta ocupado. Deten el backend anterior antes de iniciar.'
}

if (-not (Test-Path -LiteralPath $python)) {
    python -m venv (Join-Path $backend '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno virtual de Python.' }
}
& $python -m pip install --disable-pip-version-check -r (Join-Path $backend 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de Python.' }
Push-Location $backend
try {
    & $python -c 'import app.main'
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo cargar la API. Revisa la configuracion y dependencias.' }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath (Join-Path $frontend 'node_modules\@angular\cli\bin\ng.js'))) {
    Push-Location $frontend
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de Angular.' }
    } finally {
        Pop-Location
    }
}

function Start-LocalTerminal([string]$Title, [string]$Directory, [string]$Command) {
    $escapedTitle = $Title.Replace("'", "''")
    $script = "`$Host.UI.RawUI.WindowTitle = '$escapedTitle'; $Command"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
    Start-Process powershell.exe -WorkingDirectory $Directory -ArgumentList @(
        '-NoProfile', '-NoExit', '-EncodedCommand', $encoded
    ) | Out-Null
}

$escapedPython = $python.Replace("'", "''")
Start-LocalTerminal 'SMP - Backend' $backend "& '$escapedPython' run.py"
if (-not $SinWorker) {
    Start-LocalTerminal 'SMP - Citas automaticas' $backend "& '$escapedPython' -m app.tasks.appointment_worker"
}
if (Get-NetTCPConnection -State Listen -LocalPort 4200 -ErrorAction SilentlyContinue) {
    Write-Host 'El puerto 4200 ya esta ocupado; se conserva el frontend existente.'
} else {
    Start-LocalTerminal 'SMP - Frontend' $frontend 'npm.cmd start'
}

Write-Host 'Frontend: http://localhost:4200'
Write-Host 'API:      http://localhost:8000/docs'
Write-Host 'Para detener cada proceso, presiona Ctrl+C en su ventana.'
