package vn.vndoc.sdk.model

/** Một trường bóc tách (khớp DOC-07). `source`: qr | mrz | structured | ocr. */
data class FieldValue(
    val value: String?,
    val confidence: Double,
    val source: String,
)
