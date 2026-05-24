# Deploy Hermes / Jarvis na VPS (sem domínio)

Stack **isolado** dos containers `saude_*` e `seguranca_*`: rede própria `jarvis_horizon_net`, portas dedicadas, Postgres sem exposição no host.

## URLs (IP da VPS)

Substitua `72.60.55.213` pelo IP público se mudar.

| Serviço | URL |
|---------|-----|
| Painel | http://72.60.55.213:13000 |
| API | http://72.60.55.213:18080/api/v1 |
| Health | http://72.60.55.213:18080/healthz |
| OpenAPI | http://72.60.55.213:18080/docs |

## Portas (host)

| Porta | Uso |
|-------|-----|
| `18080` | API FastAPI |
| `13000` | Painel Next.js |
| *(nenhuma)* | Postgres — só rede interna Docker |

## Deploy rápido

```bash
cd /root/jarvis-horizon   # ou /opt/jarvis-horizon

cp .env.vps.example .env
nano .env                 # segredos e IP

chmod +x scripts/deploy-vps.sh
./scripts/deploy-vps.sh
```

## Comandos úteis

```bash
docker compose -f docker-compose.vps.yml ps
docker compose -f docker-compose.vps.yml logs -f api
docker compose -f docker-compose.vps.yml logs api | grep otpauth   # TOTP admin (primeiro boot)
docker compose -f docker-compose.vps.yml down                        # parar
docker compose -f docker-compose.vps.yml down -v                     # parar + apagar volumes
```

## Firewall

Se usar `ufw`, liberar só o necessário:

```bash
ufw allow 22/tcp
ufw allow 18080/tcp
ufw allow 13000/tcp
# Não abrir 5432 para o Hermes — DB é interno
```

## Agente na VPS (fora do Docker)

```bash
cd /root/jarvis-horizon/agents/hermes-agent
pip install -r requirements.txt
python -m hermes_agent pair \
  --server http://72.60.55.213:18080 \
  --code CODIGO_DO_PAINEL \
  --name VPS-Brain \
  --platform server
python -m hermes_agent run --interval 20
```

## Cérebro LLM (Hermes gateway)

Separado deste compose — corre em `~/.hermes` (`hermes gateway run`). Ver SDD e `PLANO_PRODUCAO.md`.

## Quando tiver domínio

1. Apontar DNS para o IP da VPS.
2. Nginx na frente de `:13000` e `:18080` (ou proxy direto aos containers).
3. Atualizar `.env`: `NEXT_PUBLIC_HERMES_API`, `HERMES_CORS_ORIGINS`, rebuild do painel.
