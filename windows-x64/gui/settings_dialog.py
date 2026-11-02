# -*- coding: utf-8 -*-
"""公文格式参数设置对话框。"""
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QLineEdit,
    QDialogButtonBox, QGroupBox, QVBoxLayout, QCheckBox, QHBoxLayout,
    QWidget, QComboBox,
)

from core.formatter import GongwenSettings

BODY_FONTS = ["仿宋_GB2312", "仿宋", "FangSong", "宋体", "黑体", "楷体_GB2312"]
TITLE_FONTS = ["方正小标宋简体", "宋体", "黑体", "小标宋体"]


class SettingsDialog(QDialog):
    def __init__(self, settings: GongwenSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("公文格式参数（GB/T 9704-2012）")
        self.setMinimumWidth(420)
        self.settings = settings

        # ---- 页面 ----
        page_box = QGroupBox("页面（A4）")
        pf = QFormLayout(page_box)
        self.sp_top = QDoubleSpinBox(); self.sp_top.setRange(0.5, 6.0); self.sp_top.setSuffix(" cm")
        self.sp_bottom = QDoubleSpinBox(); self.sp_bottom.setRange(0.5, 6.0); self.sp_bottom.setSuffix(" cm")
        self.sp_left = QDoubleSpinBox(); self.sp_left.setRange(0.5, 6.0); self.sp_left.setSuffix(" cm")
        self.sp_right = QDoubleSpinBox(); self.sp_right.setRange(0.5, 6.0); self.sp_right.setSuffix(" cm")
        pf.addRow("上边距", self.sp_top)
        pf.addRow("下边距", self.sp_bottom)
        pf.addRow("左边距", self.sp_left)
        pf.addRow("右边距", self.sp_right)

        # ---- 标题与正文 ----
        font_box = QGroupBox("标题与正文")
        ff = QFormLayout(font_box)
        self.cmb_title_font = QComboBox(); self.cmb_title_font.addItems(TITLE_FONTS)
        self.cmb_title_font.setEditable(True)
        self.sp_title_size = QDoubleSpinBox(); self.sp_title_size.setRange(10, 48); self.sp_title_size.setSuffix(" pt")
        self.cmb_body_font = QComboBox(); self.cmb_body_font.addItems(BODY_FONTS)
        self.cmb_body_font.setEditable(True)
        self.sp_body_size = QDoubleSpinBox(); self.sp_body_size.setRange(9, 36); self.sp_body_size.setSuffix(" pt")
        self.sp_line = QDoubleSpinBox(); self.sp_line.setRange(12, 60); self.sp_line.setSuffix(" 磅")
        self.sp_indent = QSpinBox(); self.sp_indent.setRange(0, 8); self.sp_indent.setSuffix(" 字符")
        ff.addRow("标题字体", self.cmb_title_font)
        ff.addRow("标题字号", self.sp_title_size)
        ff.addRow("正文字体", self.cmb_body_font)
        ff.addRow("正文字号", self.sp_body_size)
        ff.addRow("行距（固定值）", self.sp_line)
        ff.addRow("首行缩进", self.sp_indent)

        # ---- 功能 ----
        func_box = QGroupBox("识别选项")
        vf = QVBoxLayout(func_box)
        self.chk_title = QCheckBox("自动识别大标题（首段短行，居中二号）")
        self.chk_heading = QCheckBox("识别层次标题（一、黑体 /（一）楷体 / 1. 仿宋加粗）")
        self.chk_sign = QCheckBox("识别落款（文末日期与单位，右对齐右空二字）")
        vf.addWidget(self.chk_title)
        vf.addWidget(self.chk_heading)
        vf.addWidget(self.chk_sign)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(page_box)
        lay.addWidget(font_box)
        lay.addWidget(func_box)
        lay.addWidget(buttons)

        self._load(settings)

    def _load(self, s: GongwenSettings):
        self.sp_top.setValue(s.margin_top)
        self.sp_bottom.setValue(s.margin_bottom)
        self.sp_left.setValue(s.margin_left)
        self.sp_right.setValue(s.margin_right)
        self.cmb_title_font.setCurrentText(s.title_font)
        self.sp_title_size.setValue(s.title_size)
        self.cmb_body_font.setCurrentText(s.body_font)
        self.sp_body_size.setValue(s.body_size)
        self.sp_line.setValue(s.line_spacing)
        self.sp_indent.setValue(s.first_line_chars)
        self.chk_title.setChecked(s.detect_title)
        self.chk_heading.setChecked(s.detect_headings)
        self.chk_sign.setChecked(s.auto_sign)

    def apply_to(self, s: GongwenSettings):
        s.margin_top = self.sp_top.value()
        s.margin_bottom = self.sp_bottom.value()
        s.margin_left = self.sp_left.value()
        s.margin_right = self.sp_right.value()
        s.title_font = self.cmb_title_font.currentText().strip() or "方正小标宋简体"
        s.title_size = self.sp_title_size.value()
        s.body_font = self.cmb_body_font.currentText().strip() or "仿宋_GB2312"
        s.body_size = self.sp_body_size.value()
        s.line_spacing = self.sp_line.value()
        s.first_line_chars = self.sp_indent.value()
        s.detect_title = self.chk_title.isChecked()
        s.detect_headings = self.chk_heading.isChecked()
        s.auto_sign = self.chk_sign.isChecked()
