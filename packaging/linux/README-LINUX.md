# VNDoc OCR — chạy trên Linux/Ubuntu (Docker)

Bản Windows (Inno EXE + NSSM) ở `packaging/`. Đây là bản **Linux/Docker** tương đương —
service FastAPI y hệt, chỉ khác lớp đóng gói. **CPU-only** (ADR-002), tự chứa (bundle model).

## Yêu cầu
- Docker Engine + Docker Compose plugin (`docker compose version`).
- Weights offline có sẵn tại `service/models/` trên máy build: `vgg_seq2seq.pth`,
  `corner.onnx`, `orientation.onnx` (đều gitignored — copy từ máy Windows/backup sang trước khi build).

## Build & chạy (Compose — khuyến nghị)
```bash
cd packaging/linux
cp .env.example .env          # rồi sửa: đặt DIP_API_KEY, DIP_ALLOWED_IPS (dải LAN)
docker compose up -d --build  # build ~vài phút (torch CPU ~200MB), ảnh ~1.5-2GB
docker compose logs -f        # xem log khởi động (VietOCR + corner + orient "sẵn sàng")
curl -fsS http://127.0.0.1:11001/api/v1/health
```

## Build & chạy (Docker thuần, không Compose)
```bash
# TỪ GỐC REPO (context = .), vì Dockerfile COPY service/, rectifier/, models
docker build -f packaging/linux/Dockerfile -t vndoc-ocr:0.1.0 .
docker run -d --name vndoc-ocr -p 11001:11001 \
    -e DIP_API_KEY=$(openssl rand -hex 32) \
    -e DIP_ALLOWED_IPS=192.168.1.0/24 \
    --restart unless-stopped vndoc-ocr:0.1.0
```

## Cấu hình (qua BIẾN MÔI TRƯỜNG, tiền tố DIP_)
| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `DIP_API_KEY` | Khoá client gửi header `X-API-Key`. Trống → entrypoint tự sinh mỗi lần chạy (in ra log). | (sinh ngẫu nhiên) |
| `DIP_ALLOWED_IPS` | Whitelist CIDR (phẩy ngăn). Trống = mọi IP (chỉ test). | (trống) |
| `DIP_OCR_THREADS` / `DIP_MAX_CONCURRENCY` | Luồng torch / request song song. | 8 / 8 |
| `DIP_RECTIFY_CORNER_FALLBACK` / `DIP_ORIENT_CLASSIFIER` | Model phụ trợ (đã bundle). | true / true |

Đổi cấu hình → `docker compose up -d` lại (hoặc `docker restart vndoc-ocr`).

## Gọi thử
```bash
curl -X POST http://<IP-host>:11001/api/v1/extract \
    -H "X-API-Key: <DIP_API_KEY>" \
    -F "image=@the.jpg" -F "docTypeHint=cccd_2024_front"
```
Android CÙNG LAN gọi `http://<IP-host>:11001` (service bind 0.0.0.0; nhớ mở firewall host + đặt
`DIP_ALLOWED_IPS` khớp subnet). Có thể thêm `-F assumeUpright=true` khi app đã xoay ảnh đúng chiều.

## Vì sao port dễ (so với Windows)
Code service OS-agnostic; chỉ lớp đóng gói khác: **NSSM→Docker/systemd**, **Inno EXE→image**,
**PowerShell→entrypoint.sh**. Điểm khác DUY NHẤT đáng lưu ý: trên Linux `torch` mặc định là bản
CUDA (nặng) → `requirements-linux.txt` lấy `torch==2.6.0+cpu` từ CPU index của PyTorch.

## Không dùng Docker? (systemd + venv)
```bash
python3.11 -m venv /opt/vndoc/venv && /opt/vndoc/venv/bin/pip install -r packaging/linux/requirements-linux.txt
# copy service/app, service/plugins, service/models, rectifier/rectifier vào /opt/vndoc
# tạo unit systemd chạy: uvicorn app.main:app --host 0.0.0.0 --port 11001  (WorkingDirectory=/opt/vndoc, PYTHONPATH=/opt/vndoc)
```
