package com.hermes.feature.commands

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.hermes.core.network.NetworkModule
import com.hermes.core.security.SecureTokenStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class CommandForegroundService : Service() {

    private val scope = CoroutineScope(Dispatchers.Default + Job())
    private lateinit var store: SecureTokenStore
    private lateinit var dispatcher: CommandDispatcher

    override fun onCreate() {
        super.onCreate()
        store = SecureTokenStore(this)
        val base = store.apiBaseUrl ?: return stopSelf()
        val api = NetworkModule.createApi(store, "$base/api/v1/")
        val logs = LocalLogBuffer(this)
        dispatcher = CommandDispatcher(
            this,
            api,
            logs,
            onRevokeLocal = {
                store.clear()
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    stopForeground(STOP_FOREGROUND_DETACH)
                } else {
                    @Suppress("DEPRECATION")
                    stopForeground(true)
                }
                stopSelf()
            },
        )
        startFg()
        scope.launch {
            val ver = try {
                packageManager.getPackageInfo(packageName, 0).versionName ?: "0"
            } catch (_: Exception) {
                "0"
            }
            while (isActive) {
                runCatching {
                    dispatcher.heartbeat(ver)
                }
                runCatching { dispatcher.pollOnce() }
                delay(5_000)
            }
        }
    }

    private fun startFg() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Hermes sync", NotificationManager.IMPORTANCE_LOW),
            )
        }
        val n: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Hermes")
            .setContentText("Remote admin session active")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFY_ID, n, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(NOTIFY_ID, n)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val CHANNEL_ID = "hermes_cmd"
        private const val NOTIFY_ID = 42
    }
}
