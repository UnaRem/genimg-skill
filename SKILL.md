---
name: genimg
description: 生成图片/生图/配图/插图/图标/头像/海报/封面/背景图，或英文 generate an image, illustration, icon, avatar, hero art, wallpaper。用 fastaitoken 网关的 gpt-image-2 生成并落盘到本地。
---

# 生图（fastaitoken · gpt-image-2）

一句大白话描述 → 写成结构化 prompt → 调脚本 → 自查 → 给用户验收。

## 唯一执行入口

```bash
python /c/Users/qrww-无界15xa-/.config/opencode/skills/genimg/scripts/genimg.py \
  --prompt "英文描述" --slug "中文短名"
```

- 只走这一个脚本，不要自己拼 curl。契约与实测细节见 `references/api.md`。
- key 由脚本从 skill 目录 `.env` 读取，**任何时候不要把 key 打印出来或写进回复**。换 key 直接改 `.env`，
  不要用环境变量注入——本机 shell 链路里环境变量注入不可靠（见 `references/api.md`）。
- 输出默认 `C:\Files\Pictures\genimg\`，同时写同名 `.meta.json`（请求参数、响应、耗时）。
- 脚本最后一行 `LOCAL=<路径>` 就是成品，用 `read` 打开它看效果。

## 流程

1. 先定用途和形状：方图（头像/图标/贴纸）`1024x1024`；横图（封面/横幅/PPT）`1536x1024`；竖图（手机壁纸/海报）`1024x1536`。
2. 写 prompt：英文为主，结构为 主体 + 风格 + 构图/光线 + 背景。风格词要具体（flat illustration、watercolor、3D render、line art），避免"beautiful""nice"这类空词。
3. 用户要求图上出现文字时，先说明风险：模型生成中文文字容易出错，可能需要多轮。文字内容用引号写进 prompt。
4. **第一次必定用默认参数**：`1024x1024` + `quality=low`，先出草稿。
5. `read` 打开成品自查：主体是否正确、有无乱码文字、是否被裁切、风格是否符合。有明显问题就改 prompt 重来，没问题才给用户看。
6. 用户认可后才升级：`--quality medium`，或按需换尺寸。升级前告知耗时会更长。

## 成本护栏

按次计费，1K 尺寸档 $0.10/张，2K 尺寸档 $0.15/张。

- 默认不出超过 1024 的尺寸。要出大图必须显式加 `--force-large`，且先跟用户确认。
- 脚本不自动重试。退出码非 0 时把状态码和错误体原样转给用户，不要擅自重试——重试就是再扣一次钱。
- 一次 `--n 1`。需要多张备选时先说明数量和费用，用户同意再调大 `--n`。

## 退出码

`0` 成功 / `1` 响应里没有图片 / `2` 参数或缺 key / `3` HTTP 错误 / `4` 网络或超时。

## 不做

- 图生图、局部编辑、去背景：网关未实测，需要时先单独验证再扩展。
- 批量超过 4 张：先停下确认预算。
