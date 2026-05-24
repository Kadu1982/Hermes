package com.hermes.feature.inventory

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.StatFs
import androidx.core.content.ContextCompat

class InventoryCollector(private val context: Context) {
    fun collect(): Map<String, Any?> {
        return mapOf(
            "android_version" to safeString { Build.VERSION.RELEASE },
            "sdk_int" to Build.VERSION.SDK_INT,
            "model" to safeString { Build.MODEL },
            "manufacturer" to safeString { Build.MANUFACTURER },
            "network_type" to readNetworkType(),
            "storage_total_bytes" to safeLong { readStorageTotal() },
            "storage_free_bytes" to safeLong { readStorageFree() },
            "apps" to readInstalledApps(),
            "battery_percent" to safeDouble { readBatteryPercent() },
        )
    }

    private fun readNetworkType(): String {
        if (!hasNetworkStatePermission()) {
            return "permission_required"
        }
        return runCatching {
            val connectivity =
                context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val active = connectivity.activeNetwork
            val caps = active?.let { connectivity.getNetworkCapabilities(it) }
            when {
                caps == null -> "unknown"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cellular"
                else -> "other"
            }
        }.getOrElse { ex ->
            "unavailable"
        }
    }

    private fun hasNetworkStatePermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.ACCESS_NETWORK_STATE,
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun readStorageTotal(): Long? = runCatching {
        val stat = StatFs(Environment.getDataDirectory().path)
        stat.blockCountLong * stat.blockSizeLong
    }.getOrNull()

    private fun readStorageFree(): Long? = runCatching {
        val stat = StatFs(Environment.getDataDirectory().path)
        stat.availableBlocksLong * stat.blockSizeLong
    }.getOrNull()

    private fun readInstalledApps(): List<Map<String, String>> = runCatching {
        val pm = context.packageManager
        val apps = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            pm.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(0))
        } else {
            @Suppress("DEPRECATION")
            pm.getInstalledApplications(PackageManager.GET_META_DATA)
        }
        apps.map { info ->
            mapOf(
                "package" to info.packageName,
                "label" to pm.getApplicationLabel(info).toString(),
            )
        }.take(400)
    }.getOrElse { emptyList() }

    private fun readBatteryPercent(): Double? = runCatching {
        val filter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        val battery = context.registerReceiver(null, filter) ?: return null
        val level = battery.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = battery.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        if (level < 0 || scale <= 0) null else (level * 100.0 / scale)
    }.getOrNull()

    private fun safeString(block: () -> String): String = runCatching { block() }.getOrDefault("unknown")

    private fun safeLong(block: () -> Long?): Long? = runCatching { block() }.getOrNull()

    private fun safeDouble(block: () -> Double?): Double? = runCatching { block() }.getOrNull()
}
