# 接口契约（本机实测于 2026-10-28）

## 请求

```
POST https://fast.ns.tisoz.com/v1/images/generations
Authorization: Bearer <FASTITOKEN_IMAGE_KEY>
Content-Type: application/json

{"model":"gpt-image-2","prompt":"...","size":"1024x1024","quality":"low","n":1,"output_format":"png"}
```

实测耗时：1024x1024 + quality=low ≈ 25–40 秒。

**必须带非默认 User-Agent**：默认 `Python-urllib/3.x` 会被网关前面的 Cloudflare 拦成
`HTTP 403 / error code: 1010`，请求根本没到鉴权。`curl` 和自定义 UA 实测可以通过。
输出的 PNG 实测就是请求的 1024x1024，无隐式放大。

## API key 的来源

- 稳定路径：skill 目录下的 `.env`（已实测多次）。
- 环境变量 `FASTITOKEN_IMAGE_KEY` 在本机 pwsh → Git Bash → python 这条链路里注入时灵时不灵，
  **不要依赖它做临时覆盖 key**，要换 key 直接改 `.env`。

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
