# Hermes monorepo — legitimate remote admin MVP
# See docs/openapi/hermes-v1.yaml for API contract.

## Layout

- `backend/` — FastAPI, PostgreSQL, Alembic
- `panel/` — Next.js App Router admin UI
- `android/` — Kotlin multi-module app
- `docs/openapi/` — OpenAPI 3.1 specification
- `docs/SDD-HERMES-JARVIS-UNIFICADO.md` — **SDD formal** (fonte da verdade do produto Jarvis)
- `docs/PLANO_PRODUCAO.md` — plano para produção (VPS, Android, agentes, E2E)
- `docs/DEPLOY_VPS.md` — deploy na VPS por IP (stack isolado, portas 18080/13000)
- `docker-compose.vps.yml` — compose produção sem partilhar rede com saude
- `docs/TESTES_E2E.md` — checklist de testes

## Arquitetura e SDD

O produto segue o modelo **um cérebro (Hermes), muitos alvos (dispositivos e conectores)**. Antes de codar, leia o [SDD Hermes / Jarvis Unificado](docs/SDD-HERMES-JARVIS-UNIFICADO.md) e, para agentes de IA, [AGENTS.md](AGENTS.md).

## Produção

Ver [docs/PLANO_PRODUCAO.md](docs/PLANO_PRODUCAO.md) para levar o Hermes a 100% na VPS, Galaxy e PCs.

## Quick start with Docker (recommended)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2).

```bash
# From repo root
docker compose up --build
```

| Service | URL |
|---------|-----|
| Panel | http://localhost:3000 |
| API | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| Postgres | `localhost:5432` (user/pass/db: `hermes`) |

**First admin user** (created on first API start):

- Email: `admin@example.com`
- Password: `change-me-now`
- TOTP: read the **TOTP URI** from API logs (one-time):

```bash
docker compose logs api | findstr otpauth
```

Add that URI to Google Authenticator / Authy, then log in on the panel (password → 6-digit code).

**Android emulator** pointing at API on your PC: use `http://10.0.2.2:8000` as server base URL (not `localhost`).

Stop everything:

```bash
docker compose down
```

Reset database and uploaded files:

```bash
docker compose down -v
```

### Docker-only env overrides

Copy optional overrides (not required for first run):

```bash
# Create backend/.env only if running API outside Docker
# In compose, variables are set in docker-compose.yml
```

To change admin password/email before first boot, edit `HERMES_ADMIN_EMAIL` / `HERMES_ADMIN_PASSWORD` under `api` in `docker-compose.yml`, then `docker compose up --build` on a fresh volume (`docker compose down -v`).

---

## Quick start (development, without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
copy .env.example .env  # set HERMES_DATABASE_URL, HERMES_JWT_SECRET, HERMES_PAIRING_PEPPER
alembic upgrade head
python -m app.scripts.bootstrap_admin
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Panel

```bash
cd panel
npm install
copy .env.local.example .env.local
npm run dev
```

### Android (agent + commander)

Open `android/` in Android Studio. Two tabs in the app:

- **Este telemóvel** — agent (pareamento, recebe comandos).
- **Comando** — login no cérebro (VPS), fala ou escreve ordens, escolhe aviso (voz / notificação / silencioso).

Set `BuildConfig.API_BASE_URL` to your VPS `https://your-domain` or LAN IP for dev.

### Desktop agents (Linux / Windows / macOS / VPS)

See [agents/hermes-agent/README.md](agents/hermes-agent/README.md).

```bash
pip install -r agents/hermes-agent/requirements.txt
python -m hermes_agent pair --server https://YOUR_VPS --code CODE --name "PC-Casa" --platform windows
python -m hermes_agent run
```

Pair the VPS itself with `--platform server` to run `server_docker_ps` / `server_disk` on the brain host.

### Voice identity

Single profile: [shared/hermes_voice.json](shared/hermes_voice.json) and API `GET /api/v1/hermes/voice-profile` (same voice on phone TTS, optional desktop TTS).

## Security notes

- Use TLS (Nginx + Let’s Encrypt) in production.
- Rotate `HERMES_JWT_SECRET`, `HERMES_PAIRING_PEPPER`, and admin passwords after deploy.
- Device tokens are shown once at pairing; only hashes are stored.
