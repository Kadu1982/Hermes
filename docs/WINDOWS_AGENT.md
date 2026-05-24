# Agente Hermes no Windows (PC-Casa)

O PC responde ao painel enquanto o processo `hermes_agent run` estiver ativo. **Não precisa** deixar PowerShell aberto se usar o Agendador de Tarefas.

## Pré-requisitos (uma vez)

```powershell
cd C:\Users\G15\App-Hermes\agents\hermes-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m hermes_agent pair `
  --server http://72.60.55.213:18080 `
  --code CODIGO_DO_PAINEL `
  --name "PC-Casa" `
  --platform windows
```

Atualize `hermes_agent\client.py` do repositório se ainda aparecer `poll error` frequente (correção de conexão HTTP no Windows).

## Opção A — Automático (recomendado)

1. Copie a pasta `agents\hermes-agent` do repositório (com `scripts\run-agent.bat` e `install-task-scheduler.ps1`).
2. No PowerShell (se der **Acesso negado**, abra **Executar como administrador**):

```powershell
cd C:\Users\G15\App-Hermes\agents\hermes-agent\scripts
powershell -ExecutionPolicy Bypass -File .\install-task-scheduler.ps1
```

**Sem admin** — use `schtasks` direto:

```powershell
cd C:\Users\G15\App-Hermes\agents\hermes-agent\scripts
$bat = (Resolve-Path .\run-agent.bat).Path
schtasks /Create /TN HermesAgent /TR "`"$bat`"" /SC ONLOGON /RL LIMITED /F
schtasks /Run /TN HermesAgent
```

3. A tarefa **HermesAgent** roda ao **fazer login** e reinicia se cair.
4. Log: `%LOCALAPPDATA%\Hermes\agent.log`

### Comandos úteis

```powershell
Get-ScheduledTask -TaskName HermesAgent
Start-ScheduledTask -TaskName HermesAgent
Stop-ScheduledTask -TaskName HermesAgent
Unregister-ScheduledTask -TaskName HermesAgent -Confirm:$false
```

## Opção B — Manual (teste)

```powershell
cd C:\Users\G15\App-Hermes\agents\hermes-agent
.\.venv\Scripts\Activate.ps1
python -m hermes_agent run --interval 5
```

Fechar a janela encerra o agente.

## Teste no painel

1. http://72.60.55.213:13000 → login → **Devices** → **PC-Casa**
2. Comando **ping** → resultado `pong` em alguns segundos

## Requisitos para acesso remoto

| Necessário | Observação |
|------------|------------|
| PC ligado | Suspensão pode interromper a rede |
| Internet | Porta **18080** de saída até o VPS |
| Agente rodando | Tarefa agendada ou terminal aberto |
| Pareamento feito | Só uma vez; token em config do usuário |

Não é acesso remoto de desktop (RDP/TeamViewer): são **comandos** enviados pelo painel (ping, inventário, etc.).
