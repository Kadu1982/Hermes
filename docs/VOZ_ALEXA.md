# Modo «Ei Jarvis» (estilo Alexa)

## O que é

Com o **modo escuta** ativo, o telemóvel fica à escuta em segundo plano. Não precisa abrir o teclado: fale a palavra de ativação + o pedido.

Se você configurar a `picovoiceAccessKey`, o app usa wake word local de baixo consumo para ouvir `Jarvis` e só depois abre a captura do comando.
No Android Studio, essa chave pode ser fornecida como propriedade Gradle `picovoiceAccessKey`.
Sem essa chave, o app continua funcionando no modo antigo com `Ei Jarvis`, mas consome mais bateria.

## Como usar

1. Aba **Este telemóvel** — pareamento feito e notificação Jarvis ativa.
2. Aba **Comando** — login completo (senha + **2FA** → «Sessão de comando ativa»).
3. Toque **Ativar escuta «Ei Jarvis»**.
4. Aceite permissão de **microfone** se pedir.
5. Fale, por exemplo:
   - «**Jarvis**» e depois «**ping no PC-Casa**»
   - «**Jarvis**» e depois «**diga olá**»
   - «**Jarvis**» e depois «**inventário do VPS**»

6. Para desligar: notificação **Parar** ou botão **Parar escuta «Ei Jarvis»**.

## Palavras de ativação

`Jarvis` (modo de baixo consumo) ou `Ei Jarvis` (fallback) — seguidas do comando.

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

- Integração «Ok Google, abrir Jarvis»
- Respostas por voz sem abrir o app
