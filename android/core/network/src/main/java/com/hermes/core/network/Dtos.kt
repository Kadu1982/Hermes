package com.hermes.core.network

data class PairRequest(
    val pairing_code: String,
    val device_name: String,
    val platform: String = "android",
    val public_key: String? = null,
)

data class PairResponse(val device_id: String, val device_token: String)

data class CommandDto(
    val id: String,
    val type: String,
    val payload: Map<String, Any>?,
    val status: String,
)

data class CommandCompleteBody(
    val status: String,
    val result: Map<String, Any>?,
    val logs: String?,
)

data class BrainGoogleBody(
    val text: String,
    val confirm: Boolean = false,
    val thread_id: String? = null,
)

data class BrainGoogleResp(
    val thread_id: String? = null,
    val service: String,
    val action: String,
    val status: String,
    val message: String,
    val requires_confirmation: Boolean = false,
    val summary: String? = null,
    val data: Any? = null,
    val raw_output: String? = null,
)
