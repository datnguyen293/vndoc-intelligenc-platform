package vn.vndoc.sdk.capture

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import vn.vndoc.sdk.VNDoc
import vn.vndoc.sdk.model.DocType
import vn.vndoc.sdk.model.ErrorKind
import vn.vndoc.sdk.model.ExtractResponseDto
import vn.vndoc.sdk.model.FieldValue
import vn.vndoc.sdk.model.FieldValueDto
import vn.vndoc.sdk.model.ScanResult
import vn.vndoc.sdk.network.ApiResult
import vn.vndoc.sdk.network.OcrClient
import vn.vndoc.sdk.ui.ReviewScreen
import java.util.concurrent.Executors

/** Màn chụp do SDK cung cấp. Host app KHÔNG mở trực tiếp — dùng VNDocScanContract. */
class CaptureActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val docType = intent.getStringExtra(EXTRA_HINT)?.let { DocType.fromHint(it) }
        val config = VNDoc.currentConfig(this)
        if (docType == null || config == null || !config.isValid()) {
            finishWith(ScanResult.Error(ErrorKind.SERVER, "Chưa cấu hình server hoặc loại giấy tờ không hợp lệ"))
            return
        }

        setContent {
            MaterialTheme {
                CaptureFlow(
                    docType = docType,
                    client = OcrClient(config),
                    onDone = ::finishWith,
                    onCancel = { finishWith(ScanResult.Cancelled) },
                )
            }
        }
    }

    private fun finishWith(result: ScanResult) {
        setResult(RESULT_OK, Intent().putExtra(EXTRA_RESULT, encode(result)))
        finish()
    }

    companion object {
        const val EXTRA_HINT = "vndoc.hint"
        private const val EXTRA_RESULT = "vndoc.result"
        private val json = Json { ignoreUnknownKeys = true }

        // --- Đóng gói ScanResult qua Intent (Serializable transport) ---
        @Serializable
        private data class Transport(
            val status: String,
            val documentType: String? = null,
            val label: String? = null,
            val fields: Map<String, FieldValueDto> = emptyMap(),
            val overall: Double = 0.0,
            val warnings: List<String> = emptyList(),
            val rawJson: String? = null,
            val reason: String? = null,
            val kind: String? = null,
            val message: String? = null,
        )

        private fun encode(r: ScanResult): String {
            val t = when (r) {
                is ScanResult.Success -> Transport(
                    status = "success", documentType = r.documentType, label = r.documentTypeLabel,
                    fields = r.fields.mapValues { FieldValueDto(it.value.value, it.value.confidence, it.value.source) },
                    overall = r.overallConfidence, warnings = r.warnings, rawJson = r.rawJson,
                )
                is ScanResult.Retry -> Transport(status = "retry", reason = r.reason)
                is ScanResult.Error -> Transport(status = "error", kind = r.kind.name, message = r.message)
                ScanResult.Cancelled -> Transport(status = "cancelled")
            }
            return json.encodeToString(Transport.serializer(), t)
        }

        /** Dùng bởi VNDocScanContract.parseResult. */
        fun parseResult(intent: Intent?): ScanResult {
            val s = intent?.getStringExtra(EXTRA_RESULT) ?: return ScanResult.Cancelled
            val t = runCatching { json.decodeFromString(Transport.serializer(), s) }.getOrNull()
                ?: return ScanResult.Cancelled
            return when (t.status) {
                "success" -> ScanResult.Success(
                    documentType = t.documentType.orEmpty(), documentTypeLabel = t.label,
                    fields = t.fields.mapValues { FieldValue(it.value.value, it.value.confidence, it.value.source) },
                    overallConfidence = t.overall, warnings = t.warnings, rawJson = t.rawJson.orEmpty(),
                )
                "retry" -> ScanResult.Retry(t.reason.orEmpty())
                "error" -> ScanResult.Error(
                    kind = runCatching { ErrorKind.valueOf(t.kind.orEmpty()) }.getOrDefault(ErrorKind.SERVER),
                    message = t.message.orEmpty(),
                )
                else -> ScanResult.Cancelled
            }
        }
    }
}

// ------------------------- Compose flow -------------------------

private sealed interface Stage {
    data object Capturing : Stage
    data class Sending(val jpeg: ByteArray) : Stage
    data class Review(val body: ExtractResponseDto) : Stage
    data class Message(val text: String, val error: ScanResult?) : Stage
}

@Composable
private fun CaptureFlow(
    docType: DocType,
    client: OcrClient,
    onDone: (ScanResult) -> Unit,
    onCancel: () -> Unit,
) {
    var stage by remember { mutableStateOf<Stage>(Stage.Capturing) }

    when (val s = stage) {
        Stage.Capturing -> CameraCapture(docType, onCancel) { jpeg -> stage = Stage.Sending(jpeg) }

        is Stage.Sending -> {
            Centered { CircularProgressIndicator(); Text("Đang bóc tách…", color = Color.White) }
            LaunchedEffect(s) {
                stage = when (val r = client.extract(s.jpeg, docType.hint)) {
                    is ApiResult.Ok -> {
                        val b = r.body
                        if (b.documentType.isNullOrBlank() || b.documentType == "unknown") {
                            Stage.Message("Không nhận diện được giấy tờ — hãy chụp lại.", ScanResult.Retry("unknown"))
                        } else {
                            Stage.Review(b)
                        }
                    }
                    is ApiResult.Fail -> Stage.Message(r.message, ScanResult.Error(r.kind, r.message))
                }
            }
        }

        is Stage.Review -> ReviewScreen(
            body = s.body,
            onConfirm = { editedFields ->
                onDone(
                    ScanResult.Success(
                        documentType = s.body.documentType.orEmpty(),
                        documentTypeLabel = s.body.documentTypeLabel,
                        fields = editedFields,
                        overallConfidence = s.body.overallConfidence,
                        warnings = s.body.warnings,
                        rawJson = "",
                    )
                )
            },
            onRetake = { stage = Stage.Capturing },
        )

        is Stage.Message -> Centered {
            Text(s.text, color = Color.White)
            TextButton(onClick = { stage = Stage.Capturing }) { Text("Chụp lại") }
            TextButton(onClick = { onDone(s.error ?: ScanResult.Cancelled) }) { Text("Đóng") }
        }
    }
}

@Composable
private fun CameraCapture(
    docType: DocType,
    onCancel: () -> Unit,
    onCaptured: (ByteArray) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    var granted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }
    val permLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted = it }
    LaunchedEffect(Unit) { if (!granted) permLauncher.launch(Manifest.permission.CAMERA) }

    if (!granted) {
        Centered {
            Text("Cần quyền Camera để chụp giấy tờ.", color = Color.White)
            TextButton(onClick = { permLauncher.launch(Manifest.permission.CAMERA) }) { Text("Cấp quyền") }
            TextButton(onClick = onCancel) { Text("Huỷ") }
        }
        return
    }

    var metrics by remember { mutableStateOf<QualityMetrics?>(null) }
    var goodStreak by remember { mutableIntStateOf(0) }
    var capturing by remember { mutableStateOf(false) }
    val imageCapture = remember {
        ImageCapture.Builder().setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY).build()
    }
    val analysisExecutor = remember { Executors.newSingleThreadExecutor() }

    Box(Modifier.fillMaxSize().background(Color.Black)) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                val previewView = PreviewView(ctx)
                val future = ProcessCameraProvider.getInstance(ctx)
                future.addListener({
                    val provider = future.get()
                    val preview = Preview.Builder().build().also { it.setSurfaceProvider(previewView.surfaceProvider) }
                    val analysis = ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build().also { a ->
                            a.setAnalyzer(analysisExecutor) { proxy: ImageProxy ->
                                val m = QualityGate.analyze(proxy)
                                proxy.close()
                                metrics = m
                                goodStreak = if (m.ok) goodStreak + 1 else 0
                                if (goodStreak >= STABLE_FRAMES && !capturing) {
                                    capturing = true
                                    imageCapture.takePicture(
                                        ContextCompat.getMainExecutor(ctx),
                                        object : ImageCapture.OnImageCapturedCallback() {
                                            override fun onCaptureSuccess(image: ImageProxy) {
                                                try { onCaptured(ImageUtils.toUploadJpeg(image, docType.aspectRatio)) }
                                                finally { image.close() }
                                            }
                                            override fun onError(exc: ImageCaptureException) { capturing = false }
                                        },
                                    )
                                }
                            }
                        }
                    provider.unbindAll()
                    provider.bindToLifecycle(
                        lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageCapture, analysis,
                    )
                }, ContextCompat.getMainExecutor(ctx))
                previewView
            },
        )

        CardOverlay(docType.aspectRatio, ok = metrics?.ok == true, modifier = Modifier.fillMaxSize())

        TextButton(onClick = onCancel, modifier = Modifier.align(Alignment.TopStart).padding(8.dp)) {
            Text("Huỷ", color = Color.White)
        }
        Text(
            text = if (capturing) "Đang chụp…" else metrics?.hint() ?: "Đưa giấy tờ vào khung",
            color = Color.White,
            modifier = Modifier.align(Alignment.BottomCenter).padding(40.dp),
        )
    }
}

private const val STABLE_FRAMES = 8

@Composable
private fun Centered(content: @Composable () -> Unit) {
    Box(Modifier.fillMaxSize().background(Color.Black), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            content()
        }
    }
}
