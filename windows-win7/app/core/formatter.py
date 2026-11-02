# -*- coding: utf-8 -*-
"""公文格式化模块（GB/T 9704-2012）。

将转换得到的 docx 调整为党政机关公文格式：
- 页面：A4，页边距 上3.7cm 下3.5cm 左2.8cm 右2.6cm
- 标题：二号 方正小标宋简体，居中
- 正文：三号 仿宋_GB2312，两端对齐，首行缩进2字符，行距固定值28磅
- 一级标题（一、）：黑体三号；二级标题（（一））：楷体_GB2312三号；
  三级标题（1.）：仿宋_GB2312三号加粗
- 落款：识别文末单位署名与成文日期，右对齐、右空二字
- 表格内文字：仿宋_GB2312 小四，水平居中
- 数字与英文：Times New Roman
"""
import os
import re
from dataclasses import dataclass, asdict, field

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DATE_RE = re.compile(r"\d[\d\s]{0,6}年\s*[\d\s]{1,6}月\s*[\d\s]{1,6}日\s*$")
L1_RE = re.compile(r"^[一二三四五六七八九十百]+\s*[、.．]")
L2_RE = re.compile(r"^（[一二三四五六七八九十百]+）")
L3_RE = re.compile(r"^\d+\s*[.、．]")
NUMBER_RE = re.compile(r"[\dA-Za-zＡ-Ｚａ-ｚ＄￥％+±×÷°℃‰]")


@dataclass
class GongwenSettings:
    """公文格式参数（可在界面自定义）。"""

    enabled: bool = True
    # 页面
    margin_top: float = 3.7   # cm
    margin_bottom: float = 3.5
    margin_left: float = 2.8
    margin_right: float = 2.6
    # 标题
    title_font: str = "方正小标宋简体"
    title_size: float = 22.0  # 二号
    # 正文
    body_font: str = "仿宋_GB2312"
    body_size: float = 16.0   # 三号
    line_spacing: float = 28.0  # 磅（固定值）
    first_line_chars: int = 2
    # 层次标题
    h1_font: str = "黑体"
    h2_font: str = "楷体_GB2312"
    # 落款
    auto_sign: bool = True
    sign_right_chars: int = 2
    # 表格
    table_font_size: float = 12.0  # 小四
    # 功能开关
    detect_title: bool = True
    detect_headings: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        s = cls()
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s


def _set_run_font(run, east, size, bold=False, ascii_font="Times New Roman"):
    """设置 run 字体（含中文 eastAsia 属性）。"""
    run.font.name = ascii_font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:eastAsia"), east)


def _set_first_line_chars(p, chars, size_pt):
    """首行缩进按字符数设置（w:firstLineChars，兼容性回退 twips）。"""
    pPr = p._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLineChars"), str(int(chars * 100)))
    ind.set(qn("w:firstLine"), str(int(size_pt * chars * 20)))


def _set_right_chars(p, chars, size_pt):
    pPr = p._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:rightChars"), str(int(chars * 100)))
    ind.set(qn("w:right"), str(int(size_pt * chars * 20)))
    # 清除首行缩进，避免落款参差
    if ind.get(qn("w:firstLineChars")):
        ind.set(qn("w:firstLineChars"), "0")
        ind.set(qn("w:firstLine"), "0")


def _set_exact_spacing(p, pt_value):
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(pt_value)
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)


def _all_runs(p):
    return p.runs


def _split_soft_breaks(doc):
    """把含软换行（w:br）的段落拆分为独立段落。

    pdf2docx 0.5.x（Py3.8 可用版本）常把「标题+正文」合并进同一段落，
    若不拆分，整段会被套用标题样式。仅拆分纯文本段落（含图片的不动）。
    """
    import copy

    split_count = 0
    for p in list(doc.paragraphs):
        if "\n" not in p.text:
            continue
        # 含图片等复杂内容的段落不拆
        if p._p.findall(".//" + qn("w:drawing")) or p._p.findall(
            ".//" + qn("w:pict")
        ):
            continue
        lines = p.text.split("\n")
        if len(lines) < 2:
            continue
        pPr = p._p.find(qn("w:pPr"))
        # 清空原段落内容，仅保留段落属性
        for child in list(p._p):
            if child is not pPr:
                p._p.remove(child)
        cur = p._p
        for j, line in enumerate(lines):
            if j > 0:  # 第一行留在原段落，其余新建段落
                newp = OxmlElement("w:p")
                if pPr is not None:
                    newp.append(copy.deepcopy(pPr))
                cur.addnext(newp)
                cur = newp
            if line:
                r = OxmlElement("w:r")
                t = OxmlElement("w:t")
                t.set(qn("xml:space"), "preserve")
                t.text = line
                r.append(t)
                cur.append(r)
        split_count += 1
    return split_count


def format_docx(docx_path, settings: GongwenSettings, log=None):
    """对 docx 就地应用公文格式，返回 (是否成功, 消息)。"""

    def _log(msg):
        if log:
            log(msg)

    doc = Document(docx_path)

    # ---- 预处理：拆分软换行合并段 ----
    n = _split_soft_breaks(doc)
    if n:
        _log(f"拆分软换行合并段落 {n} 个")

    # ---- 页面设置 ----
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(settings.margin_top)
        section.bottom_margin = Cm(settings.margin_bottom)
        section.left_margin = Cm(settings.margin_left)
        section.right_margin = Cm(settings.margin_right)

    paragraphs = doc.paragraphs
    # 非空段落下标
    nonempty = [i for i, p in enumerate(paragraphs) if p.text.strip()]

    title_idx = None
    if settings.detect_title and nonempty:
        # 第一个非空且较短（<=60字）的段落视为标题；跳过形如 "第X页" 的页眉残留
        for i in nonempty[:3]:
            t = paragraphs[i].text.strip()
            if len(t) <= 60 and not re.match(r"^第\s*\d+\s*页", t):
                title_idx = i
                break

    sign_idx = date_idx = None
    if settings.auto_sign and nonempty:
        # 文末倒数 5 个非空段内找成文日期；其上一短行视为单位署名
        tail = nonempty[-5:]
        for j in range(len(tail) - 1, -1, -1):
            t = paragraphs[tail[j]].text.strip()
            if DATE_RE.search(t):
                date_idx = tail[j]
                if j > 0 and len(paragraphs[tail[j - 1]].text.strip()) <= 30:
                    sign_idx = tail[j - 1]
                break

    for i, p in enumerate(paragraphs):
        text = p.text.strip()
        if not text:
            continue

        # ---- 表格不在此处理 ----
        _set_exact_spacing(p, settings.line_spacing)

        if i == title_idx:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_first_line_chars(p, 0, settings.title_size)
            for r in _all_runs(p):
                _set_run_font(r, settings.title_font, settings.title_size)
            # 标题与正文间空一行视觉间隔：段后一行
            p.paragraph_format.space_after = Pt(settings.line_spacing)
            continue

        if settings.auto_sign and i in (sign_idx, date_idx):
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            _set_right_chars(p, settings.sign_right_chars, settings.body_size)
            for r in _all_runs(p):
                _set_run_font(r, settings.body_font, settings.body_size)
            continue

        is_h1 = is_h2 = is_h3 = False
        if settings.detect_headings:
            if L1_RE.match(text):
                is_h1 = True
            elif L2_RE.match(text):
                is_h2 = True
            elif L3_RE.match(text) and len(text) <= 40:
                is_h3 = True

        if is_h1:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _set_first_line_chars(p, settings.first_line_chars, settings.body_size)
            for r in _all_runs(p):
                _set_run_font(r, settings.h1_font, settings.body_size)
        elif is_h2:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _set_first_line_chars(p, settings.first_line_chars, settings.body_size)
            for r in _all_runs(p):
                _set_run_font(r, settings.h2_font, settings.body_size)
        elif is_h3:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _set_first_line_chars(p, settings.first_line_chars, settings.body_size)
            for r in _all_runs(p):
                _set_run_font(r, settings.body_font, settings.body_size, bold=True)
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _set_first_line_chars(p, settings.first_line_chars, settings.body_size)
            for r in _all_runs(p):
                _set_run_font(r, settings.body_font, settings.body_size)

    # ---- 表格 ----
    for table in doc.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    pf = p.paragraph_format
                    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
                    pf.first_line_indent = Pt(0)
                    for r in _all_runs(p):
                        _set_run_font(
                            r, settings.body_font, settings.table_font_size
                        )

    try:
        doc.save(docx_path)
    except PermissionError:
        return False, "文件被占用（可能在 Word/WPS 中打开），请关闭后重试"
    _log(f"公文格式化完成：{os.path.basename(docx_path)}")
    return True, "ok"
