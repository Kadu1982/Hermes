package com.hermes.feature.commands

import android.content.ContentValues
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class PhotoCaptureActivity : ComponentActivity() {
    private var commandId: String = ""
    private var archiveOnly: Boolean = true
    private var pendingCaptureFile: File? = null

    private val captureLauncher =
        registerForActivityResult(ActivityResultContracts.TakePicture()) { success ->
            val tempFile = pendingCaptureFile
            if (!success || tempFile == null) {
                PhotoCaptureBridge.fail(commandId, "camera_cancelled")
                finish()
                return@registerForActivityResult
            }
            lifecycleScope.launch(Dispatchers.IO) {
                runCatching {
                    val archived = archivePhoto(tempFile)
                    val galleryUri = saveToGallery(archived)
                    PhotoCaptureBridge.complete(
                        commandId,
                        mapOf(
                            "archived_path" to archived.absolutePath,
                            "gallery_uri" to galleryUri?.toString(),
                            "archive_only" to archiveOnly,
                            "share_requested" to (!archiveOnly),
                            "mime_type" to "image/jpeg",
                            "stored_local" to true,
                        ),
                    )
                }.onFailure { err ->
                    PhotoCaptureBridge.fail(commandId, err.message ?: "photo_capture_failed")
                }
                runCatching { tempFile.delete() }
                finish()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        commandId = intent.getStringExtra(EXTRA_COMMAND_ID).orEmpty()
        archiveOnly = intent.getBooleanExtra(EXTRA_ARCHIVE_ONLY, true)
        if (commandId.isBlank()) {
            finish()
            return
        }
        if (checkSelfPermission(android.Manifest.permission.CAMERA) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            PhotoCaptureBridge.fail(commandId, "camera_permission_required")
            finish()
            return
        }
        startCapture()
    }

    private fun startCapture() {
        val baseDir = File(cacheDir, "hermes/capture").apply { mkdirs() }
        val tempFile = File(baseDir, "photo_${System.currentTimeMillis()}.jpg")
        val uri = FileProvider.getUriForFile(this, "${packageName}.hermes.fileprovider", tempFile)
        pendingCaptureFile = tempFile
        captureLauncher.launch(uri)
    }

    private fun archivePhoto(tempFile: File): File {
        val archiveDir = File(filesDir, "hermes/photos").apply { mkdirs() }
        val archived = File(archiveDir, tempFile.name)
        tempFile.copyTo(archived, overwrite = true)
        return archived
    }

    private fun saveToGallery(photoFile: File): Uri? {
        return insertIntoGallery(photoFile)
    }

    private fun insertIntoGallery(photoFile: File): Uri? {
        val filename = photoFile.name
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, filename)
            put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + File.separator + "Hermes")
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
        }
        val collection = MediaStore.Images.Media.EXTERNAL_CONTENT_URI
        val uri = contentResolver.insert(collection, values) ?: return null
        return try {
            contentResolver.openOutputStream(uri)?.use { out ->
                photoFile.inputStream().use { input -> input.copyTo(out) }
            } ?: run {
                contentResolver.delete(uri, null, null)
                return null
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                values.clear()
                values.put(MediaStore.Images.Media.IS_PENDING, 0)
                contentResolver.update(uri, values, null, null)
            }
            uri
        } catch (_: Exception) {
            contentResolver.delete(uri, null, null)
            null
        }
    }

    companion object {
        const val EXTRA_COMMAND_ID = "command_id"
        const val EXTRA_ARCHIVE_ONLY = "archive_only"
    }
}
