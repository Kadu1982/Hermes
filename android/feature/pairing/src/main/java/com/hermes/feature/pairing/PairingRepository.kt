package com.hermes.feature.pairing

import com.hermes.core.network.NetworkModule
import com.hermes.core.network.PairRequest
import com.hermes.core.security.SecureTokenStore
import retrofit2.HttpException

class PairingRepository(
    private val store: SecureTokenStore,
) {
    suspend fun pair(baseUrl: String, code: String, deviceName: String): Result<Unit> {
        return try {
            val normalized = normalizeBaseUrl(baseUrl)
            val pairingCode = normalizePairingCode(code)
            if (pairingCode.length < 6) {
                return Result.failure(IllegalArgumentException("Código muito curto. Use o código de 8 letras do painel."))
            }
            store.apiBaseUrl = normalized
            store.deviceToken = null
            val api = NetworkModule.createApi(store, "$normalized/api/v1/")
            val res = api.pair(
                PairRequest(
                    pairing_code = pairingCode,
                    device_name = deviceName.trim(),
                    platform = "android",
                ),
            )
            store.deviceToken = res.device_token
            Result.success(Unit)
        } catch (e: HttpException) {
            val msg = when (e.code()) {
                400 -> "Código inválido ou expirado. No PC: painel → Pairing → Generate (código novo, válido ~10 min)."
                404 -> "URL incorreta. Use a API (ex.: http://IP:18080), não o painel (:13000). Sem /api/v1 no fim."
                else -> "Erro HTTP ${e.code()}: ${e.message()}"
            }
            Result.failure(Exception(msg))
        } catch (e: Exception) {
            Result.failure(
                Exception(
                    when {
                        e.message?.contains("Failed to connect", ignoreCase = true) == true ->
                            "Sem ligação ao servidor. Mesma Wi‑Fi? Docker ligado? URL http://IP:8000"
                        else -> e.message ?: e.toString()
                    },
                ),
            )
        }
    }

    companion object {
        fun normalizeBaseUrl(raw: String): String {
            var u = raw.trim().trimEnd('/')
            val suffix = "/api/v1"
            if (u.endsWith(suffix, ignoreCase = true)) {
                u = u.dropLast(suffix.length).trimEnd('/')
            }
            return u
        }

        fun normalizePairingCode(raw: String): String =
            raw.trim().replace(" ", "").replace("-", "").uppercase()
    }
}
