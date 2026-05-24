package com.hermes.core.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class AdminLoginBody(val email: String, val password: String)
data class AdminLoginResp(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("requires_2fa") val requires2fa: Boolean,
)
data class TwoFaBody(
    @SerializedName("access_token") val accessToken: String,
    val code: String,
)
data class TokenResp(@SerializedName("access_token") val accessToken: String)
data class NaturalCommandBody(
    val text: String,
    val device_id: String? = null,
    val notify_channel: String = "voice",
    val notify_on: String = "done",
)
data class NaturalCommandResp(
    val command: CommandJobAdminDto,
    val parsed_device_name: String,
    val parsed_type: String,
    val confidence: String,
)
data class CommandJobAdminDto(
    val id: String,
    val type: String,
    val status: String,
    val result: Map<String, Any>?,
)
data class DevicesListResp(val items: List<DeviceSummaryDto>, val total: Int)
data class DeviceSummaryDto(
    val id: String,
    val name: String,
    val platform: String,
)

interface AdminApi {
    @POST("auth/login")
    suspend fun login(@Body body: AdminLoginBody): AdminLoginResp

    @POST("auth/2fa/verify")
    suspend fun verify2fa(@Body body: TwoFaBody): TokenResp

    /** Confirma JWT com 2FA completo (evita 401 por token parcial/expirado). */
    @GET("auth/session")
    suspend fun session(): Map<String, Any?>

    @GET("devices")
    suspend fun devices(
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0,
    ): DevicesListResp

    @POST("commands/natural")
    suspend fun natural(@Body body: NaturalCommandBody): NaturalCommandResp

    @POST("brain/google")
    suspend fun google(@Body body: BrainGoogleBody): BrainGoogleResp

    @GET("hermes/voice-profile")
    suspend fun voiceProfile(): Map<String, Any?>
}
