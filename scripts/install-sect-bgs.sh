#!/bin/bash
# 一键安装 5 派背景图
#
# 用法:
#   1. 在 Claude 对话里,**按顺序**右键每张图 → "Save image as..."(或复制到剪贴板用 Preview 粘贴)
#      顺序:1=天机阁  2=玄机宗  3=青冥派  4=月隐宫  5=沧澜剑派
#      存到任何位置(默认 ~/Downloads/),文件名随便,只要是 PNG
#   2. cd /Users/bobdong/项目/LingshuCodex && bash scripts/install-sect-bgs.sh [来源目录]
#      默认扫描 ~/Downloads/ 里最近 30 分钟新建的 PNG
#   3. 浏览器 Cmd+Shift+R 刷新

set -e

SRC="${1:-$HOME/Downloads}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/frontend/public/images"
WINDOW_MIN=30  # 只看最近 N 分钟的 PNG

# 按上传顺序 → 对应宗门(用户回贴顺序)
SECTS=(tianji xuanji qingming yueyin canglan)
SECT_LABELS=("天机阁" "玄机宗" "青冥派" "月隐宫" "沧澜剑派")

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎨 灵枢笔录 · 5 派背景图自动安装"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  源目录:  $SRC"
echo "  目标:    $DEST"
echo "  时间窗:  最近 ${WINDOW_MIN} 分钟"
echo ""

# 找最近的 5 个 PNG,按修改时间正序(早保存的在前 = 第一张图)
mapfile -t IMAGES < <(
  find "$SRC" -maxdepth 2 -name "*.png" -type f -mmin -${WINDOW_MIN} 2>/dev/null \
    | xargs -I {} stat -f '%m %N' {} 2>/dev/null \
    | sort -n \
    | awk '{$1=""; print substr($0,2)}'
)

if [ ${#IMAGES[@]} -lt 5 ]; then
  echo "❌ 在 $SRC 只找到 ${#IMAGES[@]} 张最近 ${WINDOW_MIN} 分钟内的 PNG,需要 5 张"
  echo ""
  if [ ${#IMAGES[@]} -gt 0 ]; then
    echo "已检测到:"
    for img in "${IMAGES[@]}"; do
      echo "  · $img"
    done
  fi
  echo ""
  echo "请确认:"
  echo "  1. 5 张图都另存到了 $SRC"
  echo "  2. 都是 PNG 格式"
  echo "  3. 是最近 ${WINDOW_MIN} 分钟内新增的"
  echo "  或者跑:   bash $0 /你/图片/所在/目录"
  exit 1
fi

# 取前 5 个(按时间正序)
echo "✓ 找到 ${#IMAGES[@]} 张候选,使用最早 5 张:"
echo ""
for i in 0 1 2 3 4; do
  src="${IMAGES[$i]}"
  sect="${SECTS[$i]}"
  label="${SECT_LABELS[$i]}"
  dest="$DEST/sect-bg-${sect}.png"
  size=$(du -h "$src" | cut -f1)
  echo "  [$((i+1))] ${label} ←  $(basename "$src")  (${size})"
  cp -f "$src" "$dest"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 已安装到 $DEST"
ls -la "$DEST"/sect-bg-*.png | awk '{print "    " $NF "  " $5 " bytes"}'
echo ""
echo "👉 现在去浏览器按 Cmd+Shift+R 强刷,5 派背景就出来了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
