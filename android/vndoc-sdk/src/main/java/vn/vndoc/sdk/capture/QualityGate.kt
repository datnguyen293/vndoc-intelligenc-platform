package vn.vndoc.sdk.capture

import androidx.camera.core.ImageProxy
import kotlin.math.abs

/** Chỉ số chất lượng khung (DOC-09 §6). Ngưỡng khởi điểm — tinh chỉnh thực địa. */
data class QualityMetrics(
    val brightness: Double,
    val sharpness: Double,
    val glareRatio: Double,
) {
    val bright: Boolean get() = brightness in 60.0..200.0
    val sharp: Boolean get() = sharpness > 8.0
    val lowGlare: Boolean get() = glareRatio < 0.05
    val ok: Boolean get() = bright && sharp && lowGlare

    /** Gợi ý ngắn hiển thị cho cán bộ khi chưa đạt. */
    fun hint(): String = when {
        brightness < 60 -> "Cần sáng hơn"
        brightness > 200 || glareRatio >= 0.05 -> "Tránh loá / giảm sáng"
        sharpness <= 8.0 -> "Giữ máy yên, lấy nét"
        else -> "Giữ yên…"
    }
}

/** Đo chất lượng trên Y-plane (luma) của khung YUV từ ImageAnalysis — lấy mẫu thưa cho nhẹ. */
object QualityGate {

    fun analyze(image: ImageProxy): QualityMetrics {
        val plane = image.planes[0]                 // Y
        val buf = plane.buffer
        val rowStride = plane.rowStride
        val pixStride = plane.pixelStride
        val w = image.width
        val h = image.height
        val step = 8

        var sum = 0.0
        var count = 0
        var glare = 0
        var gradSum = 0.0
        var gradCount = 0

        var y = 0
        while (y < h) {
            var x = 0
            var prev = -1
            val base = y * rowStride
            while (x < w) {
                val luma = buf.get(base + x * pixStride).toInt() and 0xFF
                sum += luma
                count++
                if (luma > 250) glare++
                if (prev >= 0) {
                    gradSum += abs(luma - prev).toDouble()
                    gradCount++
                }
                prev = luma
                x += step
            }
            y += step
        }

        val brightness = if (count > 0) sum / count else 0.0
        val sharpness = if (gradCount > 0) gradSum / gradCount else 0.0     // ~độ nét trung bình
        val glareRatio = if (count > 0) glare.toDouble() / count else 0.0
        return QualityMetrics(brightness, sharpness, glareRatio)
    }
}
