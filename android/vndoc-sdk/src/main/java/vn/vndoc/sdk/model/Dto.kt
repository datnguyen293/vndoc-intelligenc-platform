package vn.vndoc.sdk.model

import kotlinx.serialization.Serializable

/** DTO parse JSON phản hồi API (DOC-07). Bỏ qua field lạ để bền với thay đổi phụ. */
@Serializable
data class ExtractResponseDto(
    val requestId: String? = null,
    val documentType: String? = null,
    val documentTypeLabel: String? = null,
    val classificationConfidence: Double = 0.0,
    val fields: Map<String, FieldValueDto> = emptyMap(),
    val overallConfidence: Double = 0.0,
    val structuredDataUsed: List<String> = emptyList(),
    val warnings: List<String> = emptyList(),
    val errors: List<String> = emptyList(),
)

@Serializable
data class FieldValueDto(
    val value: String? = null,
    val confidence: Double = 0.0,
    val source: String = "ocr",
    val raw: String? = null,
)

@Serializable
data class HealthDto(
    val status: String = "",
    val modelsWarm: Boolean = false,
    val uptimeSec: Int = 0,
    val queueDepth: Int = 0,
)

/** Body lỗi chuẩn của API: {"detail": {"code": "...", "message": "..."}}. */
@Serializable
data class ErrorBodyDto(val detail: ErrorDetailDto? = null)

@Serializable
data class ErrorDetailDto(val code: String = "", val message: String = "")
