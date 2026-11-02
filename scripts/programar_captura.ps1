# Registra (o actualiza) la tarea programada de Windows que captura los precios dos veces al día.
#
#   powershell -ExecutionPolicy Bypass -File scripts\programar_captura.ps1          # registrar
#   powershell -ExecutionPolicy Bypass -File scripts\programar_captura.ps1 -Quitar  # eliminarla
#
# Corre a las 8:00 y a las 20:00 (cada 12 horas, como CAPTURA_INTERVALO_HORAS). Si el equipo
# estaba apagado a esa hora, la pasada se hace apenas se encienda. Solo corre con la sesión
# del usuario iniciada y sin permisos de administrador.

param([switch]$Quitar)

$nombre = 'MasBaratoAqui - Captura'

if ($Quitar) {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false
    Write-Output "Tarea '$nombre' eliminada"
    return
}

$script = Join-Path $PSScriptRoot 'captura_diaria.ps1'
$accion = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$horarios = @(
    New-ScheduledTaskTrigger -Daily -At '08:00'
    New-ScheduledTaskTrigger -Daily -At '20:00'
)
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $horarios -Settings $ajustes `
    -Description 'Mas Barato Aquí!: captura de precios del catálogo (scripts\captura_diaria.ps1)' -Force | Out-Null
Write-Output "Tarea '$nombre' registrada: todos los días a las 8:00 y a las 20:00"
