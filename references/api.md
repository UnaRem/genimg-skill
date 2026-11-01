# 接口契约 · 网关（fastaitoken，实测于 2026-10-28）

下方另有一节「本机 Strata 后端（实测于 2026-10-30 / 10-31）」，那节才是默认后端。

## 请求

```
POST https://fast.ns.tisoz.com/v1/images/generations
Authorization: Bearer <GENIMG_API_KEY>
Content-Type: application/json

{"model":"gpt-image-2","prompt":"...","size":"1024x1024","quality":"low","n":1,"output_format":"png"}
```

实测耗时：1024x1024 + quality=low ≈ 25–40 秒。

**必须带非默认 User-Agent**：默认 `Python-urllib/3.x` 会被网关前面的 Cloudflare 拦成
`HTTP 403 / error code: 1010`，请求根本没到鉴权。`curl` 和自定义 UA 实测可以通过。
输出的 PNG 实测就是请求的 1024x1024，无隐式放大。

## API key 的来源（实测于 2026-10-28）

- 稳定路径：skill 目录下的 `.env`，变量名 `GENIMG_API_KEY`（脚本同时接受旧名 `FASTITOKEN_IMAGE_KEY`）。
- 命令行临时覆盖：`GENIMG_API_KEY=sk-xxx python ...` 实测可用（覆盖后 `KEY_LEN` 会变）。
- **`FASTITOKEN*` 开头的变量传不进子进程**：bash 里 `printenv` 有值，python 的 `os.environ` 里是 `None`；
  与用 pwsh 还是 Git Bash 无关，换成 `GENIMG_API_KEY` 这类名字就正常。过滤规则未知，别依赖这个名字。
- 排查用 `--check`：只校验 key 和参数并打印来源、长度，不请求接口，不花钱。

## 响应（实测）

```json
{
  "created": 1793172463,
  "data": [
    {
      "url": "https://fast-img.ns.tisoz.com/outputs/xxxx.png",
      "revised_prompt": "原 prompt\n【以下是这张图的参数，1024x1024，方图】"
    }
  ],
  "usage": {"input_tokens": 33, "output_tokens": 272, "total_tokens": 305}
}
```

图片 URL 可直接 curl 下载，实测得到 1024x1024 8bit RGB PNG，约 1 MB。

## 与官方文档不一致的地方（以实测为准）

| 文档写的 | 实测 |
| :--- | :--- |
| 端点 `POST https://fast.ns.tisoz.com`（根路径） | 根路径返回站点前端 HTML（HTTP 200，不是 API）。必须用 `/v1/images/generations`；带尾斜杠会 307 |
| 响应示例是 `b64_json` | 实际只返回 `url`。脚本两种都支持，优先 `url` |

`revised_prompt` 里网关会自动追加一句参数标注，不影响出图。

## 计费（控制台实测于 2026-10-28）

`gpt-image-2` 按次计费（计费模式显示「按次(图片)」，分组 `0.2x折扣限时OpenAI 普通分组`）：

| 档位 | 单价 |
| :--- | :--- |
| 1 张（1K） | $0.10 |
| 1 张（2K） | $0.15 |

- 响应里的 `usage` 只有 token 数，没有金额。
- `0.2x折扣` 是限时分组折扣，原价可能约 5 倍。折扣结束后要重新核对控制台。
- 计费档位按尺寸（1K/2K）走，与 `quality` 参数关系不明确——按尺寸控制成本即可。

## 失败形态（已知）

- 缺 key / key 错：HTTP 错误，错误体会返回，原样打印即可。
- 根路径或带尾斜杠的路径：拿到 HTML 或 307，脚本按「响应不是 JSON」报错退出。
- **上游不可用（2026-10-30 实测）**：`HTTP 500 {"error":{"message":"Upstream gateway error","type":"upstream_error"}}`，
  连 `"prompt":""` 这种应当本地拒绝的请求也是 500。**分辨是网关坏了还是我的参数坏了：发一个参数错的请求**
  （`"n":0` → **400 `n must be greater than 0`**）——返 400 说明网关与鉴权都活着，500 属于上游故障。
  这种 500 不产出图，重试不重复计费，但仍应先确认再试。

## 未验证

- `input_images` / 图生图 / 局部编辑：文档参数里出现过 `input_images`，未实测。
- 尺寸上限「长边 ≤ 3840、方形 ≤ 1024（实测方形 1024 请求输出正好 1024）」中的更大尺寸档位。
- `seed`：网关没有试过（本机后端实测可复现，见下一节）。

---

# 本机 Strata 后端（实测于 2026-10-30 / 10-31）

**这一节是默认后端**：脚本不带 `--backend` 就走这里（`DEFAULT_BACKEND = "local"`）。
要 gpt-image-2 才加 `--backend gateway`；改默认值可以在 `.env` 写 `GENIMG_BACKEND=gateway`（命令行参数优先）。
上面网关那一节的契约内容不受这次改默认值影响。

## 请求

```
POST http://192.168.1.21:8080/v1/images/generations
Authorization: Bearer <STRATA_LOCAL_KEY>
Content-Type: application/json

{"prompt":"...","size":"1024x1024","n":1,"response_format":"b64_json","seed":7}
```

- `GET /health` → **200 / 0.003 s**（服务已绑 LAN）；不带 key 访问 `/v1/models` → 401 `authentication_error`。
  `/health` 本身不需要鉴权（实测不带 key 也 200），脚本带着 key 发只为省掉一次歧义。
- api key 在远端 `/data/Strata/strata-iq3_s.json` 的 `api_key`（64 字符）。取它但别打印：

  ```sh
  cd /data/Strata && python3 -c "import json;print(json.load(open('strata-iq3_s.json',encoding='utf-8-sig'))['api_key'])"
  ```

## 参数支持（都是活服务器上的探针，不占 GPU）

| 项 | 实测 |
|---|---|
| `model` | **不校验**，照收（`serve/server.py:6908` 不做 model 检查）。脚本不发这个字段，发了会误导 |
| `quality` / `style` / `user` / `background` / `moderation` | **接受并忽略**（`serve/images.py:87` docstring 原文） |
| `output_format` | 只支持 `png`，别的才报错 |
| `response_format` | **默认就是 `b64_json`**（`images.py:96`）→ 脚本明确要 b64，落盘代码与网关共用 |
| `size` | 每边 **256–2048 且必须是 32 的倍数**。报错原文：`size 1023x1024: each side a multiple of 32 from 256 to 2048` |
| `n` | 1–4。报错原文：`n: a whole number from 1 to 4`。上限来自服务端配置 `max_n: 4`，**`n=3/4` 未实测** |
| `prompt` | 非空、≤16000 字符、无 NUL。**LoRA 也只能从这里进**（`<lora:文件.safetensors:权重>`），但现配置下 0 生效，见「本机后端的边界」 |
| **没有的参数** | 图生图/局部编辑要的 `image` / `input_images` / `strength`：**HTTP 端点都没有**（img2img 只在离线 sd-cli 上跑通，见文末「本 skill 走 HTTP 做不了的」）。负向也没有独立开关，否定只能写进 prompt（实测只部分遵守） |
| `seed` | 本机独有。**同 prompt + 同 seed + 同配置 → PNG 逐字节相同**（sha256 实测一致） |
| `steps` | 本机独有。**HTTP 接受 1–100，但本 skill 的 CLI 不暴露它**（要换步数只能自己 POST，例：`C:\Files\Codes\unaserver\scripts\s16_ui_arms.py --post e5`）。默认固定 8（Turbo `--sigmas`）。`steps 8→6` 省 26% 但画质明显变差（PSNR 16.37 dB）→ **已判定不用**；`steps 8→16` 对界面稿的文字**没有可辨提升**，单张 61.8 → 97.4 s → **也不用**（2026-11-01，见「界面稿」节） |
| `/v1/models` | 列出 `qwen3.8-flash-next-iq3_s` 与 `qwen-image-2.1-turbo` |

## 响应

```json
{
  "created": 1793200000,
  "data": [{"b64_json": "..."}],
  "strata": {"seconds": 27.62, "sampling_s": 18.72, "vae_decode_s": 4.74,
             "gpu_policy": "unload", "steps": 8, "seed": 7, "quant": "...", "backend": "..."}
}
```

`url` 形态也有，但是按 Host 头拼的绝对地址（`http://192.168.1.21:8080/v1/images/files/<name>.png`），
**服务重启后旧 URL 全 404**（产物目录每次启动换一个）→ 所以脚本明确要 `b64_json`。

**与网关不同的取图顺序**：脚本这里优先用 `b64_json`，其次才 `url`。原因是本机 `url` 可能已 404，
而 b64 就在手上；网关实测只返回 `url`，所以网关那条路径的行为没变。

## 耗时与真实代价（实测）

| 项 | 实测值 | 来源 |
|---|---|---|
| 1024×1024 | 服务端 **27.62 s**（sampling 18.72 + VAE 4.74），客户端 **29.8 s**；**第二次独立复现 28.42 s**（sampling 19.4 + VAE 4.73），客户端 **30.9 s** → 两次差 ±1.5%，**按「约 28 s」算** | 实测 2026-10-30 21:06（`--seed 7`）与 21:20（`--seed 11`），同一台 Windows |
| 1152×1536（1.77 MP，竖图） | **41.4 s**（sampling 30.9 / VAE 6.2），端到端 **44.7 s**；journal 独立复现过一次 → 非方形尺寸合法且已实测 | 实测 2026-10-31 15:58 |
| 2048×2048 | **112.0–116.3 s**（sampling 95.6–98.8，占 85%；VAE 12.4 s）；纯生图峰值 18942 MiB | 实测（unaserver 侧记录） |
| **任意尺寸怎么估** | 三档折算是 **26.7 / 23.4 / 26.7–27.7 s/MP** → 粗估取 **~26 s/MP**（1.77 MP 那档略低只有一个样本，不外推规律）。给用户报时间用它，别说"几十秒" | 由上面三行折算 |
| 排队 | 生图占**单生成令牌 FIFO**，期间 chat 全排队：实测一条 chat 等 **107.2 s** | 实测 |
| 卸引擎 | 日志原文 `image job: the conversation could not be saved (session files do not support --layer-split); unloading the model` → KV 必丢 | 实测 2026-10-30 13:06 |
| 引擎重载 | 三次实测 **59 / 63 / 66 s** → 按 **60–66 s** 算。重载由「下一个请求」触发（默认 `lazy`），不是自动发生 | 实测（journal 时间戳） |
| 上下文重读 | 重载后 `reading the prompt: 44,443 of 44,506 tokens` 用时 **21 s**；200K 上下文另测得 **~61 s** → **≈2.1k tok/s，按上下文长度线性放大，不是固定 60 s** | 实测 2026-10-30 13:08 |
| **作业之间** | **连续多个生图作业之间不付重载**：实测第二个作业 **42.5 s**、日志里没有重载（引擎已卸 → 策略自动标 `keep`）。所以一轮的「重载 + 重读」总共只付一次，付在这一轮之后的第一个 chat 请求头上 | 实测 2026-10-31 |
| 一次生图的完整打断 | 1024² ≈ **115 s**；2048² ≈ **232 s** | 上面几项相加 |
| 客户端断开 | `_watch_client` 会**取消作业**（与网关"已计费"完全不同）→ 脚本超时给到 900 s，别中途掐。中断过就先别声称出图：只认 journal 的 `image done in N s` 与远端 `/tmp/strata-images-*/` 里的新 png（实测一次 400 s 中断 → 0 个文件） | 读码 + 实测 2026-10-31 |

服务端 journal 的对账行（`journalctl -u strata`，免费）：

```
[strata] image: 1024x1024, n=1, 8 steps, seed 7
[strata] image done in 27.6 s (unload)
[strata] loading the model again (it was unloaded) ...
```

## 本机后端的边界（没有的 / 只有一半的）

- `quality` 阶梯：不存在（固定 8 步，Turbo `--sigmas`）。`--quality` 被接受并忽略。
  `steps 8→6` 实测省 26% 但画质明显变差（PSNR 16.37 dB）→ **已判定不用**。
  所以"先 low 出草稿再升 medium"这条流程在这里不成立，能省的只有尺寸。
- **负向只部分遵守**（写进 prompt 的否定，见「提示词写法」）；没有 `negative_prompt` 这类独立开关。
- **图生图 / 换角度 / 换服装：模型跑通了，但不在 HTTP 上** → 见文末「本 skill 走 HTTP 做不了的」。
  **局部编辑、去背景：两个后端都没有。**
- **LoRA 0 生效**：入口在 prompt（`<lora:文件:权重>`），但现配置 `native` 开 → `Only (0 / 448) LoRA tensors applied`；
  另有一道基座维度墙（社区那些都是 Qwen-Image 1.0 / Edit 基座，hidden 4096 vs 3072）。
  已下的两条 2.1 基座 LoRA 效果温和（只改光比/机位），**不值得为此关 `native`**。
  判据只有 sd.cpp 自己那句 `Only (x / y) LoRA tensors have been applied`。
- **画质档位之间没比过**（没有参照图就没法判"哪档好"）：换 quant 是同构图细节漂移（18.69 dB），不是质量阶梯。
- **图上文字（中文 / 英文）已实测可用**，见下一节「图上要放字就照这个写法」。
  以前那句「图里渲染中文文字未测」到此结案（2026-10-31 四臂 8 张，零错字）。
- 题材实测范围见「提示词写法」末尾那条；对照图与逐条数据在 `C:\Files\Codes\unaserver\2026-10-30-能力边界.md` §3 / §3a / §3b。

## 批量与「一轮出完」的真实单价

- **同 prompt 多候选用 `--n`**（一个作业）。实测：
  - 1024²：`n=1` **28.4 s** → `n=2` **46.4 s**（第二张只多 **18 s**）。
    另一次四臂 `n=2`（不同 prompt/seed）= **47.2 / 41.6 / 41.6 / 41.4 s** → 1024² `n=2` 落在 **41–47 s** 区间，
    单条作业有 ±10% 抖动，别把 46.4 当定值。
  - 1152×1536：`n=1` **41.4 s** → `n=2` **71.8–76.6 s**（端到端 72.5–79.2 s，四次独立作业，第二张多 **30–35 s**）
  → 便宜的是**加载与文本编码（~10 s）那一段**，不是每张都省 18 s。**别把 18 s 当通用值。**
- **不同内容就连着发多个作业**：作业之间不付重载（实测第二作业 42.5 s、日志无重载），
  所以一轮只付一次「重载 + 重读」。**穿插一次 chat 就多付一轮**，实测 80–120 s。
- 要「同一主题换一张重抽」用不同 `--seed`：换 seed 基本是换一张画（PSNR 12.7–13.7 dB ≈ 无关图的地板），
  而换 quant 只是同构图细节漂移（18.69 dB）。**人数、交合处这类模型画不准的东西，只能换 seed 多出候选挑。**
- **多张响应的计时陷阱**：`strata.sampling_s` / `vae_decode_s` **既不是作业总量也不能按张数换算，它们比单张还小**
  （1152×1536：`n=1` 报 30.9，`n=2` 报 27.0；1024²：`n=1` 报 18.7，`n=2` 报 13.64）。
  多张时这两个字段只能忽略，总量只看 `strata.seconds`（46.43 与客户端 48.8 s 对得上）或 journal 的 `image done in N s`。

## 提示词写法（实测配方，中英都行）

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

## 本 skill 走 HTTP 做不了的（不是模型没有）

- **图生图 / 换角度 / 换服装**：模型侧**跑通了**，靠离线 sd-cli 的 `-i <图> --strength <0..1>`；
  **这条没有接进 serve 的 HTTP API**，所以本脚本发不出去。配方（实测 PSNR 对原图）：
  `--strength 0.35` → 29.21 dB（修图、去瑕疵）；`0.75` 默认 → 22.04 dB（同场景同构图，身份只部分保留）；
  `0.95` → 19.34 dB（prompt 不变时构图仍没散架）；**`0.75` + 换 prompt → 换服装与机位成功，场景与人脸保留**。
  → **实际配方是 `-i` + `--strength 0.7~0.8` + 把要改的部分重写进 prompt、其余不动**。
  这条是 img2img，本机模型也不是 edit 版；输入图要先推到远端（serve 子进程在临时目录，只认远端路径）。
  参考脚本：`C:\Files\Codes\unaserver\scripts\s14_img_refedit.py`。
- 局部编辑、去背景：两个后端都没有。

