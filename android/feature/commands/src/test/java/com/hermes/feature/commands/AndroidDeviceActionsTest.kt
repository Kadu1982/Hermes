package com.hermes.feature.commands

import android.accessibilityservice.AccessibilityService
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidDeviceActionsTest {
    @Test
    fun app_launch_resolver_maps_known_apps() {
        val resolver = AppLaunchResolver()
        val target = resolver.resolve("WhatsApp", null)
        assertNotNull(target)
        assertEquals("WhatsApp", target?.appName)
        assertEquals("com.whatsapp", target?.packageName)
    }

    @Test
    fun app_launch_resolver_maps_youtube_aliases() {
        val resolver = AppLaunchResolver()
        val target = resolver.resolve("YouTube Ultra", null)
        assertNotNull(target)
        assertEquals("YouTube", target?.appName)
        assertEquals("com.google.android.youtube", target?.packageName)
    }

    @Test
    fun app_launch_resolver_maps_deep_links() {
        val resolver = AppLaunchResolver()
        val camera = resolver.resolveDeepLink("camera")
        val maps = resolver.resolveDeepLink("maps")
        val settings = resolver.resolveDeepLink("settings")

        assertEquals("Camera", camera?.appName)
        assertEquals("android.media.action.STILL_IMAGE_CAMERA", camera?.intentAction)
        assertEquals("com.google.android.apps.maps", maps?.packageName)
        assertEquals("android.settings.SETTINGS", settings?.intentAction)
    }

    @Test
    fun system_action_runner_maps_known_actions_and_uses_executor() {
        var receivedAction = -1
        val runner = SystemActionRunner(
            executorProvider = {
                object : SystemActionExecutor {
                    override fun performGlobalAction(action: Int): Boolean {
                        receivedAction = action
                        return true
                    }
                }
            },
        )

        val result = runner.run("home")
        assertTrue(result.performed)
        assertEquals(AccessibilityService.GLOBAL_ACTION_HOME, receivedAction)
    }

    @Test
    fun system_action_runner_rejects_unknown_action() {
        val runner = SystemActionRunner(executorProvider = { null })
        val result = runner.run("sleep")
        assertFalse(result.performed)
        assertEquals("unsupported_system_action", result.error)
    }

    @Test
    fun unlock_controller_delegates_to_requester() = runBlocking {
        val controller = UnlockController()
        val outcome = controller.request(
            object : UnlockRequester {
                override suspend fun requestDismissKeyguard(): UnlockOutcome {
                    return UnlockOutcome(approved = true, dismissed = true, message = "unlock_dismissed")
                }
            },
        )
        assertTrue(outcome.approved)
        assertTrue(outcome.dismissed)
    }

    @Test
    fun command_bridge_unlock_round_trip() = runBlocking {
        val commandId = "unlock-test-1"
        CommandBridge.requestUnlockUi(commandId)
        CommandBridge.completeUnlock(
            commandId,
            mapOf(
                "approved" to true,
                "dismissed" to true,
                "message" to "unlock_dismissed",
            ),
        )
        val result = CommandBridge.awaitUnlock(commandId)
        assertEquals(true, result["approved"])
        assertEquals(true, result["dismissed"])
    }
}
