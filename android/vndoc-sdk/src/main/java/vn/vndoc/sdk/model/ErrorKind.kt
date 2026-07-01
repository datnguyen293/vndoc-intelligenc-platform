package vn.vndoc.sdk.model

/** Phân loại lỗi để host app hiển thị thông báo thân thiện (DOC-09 §8). */
enum class ErrorKind {
    UNAUTHORIZED,        // 401 — sai/thiếu API key
    FORBIDDEN_IP,        // 403 — IP thiết bị ngoài whitelist (DEC-087)
    BAD_REQUEST,         // 400 — thiếu/sai docTypeHint (lỗi lập trình)
    QUALITY_LOW,         // 422 — ảnh quá kém
    PAYLOAD_TOO_LARGE,   // 413 — ảnh vượt giới hạn
    TOO_BUSY,            // 429 — server quá tải
    NETWORK,             // timeout / mất kết nối
    SERVER,              // 5xx / phản hồi không hợp lệ
}
