package vn.vndoc.sdk.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import vn.vndoc.sdk.config.ServerConfig
import vn.vndoc.sdk.model.ErrorKind
import vn.vndoc.sdk.model.ExtractResponseDto
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Kết quả tầng mạng (VNDoc map tiếp sang ScanResult). */
sealed interface ApiResult {
    data class Ok(val body: ExtractResponseDto) : ApiResult
    data class Fail(val kind: ErrorKind, val message: String) : ApiResult
}

/** Client gọi OCR service (DOC-07). Chỉ HTTP nội bộ (DEC-067). */
class OcrClient(private val config: ServerConfig) {

    private val http = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .callTimeout(15, TimeUnit.SECONDS)
        .build()

    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true }

    /** GET /health — dùng cho nút "Kiểm tra kết nối" ở màn Settings. */
    suspend fun health(): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            http.newCall(req("/api/v1/health").get().build()).execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }

    /** POST /api/v1/extract (multipart) → ApiResult. */
    suspend fun extract(jpeg: ByteArray, hint: String): ApiResult = withContext(Dispatchers.IO) {
        val body = MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart("image", "capture.jpg", jpeg.toRequestBody(JPEG))
            .addFormDataPart("docTypeHint", hint)
            .addFormDataPart("returnImage", "none")
            .build()
        try {
            http.newCall(req("/api/v1/extract").post(body).build()).execute().use { resp ->
                val text = resp.body?.string().orEmpty()
                if (resp.isSuccessful) {
                    ApiResult.Ok(json.decodeFromString(ExtractResponseDto.serializer(), text))
                } else {
                    ApiResult.Fail(mapCode(resp.code), message(resp.code))
                }
            }
        } catch (e: IOException) {
            ApiResult.Fail(ErrorKind.NETWORK, e.message ?: "Không kết nối được server")
        } catch (e: Exception) {
            ApiResult.Fail(ErrorKind.SERVER, e.message ?: "Phản hồi không hợp lệ")
        }
    }

    private fun req(path: String): Request.Builder =
        Request.Builder().url(config.baseUrl + path).apply {
            if (config.apiKey.isNotBlank()) header("X-API-Key", config.apiKey)
        }

    private fun mapCode(code: Int): ErrorKind = when (code) {
        401 -> ErrorKind.UNAUTHORIZED
        403 -> ErrorKind.FORBIDDEN_IP
        400 -> ErrorKind.BAD_REQUEST
        413 -> ErrorKind.PAYLOAD_TOO_LARGE
        422 -> ErrorKind.QUALITY_LOW
        429 -> ErrorKind.TOO_BUSY
        else -> ErrorKind.SERVER
    }

    private fun message(code: Int): String = when (mapCode(code)) {
        ErrorKind.UNAUTHORIZED -> "Sai hoặc thiếu API key — kiểm tra cấu hình."
        ErrorKind.FORBIDDEN_IP -> "IP thiết bị chưa được cấp phép — báo quản trị viên."
        ErrorKind.BAD_REQUEST -> "Yêu cầu không hợp lệ (thiếu loại giấy tờ)."
        ErrorKind.PAYLOAD_TOO_LARGE -> "Ảnh quá lớn."
        ErrorKind.QUALITY_LOW -> "Ảnh quá kém, hãy chụp lại."
        ErrorKind.TOO_BUSY -> "Server đang bận, thử lại sau giây lát."
        else -> "Lỗi server ($code)."
    }

    private companion object {
        val JPEG = "image/jpeg".toMediaType()
    }
}
