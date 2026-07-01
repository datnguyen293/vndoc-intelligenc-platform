package vn.vndoc.sdk.capture

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke

/** Khung căn theo tỉ lệ giấy tờ: làm mờ vùng ngoài + viền khung (DOC-09 §4). */
@Composable
fun CardOverlay(aspect: Float, ok: Boolean, modifier: Modifier = Modifier) {
    Canvas(modifier.fillMaxSize()) {
        val margin = size.width * 0.06f
        val frameW = size.width - 2 * margin
        val frameH = frameW / aspect
        val top = ((size.height - frameH) / 2f).coerceAtLeast(0f)
        val left = margin
        val dim = Color.Black.copy(alpha = 0.5f)

        // Làm mờ 4 vùng quanh khung (đơn giản, không cần blend mode).
        drawRect(dim, Offset(0f, 0f), Size(size.width, top))                              // trên
        drawRect(dim, Offset(0f, top + frameH), Size(size.width, size.height - top - frameH)) // dưới
        drawRect(dim, Offset(0f, top), Size(left, frameH))                                // trái
        drawRect(dim, Offset(left + frameW, top), Size(size.width - left - frameW, frameH)) // phải

        // Viền khung: xanh khi đạt chất lượng, trắng khi chưa.
        drawRect(
            color = if (ok) Color(0xFF2ECC71) else Color.White,
            topLeft = Offset(left, top),
            size = Size(frameW, frameH),
            style = Stroke(width = 6f),
        )
    }
}
