package com.hermes.feature.commands

import android.content.Context

/** Comando `speak` no dispositivo — mesma voz Jarvis que o modo Comando. */
class DeviceSpeaker(private val context: Context) {
    fun speakAndWait(text: String, timeoutSec: Long = 15) {
        JarvisTts.speakBlocking(context, text, timeoutSec)
    }
}
