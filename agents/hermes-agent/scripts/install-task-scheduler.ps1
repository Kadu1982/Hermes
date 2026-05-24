#Requires -Version 5.1
<#
  Instala HermesAgent no Agendador de Tarefas (ao logar).
  Tenta registro simples (sem admin); se falhar, usa schtasks; depois pasta Inicial.
#>
param(
    [string]$TaskName = "HermesAgent"
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$bat = Join-Path $ScriptDir "run-agent.bat"
if (-not (Test-Path $bat)) { throw "Nao encontrado: $bat" }
$AgentDir = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$python = Join-Path $AgentDir ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "venv nao encontrado em $AgentDir — rode pair e pip install antes."
}

function Remove-HermesTask {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
        Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
}

Remove-HermesTask

$action = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $ScriptDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$registered = $false

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Description "Agente Hermes" -RunLevel Limited | Out-Null
    $registered = $true
    Write-Host "OK: tarefa registrada (Register-ScheduledTask)."
} catch {
    Write-Host "Register-ScheduledTask falhou: $($_.Exception.Message)"
    Write-Host "Tentando schtasks..."
    $tr = "`"$bat`""
    schtasks /Create /TN $TaskName /TR $tr /SC ONLOGON /RL LIMITED /F | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "schtasks tambem falhou. Rode PowerShell como Administrador." }
    $registered = $true
    Write-Host "OK: tarefa registrada (schtasks)."
}

if ($registered) {
    try { Start-ScheduledTask -TaskName $TaskName } catch { schtasks /Run /TN $TaskName | Out-Null }
}

Write-Host "Log: $env:LOCALAPPDATA\Hermes\agent.log"
Write-Host "Teste no painel: PC-Casa -> ping"
