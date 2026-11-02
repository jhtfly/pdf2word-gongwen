# -*- coding: utf-8 -*-
"""PDF 转 Word 公文格式转换器 —— 程序入口。

双击运行：图形界面（PyQt6）
命令行模式：PDF转Word公文版.exe [--out 输出目录] [--no-gongwen] 文件1.pdf 文件2.pdf ...
"""
import os
import sys


def run_cli(argv):
    """命令行批量转换（无界面），日志写入输出目录的 转换日志.txt。"""
    import argparse

    from core.converter import convert_one
    from core.formatter import GongwenSettings
    from core.worker import load_settings, save_settings

    parser = argparse.ArgumentParser(description="PDF 批量转 Word（公文格式）")
    parser.add_argument("pdfs", nargs="+", help="PDF 文件路径")
    parser.add_argument("--out", default="", help="输出目录（默认源文件旁 converted）")
    parser.add_argument("--no-gongwen", action="store_true", help="不应用公文格式")
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.no_gongwen:
        settings.enabled = False
    out_dir = args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.pdfs[0])), "converted"
    )
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(out_dir, "转换日志.txt")
    log_f = open(log_path, "a", encoding="utf-8")

    def log(msg):
        log_f.write(msg + "\n")
        log_f.flush()

    ok = failed = 0
    for pdf in args.pdfs:
        status, msg, _out = convert_one(
            os.path.abspath(pdf), out_dir, settings, log=log
        )
        if status in ("ok", "scanned"):
            ok += 1
        else:
            failed += 1
        log(f"== {os.path.basename(pdf)}: {status} | {msg}")
    log(f"== 汇总: 成功{ok} 失败{failed}")
    log_f.close()
    save_settings(settings)


def run_gui():
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from gui.main_window import MainWindow

    # 打包后资源位于 _MEIPASS 临时解压目录
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base, "app.ico")

    app = QApplication(sys.argv)
    app.setApplicationName("PDF转Word公文格式转换器")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # 带参数 → 命令行模式；无参数 → 图形界面
    if len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help") and \
            not sys.argv[1].startswith("-") or \
            (len(sys.argv) > 1 and sys.argv[1] in ("--out", "--no-gongwen")):
        run_cli(sys.argv[1:])
    elif len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        run_cli(["-h"])
    else:
        run_gui()
