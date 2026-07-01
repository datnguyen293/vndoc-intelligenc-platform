package vn.vndoc.sdk.config

/** Cấu hình OCR service nội bộ (DOC-09 §9). */
data class ServerConfig(
    val host: String,
    val port: Int = 11001,
    val apiKey: String = "",
) {
    val baseUrl: String get() = "http://$host:$port"

    fun isValid(): Boolean = host.isNotBlank() && port in 1..65535
}
