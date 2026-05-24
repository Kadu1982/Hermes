# Voz Jarvis (masculina, estilo assistente)

## No Galaxy S25 — passo a passo (importante)

O Samsung usa muitas vezes uma **voz feminina** por defeito. Para voz **masculina**:

### 1. Instalar Google Text-to-Speech

Play Store → **Google Text-to-speech** → Instalar / Atualizar.

### 2. Definir motor Google

**Ajustes** → **Geral** → **Texto para voz** (ou Pesquisar "texto para voz"):

1. **Motor preferido** → **Speech Recognition and Synthesis from Google** (Google).
2. Toque no ícone de engrenagem do Google → **Idioma**.
3. **Português (Brasil)** → descarregar se pedido.
4. Escolha a voz **masculina** (ex.: **pt-br-x-pte** / "masculino" / nome masculino).
5. **Velocidade** ~85% | **Tom** mais baixo (se existir).

### 3. No app Hermes

- Recompile e instale o app (código usa motor Google + voz `pte`).
- Aba **Comando** → **Configurar voz masculina (sistema)** (abre os ajustes TTS).
- Canal **Voz Jarvis**.

### 4. Teste

Comando: `diga olá` (com aba **Este telemóvel** ativa).

---

## Perfil técnico

Ficheiro: `shared/hermes_voice.json` — `pitch` 0.75, `speech_rate` 0.84, voz `pte`.

Desktop/VPS: `pt-BR-AntonioNeural` (edge-tts).
