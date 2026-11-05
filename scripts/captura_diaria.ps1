# Una pasada de captura del catálogo (la ejecuta la tarea programada "MasBaratoAqui - Captura").
#
# Si la base es local, arranca Docker Desktop y PostgreSQL. Luego corre el worker una vez.
# El resultado queda en logs/captura_diaria.log y en GET /salud.
#
# Uso manual:  powershell -ExecutionPolicy Bypass -File scripts\captura_diaria.ps1

# Los comandos externos (docker, python) escriben su avance en stderr: se juzgan por su código de
# salida, no por lo que escriben. Su salida va al registro con cmd, en UTF-8.
$ErrorActionPreference = 'Continue'
$env:PYTHONUTF8 = '1'
$raiz = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $raiz 'logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$archivoLog = Join-Path $logs 'captura_diaria.log'

function Escribir($mensaje) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $mensaje" | Out-File -Append -Encoding utf8 $archivoLog
}

try {
    Set-Location $raiz
    Escribir 'Inicia la captura diaria'

    # Docker solo hace falta si la base es local; con una base en la nube (Neon) se omite
    $baseLocal = Select-String -Path (Join-Path $raiz '.env') -Pattern '^DATABASE_URL=.*(localhost|127\.0\.0\.1)' -Quiet
    if ($baseLocal) {
        # 1. Docker: si el motor no responde, se abre Docker Desktop y se espera hasta 3 minutos
        docker info *> $null
        if ($LASTEXITCODE -ne 0) {
            Escribir 'Docker apagado: se abre Docker Desktop'
            Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
            $limite = (Get-Date).AddMinutes(3)
            do {
                Start-Sleep -Seconds 10
                docker info *> $null
            } until ($LASTEXITCODE -eq 0 -or (Get-Date) -gt $limite)
            if ($LASTEXITCODE -ne 0) { throw 'Docker no arrancó en 3 minutos' }
        }

        # 2. Base de datos
        cmd /c "docker compose up -d --wait >> `"$archivoLog`" 2>&1"
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo levantar PostgreSQL' }
    }

    # 3. Una pasada del worker (respeta robots.txt y el intervalo entre peticiones)
    Set-Location (Join-Path $raiz 'backend')
    cmd /c ".venv\Scripts\python.exe -m app.worker --una-vez >> `"$archivoLog`" 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "El worker terminó con código $LASTEXITCODE" }

    Escribir 'Termina la captura diaria'
}
catch {
    Escribir "ERROR: $_"
    exit 1
}
