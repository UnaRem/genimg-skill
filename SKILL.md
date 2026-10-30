---
name: genimg
description: 生成图片/生图/配图/插图/图标/头像/海报/封面/背景图，或英文 generate an image, illustration, icon, avatar, hero art, wallpaper。默认用本机 Strata 的 Qwen-Image-2.1-Turbo（局域网 unaserver:8080，不花钱）；只有明确要 gpt-image-2 时加 --backend gateway 走 fastaitoken 网关。生成结果落盘到本地。
---

# 生图（默认本机 Strata · Qwen-Image-2.1-Turbo，可选 fastaitoken · gpt-image-2）

一句大白话描述 → 写成结构化 prompt → 调脚本 → 自查 → 给用户验收。

## 唯一执行入口

```bash
python ~/.config/opencode/skills/genimg/scripts/genimg.py \
  --prompt "英文描述" --slug "中文短名"
```

- **默认后端 = 本机 Strata**（不花钱）。只有用户明确要 **gpt-image-2** 时才加 `--backend gateway`。
  要改默认值就在 `.env` 写 `GENIMG_BACKEND=gateway`；命令行参数总是优先。
- 只走这一个脚本，不要自己拼 curl。两个后端的契约与实测细节见 `references/api.md`。
- 脚本路径按 `~/.config/opencode/skills/genimg/` 写（Git Bash 下 `~` 会展开），别写死某台机器的用户名。
- key 由脚本从 skill 目录 `.env` 读取，**任何时候不要把 key 打印出来或写进回复**。
  网关臂临时覆盖用 `GENIMG_API_KEY=... python ...`，**不要用 `FASTITOKEN_IMAGE_KEY=`**——这个名字会被本机
  shell 链路从子进程环境里剥掉（实测，见 `references/api.md`）。
- 输出默认 `C:\Files\Pictures\genimg\`，同时写同名 `.meta.json`（请求参数、响应、耗时）。
- 脚本最后一行 `LOCAL=<路径>` 就是成品，用 `read` 打开它看效果。

## 流程

1. 先定用途和形状：方图（头像/图标/贴纸）`1024x1024`；横图（封面/横幅/PPT）`1536x1024`；竖图（手机壁纸/海报）`1024x1536`。
2. 写 prompt：英文为主，结构为 主体 + 风格 + 构图/光线 + 背景。风格词要具体（flat illustration、watercolor、3D render、line art），避免"beautiful""nice"这类空词。
3. 用户要求图上出现文字时，先说明风险：模型生成中文文字容易出错，可能需要多轮（本机这档的中文文字渲染未测）。文字内容用引号写进 prompt。
4. **第一次用默认参数**：`1024x1024`，本机后端。要更多候选就在同一句里加 `--n 2`（一次作业出多张，引擎重载只付一次）。
5. `read` 打开成品自查：主体是否正确、有无乱码文字、是否被裁切、风格是否符合。有明显问题就改 prompt 重来，没问题才给用户看。
6. 要更大尺寸：超过 1024 必须加 `--force-large` 并先说明代价（见下表的分钟数）。
7. 只有用户明确要 gpt-image-2 时才切 `--backend gateway`，那条臂才谈 `--quality` 阶梯与按次计费。

## 默认后端：本机 Strata（Qwen-Image-2.1-Turbo）

同一台局域网机器（unaserver :8080）。**不花钱，代价是时间**，而且会打断正在用那台机器对话的会话——
如果那就是你自己在用的会话，一次 1024² 的完整打断 ≈ **115 s**，2048² ≈ **232 s**，严格串行。

| 项 | 实测值（2026-10-30） |
|---|---|
| 1024×1024 | 服务端 **27.6 s / 28.4 s**（两次独立，±1.5%；sampling 18.7–19.4 + VAE 4.7），客户端 29.8–30.9 s |
| 2048×2048 | **112.0–116.3 s**（sampling 95.6–98.8 占 85%） |
| 排队 | 生图占服务的**单生成令牌 FIFO**，期间所有 chat 排队（实测一条 chat 等了 **107.2 s**） |
| 卸引擎 | `gpu_policy: unload` → 会话 KV 丢失；下一个请求付**引擎重载 60–66 s**（三次实测 59/63/66）+ **按上下文长度重读**（44.4k tokens 21 s；200K 上下文约 61 s） |

**要出多张就这次一次出完**（`--n` 到 4，同一个作业），重载只付一次。别在对话中间穿插多次单张生图。
实测单价：1024² `--n 1` = 28 s，`--n 2` = **46 s** → **第二张只多 18 s**（加载与文本编码共摊）。要候选就直接 `--n 2`。

已实测过的题材（只有这两类，别当成通用能力）：水彩灯塔插画；**写实裸体人体**——全身比例、姿态、直视镜头的眼神、
皮肤光影都对，无乱码文字、无裁切；**已知瑕疵是手指**。未测：中文文字渲染、多约束指令遵循、多人构图。

硬限制与差异（照做，别硬套网关那套参数）：

- 尺寸：**每边 256–2048 且必须是 32 的倍数**。上面那三种形状都合法。
- `--n` 1–4；只出 png。
- **没有 `quality` 阶梯**：固定 8 步（Turbo `--sigmas`）。`--quality` 会被忽略；"先 low 出草稿再升 medium"在这里不成立，只能靠尺寸省时间。
- `--seed` 可用且值得用：同 prompt + 同 seed + 同配置 → PNG **逐字节相同**（做质量 A/B 不必重复采样）。
- **超时给足（脚本已设 900 s）**：客户端断开服务端会**取消作业**，跟网关"已计费"完全不同，别中途掐。
- 两个键在 `.env`：`STRATA_LOCAL_URL`（默认 `http://192.168.1.21:8080`）、`STRATA_LOCAL_KEY`（取自远端 `/data/Strata/strata-iq3_s.json` 的 `api_key`）。同样不要打印。

```bash
# 先不花钱、不占 GPU 地确认连得通（默认后端就是本机，--check 会探 /health）
python ~/.config/opencode/skills/genimg/scripts/genimg.py --prompt x --check
# 真出一张（超过 1024 要 --force-large）
python ~/.config/opencode/skills/genimg/scripts/genimg.py \
  --prompt "..." --slug "中文短名" --size 1024x1024 --seed 7
```

## 付费后端：fastaitoken · gpt-image-2（只在明确要求时用）

```bash
python ~/.config/opencode/skills/genimg/scripts/genimg.py --backend gateway \
  --prompt "..." --slug "中文短名" --quality low
```

- 按次计费：1K 尺寸档 $0.10/张，2K 档 $0.15/张。实测 1024² + `quality=low` ≈ 25–40 s。
- **默认不出超过 1024 的尺寸**；要大图必须 `--force-large` 且先跟用户确认。
- 脚本不自动重试。退出码非 0 时把状态码和错误体原样转给用户，不要擅自重试——重试可能再扣一次钱。
  例外：HTTP 500 `upstream_error` 是上游不可用，**不产出图**，可以用一个免费探针确认后再试一次
  （发一个参数错的请求，如 `"n":0`，返回 **400** 说明网关与鉴权活着、500 属于上游故障）。
- `--quality low → medium → high` 这条阶梯只有这条臂有；升级前告知耗时更长。
- 这条臂没有 `--seed`（未实测，脚本会退出码 2）。

## 排查

不花钱的自检（校验 key 与参数，不请求接口；本机后端还会探一次 `/health`，不占 GPU）：

```bash
python ~/.config/opencode/skills/genimg/scripts/genimg.py --prompt x --check
python ~/.config/opencode/skills/genimg/scripts/genimg.py --prompt x --check --backend gateway
```

## 退出码

`0` 成功 / `1` 响应里没有图片 / `2` 参数或缺 key / `3` HTTP 错误 / `4` 网络或超时（本机后端 `--check` 探活不通也算）。

## 不做

- 图生图、局部编辑、去背景：两个后端都没有。需要时先单独验证再扩展。
- 批量超过 4 张：先停下确认（本机：会话可以被打断多久；gateway：预算）。
- 不加 `steps` 旋钮：实测本机 `steps 8→6` 省 26% 但画质明显变差（PSNR 16.37 dB），已判定不用。
- 不拿本机后端做"文字在图上"的活，除非先测过中文渲染。
