#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一整张网格图切成单张，直接落到项目工作区。

典型用法（图标切图）：先生一张 N×N 的图标网格，再按格子切、缩到目标尺寸：

  # 1) 出整张：10×10 网格，纯白底，无文字标签
  python ~/.config/opencode/skills/genimg/scripts/genimg.py \
    --prompt "a 10 by 10 grid of 100 monochrome line icons on pure white, ... " \
    --size 1024x1024 --force-large --slug icon-sheet

  # 2) 切 + 缩到 32×32 + 去白底变透明，落到项目里
  python ~/.config/opencode/skills/genimg/scripts/slice.py \
    --in "C:/Files/Pictures/genimg/…_icon-sheet.png" \
    --grid 10x10 --resize 32x32 --alpha 40 --square \
    --prefix icon --out "<project>/public/icons"

只依赖 Pillow（本机 PATH 上的 python 已带）。退出码：0 成功；2 参数或图片读不了。
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # 提示怎么装，别只抛 ImportError
    print("[slice] 缺 Pillow。用 PATH 上的 python（已带 Pillow），或：python -m pip install pillow",
          file=sys.stderr)
    sys.exit(2)

EXIT_USAGE = 2

# Windows 控制台默认 cp936，中文诊断会被上层当成二进制。固定按 UTF-8 输出。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def parse_wh(text):
    normalized = str(text).strip().lower().replace("*", "x").replace("×", "x")
    parts = normalized.split("x")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError("格式应为 宽x高，例如 10x10 或 32x32（收到 %s）" % text)
    return int(parts[0]), int(parts[1])


def corner_color(img, radius=4):
    """取四角小块的主色当背景色（去背、判空格都用它）。"""
    px = img.convert("RGB").load()
    w, h = img.size
    r = max(1, min(radius, w // 2, h // 2))
    samples = []
    for x, y in ((0, 0), (w - r, 0), (0, h - r), (w - r, h - r)):
        for dx in range(r):
            for dy in range(r):
                samples.append(px[x + dx, y + dy])
    counts = {}
    for rgb in samples:
        counts[rgb] = counts.get(rgb, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def is_uniform(tile, tol=6):
    """整格几乎一个颜色 → 模型这一格没画东西（实测网格里有空位）。"""
    img = tile.convert("RGB").resize((min(16, tile.width), min(16, tile.height)))
    raw = img.tobytes()  # 不用 getdata()：Pillow 14 要移除
    lum = [sum(raw[i:i + 3]) / 3 for i in range(0, len(raw), 3)]
    mean = sum(lum) / len(lum)
    return max(abs(v - mean) for v in lum) <= tol


def make_preview(img, cols, rows, gap, path):
    """画格线出一张对照图：切之前先 1:1 看格子对不对齐，比切完再返工便宜。"""
    view = img.convert("RGB").copy()
    draw = ImageDraw.Draw(view)
    w, h = view.size
    cell_w = (w - gap * (cols - 1)) / cols
    cell_h = (h - gap * (rows - 1)) / rows
    for c in range(1, cols):
        x = int(c * cell_w + (c - 1) * gap)
        draw.line([(x - gap // 2, 0), (x - gap // 2, h)], fill=(255, 0, 0), width=2)
    for r in range(1, rows):
        y = int(r * cell_h + (r - 1) * gap)
        draw.line([(0, y - gap // 2), (w, y - gap // 2)], fill=(255, 0, 0), width=2)
    for c in range(cols):
        for r in range(rows):
            x = int(c * cell_w + c * gap)
            y = int(r * cell_h + r * gap)
            draw.text((x + 4, y + 2), "%d" % (r * cols + c + 1), fill=(255, 0, 0))
    view.save(path, "PNG")


def square_canvas(tile, color):
    """把格子里的内容按包围盒居中到正方形画布（切出来的图标尺寸才一致）。"""
    img = tile.convert("RGBA")
    bg = color
    px = img.load()
    w, h = img.size
    tol = 24
    left, top, right, bottom = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b, _a = px[x, y]
            if abs(r - bg[0]) > tol or abs(g - bg[1]) > tol or abs(b - bg[2]) > tol:
                left, top, right, bottom = min(left, x), min(top, y), max(right, x), max(bottom, y)
    if right < 0:
        return img
    crop = img.crop((left, top, right + 1, bottom + 1))
    side = max(crop.size)
    pad = max(1, int(side * 0.08))  # 留 8% 内边距，避免贴边
    canvas = Image.new("RGBA", (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
    canvas.paste(crop, ((canvas.width - crop.width) // 2, (canvas.height - crop.height) // 2), crop)
    return canvas


def main():
    parser = argparse.ArgumentParser(
        description="把整张网格图切成单张（图标切图、缩略图组、多屏概念板都用它）",
        epilog="切之前先跑 --preview 看格子对不对齐；模型有时会空几格或画歪半格，"
               "这时调 --gap / --inset 再切，比切完再返工便宜。",
    )
    parser.add_argument("--in", dest="src", required=True, help="整张图（genimg.py 的产物）")
    parser.add_argument("--grid", help="列x行，例如 10x10；与 --cell 二选一")
    parser.add_argument("--cell", help="每格 宽x高，例如 32x32；给了就按它推格子数")
    parser.add_argument("--gap", type=int, default=0, help="格子之间的留白像素，默认 0")
    parser.add_argument("--inset", type=int, default=0, help="每格向内收的像素，默认 0（画歪半格时用）")
    parser.add_argument("--resize", help="切成之后缩放到 宽x高，例如 32x32")
    parser.add_argument("--square", action="store_true",
                        help="按内容包围盒居中到正方形画布（图标尺寸才统一）")
    parser.add_argument("--alpha", type=int, metavar="TOL",
                        help="把接近背景色的像素变透明（四角取背景色），给容差如 40")
    parser.add_argument("--prefix", default="cell", help="文件名前缀，默认 cell")
    parser.add_argument("--names", help="每格的名字：逗号分隔，或一个文本文件（一行一个，按行优先）")
    parser.add_argument("--out", required=True, help="输出目录（项目工作区里的路径）")
    parser.add_argument("--preview", action="store_true",
                       help="另存一张画了格线和编号的对照图，用来 1:1 核对格子对齐")
    parser.add_argument("--no-manifest", action="store_true", help="不写 manifest.json")
    args = parser.parse_args()

    src = Path(args.src).expanduser()
    if not src.exists():
        print("[slice] 找不到图片：%s" % src, file=sys.stderr)
        return EXIT_USAGE
    img = Image.open(src)
    img.load()
    w, h = img.size

    if bool(args.grid) == bool(args.cell):
        print("[slice] --grid 与 --cell 二选一（一个说几列几行，一个说每格多大）", file=sys.stderr)
        return EXIT_USAGE
    try:
        if args.grid:
            cols, rows = parse_wh(args.grid)
            gap = args.gap
            cell_w = (w - gap * (cols - 1)) // cols
            cell_h = (h - gap * (rows - 1)) // rows
        else:
            cell_w, cell_h = parse_wh(args.cell)
            gap = args.gap
            cols = (w + gap) // (cell_w + gap)
            rows = (h + gap) // (cell_h + gap)
    except ValueError as exc:
        print("[slice] %s" % exc, file=sys.stderr)
        return EXIT_USAGE

    if cols < 1 or rows < 1 or cell_w < 1 or cell_h < 1:
        print("[slice] 格子算不出来：图 %dx%d，%s" % (w, h, args.grid or args.cell), file=sys.stderr)
        return EXIT_USAGE
    leftover_w = w - (cols * cell_w + (cols - 1) * gap)
    leftover_h = h - (rows * cell_h + (rows - 1) * gap)

    resize = parse_wh(args.resize) if args.resize else None
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    names = None
    if args.names:
        raw = Path(args.names).expanduser()
        text = raw.read_text(encoding="utf-8") if raw.exists() else args.names
        names = [n.strip() for n in text.replace(",", "\n").splitlines() if n.strip()]
        if len(names) < cols * rows:
            print("[slice] 名字只有 %d 个，格子有 %d 个，缺的按序号命名"
                  % (len(names), cols * rows), file=sys.stderr)

    bg = corner_color(img)
    if args.preview:
        preview = out_dir / "_grid-preview.png"  # 下划线开头，不会被 <prefix>-*.png 的 glob 捞到
        make_preview(img, cols, rows, gap, preview)
        print("PREVIEW=%s" % preview)

    entries = []
    empties = []
    for row in range(rows):
        for col in range(cols):
            index = row * cols + col + 1
            x = col * (cell_w + gap)
            y = row * (cell_h + gap)
            box = (x + args.inset, y + args.inset, x + cell_w - args.inset, y + cell_h - args.inset)
            if box[2] <= box[0] or box[3] <= box[1]:
                print("[slice] --inset %d 太大，格子只剩 %dx%d"
                      % (args.inset, box[2] - box[0], box[3] - box[1]), file=sys.stderr)
                return EXIT_USAGE
            tile = img.crop(box)
            empty = is_uniform(tile)
            if empty:
                empties.append(index)
            if args.alpha:
                tile = tile.convert("RGB")
                px = tile.load()
                tol = args.alpha
                rgba = Image.new("RGBA", tile.size, (0, 0, 0, 0))
                top = rgba.load()
                for ty in range(tile.height):
                    for tx in range(tile.width):
                        r, g, b = px[tx, ty]
                        if abs(r - bg[0]) <= tol and abs(g - bg[1]) <= tol and abs(b - bg[2]) <= tol:
                            top[tx, ty] = (0, 0, 0, 0)
                        else:
                            top[tx, ty] = (r, g, b, 255)
                tile = rgba
            if args.square:
                tile = square_canvas(tile, bg)
            if resize:
                tile = tile.resize(resize, Image.LANCZOS)

            name = names[index - 1] if names and index <= len(names) else "%02d" % index
            dest = out_dir / ("%s-%s.png" % (args.prefix, name))
            tile.save(dest, "PNG")
            entries.append({"index": index, "row": row, "col": col, "name": name,
                            "file": str(dest), "size": list(tile.size), "empty": empty})

    if not args.no_manifest:
        manifest = out_dir / ("%s.manifest.json" % args.prefix)
        manifest.write_text(json.dumps(
            {
                "source": str(src),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "grid": {"cols": cols, "rows": rows, "cell": [cell_w, cell_h], "gap": gap,
                         "inset": args.inset},
                "resize": list(resize) if resize else None,
                "alpha_tolerance": args.alpha,
                "square": bool(args.square),
                "tiles": entries,
            },
            ensure_ascii=False, indent=2), encoding="utf-8")
        print("MANIFEST=%s" % manifest)

    for entry in entries:
        print("OUT=%s" % entry["file"])
    print("TILES=%d  %dx%d 每格 %dx%d → %s"
          % (len(entries), cols, rows, cell_w, cell_h,
             ("%dx%d" % resize) if resize else "原尺寸"))
    if leftover_w or leftover_h:
        print("[slice] 提醒：右边余 %d px、下边余 %d px 没进任何格子。"
              "格子数或 --gap 不对就先 --preview 看一遍。" % (leftover_w, leftover_h), file=sys.stderr)
    if empties:
        print("[slice] 这几格几乎纯色，像是没画出来：%s。"
              "要么重出整张（换 seed 只重跑这一张不划算），要么调 --grid 把它们排除。"
              % ", ".join(str(i) for i in empties), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
