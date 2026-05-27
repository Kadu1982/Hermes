package com.hermes.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Activity
import android.content.Intent
import android.content.Context
import android.speech.RecognizerIntent
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationCompat
import com.hermes.app.voice.HermesVoice
import com.hermes.core.network.BrainGoogleBody
import com.hermes.core.network.AdminLoginBody
import com.hermes.core.network.NaturalCommandBody
import com.hermes.core.network.NetworkModule
import com.hermes.core.network.TwoFaBody
import com.hermes.feature.commands.AndroidUnlockRequester
import com.hermes.feature.commands.CommandBridge
import com.hermes.feature.commands.JarvisTts
import com.hermes.feature.commands.UnlockController
import com.hermes.feature.commands.VoiceWakeForegroundService
import com.hermes.feature.pairing.PairingRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun CommanderScreen(
    activity: Activity,
    brainUrl: String,
    onBrainUrlChange: (String) -> Unit,
    voice: HermesVoice,
    statusText: String,
    onStatus: (String) -> Unit,
) {
    val scope = rememberCoroutineScope()
    val store = HermesApp.instance.store
    var email by remember { mutableStateOf("admin@example.com") }
    var password by remember { mutableStateOf("") }
    var tfaCode by remember { mutableStateOf("") }
    var partialToken by remember { mutableStateOf(store.adminPartialToken.orEmpty()) }
    var needs2fa by remember { mutableStateOf(store.adminPartialToken != null && store.adminToken.isNullOrBlank()) }
    var adminLoggedIn by remember { mutableStateOf(false) }
    var checkingSession by remember { mutableStateOf(true) }
    var voiceWakeOn by remember { mutableStateOf(store.voiceWakeEnabled) }
    var commandText by remember { mutableStateOf("") }
    var notifyChannel by remember { mutableStateOf(store.defaultNotifyChannel) }
    var googleText by remember { mutableStateOf("buscar e-mails não lidos") }
    var googleThreadId by remember { mutableStateOf<String?>(null) }
    var googleStatus by remember { mutableStateOf("") }
    var googleSummary by remember { mutableStateOf("") }
    var googleService by remember { mutableStateOf("") }
    var googleAction by remember { mutableStateOf("") }
    var googleRaw by remember { mutableStateOf("") }
    var googleData by remember { mutableStateOf<Any?>(null) }
    var googleNeedsConfirmation by remember { mutableStateOf(false) }
    var pendingUnlock by remember { mutableStateOf(CommandBridge.pendingUnlockCommandId.get()) }
    var lastAnnouncedUnlock by remember { mutableStateOf<String?>(null) }
    val notifyOptions = listOf("voice" to "Voz Jarvis", "push" to "Notificação", "silent" to "Silencioso")

    val speechLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        val spoken = result.data
            ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull()
        if (!spoken.isNullOrBlank()) commandText = spoken
    }

    fun normalizedBrain(): String = PairingRepository.normalizeBaseUrl(brainUrl)

    fun httpErrorMessage(e: Throwable): String {
        if (e is HttpException) {
            when (e.code()) {
                401 -> return "Não autorizado (401). Faça login de novo: senha + código 2FA."
                403 -> return "Sessão incompleta (403). Confirme o código 2FA no Authenticator."
            }
            val raw = e.response()?.errorBody()?.string()?.trim().orEmpty()
            if (raw.contains("detail")) {
                return Regex("\"detail\"\\s*:\\s*\"([^\"]+)\"").find(raw)?.groupValues?.get(1)
                    ?: raw
            }
            return raw.removeSurrounding("\"").ifEmpty { "HTTP ${e.code()}" }
        }
        return e.message ?: "erro desconhecido"
    }

    fun forceLogout(message: String) {
        store.clearAdmin()
        adminLoggedIn = false
        needs2fa = false
        partialToken = ""
        onStatus(message)
    }

    suspend fun sendGoogle(confirm: Boolean) {
        onStatus(if (confirm) "Confirmando Google..." else "A falar com o Google...")
        val api = NetworkModule.createAdminApi(store, normalizedBrain())
        val r = api.google(
            BrainGoogleBody(
                text = googleText,
                confirm = confirm,
                thread_id = googleThreadId,
            ),
        )
        googleThreadId = r.thread_id ?: googleThreadId
        googleService = r.service
        googleAction = r.action
        googleStatus = r.status
        googleSummary = r.summary ?: r.message
        googleRaw = r.raw_output.orEmpty()
        googleData = r.data
        googleNeedsConfirmation = r.requires_confirmation
        onStatus(if (r.requires_confirmation) "Confirmação requerida pelo Google" else "Google concluído")
    }

    suspend fun validateAdminSession(): Boolean {
        val token = store.adminToken?.trim().orEmpty()
        if (token.isEmpty()) return false
        return runCatching {
            NetworkModule.createAdminApi(store, normalizedBrain()).session()
        }.fold(
            onSuccess = { it["ok"] == true },
            onFailure = { false },
        )
    }

    LaunchedEffect(brainUrl) {
        checkingSession = true
        val ok = validateAdminSession()
        adminLoggedIn = ok
        if (!ok && !store.adminToken.isNullOrBlank()) {
            store.clearAdmin()
            onStatus("Sessão antiga removida. Entre de novo (senha + 2FA).")
        }
        checkingSession = false
    }

    LaunchedEffect(Unit) {
        while (true) {
            pendingUnlock = CommandBridge.pendingUnlockCommandId.get()
            delay(400)
        }
    }

    LaunchedEffect(pendingUnlock) {
        val commandId = pendingUnlock
        if (commandId.isNullOrBlank()) {
            lastAnnouncedUnlock = null
            clearUnlockNotification(activity)
            return@LaunchedEffect
        }
        if (commandId != lastAnnouncedUnlock) {
            lastAnnouncedUnlock = commandId
            onStatus("Pedido de desbloqueio ativo")
            withContext(Dispatchers.IO) {
                voice.speakBlocking(activity.getString(R.string.jarvis_unlock_request_spoken))
            }
            postUnlockNotification(activity, commandId)
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Comando — fale ou escreva; o cérebro na VPS executa nos seus dispositivos.")
        OutlinedTextField(
            brainUrl,
            onBrainUrlChange,
            Modifier.fillMaxWidth(),
            label = { Text("URL do cérebro (VPS, porta 18080)") },
            placeholder = { Text("http://72.60.55.213:18080") },
            singleLine = true,
        )
        Text(
            "Use admin@example.com e a porta 18080 (não 13000).",
            color = Color.Gray,
        )

        if (checkingSession) {
            Text("A verificar sessão…")
        } else if (!adminLoggedIn) {
            OutlinedTextField(email, { email = it }, Modifier.fillMaxWidth(), label = { Text("Email admin") })
            if (!needs2fa) {
                OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), label = { Text("Password") })
                Button(
                    onClick = {
                        scope.launch {
                            onStatus("Autenticando…")
                            runCatching {
                                store.clearAdmin()
                                val api = NetworkModule.createAdminApi(store, normalizedBrain())
                                val r = api.login(AdminLoginBody(email.trim(), password))
                                if (r.requires2fa) {
                                    store.adminToken = null
                                    partialToken = r.accessToken
                                    store.adminPartialToken = r.accessToken
                                    needs2fa = true
                                    onStatus("Digite o código do Google Authenticator")
                                } else {
                                    store.adminToken = r.accessToken
                                    store.adminPartialToken = null
                                    if (validateAdminSession()) {
                                        adminLoggedIn = true
                                        onStatus("Sessão de comando ativa")
                                        withContext(Dispatchers.IO) {
                                            voice.speakBlocking(voice.readyLine())
                                        }
                                    } else {
                                        forceLogout("Token rejeitado pela API. Verifique URL e credenciais.")
                                    }
                                }
                            }.onFailure { onStatus("Login: ${httpErrorMessage(it)}") }
                        }
                    },
                ) { Text("Entrar no cérebro") }
            } else {
                OutlinedTextField(tfaCode, { tfaCode = it }, Modifier.fillMaxWidth(), label = { Text("Código 2FA") })
                Button(
                    onClick = {
                        scope.launch {
                            onStatus("A confirmar 2FA…")
                            runCatching {
                                val token = partialToken.ifBlank { store.adminPartialToken.orEmpty() }
                                if (token.isBlank()) {
                                    onStatus("2FA: sessão expirada — toque Entrar no cérebro de novo")
                                    needs2fa = false
                                    return@runCatching
                                }
                                val code = tfaCode.trim().replace(" ", "")
                                val api = NetworkModule.createAdminApi(store, normalizedBrain())
                                val r = api.verify2fa(TwoFaBody(token, code))
                                store.adminToken = r.accessToken
                                store.adminPartialToken = null
                                needs2fa = false
                                tfaCode = ""
                                if (validateAdminSession()) {
                                    adminLoggedIn = true
                                    onStatus("Sessão de comando ativa (2FA OK)")
                                    withContext(Dispatchers.IO) {
                                        voice.speakBlocking(voice.readyLine())
                                    }
                                } else {
                                    forceLogout("2FA aceite mas sessão inválida. Tente login de novo.")
                                }
                            }.onFailure { onStatus("2FA: ${httpErrorMessage(it)}") }
                        }
                    },
                ) { Text("Confirmar 2FA") }
            }
        } else {
            Text("Modo voz Jarvis")
            Text(
                "Ative e diga: «Jarvis», depois «ping no PC-Casa», «tira uma foto» " +
                    "ou «onde estou» / «me leva para casa». Sem AccessKey, o app cai no modo antigo com «Ei Jarvis».",
            )
            Button(
                onClick = {
                    scope.launch {
                        onStatus("A testar voz…")
                        withContext(Dispatchers.IO) {
                            JarvisTts.speakBlocking(
                                activity,
                                "Jarvis operacional, senhor. Voz masculina ativa.",
                            )
                        }
                        onStatus("Teste de voz concluído")
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Testar voz Jarvis (masculina)") }
            Button(
                onClick = {
                    voiceWakeOn = !voiceWakeOn
                    store.voiceWakeEnabled = voiceWakeOn
                    if (voiceWakeOn) {
                        VoiceWakeForegroundService.start(activity)
                        onStatus("Escuta ativa — diga «Jarvis» e depois o comando")
                    } else {
                        VoiceWakeForegroundService.stop(activity)
                        onStatus("Escuta desligada")
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (voiceWakeOn) "Parar escuta Jarvis" else "Ativar escuta Jarvis")
            }
            Button(
                onClick = { voice.openVoiceSettings() },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Abrir definições TTS do Android") }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                notifyOptions.forEach { (id, label) ->
                    FilterChip(
                        selected = notifyChannel == id,
                        onClick = {
                            notifyChannel = id
                            store.defaultNotifyChannel = id
                        },
                        label = { Text(label) },
                    )
                }
            }
            if (pendingUnlock != null) {
                Text("Pedido de desbloqueio")
                Text("O Hermes pediu um desbloqueio legítimo do sistema para este comando.")
                Button(
                    onClick = {
                        val commandId = pendingUnlock ?: return@Button
                        scope.launch {
                            onStatus("A solicitar desbloqueio no sistema…")
                            runCatching {
                                val outcome = UnlockController().request(AndroidUnlockRequester(activity))
                                CommandBridge.completeUnlock(
                                    commandId,
                                    mapOf(
                                        "approved" to outcome.approved,
                                        "dismissed" to outcome.dismissed,
                                        "message" to outcome.message,
                                    ),
                                )
                                onStatus(
                                    if (outcome.dismissed) "Desbloqueio confirmado pelo sistema"
                                    else "Desbloqueio não concluído",
                                )
                            }.onFailure { err ->
                                CommandBridge.failUnlock(commandId, err.message ?: "unlock_failed")
                                onStatus("Desbloqueio: ${err.message ?: "falha"}")
                            }
                        }
                    },
                ) { Text("Autorizar desbloqueio") }
                Button(
                    onClick = {
                        val commandId = pendingUnlock ?: return@Button
                        CommandBridge.completeUnlock(
                            commandId,
                            mapOf(
                                "approved" to false,
                                "dismissed" to false,
                                "message" to "user_declined",
                            ),
                        )
                        onStatus("Pedido de desbloqueio recusado")
                    },
                ) { Text("Recusar desbloqueio") }
            }
            Button(
                onClick = {
                    activity.startActivity(
                        Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Abrir definições de acessibilidade") }
            OutlinedTextField(
                commandText,
                { commandText = it },
                Modifier.fillMaxWidth(),
                label = { Text("Comando (ex.: ping no PC-Casa)") },
                minLines = 2,
            )
            Button(
                onClick = {
                    val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                        putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                        putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
                        putExtra(RecognizerIntent.EXTRA_PROMPT, "Fale com o Jarvis")
                    }
                    if (intent.resolveActivity(activity.packageManager) != null) {
                        speechLauncher.launch(intent)
                    } else {
                        onStatus("Reconhecimento de voz não disponível neste aparelho")
                    }
                },
            ) { Text("Falar com Jarvis") }
            Button(
                onClick = {
                    scope.launch {
                        if (!validateAdminSession()) {
                            forceLogout("Sessão expirada. Login de novo (senha + 2FA).")
                            return@launch
                        }
                        onStatus("Enviando…")
                        runCatching {
                            val api = NetworkModule.createAdminApi(store, normalizedBrain())
                            val r = api.natural(
                                NaturalCommandBody(
                                    text = commandText,
                                    notify_channel = notifyChannel,
                                    notify_on = "done",
                                ),
                            )
                            onStatus("Enviado: ${r.parsed_type} → ${r.parsed_device_name} (${r.command.status})")
                            if (notifyChannel == "voice") {
                                withContext(Dispatchers.IO) {
                                    voice.speakBlocking(voice.commandSentLine())
                                }
                            }
                        }.onFailure { e ->
                            if (e is HttpException && (e.code() == 401 || e.code() == 403)) {
                                forceLogout(httpErrorMessage(e))
                            } else {
                                onStatus("Erro: ${httpErrorMessage(e)}")
                            }
                        }
                    }
                },
            ) { Text("Enviar comando") }
            Text("Google Workspace")
            Text("Fale com o Jarvis para Gmail, Calendar, Drive, Docs e Sheets. A mesma thread fica guardada para aprendizagem.")
            OutlinedTextField(
                googleText,
                { googleText = it },
                Modifier.fillMaxWidth(),
                label = { Text("Pedido Google") },
                minLines = 3,
            )
            Button(
                onClick = {
                    scope.launch {
                        runCatching { sendGoogle(false) }
                            .onFailure { e ->
                                if (e is HttpException && (e.code() == 401 || e.code() == 403)) {
                                    forceLogout(httpErrorMessage(e))
                                } else {
                                    onStatus("Google: ${httpErrorMessage(e)}")
                                }
                            }
                    }
                },
            ) { Text("Executar Google") }
            if (googleNeedsConfirmation) {
                Button(
                    onClick = {
                        scope.launch {
                            runCatching { sendGoogle(true) }
                                .onFailure { e ->
                                    if (e is HttpException && (e.code() == 401 || e.code() == 403)) {
                                        forceLogout(httpErrorMessage(e))
                                    } else {
                                        onStatus("Google: ${httpErrorMessage(e)}")
                                    }
                                }
                        }
                    },
                ) { Text("Confirmar e executar") }
            }
            Button(
                onClick = {
                    googleThreadId = null
                    googleStatus = ""
                    googleSummary = ""
                    googleService = ""
                    googleAction = ""
                    googleRaw = ""
                    googleData = null
                    googleNeedsConfirmation = false
                    onStatus("Nova thread Google")
                },
            ) { Text("Nova thread Google") }
            if (googleStatus.isNotBlank()) {
                Text("Status Google: $googleStatus")
            }
            if (googleThreadId != null) {
                Text("Thread Google: $googleThreadId")
            }
            if (googleService.isNotBlank() || googleAction.isNotBlank()) {
                Text("Ação Google: $googleService.$googleAction")
            }
            if (googleSummary.isNotBlank()) {
                Text("Resumo Google: $googleSummary")
            }
            if (googleData != null) {
                Text("Dados Google: ${googleData}")
            }
            if (googleRaw.isNotBlank()) {
                Text("Raw Google: $googleRaw")
            }
            Button(onClick = {
                forceLogout("Sessão de comando terminada")
            }) { Text("Sair do modo comando") }
        }
        Text(statusText)
    }
}

private const val UNLOCK_NOTIFICATION_CHANNEL_ID = "hermes_unlock"
private const val UNLOCK_NOTIFICATION_ID = 43_102

private fun postUnlockNotification(activity: Activity, commandId: String) {
    val nm = activity.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        nm.createNotificationChannel(
            NotificationChannel(
                UNLOCK_NOTIFICATION_CHANNEL_ID,
                activity.getString(R.string.jarvis_unlock_request_title),
                NotificationManager.IMPORTANCE_HIGH,
            ),
        )
    }
    val launchIntent = Intent(activity, MainActivity::class.java).apply {
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        putExtra("unlock_command_id", commandId)
    }
    val contentIntent = PendingIntent.getActivity(
        activity,
        UNLOCK_NOTIFICATION_ID,
        launchIntent,
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )
    val notification = NotificationCompat.Builder(activity, UNLOCK_NOTIFICATION_CHANNEL_ID)
        .setSmallIcon(android.R.drawable.ic_lock_lock)
        .setContentTitle(activity.getString(R.string.jarvis_unlock_request_title))
        .setContentText(activity.getString(R.string.jarvis_unlock_request_body))
        .setStyle(
            NotificationCompat.BigTextStyle().bigText(activity.getString(R.string.jarvis_unlock_request_body)),
        )
        .setPriority(NotificationCompat.PRIORITY_HIGH)
        .setCategory(NotificationCompat.CATEGORY_STATUS)
        .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
        .setOngoing(true)
        .setAutoCancel(false)
        .setContentIntent(contentIntent)
        .build()
    nm.notify(UNLOCK_NOTIFICATION_ID, notification)
}

private fun clearUnlockNotification(activity: Activity) {
    val nm = activity.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    nm.cancel(UNLOCK_NOTIFICATION_ID)
}
