---
name: genimg
description: 生成图片/生图/配图/插图/图标切图/头像/商品图/产品图/封面/背景图/插画/资源图/概念图/宣传图/风格图/风格方向示意，或英文 generate an image, illustration, icon, avatar, hero art, wallpaper, moodboard, product shots。界面与产品稿（UI 设计稿、后台/中台界面、落地页整页、web/app 产品）也走本 skill 判断，但结论是先分流：要能实现、能改、文案要准 → 交给代码模型写界面，本 skill 只补它需要的位图素材。默认走本机服务（不花钱、局域网内），成品落盘到 C:\Files\Pictures\genimg。
metadata:
  author: unarem
  version: "3.1.0"
---

# genimg

把「要一张图」变成「拿到能用的图」。默认用本机的 qwen-image-2.1（免费、局域网、逐字节可复现）。
它是**生成设计图中内容的协助者**：界面由代码模型写，页面里的商品图、头像、插画、图标、背景由这里出。

## 主流程（照这个顺序走）

1. **判断是哪种活** — 内容素材 / 风格图 / 概念图或整页设计稿（见「它在做哪种活」）。
   要落地、要改的那份界面不在这里交付，转 [references/code-first.md](references/code-first.md)。
2. **定槽位与尺寸** — 先读代码或需求里的图片槽位：几个、什么比例、出现在列表还是详情。
   **一个槽位一条 prompt**，尺寸按槽位取最小够用档（见「尺寸」）。
3. **选接口** — **没有明确要 gpt-image-2，就用本机**（见「两个接口」）。
4. **一批发完** — 写成 `--jobs` 文件一次发完，`--slug` 带上槽位名；后台跑，结束回合等通知。
   同主题要多候选用 `--n`，换构图换 `--seed`。
5. **要小图就切** — 一整张网格图（图标表、缩略图组、多屏概念板）用
   `scripts/slice.py` 切成单张、缩到目标尺寸、去背景，**直接 `--out` 到项目目录**。
6. **交付与留凭证** — 默认成品留 `C:\Files\Pictures\genimg`；要用的时候复制进项目工作区，
   资源不 gitignore。每张旁的 `.meta.json` 是复现凭据，重跑照它发（见「交付」）。

## 它在做哪种活

**1. 内容素材（最常见，也最划算）** — **界面由代码模型写，页面里的内容由这里补**。
要填进界面的位图：商品图 / 产品图、头像、封面缩略图、空状态插画、可平铺背景、图标切图。
一个商品页往往等于**一批 mock 数据的图片**：先数清槽位，一个槽位一条 prompt，一次发完。
这类活的判据最干净：有没有占住槽位、语义对不对、能不能直接用。

**2. 风格图** — 定方向用的样张。**不求精细，求要素齐**：一张图里把整套风格载体都放上去，
让人一眼看出「整个产品长这样」。看完方向，交给 StyleKit 落成 tokens，界面代码按 tokens 写。
见「风格图」一节。

**3. 概念图 / 宣传图 / 整页设计稿** — 一张讲清一个概念、一个功能、一条流程，
或把一整页（落地页、产品页 nav→footer）画出来给人看方向。写法在 prompt-recipes.md 的
「一整页产品」那节（竖屏尺寸 + 整页骨架句 + 逐区列全）。这类图的价值是「一眼看出方向」，
**它当不了规格**：要落地就按 [references/code-first.md](references/code-first.md) 写文本规格。

**要落地、要改的那份界面，不由这条链路交付。** 界面写文本规格 + 代码模型（
[references/code-first.md](references/code-first.md)），内容图从这里出。
这不是「画不出来」，是分工：先出设计图再照图实现，等于把同一个想法翻两次，
第二次只能照着第一次糊出来的地方建。

## 两个接口

**判断只有一条：有没有明确要 gpt-image-2。** 没有 → 本机 qwen-image-2.1（默认）。
不拿钱、耗时、打断做选择理由；要 gpt-image-2 才加 `--backend gateway`。
遇到「图里的数字必须对」（时间、金额、统计刻度）或「要真实摄影素材」这两类需求，
可以提一句网关在这两点更稳，**但不擅自切**。

```bash
# 先 --check：不花钱、不占 GPU，只确认 key 与参数（本机还会探一次 /health）
python ~/.config/opencode/skills/genimg/scripts/genimg.py --check --jobs jobs.tsv
```

解释器就用 PATH 上的 `python`（`C:/Applications/Python312` 不存在，别按那个路径调）。
**`~` 只在命令行上直接写出来才展开**；写进脚本变量要用绝对路径
`/c/Users/<user>/.config/opencode/skills/genimg/scripts/genimg.py`。

**脚本的全部参数就这些**，别按别的工具的惯性加：`--prompt` 或 `--jobs`（二选一）
`--size` `--quality low|medium|high`（**本机后端会忽略**） `--n 1–4` `--seed`（仅本机）
`--backend local|gateway` `--slug` `--out` `--skip-done` `--retries` `--force-large` `--check`。
**没有** `--json` / `--quiet` / `--batch` / `--negative` / `--steps` / `--cfg`。

一批的输入文件（`--jobs`）三种写法都行：JSON 数组、JSONL、或每行 `slug<TAB>prompt` 的 txt；
命令行上的 `--size`/`--n`/`--seed` 当这批的默认值。**补跑加 `--skip-done`**：
同 prompt+size+n+seed 的会跳过（已出过的不重复付费），部分失败退出码 5，摘要会写清哪几条没成。

| | **本机 Strata**（默认） | **网关 gpt-image-2** |
|---|---|---|
| 怎么发 | `genimg.py --jobs jobs.tsv` | 加 `--backend gateway`（key 在 skill 目录 `.env` 的 `GENIMG_API_KEY`；`.env` 里写 `GENIMG_BACKEND=gateway` 可改默认） |
| 复现 | `--seed` + 同配置 → PNG 逐字节相同 | 没有 seed（未验证过） |
| 参数差异 | 没有 quality 阶梯（固定 8 步 Turbo） | 有 `quality`；返回 `url` 要再下载一次 |

耗时、计费、副作用（本机独占 GPU、对正在跑的对话是实测 115 s 的打断）都在
[references/api.md](references/api.md)；**报时间前去那里取数，别凭印象说「几十秒」**。

**效率就三条**：

1. **一轮发完**：不同内容就写进同一个 `--jobs` 连着发，作业之间不付重载；
   穿插一次对话就多付一轮（实测 +80–140 s/张）。做法：一条命令发完整批，后台跑，
   结束回合等通知。**客户端超时要给到 900 s**：本机在客户端断开时会**取消作业**（网关是已计费不退），
   中断过就别声称出了图，只认响应里的 `strata.seconds` 或服务日志的 `image done in N s`。
2. **同主题要多候选就 `--n 2`**（省加载与文本编码），换构图就换 `--seed`。
   `--n 2` 不省采样：两张 ≈ 两倍时间，但比发两次少一轮重载。
3. **尺寸按槽位取最小够用档**：成本与面积线性。图标、缩略图这类小图**不需要大图**——
   出 512×512 的 4×4 图标表实测 15 s，切出来照样是干净的 32×32。
   **prompt 写多长都不加时间**（实测 1.1k→2.6k 字符同耗时），所以文案该写细就写细。

## 尺寸

每边 256–2048、必须是 32 的倍数（不合规直接 400；`1920x1080` 会被拒，要写 `1920x1088`）。

| 要画什么 | 尺寸 |
|---|---|
| 列表缩略图 / 商品图 / 头像 / 平铺背景 | `1024x1024` |
| **图标切图（一整张 N×N 图标表）** | `512x512`(4×4) / `1024x1024`(10×10)，切完再缩 |
| web 桌面视口（落地页、后台、风格图） | **`1920x1088`**，prompt 第一句写 `a 1920 by 1080 desktop viewport` |
| 一整页 APP / 一整页 web | **`1024x2048`** / **`1152x2048`**（横向尺寸只装得下一个视口，整页必须竖屏） |
| 手机 App 单屏 | `1152x1536` 或 `1024x2048` |
| 要看清楚的局部（单节、单卡） | `1536x1024`，按区域单发 |

超过 1024 的档要带 `--force-large`（确认接受代价）。

## 写 prompt

**一条铁律：每区就地给文案。** 要出现在画面上的文字，写进它所属那一区的描述里
（`the search button, reading "搜索"`），不要在末尾贴一句全局风格要求——末尾那段不改画面。
没给文案的组件会自己编内容，要空态就明说怎么空。

其余按题材照现成的骨架改，别从零写：
[references/prompt-recipes.md](references/prompt-recipes.md) 里有界面稿、后台四形态、一整页产品、
营销站与资源图、图上文字（中/英）、内容素材各题材**逐字命中过的 prompt 全文**，改品牌与文案即可。
要「新颖」而不是每次都落在同一套安全风格上，用 SSoT 抽方向：
`python ~/.config/opencode/skills/genimg/scripts/sot_sample.py --string '<我自己写的一个随机串>'`，
它按七轴给可直接粘进各区域的片段；把那个串写进 slug 留作凭据。

## 风格图

目的不是好看，是**一次看清整套方向**。一张 `1920x1088` 里把所有风格载体都放进去：
顶栏与导航、主视觉标题区、卡片流、表单或搜索、一张图表、一个插画或空状态、页脚——
**要素齐 > 单点精细**。文字只求读得出意思，不追求逐字准确。

流程是：先出 2–3 张不同方向的风格图（本机，免费，换 seed 或换 `sot_sample` 的串），
拿给用户挑；选定后用 StyleKit 把方向落成可执行的 tokens：
`stylekit_search_styles` → `stylekit_get_style_tokens` + `stylekit_get_implementation_brief` →
**tokens 写进界面的文本规格和代码里**（不是再喂回生图）。要现成主题跑 `stylekit_get_shadcn_install`
给的命令，写完用 `stylekit_lint_code` 回查。

## 切图（一整张 → 项目里的单张）

要一批尺寸一致的小图（图标、缩略图、状态图）时，**出一整张网格图再切**，比逐张发便宜得多：
一次生成拿到全套，风格天然统一，加载只付一次。

```bash
# 1) 出整张：说清几×几、每格居中、纯色底、不要文字标签
python ~/.config/opencode/skills/genimg/scripts/genimg.py \
  --prompt "a 10 by 10 grid of 100 monochrome line icons on pure white, each icon centered in its own cell, thin consistent stroke, no text, no labels, no shadows" \
  --size 1024x1024 --slug icon-sheet --out /c/Files/Pictures/genimg

# 2) 切 + 缩到 32×32 + 去白底变透明，直接落到项目里
python ~/.config/opencode/skills/genimg/scripts/slice.py \
  --in "C:/Files/Pictures/genimg/<刚出的那张>.png" \
  --grid 10x10 --resize 32x32 --alpha 40 --square \
  --prefix icon --out "<project>/public/icons" --preview
```

- **先 `--preview`**：它存一张画了格线和编号的对照图。**切之前 1:1 看一眼格子对不对齐**，
  比切完发现半张图标再返工便宜。
- 模型有时空几格或画歪半格：脚本会报「这几格几乎纯色」和「右边余 N px 没进格子」。
  对齐偏了就调 `--gap` / `--inset` 再切，别重出整张。
- `--square` 按内容包围盒居中到正方形，切出来的图标尺寸才统一；`--alpha <容差>` 把
  接近背景色（四角取色）的像素抠成透明。
- `--names names.txt` 给每格起名（按行优先），文件名就是 `icon-<名字>.png`，代码里直接引用。
- 写 `<prefix>.manifest.json`（每格的位置、尺寸、是否空），要按语义挑图时用它。

## 交付

- **默认落 `C:\Files\Pictures\genimg\`**，不在项目里留副本。
  **要用的时候再复制进项目工作区**（`public/`、`assets/`、`src/assets/`），项目里改用相对路径引用。
  复制过去的是资源，**不要 gitignore**。
- **每槽一个 PNG，不拼并置图**；用户按页、按槽挑。重跑只重跑不通过的几个（`--skip-done`）。
- 代码里引用**本地文件路径**，不要服务给的 `/v1/images/files/<name>`——每次服务重启换目录，旧链接必 404。
- 每张旁有同名 `.meta.json`（真实 prompt、参数、seed、耗时）。**要复现或要改一处重跑，照它发**：
  同 prompt + 同 seed + 同配置 → 逐字节相同，所以每种写法跑一次就够。
- 输出的 PNG 虽带 alpha 通道，但实测全不透明 → **要透明底**就在 prompt 里要纯色底再由我抠
  （整张网格图用 `slice.py --alpha`），或者这类东西本来就该让代码画 SVG。

## 能力

默认它什么都能画好，**不预设「这类画不了」**，也不在动手前替用户排除方向。
用户指出某张不好时：当次说清原因和换法（必要时查 prompt-recipes.md 末尾的「已测边界」），
**不要改这份 skill** —— 一次不满意不构成规则。
