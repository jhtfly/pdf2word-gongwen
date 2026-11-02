# -*- coding: utf-8 -*-
"""OCR 引擎：RapidOCR 处理图片型（扫描版）PDF。

流程：PyMuPDF 高分辨率渲染页面 → RapidOCR 识别文本行 →
按 y 坐标聚类成段 → 构建简单 docx。
"""
import os

import fitz
import numpy as np


class OcrEngine:
    """惰性加载的 RapidOCR 封装（首次调用才初始化模型）。"""

    def __init__(self, zoom=200 / 72):
        self._engine = None
        self.zoom = zoom

    def _get_engine(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    def recognize_pdf(self, pdf_path, progress_cb=None):
        """识别整个 PDF，返回 [(page_no, [行文本]), ...]。"""
        engine = self._get_engine()
        doc = fitz.open(pdf_path)
        pages = []
        for pno in range(len(doc)):
            page = doc[pno]
            lines = self._ocr_page(page, engine)
            pages.append((pno, lines))
            if progress_cb:
                progress_cb(pno + 1, len(doc))
        doc.close()
        return pages

    def _ocr_page(self, page, engine):
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            img = img[:, :, :3]
        result, _ = engine(img)
        if not result:
            return []
        # result: [ [box(4点), text, score], ... ]
        items = []
        heights = []
        for box, text, _score in result:
            ys = [pt[1] for pt in box]
            xs = [pt[0] for pt in box]
            items.append((min(ys), min(xs), text))
            heights.append(max(ys) - min(ys))
        items.sort(key=lambda t: (t[0], t[1]))
        med_h = float(np.median(heights)) if heights else 20.0

        # y 聚类成行
        lines, cur, cur_y = [], [], None
        for y, x, text in items:
            if cur_y is None or abs(y - cur_y) <= med_h * 0.6:
                cur.append((x, text))
                if cur_y is None:
                    cur_y = y
            else:
                cur.sort()
                lines.append("".join(t for _, t in cur))
                cur, cur_y = [(x, text)], y
        if cur:
            cur.sort()
            lines.append("".join(t for _, t in cur))
        return lines

    @staticmethod
    def build_docx(pages, docx_path):
        """将识别结果构建 docx。"""
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_BREAK

        doc = Document()
        for idx, (pno, lines) in enumerate(pages):
            if idx > 0:
                doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            if not lines:
                p = doc.add_paragraph(f"（第 {pno + 1} 页未识别到文字）")
                p.runs[0].font.size = Pt(12)
                continue
            for ln in lines:
                doc.add_paragraph(ln)
        doc.save(docx_path)


def is_scanned_pdf(pdf_path, min_chars_per_page=6):
    """判断 PDF 是否为图片型（扫描版）。

    规则：每页平均可提取文字极少，且页面含图片对象。
    """
    import fitz

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        raise ValueError(f"无法打开 PDF：{pdf_path}")
    page_count = len(doc)
    if page_count == 0:
        doc.close()
        raise ValueError("PDF 页数为 0，可能是损坏文件")

    total_chars, has_image = 0, False
    for page in doc:
        total_chars += len(page.get_text("text").strip())
        if len(page.get_images(full=True)) > 0:
            has_image = True
    doc.close()
    avg = total_chars / max(page_count, 1)
    return avg < min_chars_per_page and has_image, avg
