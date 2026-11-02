# -*- coding: utf-8 -*-
"""生成测试 PDF：
1. sample_gongwen.pdf —— 文本型：标题、三级层次正文、表格、落款
2. sample_scanned.pdf —— 图片型：将文本页渲染为图片插入（模拟扫描件）
3. sample_broken.pdf  —— 损坏文件（容错测试）
"""
import os
import sys

import fitz

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")

TITLE = "关于开展2026年度个人贷款业务专项检查的通知"
BODY = [
    ("h1", "一、检查范围与目标"),
    ("body", "本次专项检查覆盖辖内各银行业金融机构，重点核查上一年度个人贷款五级分类的准确性、贷款用途合规性以及贷后管理落实情况。检查工作坚持问题导向，突出风险研判，确保分类结果真实反映资产质量。"),
    ("h2", "（一）个人贷款分类核查"),
    ("body", "依据《商业银行金融资产风险分类办法》要求，逐笔核对各类监管报表之间的数据勾稽关系，重点关注逾期90天以上贷款是否全部计入不良。"),
    ("h3", "1.数据核对方式"),
    ("body", "采取非现场数据比对与现场抽样验证相结合的方式，抽样比例不低于30%。"),
    ("h2", "（二）贷后管理评估"),
    ("body", "评估各机构贷后检查、风险预警、不良处置等环节的制度执行情况。"),
    ("h1", "二、工作要求"),
    ("body", "各单位要高度重视本次专项检查，明确专人负责，按时保质完成数据报送与材料准备工作。"),
]
TABLE = [
    ["机构名称", "个人贷款余额（万元）", "不良率（%）"],
    ["甲银行", "125,600", "1.82"],
    ["乙银行", "43,200", "2.15"],
]
SIGN = "某某市某某局"
DATE = "2026年10月9日"


def make_text_pdf(path):
    doc = fitz.open()
    W, H = 595, 842  # A4 pt
    page = doc.new_page(width=W, height=H)
    y = 60
    # 标题
    rect = fitz.Rect(60, y, W - 60, y + 50)
    page.insert_textbox(rect, TITLE, fontname="china-s", fontsize=18, align=1)
    y += 70

    def para(text, indent=24, size=12):
        nonlocal y
        rect = fitz.Rect(60 + indent, y, W - 60, H - 60)
        used = page.insert_textbox(rect, text, fontname="china-s", fontsize=size)
        n_lines = max(1, int(len(text) * size / (W - 120 - indent) / size * size) )  # 粗略
        y = rect.y0 + 18 * (abs(int(used)) // max(W - 120 - indent, 1) + 2) if used >= 0 else y + 60
        # 简化：按字符数估算行数
        import math
        chars_per_line = (W - 120 - indent) / size
        n = max(1, math.ceil(len(text) / chars_per_line))
        y = rect.y0 + size * 1.6 * n

    for kind, text in BODY:
        if kind == "h1":
            para(text, 0, 13)
        elif kind == "h2":
            para(text, 0, 12)
        elif kind == "h3":
            para(text, 12, 12)
        else:
            para(text, 24, 12)

    # 表格
    y += 20
    col_w = [180, 180, 130]
    x0 = (W - sum(col_w)) / 2
    row_h = 22
    for r, row in enumerate(TABLE):
        x = x0
        for c, cell in enumerate(row):
            rect = fitz.Rect(x, y, x + col_w[c], y + row_h)
            page.draw_rect(rect, color=(0, 0, 0), width=0.8)
            page.insert_textbox(rect, cell, fontname="china-s", fontsize=10, align=1)
            x += col_w[c]
        y += row_h
    y += 40

    # 落款
    page.insert_textbox(fitz.Rect(W - 260, y, W - 60, y + 20), SIGN,
                        fontname="china-s", fontsize=12, align=1)
    page.insert_textbox(fitz.Rect(W - 260, y + 26, W - 60, y + 46), DATE,
                        fontname="china-s", fontsize=12, align=1)
    doc.save(path)
    doc.close()
    print("生成:", path)


def make_scanned_pdf(path, src):
    """把文本页渲染成图片再插入，模拟扫描件。"""
    src_doc = fitz.open(src)
    doc = fitz.open()
    for page in src_doc:
        pix = page.get_pixmap(dpi=150)
        new_page = doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, pixmap=pix)
    doc.save(path)
    doc.close()
    print("生成:", path)


def make_broken_pdf(path):
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4 this is not a valid pdf body \xff\xff garbage")
    print("生成:", path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    text_pdf = os.path.join(OUT, "sample_gongwen.pdf")
    make_text_pdf(text_pdf)
    make_scanned_pdf(os.path.join(OUT, "sample_scanned.pdf"), text_pdf)
    make_broken_pdf(os.path.join(OUT, "sample_broken.pdf"))
    print("测试PDF就绪 ->", OUT)
