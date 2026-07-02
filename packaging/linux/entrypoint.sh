#!/bin/sh
# Entrypoint Docker: tự sinh API key nếu chưa đặt (tương đương init-config.ps1 bên Windows),
# rồi chạy uvicorn. Cấu hình qua BIẾN MÔI TRƯỜNG (DIP_*) — không cần file .env trong container.
set -e

if [ -z "$DIP_API_KEY" ]; then
    DIP_API_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
    export DIP_API_KEY
    echo "[vndoc] CHƯA đặt DIP_API_KEY → sinh ngẫu nhiên cho lần chạy này:"
    echo "[vndoc]   $DIP_API_KEY"
    echo "[vndoc] Nên đặt cố định qua env/compose (DIP_API_KEY=...) để client không phải đổi."
fi

if [ -z "$DIP_ALLOWED_IPS" ]; then
    echo "[vndoc] CẢNH BÁO: DIP_ALLOWED_IPS trống = CHO MỌI IP. Chỉ dùng khi test; production nên đặt dải LAN."
fi

echo "[vndoc] Khởi động :${DIP_PORT:-11001} (corner=${DIP_RECTIFY_CORNER_FALLBACK}, orient=${DIP_ORIENT_CLASSIFIER})"
exec uvicorn app.main:app --host "${DIP_HOST:-0.0.0.0}" --port "${DIP_PORT:-11001}"
