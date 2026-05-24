package com.hermes.feature.commands

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.speech.tts.TextToSpeech
import android.speech.tts.Voice
import android.util.Log
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * TTS masculino PT-BR — motor Google (se instalado) + voz pte/ped/male.
 */
object JarvisTts {
    private const val TAG = "JarvisTts"
    private const val GOOGLE_TTS = "com.google.android.tts"

    fun openTtsSettings(context: Context) {
        val intent = Intent("com.android.settings.TTS_SETTINGS").apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
        } else {
            context.startActivity(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        }
    }

    class Session(
        context: Context,
        private val onReady: ((Session) -> Unit)? = null,
    ) {
        private val appContext = context.applicationContext
        private val profile = loadProfile(appContext)
        private var tts: TextToSpeech? = null
        var ready = false
            private set
        var selectedVoiceName: String? = null
            private set

        init {
            val engine = if (isPackageInstalled(appContext, GOOGLE_TTS)) GOOGLE_TTS else null
            tts = TextToSpeech(appContext, { status ->
                if (status != TextToSpeech.SUCCESS) {
                    Log.w(TAG, "TTS init failed status=$status")
                    return@TextToSpeech
                }
                val engineRef = tts ?: return@TextToSpeech
                applyProfile(engineRef, profile)
                ready = true
                selectedVoiceName = engineRef.voice?.name
                Log.i(TAG, "TTS ready engine=${engineRef.defaultEngine} voice=$selectedVoiceName")
                onReady?.invoke(this)
            }, engine)
        }

        fun speak(text: String) {
            if (!ready || text.isBlank()) return
            tts?.speak(text, TextToSpeech.QUEUE_ADD, null, "jarvis-${System.currentTimeMillis()}")
        }

        fun speakAndWait(text: String, timeoutSec: Long = 15) {
            if (!ready || text.isBlank()) return
            val latch = CountDownLatch(1)
            val utteranceId = "jarvis-${System.currentTimeMillis()}"
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.ICE_CREAM_SANDWICH_MR1) {
                tts?.setOnUtteranceProgressListener(object : android.speech.tts.UtteranceProgressListener() {
                    override fun onStart(id: String?) {}
                    override fun onDone(id: String?) {
                        if (id == utteranceId) latch.countDown()
                    }
                    @Deprecated("Deprecated in Java")
                    override fun onError(id: String?) {
                        if (id == utteranceId) latch.countDown()
                    }
                })
            }
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, utteranceId)
            latch.await(timeoutSec, TimeUnit.SECONDS)
        }

        fun shutdown() {
            tts?.shutdown()
            tts = null
            ready = false
        }
    }

    fun speakBlocking(context: Context, text: String, timeoutSec: Long = 20) {
        val latch = CountDownLatch(1)
        var session: Session? = null
        session = Session(context) { s ->
            if (s.ready) {
                s.speakAndWait(text, timeoutSec)
            }
            s.shutdown()
            latch.countDown()
        }
        latch.await(timeoutSec + 8, TimeUnit.SECONDS)
        session?.shutdown()
    }

    private fun isPackageInstalled(context: Context, packageName: String): Boolean {
        return try {
            context.packageManager.getPackageInfo(packageName, 0)
            true
        } catch (_: PackageManager.NameNotFoundException) {
            false
        }
    }

    private fun loadProfile(context: Context): JSONObject {
        return try {
            val raw = context.assets.open("hermes_voice.json").bufferedReader().use { it.readText() }
            JSONObject(raw)
        } catch (_: Exception) {
            JSONObject()
                .put("locale", "pt-BR")
                .put("android_tts_voice_name", "pte")
                .put("pitch", 0.65)
                .put("speech_rate", 0.82)
        }
    }

    private fun applyProfile(tts: TextToSpeech, profile: JSONObject) {
        val localeTag = profile.optString("locale", "pt-BR")
        var langResult = tts.setLanguage(Locale.forLanguageTag(localeTag))
        if (langResult == TextToSpeech.LANG_MISSING_DATA || langResult == TextToSpeech.LANG_NOT_SUPPORTED) {
            tts.setLanguage(Locale("pt", "BR"))
        }
        val preferred = profile.optString("android_tts_voice_name", "pte")
        val picked = pickMaleVoice(tts.voices, preferred)
        if (picked != null) {
            tts.voice = picked
        } else {
            Log.w(TAG, "Nenhuma voz masculina PT encontrada; usando pitch baixo")
            tts.setPitch(0.55f)
        }
        tts.setSpeechRate(profile.optDouble("speech_rate", 0.82).toFloat())
        tts.setPitch(profile.optDouble("pitch", 0.65).toFloat())
    }

    fun pickMaleVoice(voices: Set<Voice>?, preferredSubstring: String): Voice? {
        if (voices.isNullOrEmpty()) return null
        val pt = voices.filter { v ->
            v.locale?.toLanguageTag().orEmpty().startsWith("pt", ignoreCase = true)
        }
        if (pt.isEmpty()) return null

        fun isFemale(v: Voice): Boolean {
            val n = v.name.lowercase()
            if (n.contains("female") || n.contains("fem") || n.contains("feminina") || n.contains("mulher")) return true
            if (n.contains("afs") || n.contains("afb") || n.contains("afg")) return true
            // Samsung / Google feminino comum
            if (n.contains("brf") || n.contains("brg") || n.contains("sf") && n.contains("br")) return true
            if (n.contains("helena") || n.contains("luciana") || n.contains("francisca") || n.contains("vitória") ||
                n.contains("vitoria") || n.contains("camila")
            ) return true
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                v.features?.forEach { f ->
                    val fl = f.lowercase()
                    if (fl.contains("female") || fl == "feminine") return true
                }
            }
            return false
        }

        fun isMale(v: Voice): Boolean {
            if (isFemale(v)) return false
            val n = v.name.lowercase()
            return n.contains("pte") || n.contains("ped") || n.contains("male") || n.contains("masculin") ||
                n.contains("antonio") || n.contains("daniel") || n.contains("bre") || n.contains("yasir")
        }

        pt.filter { v -> v.name.contains(preferredSubstring, ignoreCase = true) && isMale(v) }
            .maxByOrNull { voiceScore(it, preferredSubstring) }
            ?.let { return it }

        return pt.filter { isMale(it) }.maxByOrNull { voiceScore(it, preferredSubstring) }
    }

    private fun voiceScore(v: Voice, preferred: String): Int {
        val n = v.name.lowercase()
        var s = 0
        if (n.contains(preferred.lowercase())) s += 10
        if (n.contains("local")) s += 3
        if (n.contains("network")) s += 1
        if (n.contains("google")) s += 2
        if (n.contains(GOOGLE_TTS)) s += 2
        return s
    }
}
