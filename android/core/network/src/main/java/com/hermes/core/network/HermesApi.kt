package com.hermes.core.network

import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

interface HermesApi {
    @POST("devices/pair")
    suspend fun pair(@Body body: PairRequest): PairResponse

    @GET("devices/me")
    suspend fun me(): Map<String, Any?>

    @POST("devices/me/heartbeat")
    suspend fun heartbeat(@Body body: RequestBody): Response<Unit>

    @GET("devices/me/commands/next")
    suspend fun nextCommand(): Response<CommandDto?>

    @POST("devices/me/commands/{id}/complete")
    suspend fun complete(
        @Path("id") id: String,
        @Body body: CommandCompleteBody,
    ): Response<Unit>

    @POST("devices/me/rotate-token")
    suspend fun rotateToken(): Map<String, Any?>

    @Multipart
    @POST("files/upload")
    suspend fun upload(
        @Part("command_id") commandId: RequestBody,
        @Part file: MultipartBody.Part,
    ): Map<String, Any?>

    @GET("files/{id}/download")
    suspend fun download(@Path("id") id: String): ResponseBody
}
