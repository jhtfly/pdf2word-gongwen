# -*- coding: utf-8 -*-
"""端到端测试：批量转换 3 个样例 PDF（文本型/扫描型/损坏）→ 校验公文格式。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.converter import convert_one
from core.formatter import GongwenSettings

SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
OUT = os.path.join(SAMPLES, "converted")


def run():
    logs = []
    s = GongwenSettings()  # 默认 GB/T 9704 参数
    files = [
        "sample_gongwen.pdf",
        "sample_scanned.pdf",
        "sample_broken.pdf",
    ]
    results = {}
    for f in files:
        status, msg, out = convert_one(
            os.path.join(SAMPLES, f), OUT, s, log=lambda m: logs.append(m)
        )
        print(f"[{f}] status={status} msg={msg}")
        results[f] = (status, out)
    print("---日志尾部---")
    for line in logs[-6:]:
        print(" ", line)
    return results


if __name__ == "__main__":
    run()
