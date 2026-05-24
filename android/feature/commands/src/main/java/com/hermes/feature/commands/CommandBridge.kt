package com.hermes.feature.commands

import java.util.concurrent.atomic.AtomicReference

/**
 * Coordinates long-running upload commands between the foreground service and UI (SAF).
 */
object CommandBridge {
    val pendingUploadCommandId = AtomicReference<String?>(null)

    fun requestUploadUi(commandId: String) {
        pendingUploadCommandId.set(commandId)
    }

    fun clearUploadUi() {
        pendingUploadCommandId.set(null)
    }
}
