# 提示词写法与各题材配方（实测）

**这节回答：某类画面怎么写才成立，以及每条结论是哪一轮测出来的。**
接口参数、耗时、计费、响应字段在 `api.md`；「这条需求该不该出图」在 `../SKILL.md` §0。
每节标题带实测日期与臂数；逐臂数据在 `C:\Files\Codes\unaserver\2026-10-30-能力边界.md`（见 unaserver 的 AGENTS.md 调查数据入口表）。

## 各类型可用性汇总（全实测；判定口径见 `../SKILL.md` §4）

**这张表说的是「画面成不成立」，不是「能不能当规格」**——要落地、要改、文案要准的界面一律先看 `../SKILL.md` §0。

| 类型 | 可用性 | 稳的地方 / 不稳的地方 |
|---|---|---|
| **后台 / 中台管理界面**（若依式列表页、树表、弹窗表单、控制台工作台） | **最稳** | 稳：多级侧栏、页签条、面包屑、搜索表单、工具栏、**七列表格五行（35 条字符串两张全对）**、状态开关与禁用态、tooltip、分页、字段级报错、多选 chips、字数计数、KPI 卡 + 折线 + 环形 + 告警 + 快捷入口 + 时间线；13px 级小字号没问题。不稳：**清单的数量与层级**（10 个二级菜单会丢项、12 项快捷会重复一项、y 轴刻度会乱序）→ **要紧的清单写 6 项以内** |
| 营销站 / 落地页 | 稳 | 稳：nav、两行大标题、正文、按钮、三特性、客户名行、底部提示；用**状态并置**表达动效/交互；单节（定价）信息密度最高。不稳：精确色值与像素值 |
| 产品界面（仪表盘、表单、日历） | 稳 | 稳：侧栏、图表、表格、选中态、刻度标签、tooltip、脚注；日历热力格/点阵格（点大小=金额这种映射也能出来）、浮动明细卡、分段控件。不稳：有序数字序列（日号、刻度）、**星期表头 7 项会画成 8 项（重复一个「四」）**；「每张卡开头一个小序号」会画到卡片两端重复 |
| 资源图（可平铺背景、静物主视觉） | 稳 | 平铺不露缝；静物类主视觉可直接用。人物/场景类照片感未验证 |
| **配色与层级（有没有主次、是不是死板）** | **靠写法，不靠换后端** | 稳：**强调色一处、占面积极小 + 彩色只来自内容 + 框架全中性 + 无边框靠留白**写进 prompt 就生效，而且只改这一段文案仍然逐字全对。**「现代设计」那一套也能执行**（2026-11-01 六页 1920×1088 实测）：16–20px 圆角 + 柔和分层阴影且主卡阴影更重、页面两角大圆 + 斜切拼色块压底层、三级字号阶（44/18/12px）、导航与逐行实心图标——同时写进一条 prompt 全部落地，文案不退化。不稳：用「多色图标底 + 整片渐变」当设计层去治 AI 味，方向相反（它是 AI 味的来源）；强调色「只染第一条」会被扩展成整列都染 |
| **画面里的设计层（插画、空状态插画、彩色图标底）** | **能写出来，且不破坏文案** | 稳：区域里点名「画什么主体 + 放在哪个位置的哪一侧」→ flat vector 插画、空状态插画、彩色图标底、彩色胶囊都出来（彩色像素占比从 0–1% 升到 16–19%）。不稳：这些词**贴到末尾完全不改画面**；**整片对角渐变会被判成 AI 味**；「每行头像各不同」这类逐项不同不成立；图标语义仍不对 |
| **移动端 App 界面 / 三屏产品概念板** | 与桌面界面同档 | 稳：竖屏布局（状态栏、卡片、五行列表、底部五个 tab）、三屏并置 + 标注、真实照片头像。不稳：**时间、金额这类有序数字**（`21:30` 会画成 `07:90`）→ 数字要紧就换付费后端，或后期贴 |
| **一整页产品**（移动端整页 / web 整页 nav→footer） | **稳** | 稳：从上到下每一区都出现（状态栏→分类栏→搜索→卡片流→底部 tab；nav→大标题→客户→特性→焦点面板→定价→footer）；**把焦点写成尺寸差就真的有焦点**（焦点块两格高、大数字巨大）。要的是竖屏 `1024x2048` / `1152x2048` + 一句整页骨架句 + 逐区列全（见 §3 的第 1b 条）。不稳：长段「设计系统锁定」会挤掉版面；抽象的「为什么这样设计」句反而让画面变差 |
| 图标集 | 只当风格参考 | 稳：统一描边、统一圆角、统一网格。不稳：语义（9/12 错位）、短标签（4 条错字）、指定行列数 |
| 头像 / 人像 / 角色（含多人群像、双人体位） | 很稳 | 稳：构图、景别、视线、表情、服装逐项、手部动作与道具、背景物、光线都能指定；13 项约束的长提示四条臂全部命中；多人群像无多余手臂/断肢。不稳：**人数控制不住**（同作业 n=2 一张 3 位、一张 4 位）；**双人交合的接触点 0/6 成立**（绕法见能力边界「双人体位」条：选天然遮挡接触点的体位，或要特写就多出候选挑） |
| 真实摄影质感 | **有条件成立** | 稳：单主体 + 逐项光学词（`documentary photograph`、35mm、光圈、颗粒）→ 可直接当主视觉（这条推翻了「真实摄影做不到」）。不稳：**产品渲染（耳机/手机）仍不行**；只写 `photograph` 常得到哑光插画；带品牌文字的 UI 卡片不行 |

## 通用写法骨架（实测配方，中英都行）

一句自然语言散文，按这个顺序写：**主体 → 姿态与镜头关系 → 服装逐项 → 道具与手部动作 → 表情与视线 →
场景物件逐项 → 光线 / 景深 / 镜头 → 末尾一句「画面里没有任何文字、字母和水印」**（不要文字时才加）。
上面那条多约束测试就是照这个顺序写的：**英文、中文各 2 张、同 seed，四条全部命中全部约束**
（13 项约束：女仆装 + 蕾丝头饰 + 荷叶边围裙 + 白丝 + 握羽毛掸子 + 捂嘴笑 + 脚底强透视 + 雕花木椅 + 橙粉玫瑰 +
金框油画 + 蕾丝窗帘 + 浅景深 + 35mm），还自动给出前景脚底的镜头虚化。中文那臂还略快（42.5 s vs 49.0 s）。

四条写法边界（都是实测）：

- **视角靠改词**：`looking over shoulder` + `bare back` → 背面 3/4；`front view, facing the camera` → 正面。没有开关。
- **尺度词不脱衣**：`sensual` / `intimate` 只改气氛；裸体要显式写 `completely naked, no trousers and no towel`。
- **否定只部分遵守**：`no body hair` 在面部/胸部成立、阴毛与腿毛仍在。Midjourney 的 `--no` / `--ar` / `--v` 本机没有对应物，
  `--ar 3:4` 等于自己选 `1152x1536`。
- **人数控制不住**：同一个作业 `n=2` 的两张，一张 3 位、一张 4 位。指定人数只能换 seed 多试（模型能力，不是参数问题）。
- **不要写 `<lora:…>`**：入口确实在 prompt 里，但现配置下 **0 生效**（`native` 开 = `0 / 448` 张量；另有基座维度墙
  1.0 的 LoRA 全不行）。**这个标签本身就是 32–34 dB 的扰动**——照抄社区提示词会让画面漂移却拿不到 LoRA 效果。

题材实测过的（别当通用能力）：写实女/男裸体（站姿、正面坐姿，手指也对）、cosplay 写真、多约束长提示、
多人群像（无多余手臂/断肢）、单人色情姿态可控、**双人体位**：几何 6/6 对但**交合处 0/6 成立**——
可用绕法是**选天然遮挡接触点的体位**（侧卧 spooning，2/2 可用）或**写交合特写**（约五成，多出候选挑）。
**图上渲染文字（中/英）也已实测通过** → 见下一节。

## 图上要放字就照这个写法（实测 2026-10-31 12:47–12:50，四臂 8 张）

**结论：要中文文字可以要，规模和英文一样。** 四臂都是 `1024x1024`、`--n 2`、固定 seed，**连着发完不穿插**
（第一臂 `gpu_policy=unload`，**第二到第四臂自动变 `keep`**，单臂 41.6 / 41.6 / 41.4 s，第一臂 47.2 s）。

| 臂 / seed | 要求渲染的内容 | 结果（各 2 张） |
|---|---|---|
| A 101 杂志封面 | 大字「山海」+ 小字「2026 秋季特刊」 | **2/2 全对**：书法体大字笔触正常，数字与中文混排正确 |
| B 202 活动海报 | 「秋日山野徒步」+「周六早上七点在山脚集合」 | **2/2 逐字全对**；一张的「周」字形畸变（能读出，算字形瑕疵不是错字） |
| C 303 通知（最严） | 「读书会通知」+ 三行小字（本周六下午两点在城市图书馆三楼 / 讲题是宋代瓷器的鉴赏 / 免费入场无需报名，共 33 字） | **2/2 三行全部逐字正确**，「鉴」「瓷」这类繁笔字也对 |
| D 404 英文对照 | `AUTUMN MOUNTAIN HIKE` + `SATURDAY 7AM AT THE FOOT OF THE HILL` | **2/2 拼写全对**，但**都被拆成两行**（我要求的是一行）→ **换行不可控** |

**写法**：

- 要渲染的字用 **`written exactly as X`** 引出来；末尾加 **`no other text anywhere, no watermark`**。
- **要几行就一行一行写**：`first line exactly …, second line exactly …`。别指望模型自己不断行。
- **字体族可以指定**（`brush calligraphy` → 书法体；`clean sans-serif` → 黑体；宋体也出得来）。不指定就随机给一种。
- **判据只能逐字对照**要求的字符串（错字 / 缺字 / 多字 / 乱码 / 行数）。**不要用 PSNR 判文字**——它只说画面像不像。
- 证据：对照图 `C:\Files\Codes\unaserver\figures\cn-text-arms.png`（四臂 2×2），
  原图 `C:\Files\Pictures\genimg\20261031-12{47,48,49,50}_*`（含同名 `.meta.json`），
  副本在 `figures/raw/cn-{a,b,c,d}-{1,2}.png`；拼图脚本 `C:\Files\Codes\unaserver\scripts\s15_cn_text.py`
  （四臂的 prompt 与 seed 写在它的 docstring 里，可逐字重跑）。

## 界面稿（UI / 设计稿）就照这个写法（实测 2026-11-01 04:2x–04:5x，九臂）

**结论：界面稿的结构（侧栏、图表、热力图、表格、控件选中态）一直是合格的，缺的是屏上的文字与数据。
把这屏的文案逐条写进 prompt，它们就逐字命中；没写的位置一定自造伪英文。**

九臂共用同一份文案表、同一个 `seed 1530101906`，**差异只可能来自写法**；对照臂 E0 不重跑
（同 prompt + 同 seed 逐字节可复现，直接从它的 `.meta.json` 读原 prompt）。E1/E3 是 E0 原文
**只换末尾「文字处理」那一段**（单变量）。判定只在 **1:1 裁块**上逐字对照。

| 臂 | 写法 | prompt 字符 | 尺寸·n·steps | 引擎秒 | 文字结果 |
|---|---|---|---|---|---|
| E0 对照 | 只点名 6 条 + 「其余是灰条无字母」+ `No gibberish text` | 1,864 | 2048×1152·1·8 | 54.0 | 引号里那 6 条对，**其余全伪英文**，刻度 `4 5 6 9 0`、金额 `¥..5%` |
| E1 | 末尾换成**逐条列出整屏文案**（清单式） | 2,711 | 2048×1152·1·8 | 61.8 | 导航 / hero / 五行交易**逐字对**；分类区丢行、重复 |
| **E2** | **按区域走帧、每区就地写该区文案**（照上游 `prompt_rewrite/prompts/system_prompt_t2i.txt` 的观察式规范） | 3,442 | 2048×1152·2·8 | 106.3 | **几乎全对**：图例、12 个月刻度、tooltip、分类五行、预算三行含 `112%` 橙色、表头四列、交易行、脚注 |
| E3 | 只给 6 条大字，其余写成「无字母的灰条、小到读不清」 | 2,026 | 2048×1152·2·8 | 103.0 | 给过的对，**没给的又变伪文字**（与 E0 同） |
| E4 | **局部放大**：只画两块面板 | 1,253 | 1536×1024·2·8 | 64.4 | **文字全对**，可读性最高 |
| E5 | = E1 原文，只把 `steps` 8→16 | 2,711 | 2048×1152·1·**16** | 97.4（sampling 86.2） | **与 E1 同级** → 步数不是开关 |
| E6 | E2 写法迁到**表单屏** | 3,225 | 2048×1152·2·8 | 110.9 | 选中态、`¥128+56` + `合计 ¥184`、月份选择器、警告文案、自动补全 `12 次`、`保存` 按下态 —— 全对 |
| E7 | E2 写法迁到**日历热力图屏** | 2,843 | 2048×1152·2·8 | 104.4 | 明细卡 `3 月 14 日` + 三行 + `合计 ¥224`、排行五行全对；**日号网格不是 1–31**：出现 `24` 三次、`38`，第二张 `1 3 10 18 13 / 13 16 10 11 18` |
| D1 / D2 | 把另两屏（深色总览、AI 问答）按 E2 写法重做 | 3,153 / 2,543 | 2048×1152·2·8 | 111.5 / 104.3 | 气泡、失败提示、回答卡三行表、数据源三行全对；**月份刻度**一张把 `10月` 留空、另一张写两遍；**四段分段控件丢了第三段** |

### 参考 prompt（照这个骨架换槽位，实测逐字命中的那份就是它生成的）

六段，按区域走帧；**屏上文案一律用引号包住原样字符串**，中文/`¥`/日期直接写。
槽位用 `<>`，不要留空段落——空段落会让模型自己填内容。

```text
The image is a wide flat screenshot of a <哪类产品> application in a <light|dark> theme,
an Apple-class product interface with white and graphite grey surfaces, one deep <强调色>
accent, hairline dividers and generous quiet margins.
The whole frame is the interface itself, edge to edge, with no monitor, no keyboard and no
desk around it; the surface is a flat matte off-white canvas with panels of pure white
lifted by barely visible soft shadows.

Down the left edge sits a narrow rail about sixty pixels wide with <n> small grey line icons
stacked vertically, the topmost one tinted <强调色> to show it is selected, each icon with a
tiny charcoal label beneath it reading in order "<导航1>" "<导航2>" "<导航3>", and the wordmark
"<产品名>" set in medium charcoal type at the very top of that rail.
Across the top band, a slim header carries the title "<标题栏文案>" in sixteen pixel medium
grey type at the left, and a plain text button "<按钮>" at the far right, with a one pixel
hairline rule running the full width beneath it.

In the upper-left of the body, a large white card holds the label "<卡片标签>" in small grey
capitals above a very large tabular figure "<大数字>" in near-black numerals roughly seventy
pixels tall, with a small upward delta "<+x.x%>" in green beside it. To its right, two smaller
cards of identical size each carry a label and a figure: "<标签2>" with "<数字2>", and
"<标签3>" with "<数字3>".
Across the middle band, a full-width chart panel is titled "<图表标题>" in dark medium weight
type at its upper-left, with two legend swatches to its right reading "<图例1>" and "<图例2>".
A single thin <强调色> line rises and falls across <4–8 之间取一个数> positions above a series
of pale grey bars; beneath the plot, <同一个数> small grey tick labels read "<刻度1>" "<刻度2>"
"…". Hovering over the last point, a small floating card with rounded corners and a crisp shadow
reads "<提示框标题>" in dark type, then "<提示框行1>" and "<提示框行2>" as two right-aligned
grey lines.
On the right side of the body, a narrow panel titled "<排行标题>" lists <n> ranked rows, each
with a label and amount reading "<行1 金额>" beside thin horizontal bars that step down in
length. Directly beneath it, a second panel titled "<第二面板标题>" shows <n> rows reading
"<行1>", "<行2>", the second row tinted amber to mark it over budget while the others stay grey-green.
Along the lower third, a wide table spans the frame under a dark heading; its header cells read
"<表头1>" "<表头2>" "<表头3>" "<表头4>" in small grey capitals, and <n> hairline-separated rows
below them read in order "<整行1>", "<整行2>", each amount right-aligned in tabular numerals,
with the third row carrying a faint grey hover fill and a small pointer at its left edge.
At the bottom right of the frame, a footnote in pale grey reads "<脚注>".

The lighting is flat and even, the kind of diffuse front light that produces no highlights on
the panels, with only the soft shadows under the floating card and the hover row giving any depth.
The overall composition is a strict asymmetric grid on an eight pixel rhythm, calm and monochrome
apart from one <强调色> accent and one amber warning, dense in data but spacious in padding,
with numerals as the visual hierarchy and every element aligned to a shared column structure.
```

跑这条的命令（界面稿字段多，**≥1536 才看得清**；`--n 2` 留一张候选）：

```sh
python ~/.config/opencode/skills/genimg/scripts/gen_local_strata.py \
  --prompt "$(cat ui-prompt.txt)" --size 2048x1152 --n 2 --seed 1530101906 --force-large \
  --slug "界面稿-<屏名>"
```

要**逐字节复现那份文字全对的成品**，直接取它的原文，不要用上面改过槽位的版本：

```sh
python /c/Files/Codes/unaserver/scripts/s16_ui_arms.py --emit e2     # 整屏仪表盘，文字全对
python /c/Files/Codes/unaserver/scripts/s16_ui_arms.py --emit e4     # 局部放大两块面板，可读性最高
```

**写法要点**：- **先列一张「这一屏有哪些文案」的表**，再逐条放进 prompt，**用引号包住原样字符串**
  （`"总览"`、`"¥128,640"`、`"03-14 全家便利店 餐饮 ¥32"`）。中文、`¥`、日期、金额都对。
- **顺序按区域走帧**：整屏是什么 + 主题 → 侧栏（wordmark、每条导航）→ 顶栏 → hero（标签 + 大数字 + delta）→
  图表（标题 + 图例 + **每一个刻度标签**）→ 排行（标题 + 每行文字与金额）→ 表格（**每个表头单元格** + 每行每个字段）→ 脚注。
  写成「画面里有什么」（观察式），不要写「要做什么」。
- **末尾集中列清单不如按区域就地写**（E1 vs E2 同一屏：E1 在分类区丢行、重复，E2 全对）。
- **不要靠否定句压乱码**：`No gibberish text` / `no gibberish letters` 实测压不住。
  **而且本机后端没有 `negative` 参数**（`serve/images.py` 只接 prompt / size / n / steps / seed / response_format），
  社区那套「加 negative 去掉乱码文字」在这里没有对应入口。
- **不可读的文字**描述成「太小、读不清」，**不要造字母**；不加 quality booster。
- **墙：有序数字序列不可靠**（不是必错，是**不稳**）。同一份 12 项月份刻度，E2 的两张都排对，
  D1 的两张一张留空一格、一张重复；日历日号 1–31 两张都错（出现 `38`、`24` 三次）；四段分段控件丢第三段。
  **关键序列缩短它**（12 段刻度写成 4 段）或**局部放大**（E4）。
- **成本**：2048×1152 `n=1` ≈ 62 s、`n=2` ≈ 104–111 s；1536×1024 `n=2` = 64 s；
  `steps 8→16`（同一臂对照）把 sampling 48.7 → 86.2 s（+77%）、总长 61.8 → 97.4 s（+58%），文字没有可辨提升。
  界面稿要 ≥1536 才看得清字段。
- 证据：`C:\Files\Codes\unaserver\figures\ui-{prompt-arms,text-crops,copy-check,before-after}.png`，
  原图 `C:\Files\Pictures\genimg\20261101-04{24,25,27,28,31,38,40,49,51}_界面稿-*`，
  脚本 `C:\Files\Codes\unaserver\scripts\s16_ui_arms.py`（`--emit` 取 prompt，`--post` 直连带 `steps`，
  `--figure` / `--crops` / `--copy-check` / `--before-after` 拼图）。完整表与已撤回项：
  `C:\Files\Codes\unaserver\2026-10-30-能力边界.md` §3d。

### 要改风格：改那一段的描述，不要加全局句（实测 2026-11-01 12:45–13:08，六臂，同一屏同文案同 seed）

上面那份参考 prompt 已经含 `an Apple-class product interface … generous quiet margins …
eight pixel rhythm … dense in data but spacious in padding`——**风格名不是缺的东西**。
六臂只替换指定的句子（脚本先断言原文存在），结果只分两种：**改到区域里就生效，只改全局句就不生效。**

| 只改这一处 | 结果 |
|---|---|
| 末尾把 `dense in data but spacious in padding` 换成 `only four panels on a mostly empty canvas…`，数字 `seventy`→`one hundred twenty pixels` | **✗ 区块一个不少、栅格不变**，只有新写的那句标题与更大的数字出现 |
| 插一段列组件名：搜索框 / 铃铛 / 头像 / 四段胶囊 / 三张 sparkline 卡 / 网格线与 y 轴刻度 / 开关 / 复选框列 / 合计行 / 分页 / 四列页脚 | **◐ 约一半出来**（铃铛、头像、开关、复选框、`⟨ 1 2 3 ⟩`、四列页脚、y 轴刻度）；另一半没有；**没给文案的组件自造伪中文**（`笔用等分14号`）；y 轴数值不成比例 |
| 把「平光无高光」换成 模糊背景 + 磨砂玻璃 + 大圆角 + 顶边高光 + 发光与渐变面积 | **◐ 只有「曲线下的渐变面积 + 柔光」成立**，其余四项一个都没出现 |
| 第一段 `light theme` → `dark theme` + 画布那句改成 near-black | **✗ 页面/侧栏/表格黑了，三张 hero 卡仍纯白**——正文写死了 `a large white card` |
| 上一条基础上把 7 处区域颜色词逐处改过来 | **✓ 两张全深色**、文字仍逐字对、12 个月刻度仍排对 |
| 重写 hero 那段：左侧 55% 一整块**无卡框**排版（中文标题 ~90px、数字 ~220px），其它区域 `small, low contrast and muted` | **✓ 两张成立**：apple 那种「一个巨大焦点 + 其余很安静」 |

两条能直接用的改法（对上面模板做替换）：

```text
# 深色主题：第一段改成 dark/near-black 之后，还要把这些词逐处换掉
  a large white card …                      → a large dark charcoal card with a thin light border …
  in near-black numerals …                  → in bright white numerals …
  titled "…" in dark medium weight type     → titled "…" in bright white medium weight type
  above a series of pale grey bars          → above a series of mid grey bars
  a small floating card … in dark type      → a small floating card … in bright white type
  a wide table … under a dark heading       → a wide table … on a dark panel with a bright white heading
（自检：white / off-white / near-black / dark type / pale grey 在深色里都不该再出现）

# 强层级（apple 式）：重写主数字那一段，别加全局句
  The left 55 percent of the body is one oversized editorial headline with no card and no border,
  surrounded by empty space: the label "净资产" in small grey capitals, then a very large thin-weight
  headline "你的钱，这一个月的全貌" at roughly ninety pixels, then the figure "¥128,640" at roughly
  two hundred twenty pixels in near-black numerals …
  + 其它区域前面加一句：Everything to the right of and below that headline is rendered small,
    low contrast and muted in light grey so the headline stays the only focal point.
```

**六臂的服务端作业都是 112 s**（风格写法不影响耗时）。对照图 `C:\Files\Codes\unaserver\figures\
ui-{style-arms,style-detail,style-pairs}.png`，脚本 `C:\Files\Codes\unaserver\scripts\s16_ui_arms.py --style`，
数据与已试过判定不用：`C:\Files\Codes\unaserver\2026-10-30-能力边界.md` §3e。

## 后台 / 中台管理界面就照这个写法（实测 2026-11-01 15:0x，四种界面 × 各两张）

**这一类最稳**：它本来就是网格 + 重复行，而网格与重复行正是它稳的原因。
若依式列表页（表格 7 列 × 5 行 = 35 条字符串，两张都逐字全对）、左树右表、模态表单全部成立。
骨架按真实后台的顺序写：侧栏 → 页签条 → 面包屑 → 搜索表单 → 工具栏 → 表格 → 分页。
**不需要解释什么是若依 / 阿里云**，照真实骨架写就行。**四种形态的作业都是 103–113 s。**
不稳的只有「清单的数量与层级」：菜单 10 项会丢项、12 项快捷会重复一个、y 轴刻度会乱序
→ **要紧的清单写 6 项以内**。

**若依式列表页（实测采用）**

```text
The image is a flat screenshot of a Chinese admin console page, edge to edge, no browser chrome, no
device frame: the 用户管理 screen of a back-office system called 墨渡. Light theme, white panels on a
very light grey page, blue-grey body text at ordinary small UI size, one vermilion accent, flat borders
and no shadows except on the dropdown. Layout exactly as follows.
a dark charcoal navigation rail, 240 pixels wide, running the full height of the left edge: the wordmark
墨渡 at the top in white, then a vertical menu with group captions in small dim grey type reading 系统管理,
内容管理, 系统监控, and under those, menu items in light grey type reading 用户管理, 角色管理, 菜单管理,
部门管理, 字典管理, 文章管理, 分类管理, 评论管理, 服务监控, 缓存监控; the item 用户管理 is drawn selected
with a lighter background and a thin vermilion left edge; small caret triangles sit beside the two
expanded groups, and the collapsed groups show closed carets
Along the top of the content area a slim white bar: at its left a row of open page tabs reading 首页
and 用户管理 with a small close cross on the second tab, and a small dropdown labelled 页签操作; at the
right of the bar a small magnifier icon, a bell icon, and a round avatar with the text 管理员.
Below the bar a breadcrumb line reading 首页 / 系统管理 / 用户管理 in small grey type with the last item
in dark.
Then a white search-form panel with four labelled inline fields on one row: a text input labelled 用户名
containing the placeholder 请输入用户名, a text input labelled 手机号码 containing 请输入手机号码, a select
labelled 状态 showing 不限, a date-range field labelled 创建时间 showing 开始日期 至 结束日期, and at the
right a small filled dark button reading 搜索 with a plain outlined button reading 重置 beside it.
Below the search form a toolbar row of small buttons: a filled green plus button reading 新增, an outlined
button reading 修改, an outlined red button reading 删除, an outlined button reading 导入, an outlined
button reading 导出, and at the far right three small icon buttons for column visibility, refresh and density.
Then the main table, full width, with a header row in small dark type reading 用户账号, 用户昵称, 部门,
手机号码, 状态, 创建时间, 操作. Five data rows, all strings exact:
row one  admin, 超级管理员, 墨渡科技, 138 0000 0000, an on switch in vermilion labelled 启用,
2026-03-11 09:12:04, then the text links 修改 删除 and a disabled grey 删除 with a tooltip above it
reading admin 不能删除;
row two  chenmo, 陈默, 编辑部, 137 2211 0634, an on switch labelled 启用, 2026-04-02 14:20:31, links 修改 删除;
row three  lin04, 林榆, 产品组, 136 8802 7741, an off grey switch labelled 停用, 2026-05-18 08:05:52, links 修改 删除;
row four  zhoushu, 周叔, 运维, 135 6600 1982, an on switch labelled 启用, 2026-06-27 21:44:07, links 修改 删除;
row five  xuanyin, 萱寅, 设计组, 139 4455 8823, an on switch labelled 启用, 2026-09-30 11:02:19, links 修改 删除.
Under the table, on one line, a pagination bar: at the left small grey text reading 共 54 条, then a
select reading 20条/页, then page buttons reading ‹ 1 2 3 4 › with 1 highlighted, and at the right the
text 前往 1 页.
Type is small and dense the way a real admin table is: row height about 40 pixels, body text around
13 pixels, table header and menu items the same size. No oversized headline anywhere on this page.
Every visible label is one of the strings given above.
```

**中台工作台（KPI + 图表 + 告警 + 快捷入口）** — 版面与文案成立；把快捷入口缩到 6–8 项、
y 轴刻度只标两端（首尾）会更稳。逐字文本：`s18_admin_ui.py --emit a2`。

```text
The image is a flat screenshot of a Chinese cloud console overview dashboard called 墨渡 控制台, edge to
edge, no browser chrome, no device frame. Light theme: a white top bar, a light grey page, white cards
with hairline borders and small corner radius, dense small UI type around 13 pixels, blue-grey text,
one vermilion accent for alerts only. Layout exactly as follows.
A white top bar: the wordmark 墨渡控制台 at the left, then top-level nav links reading 工作台, 产品,
费用, 备案, 工单, 文档, and at the right a wide search field containing the placeholder 搜索产品、文档与实例,
then a globe icon with the text 华东1（杭州）, a bell icon with a small red dot, and an avatar labelled 运维.
A narrow icon rail down the left edge with eight small icons and no text.
The content column starts with a greeting line in medium dark type reading 早上好，运维, and under it a
small grey line reading 上次登录 2026-11-01 08:42 · 华东1（杭州）.
Then a row of four equal metric cards with hairline borders, each with a small grey label, a large but
not oversized numeral and one line of small grey detail: 云服务器实例 with 42 and 较上周 +3; 对象存储用量
with 8.4 TB and 较上月 +6.2%; 数据库实例 with 9 and 1 个待处理; 本月费用 with ¥4,382.60 and 账单日 11-03.
Below the metric cards, two chart panels side by side. The wider left one is titled 近 7 日请求量 in
small dark type with a small segmented control reading 7天 30天 90天 above a line chart with six x-axis
labels reading 10-26 10-27 10-28 10-29 10-30 11-01, faint horizontal gridlines, a y-axis reading
0 20k 40k 60k, and a filled light area beneath the line. The right one is titled 资源分布 with a donut
chart in four muted colours and a legend listing 计算 42%, 存储 26%, 数据库 19%, 网络 13%.
Under the charts, a wide panel titled 告警 with three rows each carrying a small vermilion dot, a message
and a time: 磁盘使用率超过 85% on 节点 node-07, 2 分钟前; 证书将在 7 天后过期 on api.example.com,
1 小时前; 备份任务失败 on db-main, 昨天 23:10.
At the right of the page, a narrow column with two panels. The first is titled 我的资源 and holds a grid
of small text-only links reading 云服务器, 对象存储, 云数据库, 负载均衡, 容器服务, 日志服务. The second is
titled 最近操作 with a vertical timeline of four entries reading 创建了实例 i-7f31 · 10:12, 重启了
db-main · 09:40, 修改了安全组 sg-2 · 昨天, 导出了账单 · 10-30.
Nothing on this page is a hero headline: the largest text is the four metric numerals, everything else is
small dense UI type. Every visible label is one of the strings given above.
```

**列表上叠模态表单** — 字段级状态（报错文案 + 红边、字数计数、多选 chips、树选择高亮、单选选中点）
**给一句话就有**，做「表单出错长什么样」这类设计稿很值。

```text
The image is a flat screenshot of a Chinese admin console with a modal dialog open on top of it, edge to
edge, no browser chrome, no device frame. Light theme, small dense UI type around 13 pixels, one
vermilion accent.
Behind the dialog, dimmed under a translucent grey scrim, a list page is visible but readable: a dark
side rail with menu text, a toolbar row reading 新增 修改 删除, and a table with a header row reading
用户账号 用户昵称 部门 状态 操作 and three faint rows of grey text.
Centred on top of it, a white modal panel about 640 pixels wide with a small corner radius and a real
drop shadow. Its header bar holds the title 新增用户 in medium dark type and a small close cross at the
right. Its body is a two column form with grey labels above dark inputs, exactly these fields: 用户账号
with an input containing a single vermilion error line under it reading 用户账号不能为空; 用户昵称 with an
input containing 林榆; 归属部门 with a select showing 产品组 and a small open caret; 岗位 with a select
showing two small selected chips reading 编辑 and 审稿 with remove crosses; 手机号码 with an input
containing 136 8802 7741; 邮箱 with an input containing lin@example.com; 部门树 with a small tree picker
showing three nodes reading 墨渡科技, 产品组 and a highlighted 设计组; 状态 with two radio buttons
labelled 正常 and 停用, the first selected with a filled dot; 备注 with a tall empty textarea and a
small grey counter reading 0 / 200 in its corner.
The modal footer holds two buttons aligned right: a plain outlined button reading 取消 and a filled dark
button reading 确定.
Label text sits above each input at about 13 pixels; inputs are 32 pixels tall with hairline borders;
only the 用户账号 field shows an error, and its border is vermilion. Every visible string is one of the
strings given above.
```

**左树右表（骨架）** — 沿用上面那段侧栏 + 页签 + 面包屑，然后：
左侧面板标题 `部门` → 搜索框 placeholder → `展开 / 折叠` → **六个节点，每行一个文件夹图标 + 名称 +
右侧灰色计数数字，其中一行画选中态** → 右侧搜索行 + 工具栏 + 六列五行表格（含开关与禁用态）→ `共 6 条` 分页。
六节点与计数两张全对；逐字文本：`s18_admin_ui.py --emit a3`。

**去模板味：把插画 / 渐变 / 彩色图标底当内容点名（实测 2026-11-01 15:3x）**
只给结构与文案 → 出来是通用后台模板（等高等宽白卡片、灰块占位头像、无插图无渐变）。
**这些句子写进对应区域就出得来，而且不会让原本的文案退化**；贴到 prompt 末尾则完全不改画面。
可直接替换进上面几段：

```text
# 顶部欢迎卡换成渐变 banner + 插画（把「greeting line」那段整段替换）
The content column opens with a full-width banner card, about 170 pixels tall, filled with a soft diagonal
gradient running from deep indigo at the left to vermilion at the right. Its left side holds the greeting
line in large white type reading 早上好，运维 and under it a small white line reading 上次登录 …
The right side of the same banner holds a flat vector illustration with no text in it: a stylised server
rack with three floating rounded cards and two thin connection lines, drawn in cream, pale blue and white
over the gradient.

# 指标卡 / 快捷入口加彩色图标底（tint 逐张不同，这句成立）
each with a small duotone icon inside a tinted rounded square at its left, the tints differing per card:
pale indigo, pale green, pale amber, pale rose
… each one a small duotone icon inside a tinted rounded square above its label, reading 云服务器, 对象存储 …

# 空状态插画（最划算：一句话就有，配的文案还逐字对）
an empty-state panel holding a flat vector illustration of an open empty box with three small papers
floating out of it, drawn in indigo and cream with no text in it, and under that illustration a line of
grey type reading 今天还没有操作

# 侧栏底部帮助卡（渐变 + 小插画 + 按钮）
pinned at the bottom of that rail a small card filled with a soft indigo gradient, holding a tiny flat
illustration of a life ring and two lines of white type reading 需要帮助？ and a small white button
reading 提交工单

# 图表面积用渐变填充（比 flat 色块更像真产品）
beneath the line a vertical gradient fill fading from soft vermilion near the line down to transparent
at the axis

# 列表页：渐变提示条 + 状态胶囊 + 每行头像插画
Then a slim strip across the top of the content, filled with a soft diagonal gradient from pale indigo to
pale rose, holding a line of dark type reading 本周新增 4 位用户，记得为新同事开通权限, and at its right
a small flat vector illustration of three ID badges and a key with no text in it.
a small pill badge with a pale green fill and green type reading 启用 / a small pill badge with a pale
grey fill and grey type reading 停用
Each 用户昵称 cell carries a small circular flat-vector avatar illustration to the left of the name,
drawn in two tones. **别写「每行不同」**：`a different silhouette per row` 出来五行是同一款剪影。
```

**不成立的写法**：末尾贴 `Overall this screen should look like a real commercial product rather than a
template: illustrations and artwork woven between the panels, soft gradients, coloured icon tiles, an
asymmetric layout, avoiding a uniform grid of plain white cards…` → 与不加它的基线相比 **MAD 0.6/255、
PSNR 46.5 dB**，比同写法两张之间的噪声底（7.1 / 25.4）还小，**画面没变**。

对照图 `C:\Files\Codes\unaserver\figures\admin-{arms,crops}.png`，脚本 `…\scripts\s18_admin_ui.py`
（`--emit s1|s2|s3|s4` 取四种设计层写法，`--probes` 读浓彩/淡彩占比：基线 0–1% → 写进区域后 16–19%），
数据与已试过判定不用：`…\2026-10-30-能力边界.md` §3g、§3h。

**先提醒一句上面这段的边界**：这些句子（渐变 banner、四色图标底、彩色胶囊）会把装饰画出来，但
**多处彩色 + 大片渐变正是「AI 味」的来源**（2026-11-01 16:5x 的用户判定，见下节）。
用它们之前先把配色收敛好；渐变只在底层用一处。

## 产品概念图（移动端 App / Web 应用 / 三屏概念板）就照这个写法（实测 2026-11-01 16:2x–16:5x，3 题材 × 3 写法 × 2 后端）

**结论：「有没有主次」是配色写法问题，不是后端问题。** 同一条 prompt 下两个后端的结构与文案几乎一样；
**只改下面这一段配色描述（卡片、边框、阴影全照旧）就到线，而且小字号文案仍然逐字全对。**

真实开源产品的界面有三条共同做法（dub.co 官网界面、mihon 的 fastlane 截图、huly 界面三处独立一致）：
**强调色只有一处、面积 <2%**；**彩色全部来自内容**（照片、封面、一张图表）；**框架全中性、卡片无边框、
分组靠留白和一条细线**；**装饰只在最底层**（1px 方格网、标题区一抹淡色）。取真实界面的办法：
官网取 `og:image`；开源 App 用 `GET api.github.com/repos/<repo>/git/trees/<branch>?recursive=1`
找 `phoneScreenshots`，再从 `raw.githubusercontent.com` 取。**没有图片输入端点，所以参考只能翻成文字。**

```text
# 这一段是本轮到线的写法（只改配色，不动卡片结构）
Colour discipline: exactly ONE accent colour used in under two percent of the picture — one filled
button and one selected navigation item. All the colour in the picture comes from the content itself:
cover artwork, real photographs of people, one data chart. UI chrome carries no gradients and no
coloured icon tiles.

# 要更接近真实产品，再加（实测会让小字号出现 2 处错字，收益不如上一段）
Depth comes from type size and whitespace, not from cards: no borders and no shadows around the panels
— groups are separated by whitespace and a single hairline divider only. One large display headline,
then a clear step down to 15px body and 12px meta text. Decorative layers sit behind everything and are
barely visible: a faint 1px square grid across the background, and a single soft pale wash behind the
headline area.
```

**不成立 / 反而加重 AI 味的写法**：`Each panel is a white card with a hairline border and a soft shadow.
Section titles sit on small rounded coloured chips. Icons sit inside tinted rounded squares, the tints
differing per item: pale indigo, pale green, pale amber, pale rose. The top area is filled with a
diagonal gradient from deep indigo to vermilion. Statuses are coloured pill badges.`
→ 装饰全都出来，但出来就是「AI 味」：上半屏一整片渐变、五个导航各一种彩色底。

**两个后端怎么挑**（详细数字在 unaserver 的能力边界 §3i）：付费那条只在两种情况下值得花——
**图里的数字必须对**（有序时间、金额：默认后端把 `07:45`→`08:45`、`21:30`→`07:90`，付费的同写法全对）、
**要真实摄影素材**（它会自己加 logo 与照片，不可控）。其余都用默认后端（免费、且 1:1 文字判定同样全对）。

对照图 `C:\Files\Codes\unaserver\figures\concept-{T1,T2,T3}{,-crops}.png`，脚本
`C:\Files\Codes\unaserver\scripts\s19_concept_ui.py`（`--batch local|gateway`、`--only`、`--skip-done`）。
**做 1:1 文字裁块时左边界要留 30px 以上**：从文字起点裁会把每行第一个字母切掉，看着像模型丢字。

## 一整页产品（APP 整页 / web 整页 nav→footer）就照这个写法（实测 2026-11-01 17:1x–17:4x，12 臂，全部本机）

**这节解决什么**：之前出的图「都很小」——只有一屏的一角，不是一整页产品。
根因是**横向尺寸只能画一个视口** + prompt 只描述了一块界面。换三件事之后 **12/12 臂都画成了整页**。

**三件事**：

1. **尺寸**：APP 用 `1024x2048`，web 整页用 `1152x2048`（服务端 49–61 s）。
2. **整页骨架句**（放在开头）：
   `A mobile app screen, portrait, drawn as ONE complete full-height page from the status bar at the top
   down to the bottom tab bar, edge to edge, no device frame, no hands, no table.`
   web 版：`A web product page drawn as ONE complete full-height page from the top navigation down to the
   footer, exactly as it would read after scrolling to the bottom, portrait, edge to edge, no browser chrome.`
3. **从上到下逐区列全**：`Blocks, top to bottom, every one present:` 然后一区一段。缺的那区就不会出现。

**视觉焦点 / 重点聚焦要写成尺寸差**（抽象句不生效）：

```
Why this page is laid out this way, shown through what is on it: the page has one job — make the first
number believable — so the panel with the large figure is twice the height of any other block, and every
other block steps down from it. The pink appears only where the product acts or the data moves, so it
reads as identity, not decoration.
```

**重复卡片按行绑定（本节最有价值的一条）**。`A / B / C` 这种一行清单会让字符串跨卡片扩散
（每卡两行标题、同一句重复两遍、字段错绑到别的位）。到线的写法是**一行一句、句里写清 LEFT/RIGHT**：

```
A feed of exactly four cards in TWO COLUMNS — two rows, each card half the page width. Describe the
page one ROW at a time, and inside each row say which card is on the left and which is on the right.
The words in each sentence belong to that one card only:
Row one, LEFT card: a 16:9 photograph of a man at an animation desk, a badge reading 04:12, the title
用 Blender 做一部短片的全过程, a grey line 某川的录像间, a grey count 12.4万.
Row one, RIGHT card: a 16:9 photograph of a convenience store at night, a badge reading 04:12, the title
深夜便利店观察日记, a grey line 某川的录像间, a grey count 12.4万.
Row two, LEFT card: …    Row two, RIGHT card: …
Each card holds exactly one title and one badge. No title appears twice anywhere on the page.
```

单列列表用 `Card 1: …` / `Card 2: …`（六条全部逐字一次命中，**六张缩略图自动是六个不同场景**）；
横排卡片用 `Card A: …`（实测连图标语义都对：时钟 / 对勾 / 循环箭头各归其卡）。

**长度不是限制，段落内容才是。** 后续用这套写法一次出 11 页（App 五页 2.0–2.5k 字符、后台六页 2.2–3.4k）
全部区域与文案成立。会坏事的只有两类段落：抽象的「为什么这样设计」句、以及把配色/字体/组件/间距/图标/动效
写成一整段的「设计系统锁定」（≈2.5k 字符）——它会挤掉版面指令（要求 two column 会画成单列或左图右文混排）。
要锁风格只留配色段（见 SKILL.md 3b）+ 组件形状两句。

**后台页也必须带配色段**（实测：漏了那段时主按钮、开关、选中态全部出成黑色/灰色；补上 ≈560 字符重出，
强调色全部落对，其余文案一字未变）。

**成套出多个页面怎么做**（11 页那一批的做法）：把**共用段**写成函数——品牌与配色段、
App 外壳（状态栏 + 五个 tab，选中项按页传入）、后台外壳（220px 侧栏六项 + 顶栏 + 面包屑，
当前页与面包屑按页传入）——每页只写自己的区域与文案。一条命令连着发完，**只重跑不合格的页**；
脚本按页取**最新**那张（文件名前缀是时间，字典序即时间序）。

**另外两条在后台里成立的写法**：双列卡片网格用逐行 LEFT/RIGHT（六张动作卡全部各归其卡，
且每张只要写「一个做某动作的人」，**插画语义 6/6 正确**——「图标语义不可靠」只适用于一次画一整套小图标）；
**对话气泡**逐条绑定（谁在左谁在右 + 原文），四条逐字命中，它只会自己补句号。

**动效只写状态**：`A thin accent progress bar runs partway across the bottom edge of that card, stopped at
about forty percent` ✓ 出现；`one card lifted to 1.04 scale with a stronger shadow`、
`a wide quiet band of empty page with nothing in it` ✗ 不出现，还会把文案质量换掉。

**已试过判定不用**：长 Design Bible 段（单张）；把「为什么这样布局 / 为什么这个颜色」写成抽象句
（区域级会让小字出现乱码级错字）；多列网格里用 `Card 1 / Card 2` 绑定（跨列扩散）；变换类动效。

**完整可运行的原文**（H3 web / H4 双列 / H1 单列六条）在 `C:\Files\Codes\unaserver\scripts\s21_recipe.py`
（`--emit H4` 直接打印）；逐臂判定在 `C:\Files\Codes\unaserver\2026-10-30-能力边界.md` §3j。

## 营销站 / 落地页与资源图就照这个写法（实测 2026-11-01 13:36–14:03，八种写法，同一份文案只差写法）

**上面那套「按区域走帧 + 每区就地给文案」迁到营销站就成立，不需要新技巧。**
一整屏落地页（nav / 两栏 hero / 三特性 / 五个客户名 / 底部滚动提示）**逐字全中**。
完整 prompt 在 `C:\Files\Codes\unaserver\scripts\s17_landing_arms.py`（`--emit l1|q|l2|l3|l4|l5i|l5t|l5h`）。

**骨架（L1，实测逐字命中，2048×1152）**：

```text
The image is a wide flat screenshot of a website landing page for <产品类别> called <品牌>，shown edge to
edge with no browser chrome, no mockup frame, no device around it. The page is an editorial, asymmetric
composition on a warm cream background with ink black type, one vermilion accent, generous empty space,
and photography as the visual lead.
Along the top of the frame a slim navigation bar: the wordmark <品牌> at the left in medium black type,
four navigation links to its right reading "概览" "价格" "文档" "更新", and a small outlined button at the
far right reading "免费试用".
In the upper 60 percent of the frame, a two column hero. On the left, an eyebrow label in small grey
capitals reading "本地优先 · 不上传", a very large display headline set in two lines: the first line
"把读过的东西" and the second line "留在自己的机器上", a short paragraph under it reading "……",
a filled primary button reading "免费试用" and a plain text link reading "看它怎么工作".
On the right half of the hero, a full bleed photograph that runs to the right edge of the frame:
<一段照片描述>.
Below the hero, a thin hairline rule, then three feature blocks in a row, each with a small line icon,
a title and one line of copy: "全文检索" with "毫秒级，离线也能用"; "双向链接" with "……"; "随时导出" with "……".
Under the features, a quiet row of five grey text-only client wordmarks reading <五个真实名字>, set small
and evenly spaced.
At the very bottom edge, a small grey hint with a downward chevron reading 向下滚动看价格.
The headline is the largest element on the page by a wide margin; every other text size steps down clearly
from it. Panels are flat with no borders and no drop shadows; the only saturated colour in the whole page
is the vermilion used for the primary button and one rule under the eyebrow label.
```

三条实测到的写法细节：

- **要两行标题就分行写**（`set in two lines: the first line "…" and the second line "…"`）。
  只写 `a very large headline` 会连成一行。
- **每个组件都要带文案**，包括客户名行和底部提示——给全了就全中（本轮这臂零错字）。
- **prompt 长度不是墙**：这臂 1,975 字符，写满 tokens 那臂 2,383 字符，结构都没丢。

### 动线：把两个状态画在同一张图里（L2，1,397 字符，✓ 逐项对）

```text
The image is a wide flat interaction design sheet for the hero of a website called <品牌>, on a warm cream
background. The sheet shows the same hero block twice, side by side at identical size, with a thin
horizontal arrow drawn between them pointing right, so the two states read as one scroll interaction.
Left half — state one, before scrolling: … a large display headline in one line reading "把读过的东西",
a filled vermilion button reading "免费试用", and to the right a closed dark panel with no content visible.
Right half — state two, after scrolling: the same hero block, identical position and size, but the headline
has grown to two lines reading … and …, the dark panel has opened into a document list showing four rows of
grey text lines, the eyebrow label is gone, and a mouse cursor arrow is drawn resting on the "免费试用"
button, which is now slightly darker with a small ring around it.
Above both halves, a small grey caption over the left one reading 状态一 未滚动 and over the right one
reading 状态二 已滚动. Below the arrow, one line of small grey type reading 标题展开 · 面板打开 · 标签淡出.
```

两半的差异、两个状态标签、底部那行说明**全部逐字对** → **静态图能表达滚动/hover**。
唯一不稳：两半不是严格同一网格（左半按钮偏高），要精确对齐就多试一臂。

### 要看细节就一节一图（L4 定价节，1,465 字符，1536×1024，70 s，**全部逐字命中**）

单节比整屏便宜 40 s，文字密度高得多：三档面板的价格、副标、14 条列表行、四个按钮、
FAQ 四个问句全部对。骨架是「eyebrow + 两行大标题 + 说明 → 三档（中间档更高 + 顶部强调色 +
`最受欢迎` 标签）→ 常见问题 + 四条带 `+` 的 FAQ」，**每档的列表行逐条用引号给出**。
**要细节就重画那一节，不要裁上一张**（裁掉的块本身不可判）。

### 资源图（各发一条作业，1024² 一条 28–29 s）

```text
# 可平铺背景 ✓（脚本 seam_probe：边界接缝 MAD 2.60 vs 相邻列 2.40 = 1.1× → 平铺不露缝）
A seamless tileable abstract background pattern filling the whole frame on a warm cream field: thin
off-white and pale grey ink-brush strokes like paper fibres and faint ruled guide lines, with two small
soft vermilion marks, evenly balanced so no area is darker than another, no focal point, no text
anywhere, no frame, flat and even lighting, designed to be used as a website background.

# 主视觉照片 ✓ 可直接当 hero（这条推翻了「真实摄影做不到」；产品渲染仍不行）
A wide photographic still life for a website hero image, warm and quiet: a wooden desk beside a window
with soft morning daylight, an open paper notebook with handwritten Chinese characters, a fountain pen
resting on the page, a small stack of printed pages and a ceramic cup, shot from above at a slight three
quarter angle, shallow depth of field, natural film-like grain, muted warm palette with one small
vermilion object as the only strong colour, no text overlays, no watermarks, no visible brand names.

# 图标网格 ◐ 只当风格参考（语义与标签不可靠：12 条里 9 条语义错位、4 条错字）
A flat icon sheet on a plain warm cream background: a grid of twelve icons …, all drawn with the same
1.5 pixel ink black stroke, the same rounded joins, the same 24 pixel box and the same corner radius,
no fills, no shadows, no gradients. Each icon has one small grey Chinese label beneath it, reading in
order: 搜索, 收藏, …
```

**图标结论**：统一描边/圆角/网格 ✓，但**语义会漂**（`收藏`→齿轮、`分享`→气球）、**短标签会错字**
（`链接`→链锉、`日历`→日方、`下载`→下业、`归档`→归榕），指定的 `four rows and three columns` 出成 3 行 4 列。
**做 icon 用现成图标库，生图只用来定风格。**

### tokens 写进每个区域 = 方向成立、数值不精确（L3）

把 hex / `radius 20 pixels` / `0 12px 32px rgba(…)` / 字号阶梯**写进每一段的描述里**（不是加一段全局风格句）
→ 卡片化、圆角、阴影、强调色出现的位置都按指定来，与不写的版本明显不同。
**但只被近似**：指定 `#D7432B` 出来 `#b61700`（RGB 距离 70）；`132px/24/18/14` 只落成相对大小。
**所以颜色与字号最后要从图上取，不要照抄 prompt。** 脚本里的 `accent_probe()` 就是干这个的。

### 不要贴「对标 Awwwards / FWA / CSSDA」那段全局质量段（Q 臂，实测判掉）

与不贴相比（L1 逐字不动 + 末尾追加那段中文）：

| 比较 | MAD/255 | PSNR |
|---|---|---|
| L1 vs L1 自己的两张样本（噪声底） | 50.4 | 10.1 dB |
| **L1 vs 加了那段质量段** | **3.8** | **29.3 dB** |
| L1 vs L3（各区域描述改写，正对照） | 44.6 | 10.4 dB |

→ **画面没变。** 那段话是用来给编码 agent 定验收标准的，不是位图模型的输入。
判「加一段话改没改画面」用 `pixel_diff()`（MAD / PSNR / 上中下分带），**别忘了同臂两张样本就是噪声底**。

对照图 `C:\Files\Codes\unaserver\figures\landing-{arms,crops,quality-diff}.png`，
脚本 `C:\Files\Codes\unaserver\scripts\s17_landing_arms.py`，
逐臂数据与已试过判定不用：`C:\Files\Codes\unaserver\2026-10-30-能力边界.md` §3f；
流程（需求 → 设计图 → 代码）：`C:\Files\Codes\unaserver\2026-11-01-从需求到设计图.md`。
