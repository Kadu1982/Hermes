package com.hermes.feature.commands

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class JarvisAccessibilityService : AccessibilityService() {
    override fun onServiceConnected() {
        super.onServiceConnected()
        JarvisAccessibilityBridge.executor = object : SystemActionExecutor {
            override fun performGlobalAction(action: Int): Boolean = this@JarvisAccessibilityService.performGlobalAction(action)
        }
        JarvisAccessibilityBridge.service = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit

    override fun onInterrupt() = Unit

    override fun onDestroy() {
        if (JarvisAccessibilityBridge.service === this) {
            JarvisAccessibilityBridge.service = null
            JarvisAccessibilityBridge.executor = null
        }
        super.onDestroy()
    }

    fun executeAllowlistedAction(payload: Map<String, Any?>): Map<String, Any?> {
        val flow = payload["flow"]?.toString()?.trim().orEmpty()
        val action = payload["action"]?.toString()?.trim().orEmpty()
        return when (flow.ifBlank { action }) {
            "global_action" -> {
                val systemAction = action
                val id = SystemActionRunner().resolveAction(systemAction)
                    ?: return failure("global_action", "unsupported_system_action")
                val performed = performGlobalAction(id)
                mapOf("action" to "global_action", "system_action" to systemAction, "performed" to performed)
            }

            "open_app" -> {
                val packageName = payload["package_name"]?.toString()?.trim().orEmpty()
                if (packageName.isBlank()) {
                    return failure("open_app", "package_name_required")
                }
                val intent = packageManager.getLaunchIntentForPackage(packageName)
                    ?: return failure("open_app", "app_not_found")
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(intent)
                mapOf("action" to "open_app", "package_name" to packageName, "performed" to true)
            }

            "click_text" -> {
                val text = payload["text"]?.toString()?.trim().orEmpty()
                if (text.isBlank()) {
                    return failure("click_text", "text_required")
                }
                val node = findNodeByText(rootInActiveWindow, text)
                    ?: return failure("click_text", "node_not_found")
                val performed = node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                mapOf("action" to "click_text", "text" to text, "performed" to performed)
            }

            else -> failure(flow.ifBlank { action.ifBlank { "unknown" } }, "unsupported_ui_action")
        }
    }

    private fun failure(action: String, error: String): Map<String, Any?> {
        return mapOf("action" to action, "performed" to false, "error" to error)
    }

    private fun findNodeByText(node: AccessibilityNodeInfo?, text: String): AccessibilityNodeInfo? {
        if (node == null) return null
        val nodeText = node.text?.toString().orEmpty()
        val contentDesc = node.contentDescription?.toString().orEmpty()
        if (nodeText.contains(text, ignoreCase = true) || contentDesc.contains(text, ignoreCase = true)) {
            return node
        }
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val match = findNodeByText(child, text)
            if (match != null) return match
        }
        return null
    }
}

object JarvisAccessibilityBridge {
    @Volatile
    var service: JarvisAccessibilityService? = null
    @Volatile
    var executor: SystemActionExecutor? = null
}
