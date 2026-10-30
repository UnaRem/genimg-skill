---
name: genimg
description: 生成图片/生图/配图/插图/图标/头像/海报/封面/背景图，或英文 generate an image, illustration, icon, avatar, hero art, wallpaper。默认用 fastaitoken 网关的 gpt-image-2，可加 --backend local 切到本机 Strata 生图；生成结果落盘到本地。
---

# 生图（默认 fastaitoken · gpt-image-2，可选本机 Strata）

一句大白话描述 → 写成结构化 prompt → 调脚本 → 自查 → 给用户验收。

## 唯一执行入口

```bash
python ~/.config/opencode/skills/genimg/scripts/genimg.py \
  --prompt "英文描述" --slug "中文短名"
```

- 只走这一个脚本，不要自己拼 curl。契约与实测细节见 `references/api.md`。
- 脚本路径按 `~/.config/opencode/skills/genimg/` 写（Git Bash 下 `~` 会展开），别写死某台机器的用户名。
- key 由脚本从 skill 目录 `.env` 读取，**任何时候不要把 key 打印出来或写进回复**。换 key 直接改 `.env`；
  要临时覆盖用 `GENIMG_API_KEY=... python ...`，**不要用 `FASTITOKEN_IMAGE_KEY=`**——这个名字会被本机
  shell 链路从子进程环境里剥掉（实测，见 `references/api.md`）。
- 输出默认 `C:\Files\Pictures\genimg\`，同时写同名 `.meta.json`（请求参数、响应、耗时）。
- 脚本最后一行 `LOCAL=<路径>` 就是成品，用 `read` 打开它看效果。

## 流程

1. 先定用途和形状：方图（头像/图标/贴纸）`1024x1024`；横图（封面/横幅/PPT）`1536x1024`；竖图（手机壁纸/海报）`1024x1536`。
2. 写 prompt：英文为主，结构为 主体 + 风格 + 构图/光线 + 背景。风格词要具体（flat illustration、watercolor、3D render、line art），避免"beautiful""nice"这类空词。
3. 用户要求图上出现文字时，先说明风险：模型生成中文文字容易出错，可能需要多轮。文字内容用引号写进 prompt。
4. **第一次必定用默认参数**：`1024x1024` + `quality=low`，先出草稿。
5. `read` 打开成品自查：主体是否正确、有无乱码文字、是否被裁切、风格是否符合。有明显问题就改 prompt 重来，没问题才给用户看。
6. 用户认可后才升级：`--quality medium`，或按需换尺寸。升级前告知耗时会更长。

## 成本护栏（默认后端 gateway）

按次计费，1K 尺寸档 $0.10/张，2K 尺寸档 $0.15/张。

- 默认不出超过 1024 的尺寸。要出大图必须显式加 `--force-large`，且先跟用户确认。
- 脚本不自动重试。退出码非 0 时把状态码和错误体原样转给用户，不要擅自重试——重试就是再扣一次钱。
- 一次 `--n 1`。需要多张备选时先说明数量和费用，用户同意再调大 `--n`。

## 本机后端（`--backend local`，默认不用）

同一台局域网机器（unaserver :8080）上的 Strata 生图端点。**不花钱，代价是时间**，而且会打断正在用那台机器对话的会话。

选哪个后端：

- **干活中途顺手要一张草稿 → 用 gateway**（默认）。本机后端会把正在跑对话的会话整个卸掉。
- **用 local 的理由只有这几条**：一次要出好几张、断网/不想花钱、要 `--seed` 逐字节复现。真用就**一次出完**（`--n` 到 4），引擎重载只付一次。

代价（实测，2026-10-30）：

| 项 | 实测值 |
|---|---|
| 1024×1024 | 服务端 **27.6 s**（sampling 18.7 + VAE 4.7），客户端 29.8 s |
| 2048×2048 | **112.0–116.3 s** |
| 排队 | 生图占服务的**单生成令牌 FIFO**，期间所有 chat 排队（实测一条 chat 等了 **107.2 s**） |
| 卸引擎 | `gpu_policy: unload` → 会话 KV 丢失；下一个请求付**引擎重载 ~66 s** + **按上下文长度重读**（实测 44.4k tokens 21 s；200K 上下文约 61 s） |
| 一次生图的完整打断 | 1024² ≈ **115 s**，2048² ≈ **232 s**，严格串行 |

硬限制与差异（照做，别硬套网关那套参数）：

- 尺寸：**每边 256–2048 且必须是 32 的倍数**。上面那三种形状都合法。
- `--n` 1–4；只出 png。
- **没有 `quality` 阶梯**：固定 8 步（Turbo `--sigmas`）。`--quality` 会被忽略；"先 low 出草稿再升 medium"在 local 不成立，只能靠尺寸省时间。
- `--seed` 只在 local 可用：同 prompt + 同 seed + 同配置 → PNG 逐字节相同。配 gateway 会退出码 2。
- **超时给足（脚本已设 900 s）**：客户端断开服务端会**取消作业**，跟网关"已计费"完全不同，别中途掐。
- 两个键在 `.env`：`STRATA_LOCAL_URL`（默认 `http://192.168.1.21:8080`）、`STRATA_LOCAL_KEY`（取自远端 `/data/Strata/strata-iq3_s.json` 的 `api_key`）。同样不要打印。

```bash
# 先不花钱、不占 GPU 地确认连得通
python ~/.config/opencode/skills/genimg/scripts/genimg.py --prompt x --check --backend local
# 真出一张（超过 1024 要 --force-large）
python ~/.config/opencode/skills/genimg/scripts/genimg.py --backend local \
  --prompt "..." --slug "中文短名" --size 1024x1024 --seed 7
```

## 排查

不花钱的自检（校验 key 与参数，不请求接口；`--backend local` 会额外探一次 `/health`，不占 GPU）：

```bash
python ~/.config/opencode/skills/genimg/scripts/genimg.py --prompt x --check
python ~/.config/opencode/skills/genimg/scripts/genimg.py --prompt x --check --backend local
```

## 退出码

`0` 成功 / `1` 响应里没有图片 / `2` 参数或缺 key / `3` HTTP 错误 / `4` 网络或超时（`local --check` 探活不通也算）。

## 不做

- 图生图、局部编辑、去背景：两个后端都没有。需要时先单独验证再扩展。
- 批量超过 4 张：先停下确认预算（gateway）或确认会话可以被打断（local）。
- 不加 `steps` 旋钮：实测 `steps 8→6` 省 26% 但画质明显变差，已判定不用。
- 不在对话中间穿插 local 生图。
