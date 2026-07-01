package vn.vndoc.sdk.capture

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import androidx.camera.core.ImageProxy
import java.io.ByteArrayOutputStream
import kotlin.math.roundToInt

/** Chuyển ảnh chụp (ImageCapture JPEG) → JPEG upload: xoay đúng, cắt theo tỉ lệ khung, giảm
 *  cạnh dài, nén (DOC-09 §7, DEC-069). Cạnh dài ~2400px để thẻ có QR đọc native. */
object ImageUtils {

    fun toUploadJpeg(
        image: ImageProxy,
        cropAspect: Float,
        maxEdge: Int = 2400,
        quality: Int = 90,
    ): ByteArray {
        val raw = image.planes[0].buffer.let { b -> ByteArray(b.remaining()).also { b.get(it) } }
        var bmp = BitmapFactory.decodeByteArray(raw, 0, raw.size)

        val rot = image.imageInfo.rotationDegrees
        if (rot != 0) {
            val m = Matrix().apply { postRotate(rot.toFloat()) }
            bmp = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
        }
        bmp = centerCropToAspect(bmp, cropAspect)
        bmp = scaleDown(bmp, maxEdge)

        return ByteArrayOutputStream().use { out ->
            bmp.compress(Bitmap.CompressFormat.JPEG, quality, out)
            out.toByteArray()
        }
    }

    /** Cắt giữa theo tỉ lệ rộng/cao (xấp xỉ vùng khung overlay ~92% cạnh giới hạn). */
    private fun centerCropToAspect(src: Bitmap, aspect: Float): Bitmap {
        val fill = 0.92f
        val srcAspect = src.width.toFloat() / src.height
        val (cw, ch) = if (srcAspect > aspect) {
            // ảnh rộng hơn khung → giới hạn theo chiều cao
            val ch = (src.height * fill).roundToInt()
            (ch * aspect).roundToInt() to ch
        } else {
            val cw = (src.width * fill).roundToInt()
            cw to (cw / aspect).roundToInt()
        }
        val w = cw.coerceAtMost(src.width)
        val h = ch.coerceAtMost(src.height)
        val x = ((src.width - w) / 2).coerceAtLeast(0)
        val y = ((src.height - h) / 2).coerceAtLeast(0)
        return Bitmap.createBitmap(src, x, y, w, h)
    }

    private fun scaleDown(src: Bitmap, maxEdge: Int): Bitmap {
        val longest = maxOf(src.width, src.height)
        if (longest <= maxEdge) return src
        val scale = maxEdge.toFloat() / longest
        return Bitmap.createScaledBitmap(
            src, (src.width * scale).roundToInt(), (src.height * scale).roundToInt(), true,
        )
    }
}
