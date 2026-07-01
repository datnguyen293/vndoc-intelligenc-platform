package vn.vndoc.sdk

import android.content.Context
import android.content.Intent
import androidx.activity.result.contract.ActivityResultContract
import vn.vndoc.sdk.capture.CaptureActivity
import vn.vndoc.sdk.model.DocType
import vn.vndoc.sdk.model.ScanResult

/**
 * Hợp đồng ActivityResult để host app quét giấy tờ (DOC-09 §4):
 *
 *   val scan = registerForActivityResult(VNDocScanContract()) { result -> ... }
 *   scan.launch(DocType.CCCD)
 *
 * Yêu cầu đã gọi `VNDoc.configure(context, ...)` trước.
 */
class VNDocScanContract : ActivityResultContract<DocType, ScanResult>() {

    override fun createIntent(context: Context, input: DocType): Intent =
        Intent(context, CaptureActivity::class.java)
            .putExtra(CaptureActivity.EXTRA_HINT, input.hint)

    override fun parseResult(resultCode: Int, intent: Intent?): ScanResult =
        CaptureActivity.parseResult(intent)
}
