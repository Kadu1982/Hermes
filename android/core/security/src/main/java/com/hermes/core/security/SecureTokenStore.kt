package com.hermes.core.security

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class SecureTokenStore(context: Context) {
    private val masterKey = MasterKey.Builder(context.applicationContext)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        context.applicationContext,
        PREFS_NAME,
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    var apiBaseUrl: String?
        get() = prefs.getString(KEY_API, null)
        set(value) { prefs.edit().putString(KEY_API, value).apply() }

    var deviceToken: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) { prefs.edit().putString(KEY_TOKEN, value).apply() }

    /** Admin JWT for Commander mode (control other devices). */
    var adminToken: String?
        get() = prefs.getString(KEY_ADMIN, null)
        set(value) { prefs.edit().putString(KEY_ADMIN, value).apply() }

    /** JWT after password step, before 2FA (must survive rotation). */
    var adminPartialToken: String?
        get() = prefs.getString(KEY_ADMIN_PARTIAL, null)
        set(value) { prefs.edit().putString(KEY_ADMIN_PARTIAL, value).apply() }

    var defaultNotifyChannel: String
        get() = prefs.getString(KEY_NOTIFY, "voice") ?: "voice"
        set(value) { prefs.edit().putString(KEY_NOTIFY, value).apply() }

    /** Modo «Ei Jarvis» — escuta contínua em segundo plano. */
    var voiceWakeEnabled: Boolean
        get() = prefs.getBoolean(KEY_VOICE_WAKE, false)
        set(value) { prefs.edit().putBoolean(KEY_VOICE_WAKE, value).apply() }

    fun clearDevice() {
        prefs.edit().remove(KEY_TOKEN).apply()
    }

    fun clearAdmin() {
        prefs.edit().remove(KEY_ADMIN).remove(KEY_ADMIN_PARTIAL).apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val PREFS_NAME = "hermes_secure"
        private const val KEY_API = "api_base"
        private const val KEY_TOKEN = "device_token"
        private const val KEY_ADMIN = "admin_token"
        private const val KEY_ADMIN_PARTIAL = "admin_partial_token"
        private const val KEY_NOTIFY = "notify_channel"
        private const val KEY_VOICE_WAKE = "voice_wake_enabled"
    }
}
