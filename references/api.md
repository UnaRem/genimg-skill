# 接口契约 · 网关（fastaitoken，实测于 2026-10-28）

下方另有一节「本机 Strata 后端（实测于 2026-10-30）」。

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

## 未验证

- `input_images` / 图生图 / 局部编辑：文档参数里出现过 `input_images`，未实测。
- 尺寸上限「长边 ≤ 3840、方形 ≤ 1024（实测方形 1024 请求输出正好 1024）」中的更大尺寸档位。
- `seed`：网关没有试过（本机后端实测可复现，见下一节）。

---

# 本机 Strata 后端（实测于 2026-10-30）

`--backend local` 走这台局域网机器上的 unaserver。以上网关那一节的内容不受影响。

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
| `n` | 1–4。报错原文：`n: a whole number from 1 to 4` |
| `prompt` | 非空、≤16000 字符、无 NUL |
| `seed` | 本机独有。**同 prompt + 同 seed + 同配置 → PNG 逐字节相同**（sha256 实测一致） |
| `steps` | 本机独有，固定 8（Turbo `--sigmas`）。`steps 8→6` 省 26% 但画质明显变差（PSNR 16.37 dB）→ **已判定不用** |
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
| 1024×1024 | 服务端 **27.62 s**（sampling 18.72 + VAE 4.74），客户端端到端 **29.8 s** | 实测 2026-10-30 21:06，`--seed 7` |
| 2048×2048 | **112.0–116.3 s**（sampling 95.6–98.8，占 85%；VAE 12.4 s）；纯生图峰值 18942 MiB | 实测（unaserver 侧记录） |
| 排队 | 生图占**单生成令牌 FIFO**，期间 chat 全排队：实测一条 chat 等 **107.2 s** | 实测 |
| 卸引擎 | 日志原文 `image job: the conversation could not be saved (session files do not support --layer-split); unloading the model` → KV 必丢 | 实测 2026-10-30 13:06 |
| 引擎重载 | 生图结束到 `the engine is running again` 实测 **66 s**（13:07:29→13:08:35） | 实测 2026-10-30 13:07 |
| 上下文重读 | 重载后 `reading the prompt: 44,443 of 44,506 tokens` 用时 **21 s**（≈2.1k tok/s）。200K 上下文另测得 ~61 s → **重读代价按上下文长度走** | 实测 2026-10-30 13:08 |
| 一次生图的完整打断 | 1024² ≈ **115 s**；2048² ≈ **232 s** | 上面几项相加 |
| 客户端断开 | `_watch_client` 会**取消作业**（与网关"已计费"完全不同）→ 脚本超时给到 900 s，别中途掐 | 读码 + 实测 |

服务端 journal 的对账行（`journalctl -u strata`，免费）：

```
[strata] image: 1024x1024, n=1, 8 steps, seed 7
[strata] image done in 27.6 s (unload)
[strata] loading the model again (it was unloaded) ...
```

## 本机后端没有的能力

- `quality` 阶梯：不存在（固定 8 步）。
- 图生图 / 局部编辑 / 去背景 / 负向提示：两个后端都没有。
- 画质对比**没做过**：只跑过一句水彩灯塔提示词。中文文字渲染、复杂指令遵循、写实人像都未测。
  （Qwen-Image 系以中文文字见长，这是背景知识，不是实测结论。）

