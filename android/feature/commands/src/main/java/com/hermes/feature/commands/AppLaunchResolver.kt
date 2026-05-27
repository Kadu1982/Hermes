package com.hermes.feature.commands

data class AppLaunchTarget(
    val appName: String,
    val packageName: String?,
    val intentAction: String? = null,
    val dataUri: String? = null,
)

class AppLaunchResolver {
    fun resolve(appName: String?, packageName: String?): AppLaunchTarget? {
        val trimmedPackage = packageName?.trim().orEmpty().ifBlank { null }
        val label = appName?.trim().orEmpty().ifBlank { null } ?: trimmedPackage ?: return null
        val normalized = label.lowercase()

        val known = findKnownApp(normalized)

        return when {
            trimmedPackage != null && label.isNotBlank() -> AppLaunchTarget(label, trimmedPackage)
            known != null -> AppLaunchTarget(known.first, known.second)
            else -> AppLaunchTarget(label.replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }, trimmedPackage)
        }
    }

    fun resolveDeepLink(target: String): AppLaunchTarget? {
        return when (target.trim().lowercase()) {
            "camera" -> AppLaunchTarget("Camera", null, "android.media.action.STILL_IMAGE_CAMERA")
            "maps" -> AppLaunchTarget("Google Maps", "com.google.android.apps.maps", "android.intent.action.VIEW", "geo:0,0?q=")
            "settings" -> AppLaunchTarget("Settings", "com.android.settings", "android.settings.SETTINGS")
            "phone" -> AppLaunchTarget("Phone", "com.google.android.dialer", "android.intent.action.DIAL", "tel:")
            else -> null
        }
    }

    companion object {
        private val KNOWN_APPS: Map<List<String>, Pair<String, String>> = linkedMapOf(
            listOf("whatsapp", "wa") to ("WhatsApp" to "com.whatsapp"),
            listOf("youtube", "yt", "you tube") to ("YouTube" to "com.google.android.youtube"),
            listOf("chrome", "google chrome", "browser") to ("Chrome" to "com.android.chrome"),
            listOf("gmail", "e-mail", "email") to ("Gmail" to "com.google.android.gm"),
            listOf("telegram") to ("Telegram" to "org.telegram.messenger"),
            listOf("settings", "definições", "configurações") to ("Settings" to "com.android.settings"),
            listOf("camera", "câmera") to ("Camera" to "com.android.camera2"),
            listOf("maps", "google maps") to ("Google Maps" to "com.google.android.apps.maps"),
            listOf("phone", "dialer", "telefone") to ("Phone" to "com.google.android.dialer"),
        )

        private fun findKnownApp(normalized: String): Pair<String, String>? {
            for ((aliases, target) in KNOWN_APPS) {
                for (alias in aliases) {
                    if (normalized == alias || normalized.contains(alias)) {
                        return target
                    }
                }
            }
            return null
        }
    }
}
