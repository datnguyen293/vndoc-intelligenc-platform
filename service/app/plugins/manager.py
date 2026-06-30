"""PluginManager — nạp manifest YAML lúc startup (DOC-05 §3, DEC-022).

Lỗi một plugin không làm chết service: log + bỏ qua (NFR-004).
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

from .contract import Manifest

log = logging.getLogger("dip.plugins")


class PluginManager:
    def __init__(self, plugins_dir: Path) -> None:
        self.plugins_dir = Path(plugins_dir)
        self._registry: dict[str, Manifest] = {}

    def load_all(self) -> None:
        """Quét thư mục plugins/*/manifest.yaml và đăng ký theo docType."""
        self._registry.clear()
        if not self.plugins_dir.exists():
            log.warning("Thư mục plugin không tồn tại: %s", self.plugins_dir)
            return
        for manifest_path in sorted(self.plugins_dir.glob("*/manifest.yaml")):
            try:
                data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                manifest = Manifest.from_dict(data)
                self._registry[manifest.doc_type] = manifest
                log.info("Đã nạp plugin: %s (ready=%s)", manifest.doc_type, manifest.ready)
            except Exception as exc:  # noqa: BLE001 — cô lập lỗi từng plugin
                log.error("Bỏ qua plugin lỗi %s: %s", manifest_path, exc)

    def get(self, doc_type: str) -> Manifest | None:
        return self._registry.get(doc_type)

    def all(self) -> list[Manifest]:
        return list(self._registry.values())

    @property
    def count(self) -> int:
        return len(self._registry)
