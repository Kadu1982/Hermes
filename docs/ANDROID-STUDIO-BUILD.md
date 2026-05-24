# Compilar e instalar o app Hermes (Android Studio)

## 1. Código atualizado na pasta do PC

O projeto no PC (`App-Hermes`) pode estar **atrás** da VPS. Copie de novo:

```powershell
# No PC (PowerShell), se tiver scp/ssh:
scp -r root@72.60.55.213:/root/jarvis-horizon/android C:\Users\G15\App-Hermes\
```

Ou use Git/rsync se tiver repositório sincronizado.

---

## 2. Abrir o projeto certo

1. Android Studio → **File → Open**
2. Pasta: `C:\Users\G15\App-Hermes\android` (tem `settings.gradle.kts` dentro)
3. **Não** abra só a pasta `app` — abra **`android`**.

---

## 3. Sincronizar Gradle (obrigatório)

Na barra superior ou menu:

1. **File → Sync Project with Gradle Files**  
   (ícone elefante com seta azul na toolbar)
2. Espere terminar sem erro na aba **Build**.

Se pedir JDK: **Settings → Build → Gradle → JDK 17**.

---

## 4. Gerar e instalar no telemóvel (SM-S938B)

### Opção A — Instalar direto (recomendado)

1. Ligue o **S25** por USB.
2. No telemóvel: **Opções de programador → Depuração USB** ativada.
3. No topo do Android Studio, dispositivo: **samsung SM-S938B** (como na sua captura).
4. Módulo: **app**.
5. Clique no botão verde **Run ▶** (ou **Shift+F10**).

O Studio compila, instala e abre o app.

### Opção B — Só gerar APK

1. **Build → Clean Project**
2. **Build → Rebuild Project**
3. **Build → Build Bundle(s) / APK(s) → Build APK(s)**
4. Quando aparecer a notificação, **locate** → ficheiro:
   `android\app\build\outputs\apk\debug\app-debug.apk`
5. Copie para o telemóvel e instale (permitir fontes desconhecidas se necessário).

---

## 5. Erro 401 na aba «Comando»

O **401** quase sempre é **login incompleto** ou **token antigo** (não é falha do rebuild em si).

### Checklist

| Item | Valor correto |
|------|----------------|
| URL do cérebro | `http://72.60.55.213:18080` (porta **18080**, não 13000) |
| Email | `admin@example.com` |
| Senha | A da VPS (`.env` `HERMES_ADMIN_PASSWORD`) |
| 2FA | Código **atual** do Google Authenticator (conta certa) |

### Passos no app

1. Aba **«Este telemóvel»** — confirme pareamento OK (agente).
2. Aba **«Comando»**:
   - Toque **Entrar no cérebro** (senha).
   - Se pedir, **Confirmar 2FA** (não pare só na senha).
   - Deve aparecer **«Sessão de comando ativa»**.
3. Só depois: **Enviar comando** ou «Ei Jarvis».

Se ainda der 401:

- Desinstale o app antigo → instale o APK novo (limpa tokens encriptados).
- No painel web, logout/login funciona? Se sim, repita o mesmo no app.

---

## 6. Confirmar que é a versão nova

Depois do Run ▶, na aba Comando deve existir:

- Versão **1.2-mvp** (Definições → App Hermes)
- **«Testar voz Jarvis (masculina)»**
- **«Ativar escuta Ei Jarvis»**
- Login em **dois passos** (senha → 2FA) → mensagem **«Sessão de comando ativa (2FA OK)»**

Se não vir isto, o Studio ainda está a correr código antigo — volte ao passo 1 (copiar `android/` da VPS).

### Voz feminina

1. Play Store → instale **Speech Recognition and Synthesis from Google**
2. Definições Android → **Sistema → Idiomas → Texto para voz**
3. Motor: **Google Text-to-speech**
4. Idioma português (Brasil) → escolha voz **masculina** (ex. «Portuguese (Brazil)» voz 2 ou nome com «male»)
5. No app: **Testar voz Jarvis**

---

## 7. Problemas comuns de build

| Erro | Solução |
|------|---------|
| Gradle sync failed | File → Invalidate Caches → Restart |
| SDK not found | Tools → SDK Manager → Android 14/15 SDK |
| Device unauthorized | Aceite «Allow USB debugging» no telemóvel |
| INSTALL_FAILED_UPDATE_INCOMPATIBLE | Desinstale o Hermes antigo e Run de novo |
