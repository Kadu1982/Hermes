@echo off
setlocal EnableExtensions
REM Inicia o agente Hermes em segundo plano (uso com Agendador de Tarefas).
REM Pasta do agente = pai deste script (agents\hermes-agent).

cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
  echo [%date% %time%] ERRO: venv nao encontrado em %CD%>> "%LOCALAPPDATA%\Hermes\agent.log"
  exit /b 1
)

set "LOGDIR=%LOCALAPPDATA%\Hermes"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo [%date% %time%] Hermes agent starting>> "%LOGDIR%\agent.log"
".venv\Scripts\python.exe" -m hermes_agent run --interval 5 >> "%LOGDIR%\agent.log" 2>&1
