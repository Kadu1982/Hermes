package com.hermes.feature.files

import android.net.Uri
import com.hermes.core.network.HermesApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody

class FileTransfer(private val api: HermesApi) {
    suspend fun upload(commandId: String, uri: Uri, contentResolver: android.content.ContentResolver): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val stream = contentResolver.openInputStream(uri) ?: error("cannot open stream")
                val name = uri.lastPathSegment ?: "upload.bin"
                val bytes = stream.use { it.readBytes() }
                val body = bytes.toRequestBody("application/octet-stream".toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("file", name, body)
                val cid = commandId.toRequestBody("text/plain".toMediaTypeOrNull())
                api.upload(cid, part)
                Unit
            }
        }
}
