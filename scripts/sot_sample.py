#!/usr/bin/env python
"""SSoT 方向采样：设计方向不由我挑，由「模型生成的随机字符串 + Sum-Mod」决定。

做法照 Sakana《String Seed of Thought》(arXiv 2510.21150) 的 DAG 用法：
  (1) 随机字符串必须由模型自己写出来（不要脚本生成，这是方法的要点）；
  (2) 脚本只对该串做 Rolling Hash（每轴换一个 seed）逐轴取一个选项 → 决策级联。
同一个串 + 同一份选项表 → 结果可复现。要换方向就换一个串。
组合成立不成立、能不能落到真实前端代码，由人复核；不成立就换串重抽。

用法：
  python ~/.config/opencode/skills/genimg/scripts/sot_sample.py --string '7qXk4VobWu3P'
  加 --show 打印全部选项表（改方向池时用）。
"""

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")

AXES = [
    ("骨架 layout", [
        ("时间带：整屏以一条水平时间带为主轴，所有区块按同一时间轴对齐",
         "a single horizontal time band runs across the whole body and every block on the screen is aligned to that same time axis"),
        ("编辑式双栏：左 55% 无框大字读数区，右 45% 密集小数据",
         "the left 55 percent of the body is one borderless editorial reading area holding an oversized figure, and the right 45 percent is a dense narrow column of small muted data"),
        ("连续流水：没有卡片，整页是一条账簿流水，分组只靠缩进与一条细线",
         "there are no cards at all: the page is one continuous ledger flow where grouping comes only from indentation and one hairline rule"),
        ("两栏对照：左「本月」右「上月」，逐行同高对齐比较",
         "two columns in strict row-by-row comparison, this month on the left and last month on the right, each row exactly the same height as its counterpart"),
        ("单物焦点：一次只讲一件事，顶部标签切换",
         "only one subject is shown at a time, switched by a tab strip at the top, and only the active subject's data is drawn"),
        ("侧栏即读数：导航栏本身带金额与提醒，主区刻意窄",
         "the left rail itself carries money figures and reminders, and the main column beside it is deliberately narrow"),
        ("尺度阶梯：一大两中四小，块尺寸按优先级递减",
         "one large block, two medium blocks and four small blocks, block size stepping down exactly with information priority"),
        ("表格优先：整屏就是一张可分组表格 + 顶部一条汇总带",
         "the whole body is one grouped table with a single summary strip above it and no dashboard blocks at all"),
    ]),
    ("层级 focus", [
        ("巨大数字，其余全部压小压灰",
         "one oversized figure carries the page and everything else is rendered small, low contrast and muted"),
        ("编号与标尺线建立顺序（01 02 03）",
         "tiny numerals 01, 02, 03 and short ruler ticks carry the reading order instead of containers"),
        ("留白即分组，没有任何容器",
         "no containers at all, whitespace alone does the grouping"),
        ("基线网格外露，元素都坐在基线上",
         "a faint baseline grid is left visible across the body and every element sits on it"),
        ("每区用一个超大分类首字母做标记",
         "each block is marked by one oversized initial letter drawn at its top-left corner"),
        ("深浅反转：主体是深色块，其余保持浅色底",
         "one large inverted dark panel on an otherwise light page carries the focus"),
        ("区块标题竖排小字，读数横排大字",
         "section titles are set vertically as small type along the left edge of each block while figures stay horizontal and large"),
        ("一条贯穿全页的合计主线作为骨架",
         "one continuous horizontal total line runs through the whole page and acts as the hierarchy spine"),
    ]),
    ("图表 chart", [
        ("单一折线 + 极淡柱", "one thin line over very pale bars"),
        ("收支瀑布：逐类目累加的阶梯瀑布", "a step waterfall chart that accumulates category by category"),
        ("排行条代替任何环图", "ranked horizontal bars instead of any donut or pie"),
        ("与日历列对齐的面积图", "an area chart whose columns line up exactly with the calendar columns above it"),
        ("点阵按日，点的大小=金额", "a dot matrix with one dot per day where the dot size equals the amount spent"),
        ("每行末尾一条微型 sparkline", "a micro sparkline at the end of each table row"),
        ("一只环形仪表显示预算完成度", "one dial gauge showing how much of the budget is used"),
        ("分位条显示消费分布", "a quantile strip showing how the spending is distributed"),
    ]),
    ("色彩 palette", [
        ("石墨深灰框 + 靛蓝一点", "a graphite grey interface frame with a single indigo accent"),
        ("暖米白框 + 朱红一点", "a warm ivory interface frame with a single vermilion accent"),
        ("冷蓝灰框 + 琥珀一点", "a cool blue-grey interface frame with a single amber accent"),
        ("近黑墨绿框 + 鼠尾草绿一点", "a near-black deep green interface frame with a single sage green accent"),
        ("纯中性灰阶 + 信号红一点", "a pure neutral grey interface frame with a single signal red accent"),
        ("纸白框 + 深紫一点", "a paper white interface frame with a single deep violet accent"),
        ("冷灰框 + 电光黄一点", "a cold grey interface frame with a single electric yellow accent"),
        ("深炭框 + 暖沙一点", "a dark charcoal interface frame with a single warm sand accent"),
    ]),
    ("排印 type", [
        ("系统无衬线 + 等宽数字", "system sans-serif UI type with tabular numerals"),
        ("无衬线界面 + 衬线大数字", "sans-serif interface type with serif numerals used only for the large figures"),
        ("细字重超大数字 + 12px 极密小字", "thin-weight oversized numerals against very dense 12 pixel small type"),
        ("全页等宽，像终端", "monospaced type across the whole interface like a terminal"),
        ("高对比标题 + 常规正文", "high contrast display headings with normal body type"),
        ("中文标题用宋体，正文用无衬线", "Chinese headings set in a serif face while body text stays sans-serif"),
        ("全页小字号密集排版，没有大标题", "small dense type everywhere with no oversized headline anywhere"),
        ("表格数字 + 标签全大写小字", "tabular old-style figures with all section labels in small capitals"),
        ("明确三级字号阶：读数 44px / 区块标题 18px / 元信息 12px",
         "a strict three step type scale: page figures around 44 pixels bold, block titles around 18 pixels medium, meta labels around 12 pixels in muted grey, and the difference between the three steps is obvious"),
    ]),
    ("底层装饰 surface", [
        ("纯平无装饰", "a completely flat surface with no decoration at all"),
        ("最底层 1px 方格网", "a one pixel square grid printed only at the very bottom layer"),
        ("极淡纸张纤维", "a very faint paper fibre texture at the very bottom layer"),
        ("最底层淡色尺规刻度线", "faint ruler tick marks printed at the very bottom layer behind everything"),
        ("读数区一抹极淡色块（仅此一处）", "one pale flat colour wash behind the headline figure and nowhere else"),
        ("极淡点阵底", "a very faint dot grid at the very bottom layer"),
        ("页眉一条浅色渐变带 + 带内同心弧与点阵图案",
         "a wide soft tinted gradient band behind the header, with a pattern of concentric arcs and small dots printed inside that band only"),
        ("页面一角两枚大圆与斜切的拼色色块，压在最底层",
         "two large soft circles and one diagonally cut colour block sitting in the corners of the page, printed at the very bottom layer behind all content"),
    ]),
    ("容器 frame", [
        ("无边框无阴影，靠留白分组", "no borders and no shadows anywhere, grouping done by whitespace"),
        ("1px 细线框，无阴影", "one pixel hairline borders with no shadows at all"),
        ("实底色块分区，无描边", "flat filled tonal blocks instead of outlined cards"),
        ("硬直角，无圆角", "hard square corners, no rounded corners anywhere"),
        ("圆角只给控件，容器直角", "rounded corners only on controls, every container is square"),
        ("16-20px 圆角卡片 + 柔和分层阴影，主卡阴影更重",
         "cards with 16 to 20 pixel rounded corners and soft layered diffuse shadows, the primary card carrying a visibly deeper shadow than the rest"),
    ]),
    ("图标 icon", [
        ("每行一枚圆角彩色图标底，图标主体逐条不同",
         "each row starts with one small rounded tinted square holding one simple line icon, and every icon subject is different and matches its own row"),
        ("单色细描边图标，选中项的图标填充为强调色",
         "monochrome thin line icons only, and the icon belonging to the selected item is filled solid with the accent colour"),
        ("图标只在工具栏与区块标题旁，行内不放图标",
         "icons appear only in the toolbar and beside block titles, never inside list rows"),
        ("面性实心图标，无描边", "solid filled glyph icons with no outline strokes"),
        ("图标放在卡片右上角作辅助，尺寸很小",
         "one very small icon drawn at the top-right corner of each card as a quiet helper mark"),
        ("不用图标，用小色点与缩进识别", "no icons at all, small coloured dots and indentation do the identification"),
    ]),
]

# 组合是否成立由人来判：选项池里已排除实测的 AI 味写法（多色图标底、整片渐变装饰）。

M = 2_147_483_647


def rolling_hash(string: str, seed: int, m: int = M) -> int:
    """论文里给偏概率分布用的 Rolling Hash：h = (h*31 + ord(c)) mod M。
    这里用它是因为每轴换一个 seed，可以避免「不同轴取到同一段字符串 → 选到同号」。"""
    h = seed
    for ch in string:
        h = (h * 31 + ord(ch)) % m
    return h


def find_axis(name: str) -> int:
    for i, (axis_name, _) in enumerate(AXES):
        if axis_name.startswith(name) or name in axis_name:
            return i
    raise SystemExit(f"没有这一轴：{name}（可用：{' / '.join(a.split()[0] for a, _ in AXES)}）")


def main() -> None:
    ap = argparse.ArgumentParser(description="SSoT 设计方向采样（串由模型给，脚本只做哈希选择；用户已定的轴用 --require 锁死）")
    ap.add_argument("--string", required=True, help="模型自己生成的随机字符串")
    ap.add_argument("--require", action="append", default=[],
                    help="锁轴：「轴名=选项序号」或「轴名=序号,序号」（只在这些里选），可重复。例：--require 容器=5 --require 图标=0,3")
    ap.add_argument("--show", action="store_true", help="打印全部选项池")
    args = ap.parse_args()

    allowed: dict[int, list[int]] = {}
    for req in args.require:
        name, _, idx = req.partition("=")
        axis = find_axis(name.strip())
        allowed[axis] = [int(x) for x in idx.split(",") if x.strip() != ""]

    if args.show:
        for name, pool in AXES:
            print(f"\n== {name}")
            for i, (zh, _) in enumerate(pool):
                print(f"  {i}: {zh}")
        return

    s = args.string
    print(f"random_string = {s!r}  (len={len(s)})  映射=RollingHash(h=(h*31+ord(c)) mod 2147483647, 每轴 seed=轴序号+1)\n")
    picked = []
    for i, (name, pool) in enumerate(AXES):
        choices = allowed.get(i) or list(range(len(pool)))
        h = rolling_hash(s, i + 1, M)
        idx = choices[h % len(choices)]
        zh, en = pool[idx]
        picked.append(en)
        tag = "锁定" if i in allowed else "抽样"
        print(f"{name} [{tag}]: h={h} -> 候选 {choices} 取 {idx}")
        print(f"  -> {zh}")
        print(f"  prompt 片段: {en}\n")

    print("复核：这套组合作为整体是否成立、能不能落到真实前端代码，由人来判；"
          "不成立就换一个串重抽（同串必同结果）。")
    print("\n=== 可直接粘进各区域的英文片段（按轴顺序） ===")
    for line in picked:
        print(f"- {line}")


if __name__ == "__main__":
    main()
