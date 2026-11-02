#!/bin/bash
# 生成桌面快捷方式（UKUI / 银河麒麟 V10）
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi
set -u
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

# 桌面目录（UKUI 为 ~/桌面，兼容 ~/Desktop）
DESKTOP_DIR="$HOME/桌面"
[ -d "$DESKTOP_DIR" ] || DESKTOP_DIR="$HOME/Desktop"
mkdir -p "$DESKTOP_DIR"

DESK_FILE="$DESKTOP_DIR/PDF转Word公文版.desktop"
cat > "$DESK_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=PDF转Word公文版
Name[zh_CN]=PDF转Word公文版
Comment=PDF 批量转 Word 并应用公文格式（GB/T 9704-2012）
Exec=bash "$SCRIPT_DIR/启动.sh"
Icon="$SCRIPT_DIR/app/app.png"
Terminal=false
Categories=Office;WordProcessor;
StartupNotify=true
EOF
chmod +x "$DESK_FILE" "$SCRIPT_DIR/启动.sh"

# UKUI/GNOME 首次启动需信任快捷方式
command -v gio >/dev/null 2>&1 && gio set "$DESK_FILE" metadata::trusted true 2>/dev/null

echo "桌面快捷方式已生成：$DESK_FILE"
echo "如双击提示'不信任的程序'，右键该图标 → 允许启动/信任。"
read -r -p "按回车键关闭…" _dummy
