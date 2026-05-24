package com.hermes.feature.commands

/**
 * Extrai o comando após palavra de ativação (estilo Alexa).
 * Ex.: "Ei Jarvis, ping no PC Casa" → "ping no PC Casa"
 */
object WakePhraseParser {
    private val WAKE_PHRASES = listOf(
        "ei jarvis",
        "ei javrvis",
        "javrvis",
    ).sortedByDescending { it.length }

    fun parse(spoken: String): String? {
        val lower = spoken.lowercase().trim()
        if (lower.isEmpty()) return null
        for (wake in WAKE_PHRASES) {
            if (!lower.startsWith(wake)) continue
            var rest = lower.substring(wake.length).trim()
            rest = rest.trimStart(',', ':', '-', ' ')
            if (rest.isNotEmpty()) return rest
        }
        return null
    }

    fun containsWakeWord(spoken: String): Boolean = parse(spoken) != null
}
