package com.hermes.core.network

import com.google.gson.Gson
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody

private val gson = Gson()
private val jsonMedia = "application/json; charset=utf-8".toMediaType()

fun Map<String, Any?>.toJsonRequestBody(): RequestBody =
    gson.toJson(this).toRequestBody(jsonMedia)
