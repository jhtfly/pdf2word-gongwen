# -*- coding: utf-8 -*-
"""批量转换后台线程（QThread），防止界面卡死。"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qtcompat import QThread, pyqtSignal  # noqa: E402

from .converter import convert_one
from .formatter import GongwenSettings


class BatchWorker(QThread):
    """逐个转换文件，发射进度与状态信号。"""

    # (文件索引, 状态, 消息)
    file_status = pyqtSignal(int, str, str)
    # (已完成数, 总数)
    progress = pyqtSignal(int, int)
    # 日志行
    log_line = pyqtSignal(str)
    finished_all = pyqtSignal(str)  # 汇总消息

    def __init__(self, pdf_files, out_dir, settings: GongwenSettings):
        super().__init__()
        self.pdf_files = list(pdf_files)
        self.out_dir = out_dir
        self.settings = settings
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        ok = scanned = failed = 0
        total = len(self.pdf_files)
        for i, pdf in enumerate(self.pdf_files):
            if self._cancelled:
                self.file_status.emit(i, "cancelled", "已取消")
                continue
            try:
                status, msg, _out = convert_one(
                    pdf, self.out_dir, self.settings, log=self.log_line.emit
                )
                if status in ("ok", "scanned"):
                    label = "完成（OCR）" if status == "scanned" else "完成"
                    self.file_status.emit(i, "ok", label)
                    if status == "scanned":
                        scanned += 1
                    else:
                        ok += 1
                else:
                    self.file_status.emit(i, "failed", msg)
                    failed += 1
            except Exception as e:  # noqa: BLE001
                self.file_status.emit(i, "failed", f"{type(e).__name__}: {e}")
                self.log_line.emit(traceback.format_exc(limit=3))
                failed += 1
            self.progress.emit(i + 1, total)

        summary = (
            f"批量转换结束：成功 {ok + scanned} 个"
            f"（其中OCR识别 {scanned} 个），失败 {failed} 个，共 {total} 个"
        )
        self.log_line.emit(summary)
        self.finished_all.emit(summary)


def default_config_path():
    """配置文件与程序同目录（打包后可移植）。"""
    import sys

    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "config.json")


def load_settings():
    import json

    path = default_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return GongwenSettings.from_dict(json.load(f))
        except Exception:  # noqa: BLE001
            pass
    return GongwenSettings()


def save_settings(settings: GongwenSettings):
    import json

    try:
        with open(default_config_path(), "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
    except OSError:
        pass
