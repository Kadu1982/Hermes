package com.hermes.feature.commands

/**
 * Extrai o comando após palavra de ativação (estilo Alexa).
 * Ex.: "Ei Jarvis, ping no PC Casa" → "ping no PC Casa"
 */
object WakePhraseParser {
    private val WAKE_PHRASES = listOf(
        "ei jarvis",
        "oi jarvis",
        "hey jarvis",
        "ei hermes",
        "oi hermes",
        "ok jarvis",
        "ok hermes",
        "jarvis",
        "hermes",
    ).sortedByDescending { it.length }

    fun parse(spoken: String): String? {
        val lower = spoken.lowercase().trim()
        if (lower.isEmpty()) return null
        for (wake in WAKE_PHRASES) {
            val idx = lower.indexOf(wake)
            if (idx < 0) continue
            var rest = lower.substring(idx + wake.length).trim()
            rest = rest.trimStart(',', ':', '-', ' ')
            if (rest.isNotEmpty()) return rest
        }
        return null
    }

    fun containsWakeWord(spoken: String): Boolean = parse(spoken) != null
}
