package vn.vndoc.sdk.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.background
import vn.vndoc.sdk.model.ExtractResponseDto
import vn.vndoc.sdk.model.FieldValue

/**
 * Rà soát & SỬA TAY kết quả trước khi trả về (OCR là hỗ trợ — DEC-062). Trường confidence
 * thấp được tô cảnh báo để cán bộ kiểm tra kỹ.
 */
@Composable
fun ReviewScreen(
    body: ExtractResponseDto,
    onConfirm: (Map<String, FieldValue>) -> Unit,
    onRetake: () -> Unit,
) {
    val edited = remember {
        mutableStateMapOf<String, String>().apply {
            body.fields.forEach { (k, v) -> put(k, v.value.orEmpty()) }
        }
    }

    Surface(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState())) {
            Text(
                text = body.documentTypeLabel ?: body.documentType ?: "Kết quả",
                fontSize = 20.sp, fontWeight = FontWeight.Bold,
            )
            Text(
                text = "Độ tin cậy tổng: ${(body.overallConfidence * 100).toInt()}%",
                color = Color.Gray, modifier = Modifier.padding(bottom = 8.dp),
            )

            body.fields.forEach { (key, fv) ->
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                    ConfidenceDot(fv.confidence)
                    OutlinedTextField(
                        value = edited[key].orEmpty(),
                        onValueChange = { edited[key] = it },
                        label = { Text("$key  (${fv.source})") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().padding(start = 8.dp),
                    )
                }
            }

            Row(
                Modifier.fillMaxWidth().padding(top = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                OutlinedButton(onClick = onRetake, modifier = Modifier.fillMaxWidth().weight(1f)) {
                    Text("Chụp lại")
                }
                Button(
                    onClick = {
                        val result = body.fields.mapValues { (k, v) ->
                            FieldValue(edited[k]?.ifBlank { null }, v.confidence, v.source)
                        }
                        onConfirm(result)
                    },
                    modifier = Modifier.fillMaxWidth().weight(1f),
                ) { Text("Xác nhận") }
            }
        }
    }
}

@Composable
private fun ConfidenceDot(confidence: Double) {
    val color = when {
        confidence >= 0.8 -> Color(0xFF2ECC71)   // xanh — tốt
        confidence >= 0.5 -> Color(0xFFF1C40F)   // vàng — kiểm tra
        else -> Color(0xFFE74C3C)                // đỏ — nghi ngờ
    }
    Text(
        text = "",
        modifier = Modifier.size(12.dp).clip(CircleShape).background(color),
    )
}
