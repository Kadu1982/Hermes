package com.hermes.feature.commands

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri

object NavigationLauncher {
    fun open(context: Context, destination: String, mode: String = "driving"): Map<String, Any?> {
        val normalizedDestination = destination.trim()
        if (normalizedDestination.isBlank()) {
            throw IllegalArgumentException("missing_destination")
        }
        val googleNavigationUri = buildGoogleNavigationUri(normalizedDestination, mode)
        val primary = Intent(Intent.ACTION_VIEW, Uri.parse(googleNavigationUri)).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            setPackage("com.google.android.apps.maps")
        }
        if (primary.resolveActivity(context.packageManager) != null) {
            context.startActivity(primary)
            return mapOf(
                "destination" to normalizedDestination,
                "mode" to mode,
                "opened_url" to googleNavigationUri,
                "app" to "google_maps",
            )
        }

        val fallback = Intent(Intent.ACTION_VIEW, Uri.parse(buildGeoUri(normalizedDestination))).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return try {
            if (fallback.resolveActivity(context.packageManager) == null) {
                throw ActivityNotFoundException("No maps app found")
            }
            context.startActivity(fallback)
            mapOf(
                "destination" to normalizedDestination,
                "mode" to mode,
                "opened_url" to buildGeoUri(normalizedDestination),
                "app" to "maps_fallback",
            )
        } catch (e: ActivityNotFoundException) {
            throw IllegalStateException("navigation_app_not_found", e)
        }
    }

    private fun buildGoogleNavigationUri(destination: String, mode: String): String {
        val q = Uri.encode(destination)
        val m = when (mode.lowercase()) {
            "walking" -> "w"
            "bicycling" -> "b"
            "transit" -> "r"
            else -> "d"
        }
        return "google.navigation:q=$q&mode=$m"
    }

    private fun buildGeoUri(destination: String): String {
        return "geo:0,0?q=${Uri.encode(destination)}"
    }
}
