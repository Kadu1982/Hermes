package com.hermes.app.voice

import android.content.Context
import com.hermes.feature.commands.JarvisTts
import org.json.JSONObject

/** Voz Jarvis — motor Google TTS + voz masculina PT-BR quando disponível. */
class HermesVoice(context: Context) {
    private val appContext = context.applicationContext
    private val profile: JSONObject = loadProfile(appContext)
    private val pending = mutableListOf<String>()
    private val session = JarvisTts.Session(appContext) { s ->
        if (s.ready) {
            synchronized(pending) {
                pending.forEach { s.speak(it) }
                pending.clear()
            }
        }
    }

    private fun loadProfile(ctx: Context): JSONObject {
        return try {
            val raw = ctx.assets.open("hermes_voice.json").bufferedReader().use { it.readText() }
            JSONObject(raw)
        } catch (_: Exception) {
            JSONObject()
        }
    }

    fun speak(text: String) {
        if (text.isBlank()) return
        if (session.ready) {
            session.speak(text)
        } else {
            synchronized(pending) { pending.add(text) }
        }
    }

    /** Garante voz masculina antes de falar (login, teste). */
    fun speakBlocking(text: String) = JarvisTts.speakBlocking(appContext, text)

    fun readyLine(): String = profile.optString("ready_spoken", "Jarvis à sua disposição, senhor.")

    fun commandSentLine(): String =
        profile.optString("command_sent_spoken", "Executando agora, senhor.")

    fun taskDone() = speak(profile.optString("task_done_spoken", "Concluído, senhor."))

    fun taskFailed() = speak(profile.optString("task_failed_spoken", "Peço desculpas, senhor."))

    fun openVoiceSettings() = JarvisTts.openTtsSettings(appContext)

    fun shutdown() = session.shutdown()
}
