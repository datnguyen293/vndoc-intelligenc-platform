package vn.vndoc.sdk.config

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** Lưu cấu hình server MÃ HOÁ (EncryptedSharedPreferences — DEC-066). API key nhạy cảm. */
class ConfigStore(context: Context) {

    private val prefs by lazy {
        val master = MasterKey.Builder(context.applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context.applicationContext,
            "vndoc_config",
            master,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun save(cfg: ServerConfig) {
        prefs.edit()
            .putString(KEY_HOST, cfg.host)
            .putInt(KEY_PORT, cfg.port)
            .putString(KEY_API, cfg.apiKey)
            .apply()
    }

    fun load(): ServerConfig? {
        val host = prefs.getString(KEY_HOST, null) ?: return null
        return ServerConfig(host, prefs.getInt(KEY_PORT, 11001), prefs.getString(KEY_API, "").orEmpty())
    }

    fun clear() = prefs.edit().clear().apply()

    private companion object {
        const val KEY_HOST = "host"
        const val KEY_PORT = "port"
        const val KEY_API = "apiKey"
    }
}
