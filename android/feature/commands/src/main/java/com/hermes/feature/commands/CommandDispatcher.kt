package com.hermes.feature.commands

import android.content.Context
import android.util.Log
import com.hermes.core.network.CommandCompleteBody
import com.hermes.core.network.CommandDto
import com.hermes.core.network.HermesApi
import com.hermes.core.network.toJsonRequestBody
import com.hermes.feature.inventory.InventoryCollector
import kotlinx.coroutines.delay

class CommandDispatcher(
    private val context: Context,
    private val api: HermesApi,
    private val localLog: LocalLogBuffer,
    private val onRevokeLocal: () -> Unit = {},
) {
    private val inventory = InventoryCollector(context)
    private val speaker = DeviceSpeaker(context)

    suspend fun pollOnce(): Boolean {
        val res = api.nextCommand()
        if (res.code() == 204) return false
        if (!res.isSuccessful) {
            localLog.append("poll failed: ${res.code()}")
            return false
        }
        val cmd = res.body() ?: return false
        localLog.append("command ${cmd.id} ${cmd.type}")
        runCommand(cmd)
        return true
    }

    private suspend fun runCommand(cmd: CommandDto) {
        try {
            when (cmd.type) {
                "ping" -> complete(cmd.id, "done", mapOf("pong" to true, "ts" to System.currentTimeMillis()))
                "get_inventory" -> {
                    val inv = inventory.collect()
                    complete(cmd.id, "done", mapOf("inventory" to inv))
                }
                "request_upload" -> {
                    CommandBridge.requestUploadUi(cmd.id)
                    var waited = 0
                    while (CommandBridge.pendingUploadCommandId.get() == cmd.id && waited < 600_000) {
                        delay(500)
                        waited += 500
                    }
                    if (CommandBridge.pendingUploadCommandId.get() == cmd.id) {
                        CommandBridge.clearUploadUi()
                        complete(
                            cmd.id,
                            "failed",
                            mapOf("error" to "upload_timeout"),
                            "User did not complete upload in time",
                        )
                    }
                }
                "request_download" -> {
                    val fileId = cmd.payload?.get("file_id")?.toString() ?: error("missing file_id")
                    val body = api.download(fileId)
                    val bytes = body.use { it.byteStream().readBytes() }
                    val dir = context.getExternalFilesDir(android.os.Environment.DIRECTORY_DOWNLOADS)
                        ?: context.filesDir
                    val outFile = java.io.File(dir, "hermes_$fileId.bin")
                    outFile.writeBytes(bytes)
                    complete(
                        cmd.id,
                        "done",
                        mapOf("path" to outFile.absolutePath, "bytes" to bytes.size),
                    )
                }
                "revoke_local" -> {
                    complete(cmd.id, "done", mapOf("cleared" to true))
                    onRevokeLocal()
                }
                "noop" -> complete(cmd.id, "done", emptyMap())
                "speak" -> {
                    val text = cmd.payload?.get("text")?.toString()?.trim().orEmpty()
                        .ifEmpty { "Olá, senhor." }
                    speaker.speakAndWait(text)
                    complete(cmd.id, "done", mapOf("spoken" to text))
                }
                else -> complete(cmd.id, "failed", mapOf("error" to "unknown_type"), cmd.type)
            }
        } catch (e: Exception) {
            Log.e("Hermes", "command failed", e)
            localLog.append(Log.getStackTraceString(e).take(4000))
            complete(
                cmd.id,
                "failed",
                mapOf("error" to (e.message ?: "error")),
                Log.getStackTraceString(e).take(8000),
            )
        }
    }

    private suspend fun complete(id: String, status: String, result: Map<String, Any?>?, logs: String? = null) {
        val cleaned: Map<String, Any>? = result?.mapNotNull { (k, v) ->
            if (v == null) null else k to (v as Any)
        }?.toMap()
        api.complete(id, CommandCompleteBody(status, cleaned, logs))
    }

    suspend fun heartbeat(versionName: String) {
        val inv = inventory.collect()
        val hb: MutableMap<String, Any?> = mutableMapOf(
            "battery_percent" to inv["battery_percent"],
            "network_type" to inv["network_type"],
            "app_version" to versionName,
            "os_version" to inv["android_version"],
            "inventory" to inv,
        )
        api.heartbeat(hb.toJsonRequestBody())
    }
}
