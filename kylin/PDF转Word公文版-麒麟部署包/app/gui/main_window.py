# -*- coding: utf-8 -*-
"""主窗口：PDF 批量转 Word（公文格式）。"""
import os
import subprocess

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QAbstractItemView, QTreeWidgetItem, QPushButton, QFileDialog,
    QProgressBar, QCheckBox, QLabel, QMessageBox, QHeaderView, QLineEdit,
)

from core.formatter import GongwenSettings
from core.worker import BatchWorker, load_settings, save_settings
from gui.settings_dialog import SettingsDialog

COL_FILE, COL_SIZE, COL_STATUS = 0, 1, 2


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 转 Word 公文格式转换器")
        self.resize(760, 560)
        self.setAcceptDrops(True)

        self.settings: GongwenSettings = load_settings()
        self.worker: BatchWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)

        # ---- 按钮行 ----
        btn_lay = QHBoxLayout()
        self.btn_add = QPushButton("添加 PDF")
        self.btn_remove = QPushButton("移除选中")
        self.btn_clear = QPushButton("清空列表")
        for b in (self.btn_add, self.btn_remove, self.btn_clear):
            btn_lay.addWidget(b)
        btn_lay.addStretch()
        lay.addLayout(btn_lay)

        # ---- 文件列表 ----
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["文件名", "大小", "状态"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.tree)

        # ---- 输出目录 ----
        out_lay = QHBoxLayout()
        out_lay.addWidget(QLabel("输出目录:"))
        self.ed_out = QLineEdit()
        self.ed_out.setPlaceholderText("默认：源文件所在目录下的 converted 文件夹")
        out_lay.addWidget(self.ed_out)
        self.btn_browse = QPushButton("浏览…")
        out_lay.addWidget(self.btn_browse)
        lay.addLayout(out_lay)

        # ---- 格式选项 ----
        opt_lay = QHBoxLayout()
        self.chk_gongwen = QCheckBox("转换后应用公文格式（GB/T 9704-2012）")
        self.chk_gongwen.setChecked(self.settings.enabled)
        self.btn_settings = QPushButton("格式参数设置…")
        opt_lay.addWidget(self.chk_gongwen)
        opt_lay.addWidget(self.btn_settings)
        opt_lay.addStretch()
        lay.addLayout(opt_lay)

        # ---- 进度 ----
        self.progress = QProgressBar()
        lay.addWidget(self.progress)
        self.lbl_status = QLabel("就绪")
        lay.addWidget(self.lbl_status)

        # ---- 操作行 ----
        act_lay = QHBoxLayout()
        self.btn_start = QPushButton("开始转换")
        self.btn_start.setMinimumHeight(34)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setEnabled(False)
        self.btn_open_dir = QPushButton("打开输出目录")
        act_lay.addWidget(self.btn_start)
        act_lay.addWidget(self.btn_cancel)
        act_lay.addWidget(self.btn_open_dir)
        act_lay.addStretch()
        lay.addLayout(act_lay)

        # ---- 信号 ----
        self.btn_add.clicked.connect(self.add_files)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.tree.clear)
        self.btn_browse.clicked.connect(self.browse_out)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_start.clicked.connect(self.start_convert)
        self.btn_cancel.clicked.connect(self.cancel_convert)
        self.btn_open_dir.clicked.connect(self.open_out_dir)

    # ---------- 文件管理 ----------
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 PDF 文件", "", "PDF 文件 (*.pdf)"
        )
        for f in files:
            self._add_item(f)

    def _add_item(self, path):
        for i in range(self.tree.topLevelItemCount()):
            if self.tree.topLevelItem(i).data(COL_FILE, Qt.ItemDataRole.UserRole) == path:
                return
        item = QTreeWidgetItem(
            [os.path.basename(path), self._fmt_size(path), "待转换"]
        )
        item.setData(COL_FILE, Qt.ItemDataRole.UserRole, path)
        item.setToolTip(COL_FILE, path)
        self.tree.addTopLevelItem(item)

    @staticmethod
    def _fmt_size(path):
        try:
            n = os.path.getsize(path)
            for unit in ("B", "KB", "MB", "GB"):
                if n < 1024:
                    return f"{n:.1f} {unit}"
                n /= 1024
            return f"{n:.1f} TB"
        except OSError:
            return "-"

    def remove_selected(self):
        for item in self.tree.selectedItems():
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

    def browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.ed_out.setText(d)

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            dlg.apply_to(self.settings)
            self.settings.enabled = self.chk_gongwen.isChecked()
            save_settings(self.settings)

    # ---------- 拖拽 ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(".pdf"):
                self._add_item(p)

    # ---------- 转换 ----------
    def start_convert(self):
        total = self.tree.topLevelItemCount()
        if total == 0:
            QMessageBox.information(self, "提示", "请先添加 PDF 文件（支持拖拽）")
            return
        files = [
            self.tree.topLevelItem(i).data(COL_FILE, Qt.ItemDataRole.UserRole)
            for i in range(total)
        ]
        out_dir = self.ed_out.text().strip() or os.path.join(
            os.path.dirname(files[0]), "converted"
        )
        self.settings.enabled = self.chk_gongwen.isChecked()

        for i in range(total):
            self.tree.topLevelItem(i).setText(COL_STATUS, "转换中…")
        self.progress.setValue(0)
        self.progress.setMaximum(total)
        self._set_busy(True)
        self.lbl_status.setText("正在转换…")

        self.worker = BatchWorker(files, out_dir, self.settings)
        self.worker.file_status.connect(self._on_file_status)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log_line.connect(self._log)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.start()

    def cancel_convert(self):
        if self.worker:
            self.worker.cancel()
            self.lbl_status.setText("正在取消…")

    def _on_file_status(self, index, status, msg):
        item = self.tree.topLevelItem(index)
        if not item:
            return
        if status == "ok":
            item.setText(COL_STATUS, "✔ " + msg)
        elif status == "failed":
            item.setText(COL_STATUS, "✘ " + msg)
            item.setToolTip(COL_STATUS, msg)
        elif status == "cancelled":
            item.setText(COL_STATUS, "已取消")

    def _on_finished(self, summary):
        self._set_busy(False)
        self.progress.setValue(0)  # 复位进度条，状态栏显示汇总结果
        self.lbl_status.setText(summary)
        self.worker = None

    def _set_busy(self, busy):
        self.btn_start.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        self.btn_add.setEnabled(not busy)

    def _log(self, line):
        self.lbl_status.setText(line)

    def open_out_dir(self):
        out = self.ed_out.text().strip()
        if not out:
            total = self.tree.topLevelItemCount()
            if total:
                first = self.tree.topLevelItem(0).data(
                    COL_FILE, Qt.ItemDataRole.UserRole
                )
                out = os.path.join(os.path.dirname(first), "converted")
            else:
                out = os.getcwd()
        os.makedirs(out, exist_ok=True)
        if os.name == "nt":
            os.startfile(out)  # noqa: S606
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(out))
