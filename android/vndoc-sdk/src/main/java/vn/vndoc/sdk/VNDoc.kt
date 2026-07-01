package vn.vndoc.sdk

import android.content.Context
import vn.vndoc.sdk.config.ConfigStore
import vn.vndoc.sdk.config.ServerConfig

/**
 * Điểm vào SDK. Host app:
 *   1) VNDoc.configure(context, ServerConfig(host, port, apiKey))   // màn Settings, 1 lần
 *   2) đăng ký VNDocScanContract → launcher.launch(DocType.CCCD)     // nhận ScanResult
 */
object VNDoc {

    @Volatile
    private var cached: ServerConfig? = null

    /** Lưu cấu hình server (mã hoá). Gọi từ màn Settings sau khi admin nhập. */
    fun configure(context: Context, config: ServerConfig) {
        cached = config
        ConfigStore(context).save(config)
    }

    /** Cấu hình hiện tại (từ cache hoặc EncryptedSharedPreferences). */
    fun currentConfig(context: Context): ServerConfig? =
        cached ?: ConfigStore(context).load()?.also { cached = it }

    fun isConfigured(context: Context): Boolean = currentConfig(context)?.isValid() == true

    fun clearConfig(context: Context) {
        cached = null
        ConfigStore(context).clear()
    }
}
