# 接口契约 · 网关（fastaitoken，实测于 2026-10-28）

**这文件只有接口**：请求、参数支持、响应字段、计费、耗时、边界。
**各题材的写法与参考 prompt 全文在 `prompt-recipes.md`；「这条需求该不该出图」在 `../SKILL.md` §0。**

下方另有一节「本机 Strata 后端（实测于 2026-10-30 / 10-31）」，那节才是默认后端。

## 请求

```
POST https://fast.ns.tisoz.com/v1/images/generations
Authorization: Bearer <GENIMG_API_KEY>
Content-Type: application/json

{"model":"gpt-image-2","prompt":"...","size":"1024x1024","quality":"low","n":1,"output_format":"png"}
```

实测耗时：1024x1024 + quality=low ≈ 25–40 秒；**quality=high + 1536x1024 或 1024x1536 ≈ 23–32 秒**（实测 2026-11-01 16:4x–16:5x，6 张）。
`quality` 确实生效（high 的细节明显比 low 多）。**1024x1536 这类竖屏可用**，长边不超 3840。

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
- **偶发断连（实测 2026-11-01 16:4x）**：`[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol`。
  同一请求连断 4 次出现过，**重试（脚本里 3 次）就能过**，不是参数问题也不是鉴权问题。
  因为按张计费，**补跑要跳过已经出过图的项**（`s19_concept_ui.py --only … --skip-done`），
  判断依据是同名 `.meta.json` 里记的 backend + job key。取图那一步（`url` 下载）也会断，要单独重试。

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
| **1024×2048（2.1 MP，整页 APP）** | 服务端 **49.4–55.6 s**（sampling 41–42 / VAE 7.8）；六个样本 | 实测 2026-11-01 17:1x–17:4x |
| **1152×2048（2.36 MP，整页 web）** | 服务端 **54.0–61.0 s**（sampling 43–45 / VAE 7.6）；五个样本 | 实测 2026-11-01 17:1x–17:4x |
| **prompt 长度不影响耗时** | 1126 → 2578 字符，同一尺寸服务端都是 49–61 s → **写多长不加时间**，只影响画面（见「一整页产品」节的长度上限） | 实测 2026-11-01（12 臂） |
| **任意尺寸怎么估** | 各档折算是 **26.7 / 23.4 / 26.7–27.7 / 23.5–26.5 s/MP** → 粗估取 **~26 s/MP**（1.77 MP 那档略低只有一个样本，不外推规律）。给用户报时间用它，别说"几十秒" | 由上面三行折算 |
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


## 本 skill 走 HTTP 做不了的（不是模型没有）

- **图生图 / 换角度 / 换服装**：模型侧**跑通了**，靠离线 sd-cli 的 `-i <图> --strength <0..1>`；
  **这条没有接进 serve 的 HTTP API**，所以本脚本发不出去。配方（实测 PSNR 对原图）：
  `--strength 0.35` → 29.21 dB（修图、去瑕疵）；`0.75` 默认 → 22.04 dB（同场景同构图，身份只部分保留）；
  `0.95` → 19.34 dB（prompt 不变时构图仍没散架）；**`0.75` + 换 prompt → 换服装与机位成功，场景与人脸保留**。
  → **实际配方是 `-i` + `--strength 0.7~0.8` + 把要改的部分重写进 prompt、其余不动**。
  这条是 img2img，本机模型也不是 edit 版；输入图要先推到远端（serve 子进程在临时目录，只认远端路径）。
  参考脚本：`C:\Files\Codes\unaserver\scripts\s14_img_refedit.py`。
- 局部编辑、去背景：两个后端都没有。

