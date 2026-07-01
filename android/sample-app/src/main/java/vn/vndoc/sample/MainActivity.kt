package vn.vndoc.sample

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.registerForActivityResult
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import vn.vndoc.sdk.VNDoc
import vn.vndoc.sdk.VNDocScanContract
import vn.vndoc.sdk.config.ServerConfig
import vn.vndoc.sdk.model.DocType
import vn.vndoc.sdk.model.ScanResult

/**
 * App mẫu: nhập cấu hình server (DEC-066), chọn loại giấy tờ, quét, hiển thị kết quả.
 * Minh hoạ tích hợp VNDocScanContract — không phải sản phẩm cuối.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { Surface { SampleScreen() } } }
    }
}

@Composable
private fun SampleScreen() {
    val context = LocalContext.current
    val existing = remember { VNDoc.currentConfig(context) }
    var host by remember { mutableStateOf(existing?.host ?: "192.168.1.50") }
    var port by remember { mutableStateOf((existing?.port ?: 11001).toString()) }
    var apiKey by remember { mutableStateOf(existing?.apiKey ?: "") }
    var status by remember { mutableStateOf("") }

    val scan = registerForActivityResult(VNDocScanContract()) { result ->
        status = when (result) {
            is ScanResult.Success -> buildString {
                append("✓ ${result.documentTypeLabel ?: result.documentType}\n")
                result.fields.forEach { (k, v) -> append("$k = ${v.value}  (${(v.confidence * 100).toInt()}%)\n") }
            }
            is ScanResult.Retry -> "Chụp lại: ${result.reason}"
            is ScanResult.Error -> "Lỗi [${result.kind}]: ${result.message}"
            ScanResult.Cancelled -> "Đã huỷ"
        }
    }

    Column(
        Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("VNDoc — Cấu hình server", fontSize = 18.sp, fontWeight = FontWeight.Bold)
        OutlinedTextField(host, { host = it }, label = { Text("Host (IP máy)") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(port, { port = it }, label = { Text("Port") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(apiKey, { apiKey = it }, label = { Text("API Key") }, modifier = Modifier.fillMaxWidth())
        Button(
            onClick = { VNDoc.configure(context, ServerConfig(host.trim(), port.toIntOrNull() ?: 11001, apiKey.trim())) },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Lưu cấu hình") }

        Text("Chọn loại để quét", fontSize = 16.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 12.dp))
        DocType.entries.forEach { dt ->
            Button(onClick = { scan.launch(dt) }, modifier = Modifier.fillMaxWidth()) { Text(dt.label) }
        }

        if (status.isNotBlank()) {
            Text("Kết quả", fontSize = 16.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 12.dp))
            Text(status)
        }
    }
}
