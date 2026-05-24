package com.hermes.core.network

import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.hermes.core.security.SecureTokenStore
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object NetworkModule {
    fun createApi(store: SecureTokenStore, baseUrl: String): HermesApi {
        val gson: Gson = GsonBuilder().serializeNulls().create()

        val authInterceptor = Interceptor { chain ->
            val token = store.deviceToken
            val req = if (token != null) {
                chain.request().newBuilder().header("Authorization", "Bearer $token").build()
            } else chain.request()
            chain.proceed(req)
        }

        val log = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(log)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()

        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val retrofit = Retrofit.Builder()
            .baseUrl(normalized)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
        return retrofit.create(HermesApi::class.java)
    }

    fun createAdminApi(store: SecureTokenStore, baseUrl: String): AdminApi {
        val gson = GsonBuilder().serializeNulls().create()
        val authInterceptor = Interceptor { chain ->
            val token = store.adminToken?.trim().orEmpty()
            val req = if (token.isNotEmpty()) {
                chain.request().newBuilder().header("Authorization", "Bearer $token").build()
            } else chain.request()
            chain.proceed(req)
        }
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val retrofit = Retrofit.Builder()
            .baseUrl("${normalized}api/v1/")
            .client(
                OkHttpClient.Builder()
                    .addInterceptor(authInterceptor)
                    .connectTimeout(30, TimeUnit.SECONDS)
                    .build(),
            )
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
        return retrofit.create(AdminApi::class.java)
    }
}
