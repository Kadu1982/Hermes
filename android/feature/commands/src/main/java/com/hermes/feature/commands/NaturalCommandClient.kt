package com.hermes.feature.commands

import android.content.Context
import com.hermes.core.network.NaturalCommandBody
import com.hermes.core.network.NetworkModule
import com.hermes.core.security.SecureTokenStore
object NaturalCommandClient {
    suspend fun send(
        context: Context,
        text: String,
        notifyChannel: String = "voice",
    ): Result<String> {
        val store = SecureTokenStore(context.applicationContext)
        val base = store.apiBaseUrl?.let { normalizeBaseUrl(it) }
            ?: return Result.failure(IllegalStateException("URL da VPS não configurada"))
        val token = store.adminToken?.trim().orEmpty()
        if (token.isEmpty()) {
            return Result.failure(IllegalStateException("Faça login na aba Comando (senha + 2FA)"))
        }
        return runCatching {
            val api = NetworkModule.createAdminApi(store, base)
            val r = api.natural(
                NaturalCommandBody(
                    text = text,
                    notify_channel = notifyChannel,
                    notify_on = "done",
                ),
            )
            "${r.parsed_type} → ${r.parsed_device_name} (${r.command.status})"
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
