package com.hermes.feature.commands

import android.content.Context
import com.hermes.core.network.BrainUtteranceBody
import com.hermes.core.network.NetworkModule
import com.hermes.core.security.SecureTokenStore

object BrainVoiceClient {
    suspend fun send(
        context: Context,
        text: String,
        confirm: Boolean = false,
        threadId: String? = null,
        waitTimeoutSeconds: Int = 60,
    ): Result<com.hermes.core.network.BrainUtteranceResp> {
        val store = SecureTokenStore(context.applicationContext)
        val base = store.apiBaseUrl?.let { normalizeBaseUrl(it) }
            ?: return Result.failure(IllegalStateException("URL da VPS não configurada"))
        val token = store.adminToken?.trim().orEmpty()
        if (token.isEmpty()) {
            return Result.failure(IllegalStateException("Faça login na aba Comando (senha + 2FA)"))
        }
        return runCatching {
            val api = NetworkModule.createAdminApi(store, base)
            api.utterance(
                BrainUtteranceBody(
                    text = text,
                    confirm = confirm,
                    thread_id = threadId,
                    wait_timeout_seconds = waitTimeoutSeconds,
                ),
            )
        }
    }

    private fun normalizeBaseUrl(raw: String): String {
        var u = raw.trim().trimEnd('/')
        if (!u.startsWith("http://") && !u.startsWith("https://")) {
            u = "http://$u"
        }
        return u
    }
}
