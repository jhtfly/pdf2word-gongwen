#!/bin/bash
# ============================================================
# PDF 转 Word 公文格式转换器 —— 银河麒麟启动脚本
# 特性：sh 自愈转 bash / 首次自动解压运行时 / 离线安装依赖 /
#       import 预检 / 启动日志 / 失败暂停显示错误
# ============================================================
# sh 自愈：双击或 sh 调用时自动转 bash 重新执行
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -u

# 切换到脚本所在目录（兼容软链接）
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$SCRIPT_DIR"

LOG="$SCRIPT_DIR/启动日志.txt"
exec > >(tee -a "$LOG") 2>&1
echo "====================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动 PDF转Word公文版（麒麟版）"
echo "目录: $SCRIPT_DIR"

fail_pause() {
  echo "====================================================="
  echo "[错误] $1"
  echo "请将本窗口内容拍照反馈。"
  read -r -p "按回车键关闭…" _dummy
  exit 1
}

# ---------- 1. 首次运行：解压免安装 Python 运行时 ----------
PY="$SCRIPT_DIR/runtime/python/bin/python3"
if [ ! -x "$PY" ]; then
  echo "[1/4] 首次运行：解压 Python 运行时（约30秒）…"
  tar -xzf "$SCRIPT_DIR/runtime/python-runtime.tar.gz" -C "$SCRIPT_DIR/runtime" \
    || fail_pause "Python 运行时解压失败，请确认 runtime/python-runtime.tar.gz 完整"
  chmod +x "$PY" || true
fi
echo "[1/4] Python 运行时就绪：$($PY -V 2>&1)"

# ---------- 2. 首次运行：离线安装依赖 ----------
NEED_INSTALL=0
"$PY" -c "import PyQt6, fitz, docx, rapidocr_onnxruntime" 2>/dev/null || NEED_INSTALL=1
if [ "$NEED_INSTALL" = "1" ]; then
  echo "[2/4] 首次运行：离线安装依赖（wheels/，约1-3分钟）…"
  "$PY" -m pip install --no-index --no-cache-dir \
    --find-links "$SCRIPT_DIR/wheels" \
    -r "$SCRIPT_DIR/requirements.txt" \
    || fail_pause "离线依赖安装失败，请确认 wheels/ 目录完整"
else
  echo "[2/4] 依赖已就绪，跳过安装"
fi

# ---------- 3. 关键依赖预检 ----------
echo "[3/4] 依赖预检…"
"$PY" - <<'PYEOF' || fail_pause "依赖预检未通过（可能是系统缺库，见部署说明.txt 常见问题）"
import sys
sys.path.insert(0, "app")
import PyQt6, fitz, docx, numpy
from rapidocr_onnxruntime import RapidOCR
print("预检通过：PyQt6 / PyMuPDF / python-docx / RapidOCR / numpy")
PYEOF

# ---------- 4. 启动图形界面 ----------
echo "[4/4] 启动图形界面…"
cd "$SCRIPT_DIR/app"
"$PY" main.py
RC=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 程序退出，返回码 $RC"
if [ "$RC" -ne 0 ] && [ "$RC" -ne 130 ]; then
  read -r -p "程序异常退出，按回车键关闭…" _dummy
fi
exit $RC
