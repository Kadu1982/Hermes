package com.hermes.feature.commands

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.hermes.core.security.SecureTokenStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Escuta contínua com palavra de ativação «Ei Jarvis» (MVP estilo Alexa).
 * Requer login admin na aba Comando e permissão de microfone.
 */
class VoiceWakeForegroundService : Service() {

    private val scope = CoroutineScope(Dispatchers.Default + Job())
    private var processingCommand = false
    private val mainHandler = Handler(Looper.getMainLooper())
    private var speechRecognizer: SpeechRecognizer? = null
    private var listening = false
    private lateinit var store: SecureTokenStore

    override fun onCreate() {
        super.onCreate()
        store = SecureTokenStore(this)
        store.voiceWakeEnabled = true
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            stopSelf()
            return
        }
        startForegroundNotification()
        mainHandler.post { startListeningLoop() }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            shutdown()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    private fun startForegroundNotification() {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "Escuta Jarvis",
                    NotificationManager.IMPORTANCE_LOW,
                ),
            )
        }
        val stopIntent = PendingIntent.getService(
            this,
            0,
            Intent(this, VoiceWakeForegroundService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Jarvis à escuta")
            .setContentText("Diga: «Ei Jarvis, ping no PC» ou «Jarvis, diga olá»")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Parar", stopIntent)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFY_ID,
                notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE,
            )
        } else {
            startForeground(NOTIFY_ID, notification)
        }
    }

    private fun startListeningLoop() {
        if (listening) return
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return
        listening = true
        speechRecognizer?.destroy()
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(recognitionListener)
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1200L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1200L)
        }
        speechRecognizer?.startListening(intent)
    }

    private val recognitionListener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}
        override fun onError(error: Int) {
            scheduleRestart()
        }
        override fun onResults(results: Bundle?) {
            val text = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                .orEmpty()
            handleUtterance(text)
            scheduleRestart()
        }
        override fun onPartialResults(partialResults: Bundle?) {
            val text = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
                ?: return
            val cmd = WakePhraseParser.parse(text) ?: return
            if (cmd.length >= 3) {
                speechRecognizer?.stopListening()
                handleCommand(cmd)
            }
        }
        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    private fun handleUtterance(spoken: String) {
        val cmd = WakePhraseParser.parse(spoken) ?: return
        handleCommand(cmd)
    }

    private fun handleCommand(command: String) {
        if (processingCommand) return
        processingCommand = true
        scope.launch {
            JarvisTts.speakBlocking(applicationContext, "Executando, senhor.", 8)
            val result = NaturalCommandClient.send(applicationContext, command)
            result.fold(
                onSuccess = { msg ->
                    JarvisTts.speakBlocking(applicationContext, "Concluído, senhor.", 6)
                    updateNotification("Último: $msg")
                },
                onFailure = { e ->
                    val err = e.message ?: "erro"
                    JarvisTts.speakBlocking(
                        applicationContext,
                        if (err.contains("login", true)) {
                            "Precisa de entrar na aba Comando, senhor."
                        } else {
                            "Não foi possível executar, senhor."
                        },
                        8,
                    )
                    updateNotification("Erro: $err")
                },
            )
            processingCommand = false
        }
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        val n = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Jarvis à escuta")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .build()
        nm.notify(NOTIFY_ID, n)
    }

    private fun scheduleRestart() {
        listening = false
        scope.launch {
            delay(600)
            mainHandler.post { startListeningLoop() }
        }
    }

    private fun shutdown() {
        store.voiceWakeEnabled = false
        listening = false
        mainHandler.post {
            speechRecognizer?.destroy()
            speechRecognizer = null
        }
        scope.cancel()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    override fun onDestroy() {
        store.voiceWakeEnabled = false
        speechRecognizer?.destroy()
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val CHANNEL_ID = "hermes_voice_wake"
        private const val NOTIFY_ID = 43
        private const val ACTION_STOP = "com.hermes.STOP_VOICE_WAKE"

        fun start(context: Context) {
            val intent = Intent(context, VoiceWakeForegroundService::class.java)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            context.stopService(
                Intent(context, VoiceWakeForegroundService::class.java).setAction(ACTION_STOP),
            )
        }
    }
}
