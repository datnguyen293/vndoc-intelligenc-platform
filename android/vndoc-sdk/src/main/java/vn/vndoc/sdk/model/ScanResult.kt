package vn.vndoc.sdk.model

/** Kết quả một lần quét (trả về host app qua VNDocScanContract). */
sealed interface ScanResult {

    /** Bóc tách thành công. `fields` = map theo tên trường (idNumber, fullName, ...). */
    data class Success(
        val documentType: String,
        val documentTypeLabel: String?,
        val fields: Map<String, FieldValue>,
        val overallConfidence: Double,
        val warnings: List<String>,
        val rawJson: String,
    ) : ScanResult

    /** Nhận diện không chắc (unknown / confidence thấp) → nên chụp lại. */
    data class Retry(val reason: String) : ScanResult

    /** Lỗi có phân loại → hiển thị thông báo + tuỳ chọn thử lại. */
    data class Error(val kind: ErrorKind, val message: String) : ScanResult

    /** Người dùng thoát màn chụp. */
    data object Cancelled : ScanResult
}
