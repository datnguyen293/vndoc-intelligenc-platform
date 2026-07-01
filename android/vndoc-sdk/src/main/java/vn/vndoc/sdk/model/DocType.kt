package vn.vndoc.sdk.model

/**
 * Loại giấy tờ cán bộ CHỌN trước khi chụp → ánh xạ thẳng sang `docTypeHint` (BẮT BUỘC —
 * DEC-047/068). `cmnd`/`cccd` là HỌ: server tự nhận loại con (9/12 số, chip/2024, mặt).
 *
 * `aspectRatio` = tỉ lệ rộng/cao của khung overlay khi chụp (thẻ ID-1 ≈ 1.585; thẻ Đảng
 * viên dạng dọc; hộ chiếu gần vuông hơn).
 */
enum class DocType(val hint: String, val label: String, val aspectRatio: Float) {
    CMND("cmnd", "CMND (9/12 số)", 1.585f),
    CCCD("cccd", "CCCD / Căn cước", 1.585f),
    BHYT("bhyt", "Thẻ BHYT", 1.585f),
    HO_CHIEU("passport_vn", "Hộ chiếu", 1.42f),
    DANG_VIEN("the_dang_vien", "Thẻ Đảng viên", 0.69f),
    QUAN_NHAN("the_quan_nhan", "CM quân nhân / sĩ quan", 1.585f),
    GPLX("gplx_pet", "GPLX", 1.585f);

    companion object {
        fun fromHint(hint: String): DocType? = entries.firstOrNull { it.hint == hint }
    }
}
