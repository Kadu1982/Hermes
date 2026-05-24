package com.hermes.app

import android.app.Application
import com.hermes.core.network.HermesApi
import com.hermes.core.network.NetworkModule
import com.hermes.core.security.SecureTokenStore

class HermesApp : Application() {
    lateinit var store: SecureTokenStore
        private set

    override fun onCreate() {
        super.onCreate()
        store = SecureTokenStore(this)
        instance = this
    }

    fun api(): HermesApi? {
        val base = store.apiBaseUrl ?: return null
        return NetworkModule.createApi(store, "$base/api/v1/")
    }

    companion object {
        lateinit var instance: HermesApp
            private set
    }
}
