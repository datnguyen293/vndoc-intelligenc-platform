# DOC-10 — Triển khai & Hiệu năng

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-03, DOC-06
- **Truy vết:** NFR-001, NFR-002, NFR-007, NFR-008, FR-016, FR-019

## 1. Mô hình triển khai

```text
Windows host (offline, LAN)
├── OCR Service (Python, FastAPI + Uvicorn)  ──> chạy như Windows Service (NSSM)
│   ├── 1 process, giữ Model Runtime Pool warm (OpenVINO, CPU)
│   ├── Plugin Registry (nạp warm lúc startup)
│   └── HTTP :8080
├── /models      (PaddleOCR-DB detect, VietOCR recognize, angle cls — ONNX/IR)
├── /plugins     (manifest YAML + dictionary + hooks)
├── /config      (app config: ports, concurrency, ngưỡng, API key)
└── /logs        (log xoay vòng, đã mask dữ liệu nhạy cảm)
```

## 2. Đóng gói & cài đặt (offline)

- Môi trường Python đóng gói sẵn (embeddable Python hoặc conda-pack) để cài trên máy
  **không có Internet**; kèm toàn bộ wheel phụ thuộc.
- Đăng ký Windows Service bằng **NSSM** (khuyến nghị) hoặc pywin32:
  - tự khởi động cùng máy, tự restart khi crash (NFR-002).
- Script cài đặt: tạo service, trỏ thư mục models/plugins/config, mở port nội bộ.
- Phiên bản hóa: service version + plugin version (xem API-004).

## 3. Concurrency model (ADR-010)

```text
FastAPI (async) nhận request
   → hàng đợi giới hạn (bounded queue)
   → semaphore: tối đa N inference đồng thời (N theo số luồng CPU vật lý)
   → thread/worker pool chạy OCR (giải phóng event loop)
   → trả JSON
```

- **Một** process, model nạp **một lần** (warm), chia sẻ cho mọi request.
- `max_concurrency` (N) cấu hình được; khởi điểm N = số P-core (vd 8 trên i7-14700),
  để vài E-core lo I/O. Quá N → request xếp hàng; hàng đợi đầy → `429 too_busy`.
- Lý do giới hạn: chạy quá nhiều inference song song trên CPU làm **tăng latency
  từng request** → vỡ mục tiêu 500 ms. Bounded concurrency giữ P95 ổn định.
- Mỗi request có **timeout** (vd 3 s) để không treo tài nguyên.

## 4. Ngân sách & mục tiêu hiệu năng

| Chỉ số | Mục tiêu |
|---|---|
| Latency trung bình (ảnh đạt chất lượng) | < 500 ms (NFR-001) |
| Latency P95 | < 800 ms |
| CCCD gắn chip đọc được QR | thường < 250 ms (ít OCR) |
| RAM tiến trình (warm) | < 4 GB (NFR-008) |
| Throughput tham chiếu | ≥ 8–12 ảnh/giây ở N=8 (phụ thuộc OCR) — cần benchmark |

Phân rã thời gian: xem DOC-06 §4.

## 5. Tối ưu hiệu năng (checklist)

- [ ] Export model → ONNX → **OpenVINO IR**; chạy CPU EP tối ưu (AVX-512).
- [ ] Warm model lúc startup (chạy 1 ảnh nóng máy trước khi nhận traffic).
- [ ] **Batch recognition** nhiều ROI trong một lần gọi VietOCR.
- [ ] OCR chỉ trên ROI; structured-data-first để bỏ OCR khi có QR/MRZ.
- [ ] Resize ảnh hợp lý trước detection (cạnh dài ~1280).
- [ ] Cân nhắc **INT8 quantization** nếu cần thêm tốc độ (kiểm chứng độ chính xác).
- [ ] Đặt số luồng OpenVINO/OMP khớp `max_concurrency` để tránh tranh chấp.
- [ ] Tránh copy ảnh thừa giữa các stage (truyền tham chiếu trong ProcessingContext).

## 6. Logging & metrics (NFR-007)

- Mỗi request log: `requestId`, `documentType`, `processingTimeMs`, các mốc
  `timings`, số warning/error. **Mask** `idNumber`/`cardNumber`/`serviceNumber`
  (chỉ giữ vài ký tự cuối).
- **Không** log toàn văn họ tên/địa chỉ ở mức INFO; chỉ ghi khi DEBUG bật có chủ đích.
- Metrics: latency P50/P95, throughput, tỉ lệ `unknown`, tỉ lệ reject chất lượng,
  queue depth. Phơi qua `/health` và/hoặc file metrics cục bộ.
- Log **xoay vòng** theo dung lượng/thời gian; không lưu ảnh trong log.

## 7. Bảo mật triển khai (NFR-007)

- Service chỉ lắng nghe trên interface nội bộ; tường lửa chặn truy cập ngoài.
- **Mặc định không lưu ảnh gốc ra đĩa**; xử lý trong RAM. Nếu bật lưu để debug →
  thư mục có hạn ngạch + tự xóa theo thời gian, ghi rõ rủi ro.
- API key chia sẻ + (khuyến nghị) HTTPS nội bộ chứng chỉ tự ký.
- Phân quyền thư mục `/logs`, `/config` (chứa key) chặt.
- Dữ liệu thẻ quân nhân/đảng viên: tuân thủ DEC-053 (mask, hạn chế lưu).

## 8. Vận hành

- Khởi động/cài đặt: script tạo Windows Service; kiểm tra `/health` sau khi chạy.
- Cập nhật plugin: thả thư mục plugin mới vào `/plugins`, restart service (hoặc
  reload nếu hỗ trợ) — **không** sửa core (NFR-003, NFR-004).
- Backup cấu hình & plugin; không backup ảnh (không lưu).
- Giám sát: theo dõi `/health`, dung lượng log, tỉ lệ lỗi.

## 8b. Số đo thực nghiệm (máy dev — KHÔNG phải máy đích)

Đo trên thẻ Đảng viên thật, backend VietOCR (RapidOCR-det + VietOCR-rec), CPU máy dev
(Apple Silicon, Python 3.9). Response có trường `timings` (ms/stage) để đo trực tiếp.

| Stage | Ảnh thẳng (ms) | Ghi chú |
|---|---|---|
| detect (OpenCV) | ~20 | tìm khung thẻ |
| rectify (warp+resize) | ~5 | |
| **ocr** | **~740** | **chiếm ~95%** — detection ~336 + recognition(batch) ~442 |
| classify | ~0.5 | thuần luật |
| extract | ~4 | |
| **Tổng** | **~770** | ảnh xoay: ~2300 (orientation thử 4 chiều) |

Đã tối ưu cấu trúc: **batch recognition** (giảm ~20% rec so với gọi từng dòng),
**cắt khung + resize 1100px** (giảm vùng OCR), **orientation thích ứng** (ảnh thẳng OCR 1 lần).

**Đòn bẩy còn lại để đạt < 500 ms (làm trên máy đích):**
1. **Export VietOCR + det → ONNX/OpenVINO** (ADR-003): nhanh hơn torch/onnx hiện tại trên CPU Intel.
2. **Máy đích i7-14700 (20 nhân)** mạnh hơn máy dev rõ rệt cho cả det lẫn rec.
3. **Giảm độ phân giải detection** (det_limit_side_len) — det đang ~336 ms.
4. **Angle classifier rẻ** thay cho OCR 4 lần ở ảnh xoay (giảm case xoay từ ~2300 ms).
5. **OCR theo ROI** cho loại layout cứng (roi_fixed) thay vì cả trang.

## 9. Kế hoạch kiểm thử hiệu năng (đầu giai đoạn code)

- Bộ ảnh mẫu chuẩn cho từng loại (đạt/kém chất lượng).
- Đo latency từng stage (DOC-06 §4) để tìm nút thắt.
- Đo P50/P95 ở các mức `max_concurrency` để chốt N tối ưu.
- So sánh OpenVINO vs ONNX-CPU; FP32 vs INT8 (độ chính xác vs tốc độ).

## 10. Quyết định khóa
| ID | Quyết định |
|---|---|
| DEC-070 | Một process, model warm, bounded concurrency theo số P-core |
| DEC-071 | Đóng gói Windows Service (NSSM), môi trường Python offline |
| DEC-072 | Log mask dữ liệu định danh; không lưu ảnh ra đĩa mặc định |
| DEC-073 | Cập nhật/ thêm plugin không cần build lại core |
