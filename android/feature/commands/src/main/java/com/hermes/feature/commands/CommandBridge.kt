package com.hermes.feature.commands

import java.util.concurrent.atomic.AtomicReference
import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.withTimeout

/**
 * Coordinates long-running upload commands between the foreground service and UI (SAF).
 */
object CommandBridge {
    private const val DEFAULT_UNLOCK_TIMEOUT_MS = 60_000L
    val pendingUploadCommandId = AtomicReference<String?>(null)
    val pendingUnlockCommandId = AtomicReference<String?>(null)
    private val pendingUnlock = ConcurrentHashMap<String, CompletableDeferred<Map<String, Any?>>>()

    fun requestUploadUi(commandId: String) {
        pendingUploadCommandId.set(commandId)
    }

    fun clearUploadUi() {
        pendingUploadCommandId.set(null)
    }

    fun requestUnlockUi(commandId: String): CompletableDeferred<Map<String, Any?>> {
        pendingUnlockCommandId.set(commandId)
        return pendingUnlock.computeIfAbsent(commandId) { CompletableDeferred() }
    }

    suspend fun awaitUnlock(commandId: String, timeoutMs: Long = DEFAULT_UNLOCK_TIMEOUT_MS): Map<String, Any?> {
        return try {
            withTimeout(timeoutMs) { requestUnlockUi(commandId).await() }
        } finally {
            pendingUnlock.remove(commandId)
            if (pendingUnlockCommandId.get() == commandId) {
                pendingUnlockCommandId.set(null)
            }
        }
    }

    fun completeUnlock(commandId: String, result: Map<String, Any?>) {
        pendingUnlock[commandId]?.complete(result)
        if (pendingUnlockCommandId.get() == commandId) {
            pendingUnlockCommandId.set(null)
        }
    }

    fun failUnlock(commandId: String, error: String) {
        pendingUnlock[commandId]?.complete(mapOf("approved" to false, "dismissed" to false, "error" to error))
        if (pendingUnlockCommandId.get() == commandId) {
            pendingUnlockCommandId.set(null)
        }
    }
}
