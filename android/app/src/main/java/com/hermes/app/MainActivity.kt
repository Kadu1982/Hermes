package com.hermes.app

import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.hermes.app.voice.HermesVoice
import com.hermes.core.network.CommandCompleteBody
import com.hermes.feature.commands.CommandBridge
import com.hermes.feature.commands.CommandForegroundService
import com.hermes.feature.files.FileTransfer
import com.hermes.feature.pairing.PairingRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val runtimePermissions = mutableListOf(
            android.Manifest.permission.ACCESS_NETWORK_STATE,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            runtimePermissions += android.Manifest.permission.POST_NOTIFICATIONS
            runtimePermissions += android.Manifest.permission.RECORD_AUDIO
        }
        requestPermissions(runtimePermissions.toTypedArray(), 1)
        setContent {
            HermesRoot(this)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HermesRoot(activity: MainActivity) {
    val scope = rememberCoroutineScope()
    val app = HermesApp.instance
    var baseUrl by remember {
        mutableStateOf(app.store.apiBaseUrl ?: BuildConfig.API_BASE_URL.trimEnd('/'))
    }
    var pairCode by remember { mutableStateOf("") }
    var deviceName by remember { mutableStateOf(android.os.Build.MODEL) }
    var statusText by remember { mutableStateOf("Idle") }
    var deviceSnapshot by remember { mutableStateOf<Map<String, Any?>>(emptyMap()) }
    var pendingUpload by remember { mutableStateOf(CommandBridge.pendingUploadCommandId.get()) }
    val voice = remember { HermesVoice(activity) }

    DisposableEffect(Unit) {
        onDispose { voice.shutdown() }
    }

    val pickFile = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        val cmd = CommandBridge.pendingUploadCommandId.get() ?: return@rememberLauncherForActivityResult
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            val api = app.api() ?: return@launch
            runCatching {
                FileTransfer(api).upload(cmd, uri, activity.contentResolver)
                api.complete(cmd, CommandCompleteBody("done", mapOf("uploaded" to true), null))
            }
            CommandBridge.clearUploadUi()
        }
    }

    LaunchedEffect(Unit) {
        while (isActive) {
            pendingUpload = CommandBridge.pendingUploadCommandId.get()
            delay(400)
        }
    }

    // Agente (poll de comandos) deve correr em qualquer tab enquanto pareado.
    LaunchedEffect(app.store.deviceToken) {
        if (app.store.deviceToken != null) {
            val intent = Intent(activity, CommandForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ContextCompat.startForegroundService(activity, intent)
            } else {
                activity.startService(intent)
            }
        }
    }

    Scaffold(
        topBar = { CenterAlignedTopAppBar(title = { Text("Hermes") }) },
    ) { padding ->
        Column(Modifier.padding(padding)) {
            Column(
                Modifier
                    .padding(16.dp)
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                PhoneSection(
                    baseUrl = baseUrl,
                    onBaseUrlChange = { baseUrl = it },
                    pairCode = pairCode,
                    onPairCodeChange = { pairCode = it },
                    deviceName = deviceName,
                    onDeviceNameChange = { deviceName = it },
                    statusText = statusText,
                    onStatus = { statusText = it },
                    pendingUpload = pendingUpload,
                    deviceSnapshot = deviceSnapshot,
                    onRefreshSnapshot = {
                        scope.launch {
                            val api = app.api() ?: return@launch
                            runCatching { api.me() }
                                .onSuccess { deviceSnapshot = it; onStatus("Status atualizado") }
                                .onFailure { onStatus("Erro ao ler estado: ${it.message}") }
                        }
                    },
                    onPickFile = { pickFile.launch("*/*") },
                    activity = activity,
                    scope = scope,
                )
                CommanderScreen(
                    activity = activity,
                    brainUrl = baseUrl,
                    onBrainUrlChange = { baseUrl = it },
                    voice = voice,
                    statusText = statusText,
                    onStatus = { statusText = it },
                )
            }
        }
    }
}

@Composable
private fun PhoneSection(
    baseUrl: String,
    onBaseUrlChange: (String) -> Unit,
    pairCode: String,
    onPairCodeChange: (String) -> Unit,
    deviceName: String,
    onDeviceNameChange: (String) -> Unit,
    statusText: String,
    onStatus: (String) -> Unit,
    pendingUpload: String?,
    deviceSnapshot: Map<String, Any?>,
    onRefreshSnapshot: () -> Unit,
    onPickFile: () -> Unit,
    activity: MainActivity,
    scope: kotlinx.coroutines.CoroutineScope,
) {
    val app = HermesApp.instance
    val paired = app.store.deviceToken != null
    LaunchedEffect(baseUrl, paired) {
        if (paired) {
            onRefreshSnapshot()
        }
    }
    Text("Telefone")
    Text("O telefone fica pareado com a VPS e mostra o estado do aparelho.")
    OutlinedTextField(baseUrl, onBaseUrlChange, Modifier.fillMaxWidth(), label = { Text("Server base URL") })
    if (!paired) {
        OutlinedTextField(pairCode, onPairCodeChange, Modifier.fillMaxWidth(), label = { Text("Pairing code") })
        OutlinedTextField(deviceName, onDeviceNameChange, Modifier.fillMaxWidth(), label = { Text("Device name") })
        Button(
            onClick = {
                scope.launch {
                    onStatus("Pairing…")
                    val r = PairingRepository(app.store).pair(baseUrl, pairCode, deviceName)
                    onStatus(if (r.isSuccess) "Paired" else "Error: ${r.exceptionOrNull()?.message}")
                    if (r.isSuccess) {
                        onRefreshSnapshot()
                        val intent = Intent(activity, CommandForegroundService::class.java)
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            ContextCompat.startForegroundService(activity, intent)
                        } else {
                            activity.startService(intent)
                        }
                    }
                }
            },
        ) { Text("Pair device") }
    } else {
        Button(onClick = onRefreshSnapshot) { Text("Atualizar estado do aparelho") }
        if (deviceSnapshot.isNotEmpty()) {
            Text("Nome: ${deviceSnapshot["name"] ?: "?"}")
            Text("Plataforma: ${deviceSnapshot["platform"] ?: "?"}")
            Text("Último seen: ${deviceSnapshot["last_seen"] ?: "nunca"}")
            Text("Versão de política: ${deviceSnapshot["policy_version"] ?: "?"}")
            Text("Revogado: ${deviceSnapshot["revoked_at"] ?: "não"}")
            val inventory = deviceSnapshot["inventory"]
            if (inventory != null) {
                Text("Inventário:")
                Text(inventory.toString())
            }
        }
        Button(onClick = {
            scope.launch {
                val api = app.api()
                onStatus(
                    if (api != null) {
                        runCatching { api.me() }.fold({ "OK: ${it["name"]}" }, { "Err ${it.message}" })
                    } else "Not configured",
                )
            }
        }) { Text("Ping /me") }
        Button(onClick = {
            app.store.clearDevice()
            activity.stopService(Intent(activity, CommandForegroundService::class.java))
            onStatus("Telefone desemparelhado")
        }) { Text("Unpair / clear credentials") }
    }
    Text(statusText)
    if (pendingUpload != null) {
        Text("Upload requested for command $pendingUpload")
        Button(onClick = onPickFile) { Text("Choose file to upload") }
    }
}
