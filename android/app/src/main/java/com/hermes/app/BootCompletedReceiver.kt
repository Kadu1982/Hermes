package com.hermes.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.hermes.core.security.SecureTokenStore
import com.hermes.feature.commands.VoiceWakeForegroundService

/**
 * Religa a escuta "Ei Jarvis" depois do boot, se o usuário a tinha ativado antes.
 */
class BootCompletedReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != Intent.ACTION_BOOT_COMPLETED) return

        val store = SecureTokenStore(context.applicationContext)
        if (!store.voiceWakeEnabled) return

        VoiceWakeForegroundService.start(context.applicationContext)
    }
}
