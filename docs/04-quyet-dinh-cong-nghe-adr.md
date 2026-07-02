# DOC-04 — Quyết định công nghệ (ADR)

- **Trạng thái:** DRAFT
- **Phiên bản:** 0.1
- **Phụ thuộc:** DOC-03

Tài liệu này khóa các quyết định công nghệ dưới dạng Architecture Decision Record.
Mỗi ADR gồm: bối cảnh, quyết định, lý do, hệ quả, phương án đã loại.

---

## ADR-001 — Ngôn ngữ & framework service: Python + FastAPI

- **Bối cảnh:** Cần một service REST trên Windows, hệ sinh thái OCR/ML mạnh, làm nhanh.
- **Quyết định:** Dùng **Python 3.11+** với **FastAPI** (ASGI, chạy bằng Uvicorn).
- **Lý do:**
  - Hệ sinh thái ML/CV tốt nhất: OpenCV, PaddleOCR, VietOCR, ONNX Runtime, OpenVINO,
    pyzbar/zxing (QR/barcode), passporteye/mrz (MRZ).
  - FastAPI: async, validate request bằng Pydantic, sinh OpenAPI tự động.
- **Hệ quả:** Đóng gói thành Windows Service qua NSSM hoặc pywin32 (xem DOC-10).
  Cần quản lý môi trường Python (venv/conda) khi triển khai.
- **Đã loại:**
  - *C#/.NET*: native Windows tốt nhưng hệ OCR tiếng Việt yếu, tốn công tích hợp.
  - *Hybrid .NET + Python*: linh hoạt nhưng phức tạp vận hành, chưa cần ở V1.

---

## ADR-002 — Chiến lược tính toán: CPU-first, không dùng GPU rời

- **Bối cảnh:** Phần cứng tham chiếu có CPU **i7-14700 (20 nhân/28 luồng)** rất mạnh,
  nhưng GPU rời là **AMD Radeon RX 6300 chỉ 2 GB GDDR6** (yếu, không hỗ trợ CUDA).
- **Quyết định:** Thiết kế **CPU-only**. Mọi mục tiêu hiệu năng đo trên CPU. GPU rời
  AMD **không** dùng cho inference. Có thể cân nhắc iGPU Intel UHD 770 qua OpenVINO
  như tối ưu tùy chọn về sau, không bắt buộc.
- **Lý do:**
  - 2 GB VRAM quá nhỏ và không có CUDA → lợi ích GPU không đáng tin cậy.
  - i7-14700 đủ mạnh để đạt < 500 ms khi kết hợp ROI-template + structured-data-first.
  - CPU-only giúp hệ thống bền vững khi đổi cấu hình máy.
- **Hệ quả:** Phải tối ưu kỹ phần CPU (xem ADR-003, ADR-005). Dùng runtime tối ưu CPU.
- **Đã loại:** *CUDA* (không phải NVIDIA), *DirectML trên RX 6300* (2 GB không đủ ổn định).

---

## ADR-003 — Runtime inference: OpenVINO (chính) + ONNX Runtime

- **Bối cảnh:** Cần inference CPU nhanh trên Intel i7-14700; model đến từ nhiều nguồn
  (PaddleOCR, VietOCR).
- **Quyết định:** Export model về **ONNX**, chạy bằng **OpenVINO** (tối ưu cho CPU
  Intel) làm runtime chính; **ONNX Runtime (CPU EP)** làm phương án dự phòng/đối chiếu.
- **Lý do:**
  - OpenVINO tối ưu sâu cho CPU Intel (AVX-512, luồng), thường nhanh hơn ONNX-CPU
    thuần trên phần cứng Intel.
  - ONNX là định dạng trung gian chung → không khóa cứng vào một engine.
- **Hệ quả:** Có bước build pipeline export PaddleOCR/VietOCR → ONNX → (tùy chọn) IR
  OpenVINO. Cần kiểm chứng độ chính xác sau khi convert (FP32; cân nhắc INT8 nếu cần
  thêm tốc độ).
- **Đã loại:** *PyTorch eager / PaddlePaddle native* khi serving (chậm hơn, nặng hơn
  cho production CPU).

---

## ADR-004 — OCR engine: PaddleOCR (detection) + VietOCR (recognition)

- **Bối cảnh:** Cần OCR tiếng Việt **có dấu** chính xác cao, tốc độ tốt trên CPU.
- **Quyết định:** Dùng **PaddleOCR** cho **text detection** (định vị dòng chữ) và
  **VietOCR** (mô hình transformer/seq2seq chuyên tiếng Việt) cho **recognition**.
- **Lý do:**
  - VietOCR được huấn luyện riêng cho tiếng Việt → xử lý dấu thanh tốt hơn model OCR
    đa ngữ tổng quát.
  - PaddleOCR detection (DB) nhẹ, nhanh, ổn định để khoanh vùng dòng chữ.
  - Vì bóc tách theo ROI cố định, recognition chỉ chạy trên vùng nhỏ → nhanh.
- **Hệ quả:** Hai model phải cùng export ONNX/OpenVINO. Cần benchmark recognition
  transformer trên CPU; nếu chậm, cân nhắc bản VietOCR seq2seq nhẹ hoặc batching ROI.
- **Đã loại:**
  - *Tesseract (vie)*: độ chính xác trên thẻ/dấu kém hơn.
  - *PaddleOCR recognition thuần*: cần fine-tune nặng cho tiếng Việt mới bằng VietOCR.
  - *Vision LLM cục bộ*: quá nặng cho 16 GB RAM / CPU và mục tiêu 500 ms.

---

## ADR-005 — Bóc tách theo ROI template, không OCR cả trang

- **Bối cảnh:** Layout các giấy tờ là **cố định**; OCR cả trang vừa chậm vừa dễ nhầm.
- **Quyết định:** Sau khi nắn về template chuẩn, OCR **chỉ trên các ROI** khai báo
  trong plugin (toạ độ tương đối). Mỗi ROI tương ứng một trường.
- **Lý do:** Giảm khối lượng recognition → đạt 500 ms; tăng độ chính xác vì biết
  trước ngữ cảnh từng vùng (áp dictionary/regex phù hợp).
- **Hệ quả:** Phụ thuộc chất lượng rectification + định nghĩa ROI đúng. Cần margin
  ROI và cơ chế dò lệch nhỏ (anchor) để bền với sai số nắn ảnh.
- **Đã loại:** *Full-page free OCR rồi parse theo heuristic* (chậm, dễ sai trường).

---

## ADR-006 — Structured-data-first: ưu tiên QR / MRZ / barcode

- **Bối cảnh:** Nhiều giấy tờ VN có sẵn dữ liệu máy đọc chính xác cao.
- **Quyết định:** Trước khi OCR, đọc **QR** (CCCD gắn chip — QR nằm ở **góc trên
  phải mặt trước**), **MRZ** (hộ chiếu — trang nhân thân), **mã thẻ BHYT**, **QR
  GPLX** (tuỳ bản). Kết quả từ vùng máy đọc là **nguồn ưu tiên**; OCR chỉ bù trường
  còn thiếu hoặc để cross-check.
  - Lưu ý: CCCD mã vạch (đời cũ) có barcode ở **mặt sau** → vì V1 chỉ xử lý mặt
    trước nên loại này **không** có nguồn máy đọc, bóc tách thuần bằng OCR.
- **Lý do:** QR/MRZ chính xác gần tuyệt đối, có checksum (MRZ), đọc rất nhanh (vài ms),
  giảm tải OCR.
- **Hệ quả:** Cần thư viện đọc QR/barcode (pyzbar/zxing/OpenCV) và parser MRZ (chuẩn
  TD3) + parser QR CCCD (định dạng các trường ngăn cách bằng `|`).
- **Đã loại:** *OCR thuần bỏ qua QR/MRZ* (chậm hơn, dễ sai số định danh hơn).

---

## ADR-007 — Phát hiện giấy tờ: classical CV trước, ML fallback

- **Bối cảnh:** Ảnh chụp có căn khung, nền thường tương phản với thẻ.
- **Quyết định:** Dùng **OpenCV classical** (grayscale → blur → edge/threshold →
  contour → tứ giác lớn nhất → perspective warp). Nếu thất bại (nền phức tạp), fallback
  một model **segmentation nhẹ**.
- **Lý do:** Classical CV nhanh (<~20 ms), không cần model, đủ tốt khi đã căn khung.
- **Hệ quả:** Cần ngưỡng và heuristic tốt; client hỗ trợ bằng khung căn (DOC-09).
- **Hiện thực:** dùng **package `rectifier`** (project riêng, thuần OpenCV offline,
  cài `pip install -e ../rectifier`) qua preset `id_card`; segmenter **pluggable**:
  `classic` (OpenCV, mặc định, có GrabCut fallback) hoặc `yolo` (YOLOv11-seg, tuỳ chọn,
  weights cục bộ). Pipeline: segment → polygon → corner refine → perspective → rotate →
  pad → deskew → CLAHE → sharpen. Tích hợp tại `app/cv/build_preprocessors`.
- **Đã loại:** *Luôn dùng segmentation model* (thừa, tốn thời gian cho ảnh dễ).

---

## ADR-008 — Phân loại giấy tờ: thuần luật (rule-based), không train

- **Bối cảnh:** Chỉ ~10 loại, mỗi loại có tiêu đề/dấu hiệu rất khác nhau. Ràng buộc
  không-train (ADR-012) → không dùng model phân loại cần dữ liệu huấn luyện.
- **Quyết định:** Phân loại bằng **luật trên tín hiệu cứng**: cụm chữ tiêu đề (anchor
  text qua OCR nhanh) như "CĂN CƯỚC CÔNG DÂN", "CHỨNG MINH NHÂN DÂN", "GIẤY PHÉP LÁI
  XE", "THẺ BẢO HIỂM Y TẾ", "HỘ CHIẾU/PASSPORT", "THẺ ĐẢNG VIÊN", "THẺ QUÂN NHÂN";
  kết hợp dấu hiệu phụ: có QR/MRZ?, tỉ lệ khung, số chữ số định danh (9 vs 12).
- **Lý do:** số loại ít và đủ khác biệt để luật phân biệt chính xác; không cần dữ liệu train.
- **Hệ quả:** Mỗi plugin khai bảng anchor/luật trong khối `classify`. Trả `unknown`
  khi không khớp anchor nào đạt ngưỡng.
- **Đã loại:** *CNN phân loại* (cần dữ liệu train — vi phạm ADR-012).

---

## ADR-009 — Cơ chế plugin: manifest YAML, nạp động

- **Bối cảnh:** Thêm loại giấy tờ không được sửa core (FR-017).
- **Quyết định:** Mỗi loại giấy tờ là một plugin gồm **manifest YAML** (ROI map,
  field mapping, validation rule, normalization, dictionary) + (tuỳ chọn) hook xử lý
  riêng. Plugin Manager nạp động từ thư mục `/plugins` theo `DOC-TYPE`.
- **Lý do:** YAML dễ đọc/sửa cho người vận hành, comment được; phần lớn loại giấy tờ
  chỉ cần khai báo, không cần code.
- **Hệ quả:** Cần định nghĩa schema manifest chặt và validate khi load (DOC-05).
- **Đã loại:** *Hardcode trong core* (vi phạm FR-017), *plugin bằng code thuần* (cao
  rào với người vận hành; vẫn cho phép hook nâng cao).

---

## ADR-010 — Concurrency: warm model pool + bounded workers

- **Bối cảnh:** Phải phục vụ nhiều request đồng thời mà giữ < 500 ms (FR-019, NFR-001).
- **Quyết định:** Một process giữ **model warm** (nạp một lần). Giới hạn số request
  OCR đồng thời bằng một **semaphore/queue** theo số luồng CPU để tránh tranh chấp
  làm tăng latency. API async, phần inference chạy trong thread/worker pool.
- **Lý do:** Nạp model mỗi request là quá chậm; chạy quá nhiều inference song song
  trên CPU làm chậm tất cả. Bounded concurrency giữ latency ổn định.
- **Hệ quả:** Cần cấu hình `max_concurrency`, hàng đợi, timeout. Đo P50/P95 ở DOC-10.
- **Đã loại:** *Tạo process/model mỗi request*, *không giới hạn song song* (vỡ latency).

---

## ADR-011 — Đóng gói triển khai: Windows Service

- **Bối cảnh:** Cần chạy nền ổn định, tự bật khi máy khởi động, offline.
- **Quyết định:** Đóng gói service Python chạy như **Windows Service** (NSSM khuyến
  nghị; hoặc pywin32). Model/plugin/config tách thư mục riêng. Có script cài đặt.
- **Lý do:** Vận hành như dịch vụ hệ thống, tự khởi động lại khi lỗi (NFR-002).
- **Hệ quả:** Tài liệu cài đặt + cấu hình ở DOC-10. Cân nhắc đóng gói môi trường
  Python (embeddable/conda) để cài trên máy không có Internet.
- **Đã loại:** *Chạy tay bằng terminal* (không bền cho production).

---

## ADR-012 — Ràng buộc không-train: chỉ pre-trained + luật

- **Bối cảnh:** Đơn vị **không có tập dữ liệu gán nhãn** để huấn luyện model riêng.
- **Quyết định:** V1 **không train/fine-tune** bất kỳ model nào. Chỉ dùng:
  - Model **pre-trained** tải sẵn: PaddleOCR text detection, VietOCR recognition,
    (tuỳ chọn) PaddleOCR angle classifier để chuẩn hóa hướng ảnh.
  - **Luật khai báo** trong plugin: anchor phân loại, nhãn (label-anchored), regex,
    dictionary, chuẩn hóa.
  - **Ảnh mẫu thật chỉ để HIỆU CHỈNH** nhãn/regex/ngưỡng/ROI — **không** để train.
- **Lý do:** Loại bỏ rào cản dữ liệu mà vẫn đạt độ chính xác nhờ structured-data
  (QR/MRZ) + label-anchored + cross-check + dictionary.
- **Hệ quả:** Mọi loại giấy tờ phải bóc tách được bằng pre-trained + luật. Nếu sau
  này có dữ liệu, fine-tune OCR là **tùy chọn nâng cấp**, không bắt buộc ở V1.
- **Đã loại:** *Train CNN phân loại*, *fine-tune OCR* như điều kiện bắt buộc của V1.

### Sửa đổi 2026-07-02 (Amended) — cho phép MODEL PHỤ TRỢ train offline

Thực tế vận hành cho thấy ảnh chụp từ người dùng (thẻ nhỏ/nền nhiễu/xoay bất kỳ) làm khâu
**tiền xử lý** (nắn ảnh + xác định hướng) kém, kéo tốc độ 6-10s. Vì **nhãn cho các tác vụ này
tự sinh được** (không cần gán tay), ta **nới ADR-012** như sau:

- **VẪN không-train phần lõi:** recognition (VietOCR pre-trained) và phân loại loại giấy tờ
  ([[ADR-008]] thuần luật) — giữ nguyên, đây mới là chỗ thiếu dữ liệu.
- **CHO PHÉP model phụ trợ nhẹ, train OFFLINE, nhãn tự sinh**, chạy **ONNX/CPU** (ADR-002),
  làm **fallback/tăng tốc** chứ không thay lõi:
  - **Corner-detector** (YOLOv8-pose→ONNX): 4 góc thẻ để nắn ảnh nhỏ/nghiêng; nhãn từ
    **tổng hợp homography** + gán vài chục ảnh thật. Là fallback của rectifier classic.
  - **Orientation classifier** (MobileNetV3-small→ONNX): đoán hướng 0/90/180/270; nhãn tự
    sinh bằng **distillation** (OCR-search hiện có tự gán chiều upright). Là fast-path của
    `OrientingOcr`, vẫn giữ OCR-search làm fallback.
- **Ràng buộc kèm theo:** model phụ trợ (a) chỉ infer ONNX/CPU offline; (b) luôn có đường
  fallback không-model để không giảm độ chính xác; (c) weights gitignored + bundle qua
  `build.ps1`; (d) mặc định TẮT ở dev, bật qua config khi giao hàng.
- **Bước 3 roadmap (chưa làm):** bộ đọc SỐ chuyên dụng (CCCD/CMND/quân nhân) — cũng thuộc
  diện "model phụ trợ nhãn tự sinh" này, sẽ áp cùng ràng buộc.

---

## Bảng tổng hợp

| ADR | Quyết định | Trạng thái |
|---|---|---|
| ADR-001 | Python + FastAPI | Accepted |
| ADR-002 | CPU-first, bỏ GPU rời | Accepted |
| ADR-003 | OpenVINO + ONNX Runtime | Accepted |
| ADR-004 | PaddleOCR det + VietOCR rec | Accepted |
| ADR-005 | ROI template, không OCR cả trang | Accepted |
| ADR-006 | Structured-data-first (QR/MRZ/barcode) | Accepted |
| ADR-007 | Classical CV detect + ML fallback | Accepted |
| ADR-008 | Phân loại: thuần luật (rule-based), không train | Accepted |
| ADR-009 | Plugin manifest YAML, nạp động | Accepted |
| ADR-010 | Warm pool + bounded concurrency | Accepted |
| ADR-011 | Đóng gói Windows Service | Accepted |
| ADR-012 | Không-train phần LÕI (recognition + phân loại); cho phép model PHỤ TRỢ train offline (nắn góc, đoán hướng) | Accepted (sửa đổi 2026-07-02) |
