# 界面交给代码模型：one-shot 规格模板（实测于 2026-11-02）

**这节解决什么问题**：需求是「做一个 web/app 产品或某个界面」时，怎么一条 prompt 让它一次生成到位。
五例实测的路径是 **文本规格 → 代码 → 本地构建渲染**：4 reproduced / 1 degraded；
同一批题走「先出设计图」两条路（prompt→图、图→代码）都是 0 reproduced / 5 degraded。
出处：`C:\Files\Codes\unaserver\goodcase-eval\`（三份 `eval-*.json` + `README.md`）。

## 一条能用的规格（照这个骨架填，别只写「做个 XX 页面」）

````text
做一个 <产品名> 的 <界面：落地页 / 后台列表页 / 移动 App 某页>，React + Tailwind，可直接运行。

【风格方向】<把 StyleKit 的 tokens 抄在这里：主色/强调色、圆角、阴影、字号阶、anti-patterns>
【骨架，从上到下逐区列全】1) 顶部导航 2) 主视觉 3) 客户 logo 行 4) 三张特性卡 5) 定价 6) 页脚
   —— 缺的区不会出现，所以要列全。
【每区的关键文案逐字给出】区 2：主标题两行，第一行 "Work Smarter." 第二行 "Move Faster."；
   副文案 "…"；主按钮 "Begin Free Trial"；下方微文案 "…"；输入框 placeholder "…"
   —— 没给文案的地方它一定自己编（实测会补规范外的微文案）。
【重复内容按单位绑定】多列写 "Row one, LEFT card: 标题…说明…" / "RIGHT card: …"；
   单列写 "Card 1: …"。不要写「特性有 A、B、C」这种一行清单——实测会跨卡串文案、标题重复。
【数量与显隐写死】导航四项、特性三张、移动端菜单 sm:hidden。
【配色与层级写成可校验的关系】强调色只有一处、面积 <2%，界面框架全部中性；
   焦点块写成尺寸差（"twice the height of any other block"）。
【素材】真实图片/视频给 URL 或本地路径；不给就要求它用同尺寸占位块，别自己找。
【交互状态】条件渲染要说明触发条件（"点 tab 才渲染对应浮层"），否则按静态截图判定会误判。
````

- **规格长度不是问题**：实测 3.9k–10.4k 字符的规格都能一次做对（最长那条 16/16 文案全中）。
- **别把类名当规格给它之外的东西**：给代码模型时 Tailwind 类名可以直说（它能执行）；
  这条只针对生图——生图会把 `max-w-7xl`、`#191919` 当画面文案画出来。

## 调用参数（本机 Strata，实测）

- **`max_tokens` 至少给 32000**：`16000` 五题里截断 2 题（thinking 写 3.4–4.9 万字符），
  被截断的代码会退化（见过结尾复读 `'eu'eu'eu…` 导致构建失败）。判「成没成」先看 `finish_reason`。
- **`temperature=0`**，每个界面全新上下文，别接着上一轮的对话往下写。
- **耗时**：单题 84–280 s（thinking 是成本主体），五题整批 ~14 分钟。**要快就先做一屏。**
- 一个完整产品**按路由拆开发**：一次调用做一屏/一路由，共用 tokens 单独给一遍（实测多页拆发比
  一整坨长规格更可控）。做完全站再补资源图（走 `genimg.py`，见 SKILL.md §0/§2）。

## StyleKit 那一步怎么用

1. `stylekit_search_styles`（按 modern/minimal/retro/expressive 或关键词）选一个 slug；
2. `stylekit_get_style_tokens` + `stylekit_get_implementation_brief` 读 tokens 与 anti-patterns，
   **抄进上面那份规格的风格段**；要现成主题可跑 `stylekit_get_shadcn_install` 给的命令；
3. 生成完用 `stylekit_lint_code` 回查，不合格再 `stylekit_repair_code`。

**tokens 别写进生图 prompt**（实测不改画面）；它们只对代码有效。

## 验收（别只看代码）

```sh
# 本地起个 vite + tailwind v4 的壳子，构建 + 1920x1088 截图，参考 goodcase-eval/render/
python to_project.py && cd render && bunx vite build && python -m http.server 5199 --bind 127.0.0.1
```

- **文案命中用 `document.textContent`（空白归一）+ input placeholder 自动判定**，
  但条件渲染要按交互采样：tab 浮层、打字机、`sm:hidden` 菜单在某一瞬间取不到，据此判负会误判。
- **页面上出现占位符或规格残渣 = 判负**：遍历可见文本节点，命中 `TODO` / `Lorem ipsum` /
  `font-family:` / `@import` / `px-` 就算垃圾节点（这条是用来抓「照着图实现」的病的，见 §0）。
- 字体 CDN（Google Fonts / onlinewebfonts）在本机浏览器不可达，回退不算判负；
  CloudFront 视频与 framerusercontent 图片可达。
