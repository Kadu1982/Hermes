package com.hermes.feature.commands

import android.app.Activity
import android.app.KeyguardManager
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

data class UnlockOutcome(
    val approved: Boolean,
    val dismissed: Boolean,
    val message: String? = null,
)

fun interface UnlockRequester {
    suspend fun requestDismissKeyguard(): UnlockOutcome
}

class UnlockController {
    suspend fun request(requester: UnlockRequester): UnlockOutcome = requester.requestDismissKeyguard()
}

class AndroidUnlockRequester(
    private val activity: Activity,
) : UnlockRequester {
    override suspend fun requestDismissKeyguard(): UnlockOutcome = suspendCancellableCoroutine { continuation ->
        val km = activity.getSystemService(Activity.KEYGUARD_SERVICE) as? KeyguardManager
        if (km == null) {
            continuation.resume(
                UnlockOutcome(
                    approved = false,
                    dismissed = false,
                    message = "keyguard_manager_unavailable",
                ),
            )
            return@suspendCancellableCoroutine
        }

        km.requestDismissKeyguard(activity, object : KeyguardManager.KeyguardDismissCallback() {
            override fun onDismissSucceeded() {
                if (continuation.isActive) {
                    continuation.resume(UnlockOutcome(approved = true, dismissed = true, message = "unlock_dismissed"))
                }
            }

            override fun onDismissError() {
                if (continuation.isActive) {
                    continuation.resume(
                        UnlockOutcome(
                            approved = true,
                            dismissed = false,
                            message = "unlock_rejected",
                        ),
                    )
                }
            }

            override fun onDismissCancelled() {
                if (continuation.isActive) {
                    continuation.resume(
                        UnlockOutcome(
                            approved = false,
                            dismissed = false,
                            message = "unlock_cancelled",
                        ),
                    )
                }
            }
        })
    }
}
