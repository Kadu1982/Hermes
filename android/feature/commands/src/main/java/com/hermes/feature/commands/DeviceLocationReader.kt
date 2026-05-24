package com.hermes.feature.commands

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Looper
import androidx.core.content.ContextCompat
import kotlin.coroutines.resume
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

class DeviceLocationReader(private val context: Context) {
    suspend fun read(timeoutMs: Long = 12_000): Map<String, Any?> = withContext(Dispatchers.Main) {
        ensurePermission()
        val location = withTimeoutOrNull(timeoutMs) { resolveLocation() }
            ?: throw IllegalStateException("location_unavailable")
        mapOf(
            "latitude" to location.latitude,
            "longitude" to location.longitude,
            "accuracy_m" to if (location.hasAccuracy()) location.accuracy.toDouble() else null,
            "provider" to location.provider,
            "timestamp_ms" to location.time,
            "maps_url" to "https://www.google.com/maps/search/?api=1&query=${location.latitude},${location.longitude}",
        )
    }

    private fun ensurePermission() {
        val fine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!fine && !coarse) {
            throw IllegalStateException("location_permission_required")
        }
    }

    private suspend fun resolveLocation(): Location? {
        val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val candidates = listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER,
            LocationManager.PASSIVE_PROVIDER,
        ).filter { lm.isProviderEnabled(it) }

        val lastKnown = candidates.mapNotNull { provider ->
            runCatching { lm.getLastKnownLocation(provider) }.getOrNull()
        }.maxByOrNull { it.time }
        if (lastKnown != null) return lastKnown

        return suspendCancellableCoroutine { cont ->
            val provider = candidates.firstOrNull() ?: run {
                cont.resume(null)
                return@suspendCancellableCoroutine
            }
            val listener = object : LocationListener {
                override fun onLocationChanged(location: Location) {
                    if (cont.isActive) cont.resume(location)
                }

                @Deprecated("Deprecated in Java")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit

                override fun onProviderEnabled(provider: String) = Unit

                override fun onProviderDisabled(provider: String) = Unit
            }
            cont.invokeOnCancellation {
                runCatching { lm.removeUpdates(listener) }
            }
            @Suppress("DEPRECATION")
            lm.requestSingleUpdate(provider, listener, Looper.getMainLooper())
        }
    }
}
