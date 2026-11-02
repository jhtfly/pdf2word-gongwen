# -*- coding: utf-8 -*-
"""Qt 绑定兼容层（Win7 版专用）。

本版本固定使用 PySide2（Qt 5.15.2，最后支持 Win7 的 Qt 绑定），
统一对外提供 PyQt6 风格的常用名称，业务代码无需关心绑定差异。
"""
from PySide2.QtCore import QThread, Qt, QUrl, Signal as pyqtSignal  # noqa: F401
from PySide2.QtGui import QDesktopServices, QIcon  # noqa: F401
from PySide2.QtWidgets import (  # noqa: F401
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QApplication,
)
