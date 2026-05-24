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
