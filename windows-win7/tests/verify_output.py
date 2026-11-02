# -*- coding: utf-8 -*-
"""校验转换产物的公文格式是否符合预期（GB/T 9704-2012 默认参数）。"""
import os
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
OUT = os.path.join(SAMPLES, "converted")

EXPECT = {
    "margins": (3.7, 3.5, 2.8, 2.6),
    "title_font": "方正小标宋简体",
    "title_size": 22.0,
    "body_font": "仿宋_GB2312",
    "body_size": 16.0,
    "line_spacing": 28.0,
    "h1_font": "黑体",
}

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def east_of(run):
    rPr = run._element.rPr
    if rPr is None:
        return None
    rf = rPr.find(qn("w:rFonts"))
    return rf.get(qn("w:eastAsia")) if rf is not None else None


def verify(path, ocr_mode=False):
    print(f"\n===== 校验 {os.path.basename(path)} =====")
    doc = Document(path)
    sec = doc.sections[0]
    m = (
        round(sec.top_margin.cm, 2),
        round(sec.bottom_margin.cm, 2),
        round(sec.left_margin.cm, 2),
        round(sec.right_margin.cm, 2),
    )
    check("页边距", m == EXPECT["margins"], f"实际={m}")

    paras = [p for p in doc.paragraphs if p.text.strip()]
    title = paras[0]
    # 正文 = 第一个非标题段落（跳过 一、/（一）/1. 开头）
    h1_re = re.compile(r"^([一二三四五六七八九十百]+\s*[、.．]|（[一二三四五六七八九十百]+）|\d+\s*[.、．])")
    body1, h1 = None, None
    # 落款占末尾 2 段，选正文时排除
    core_paras = paras[:-2] if len(paras) > 4 else paras
    for p in core_paras:
        t = p.text.strip()
        if h1 is None and t.startswith("一、"):
            h1 = p
        if body1 is None and not h1_re.match(t) and p is not title:
            body1 = p
        if body1 and h1:
            break

    check("标题居中", title.alignment == WD_ALIGN_PARAGRAPH.CENTER,
          f"对齐={title.alignment}")
    check("标题字体", east_of(title.runs[0]) == EXPECT["title_font"],
          f"实际={east_of(title.runs[0])}")
    check("标题字号", abs(title.runs[0].font.size.pt - EXPECT["title_size"]) < 0.01,
          f"实际={title.runs[0].font.size.pt if title.runs[0].font.size else None}pt")

    if body1 is not None and h1 is not None:
        check("正文字体", east_of(body1.runs[0]) == EXPECT["body_font"],
              f"实际={east_of(body1.runs[0])}")
        check("正文字号", abs(body1.runs[0].font.size.pt - EXPECT["body_size"]) < 0.01,
              f"实际={body1.runs[0].font.size.pt if body1.runs[0].font.size else None}pt")
        check("正文两端对齐", body1.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY,
              f"对齐={body1.alignment}")
        ls = body1.paragraph_format.line_spacing
        check("行距28磅固定值",
              body1.paragraph_format.line_spacing_rule == WD_LINE_SPACING.EXACTLY
              and ls is not None and abs(ls.pt - EXPECT["line_spacing"]) < 0.01,
              f"规则={body1.paragraph_format.line_spacing_rule} 行距={ls}")
        ind = body1._p.pPr.find(qn("w:ind"))
        flc = ind.get(qn("w:firstLineChars")) if ind is not None else None
        check("首行缩进2字符", flc == "200", f"firstLineChars={flc}")
        check("一级标题黑体", east_of(h1.runs[0]) == EXPECT["h1_font"],
              f"实际={east_of(h1.runs[0])}")

    # 落款：最后一个段落应为日期且右对齐（OCR 模式下宽松处理）
    last = paras[-1]
    # 层次标题必须独立成段（防合并段回归：标题后不得直接跟正文文字）
    merged = [p.text.strip()[:20] for p in paras
              if re.match(r"^([一二三四五六七八九十百]+\s*[、.．]|（[一二三四五六七八九十百]+）)", p.text.strip())
              and len(p.text.strip()) > 25]
    check("层次标题独立成段", not merged, f"合并段={merged}")

    is_date = re.search(r"\d[\d\s]{0,6}年[\s\d]{1,6}月", last.text) is not None
    if ocr_mode:
        check("落款段落存在", len(paras) >= 2, f"末段={last.text[:20]!r}")
    else:
        check("落款日期右对齐",
              is_date and last.alignment == WD_ALIGN_PARAGRAPH.RIGHT,
              f"文本={last.text[:20]!r} 对齐={last.alignment}")

    # 表格
    if doc.tables:
        cell_p = doc.tables[0].rows[0].cells[0].paragraphs[0]
        if cell_p.runs:
            check("表格字体", east_of(cell_p.runs[0]) == EXPECT["body_font"],
                  f"实际={east_of(cell_p.runs[0])}")
            sz = cell_p.runs[0].font.size
            check("表格字号小四", sz is not None and abs(sz.pt - 12.0) < 0.01,
                  f"实际={sz.pt if sz else None}pt")


if __name__ == "__main__":
    verify(os.path.join(OUT, "sample_gongwen.docx"))
    verify(os.path.join(OUT, "sample_scanned.docx"), ocr_mode=True)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [r for r in results if not r[1]]
    print(f"\n===== 校验汇总：通过 {passed} / {len(results)} =====")
    for name, _, detail in failed:
        print(f"  FAIL: {name}  {detail}")
    sys.exit(1 if failed else 0)
