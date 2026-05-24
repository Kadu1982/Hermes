# Modo «Ei Jarvis» (estilo Alexa)

## O que é

Com o **modo escuta** ativo, o telemóvel fica à escuta em segundo plano. Não precisa abrir o teclado: fale a palavra de ativação + o pedido.

## Como usar

1. Aba **Este telemóvel** — pareamento feito e notificação Jarvis ativa.
2. Aba **Comando** — login completo (senha + **2FA** → «Sessão de comando ativa»).
3. Toque **Ativar escuta «Ei Jarvis»**.
4. Aceite permissão de **microfone** se pedir.
5. Fale, por exemplo:
   - «**Ei Jarvis, ping no PC-Casa**»
   - «**Ei Jarvis, diga olá**»
   - «**Ei Jarvis, inventário do VPS**»

6. Para desligar: notificação **Parar** ou botão **Parar escuta «Ei Jarvis»**.

## Palavras de ativação

`Ei Jarvis` — seguidas do comando.

## Limitações (MVP)

| Alexa comercial | Jarvis (agora) |
|-----------------|----------------|
| «Alexa» sempre à escuta, otimizado | Usa reconhecimento Google/Samsung; reinicia a cada frase |
| Baixo consumo em chip dedicado | **Gasta mais bateria** — notificação permanente |
| Funciona com ecrã off longo | Android pode matar o serviço; mantenha app autorizada em bateria |
| Wake word dedicado | Frase completa numa única fala funciona melhor |

## Bateria

**Ajustes** → **Apps** → **Jarvis** → **Bateria** → **Sem restrições** (recomendado com escuta ativa).

## Futuro

- Wake word offline (ex. Porcupine «Jarvis»)
- Integração «Ok Google, abrir Jarvis»
- Respostas por voz sem abrir o app
