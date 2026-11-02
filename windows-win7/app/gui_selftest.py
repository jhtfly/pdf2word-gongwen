# -*- coding: utf-8 -*-
"""GUI 自检脚本（供分离进程运行，结果写文件）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RESULT = os.path.join(HERE, "gui_selftest_result.txt")

try:
    from PySide2.QtWidgets import QApplication

    app = QApplication([])
    from gui.main_window import MainWindow

    w = MainWindow()
    w.progress.setValue(100)
    w._on_finished("selftest")
    assert w.progress.value() == 0, "progress not reset"

    from gui.settings_dialog import SettingsDialog

    d = SettingsDialog(w.settings, w)

    from qtcompat import QIcon

    ic = QIcon(os.path.join(HERE, "app.png"))
    assert not ic.isNull(), "icon load failed"
    with open(RESULT, "w", encoding="utf-8") as f:
        f.write("OK: PySide2 GUI selftest passed (QApplication+MainWindow+SettingsDialog+Icon)")
except Exception as e:  # noqa: BLE001
    import traceback

    with open(RESULT, "w", encoding="utf-8") as f:
        f.write("FAIL: " + repr(e) + "\n" + traceback.format_exc())
