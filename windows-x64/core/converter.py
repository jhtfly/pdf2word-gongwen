# -*- coding: utf-8 -*-
"""PDF → Word 转换核心模块。

- 文本型 PDF：pdf2docx（版面分析 + 表格还原）
- 图片型（扫描版）PDF：RapidOCR 识别后构建 docx
- 转换后可选应用公文格式（formatter）
"""
import os
import traceback

from .formatter import GongwenSettings, format_docx
from .ocr_engine import OcrEngine, is_scanned_pdf

_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OcrEngine()
    return _ocr_engine


def convert_one(pdf_path, out_dir, settings: GongwenSettings, log=None):
    """转换单个 PDF，返回 (status, message, out_path)。

    status: "ok" / "scanned"（经OCR成功）/ "failed" / "skipped"
    """
    def _log(msg):
        if log:
            log(msg)

    name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(out_dir, name + ".docx")
    os.makedirs(out_dir, exist_ok=True)

    # 1. 扫描件检测
    try:
        scanned, avg_chars = is_scanned_pdf(pdf_path)
    except ValueError as e:
        return "failed", str(e), None

    try:
        if scanned:
            _log(f"[{name}] 检测为图片型PDF（均字数{avg_chars:.1f}），启用OCR识别")
            engine = get_ocr_engine()
            pages = engine.recognize_pdf(
                pdf_path,
                progress_cb=lambda done, total: _log(
                    f"[{name}] OCR进度 {done}/{total} 页"
                ),
            )
            OcrEngine.build_docx(pages, out_path)
            _log(f"[{name}] OCR识别完成，共{len(pages)}页")
        else:
            from pdf2docx import Converter

            cv = Converter(pdf_path)
            cv.convert(out_path)
            cv.close()
            _log(f"[{name}] pdf2docx 转换完成")
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
        _log(f"[{name}] 转换失败：{err}\n{traceback.format_exc(limit=3)}")
        if isinstance(e, MemoryError):
            return "failed", "内存不足，请关闭其他程序后重试", None
        return "failed", err, None

    # 2. 公文格式化
    if settings.enabled:
        ok, msg = format_docx(out_path, settings, log=log)
        if not ok:
            return "failed", f"格式化失败：{msg}", out_path

    return ("scanned" if scanned else "ok"), "转换成功", out_path
