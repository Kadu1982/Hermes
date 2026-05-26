package com.hermes.feature.commands

import android.accessibilityservice.AccessibilityService

interface SystemActionExecutor {
    fun performGlobalAction(action: Int): Boolean
}

data class SystemActionResult(
    val action: String,
    val performed: Boolean,
    val error: String? = null,
)

class SystemActionRunner(
    private val executorProvider: () -> SystemActionExecutor? = { JarvisAccessibilityBridge.executor },
) {
    fun run(action: String): SystemActionResult {
        val actionId = resolveAction(action)
            ?: return SystemActionResult(action = action, performed = false, error = "unsupported_system_action")
        val executor = executorProvider()
            ?: return SystemActionResult(action = action, performed = false, error = "accessibility_service_not_enabled")
        return if (executor.performGlobalAction(actionId)) {
            SystemActionResult(action = action, performed = true)
        } else {
            SystemActionResult(action = action, performed = false, error = "system_action_failed")
        }
    }

    fun resolveAction(action: String): Int? {
        return when (action.trim().lowercase()) {
            "back" -> AccessibilityService.GLOBAL_ACTION_BACK
            "home" -> AccessibilityService.GLOBAL_ACTION_HOME
            "recents" -> AccessibilityService.GLOBAL_ACTION_RECENTS
            "notifications" -> AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS
            "quick_settings" -> AccessibilityService.GLOBAL_ACTION_QUICK_SETTINGS
            else -> null
        }
    }
}
