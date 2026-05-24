package com.hermes.feature.commands

import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.withTimeout

object PhotoCaptureBridge {
    private val pending = ConcurrentHashMap<String, CompletableDeferred<Map<String, Any?>>>()

    fun register(commandId: String): CompletableDeferred<Map<String, Any?>> {
        return pending.computeIfAbsent(commandId) { CompletableDeferred() }
    }

    suspend fun await(commandId: String, timeoutMs: Long = 120_000): Map<String, Any?> {
        return try {
            withTimeout(timeoutMs) { register(commandId).await() }
        } finally {
            pending.remove(commandId)
        }
    }

    fun complete(commandId: String, result: Map<String, Any?>) {
        pending.remove(commandId)?.complete(result)
    }

    fun fail(commandId: String, error: String) {
        pending.remove(commandId)?.completeExceptionally(IllegalStateException(error))
    }
}
