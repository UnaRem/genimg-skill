#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文生图：调用 fastaitoken 网关的 gpt-image-2，落盘到本地。

仅用 Python 3.9 标准库。契约见同 skill 的 references/api.md。

退出码：
  0 成功
  1 响应里没有图片（结构变化或被风控拦截）
  2 参数错误 / 缺少 API key
  3 HTTP 错误（状态码与错误体原样打印）
  4 网络错误或超时

按次计费：脚本不自动重试，失败就是失败，是否再试由人决定。
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API_URL = "https://fast.ns.tisoz.com/v1/images/generations"
USER_AGENT = "genimg/1.0 (opencode skill)"
DEFAULT_OUT_DIR = Path("C:/Files/Pictures/genimg")
DEFAULT_SIZE = "1024x1024"
QUALITY_CHOICES = ("low", "medium", "high")
# 实测计费按尺寸分档：1K 档 $0.10/张，2K 档 $0.15/张，超过 1K 要先确认
LARGE_LIMIT = 1024
TIMEOUT = 300

EXIT_OK = 0
EXIT_NO_IMAGE = 1
EXIT_USAGE = 2
EXIT_HTTP = 3
EXIT_NETWORK = 4


def eprint(msg):
    print(msg, file=sys.stderr)


def load_key(skill_dir):
    """环境变量优先，其次 skill 目录下的 .env。返回 (key, 来源说明)。"""
    env_key = os.environ.get("FASTITOKEN_IMAGE_KEY", "").strip()
    if env_key:
        return env_key, "环境变量 FASTAITOKEN_IMAGE_KEY"

    env_file = skill_dir / ".env"
    if env_file.exists():
        for raw in env_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == "FASTITOKEN_IMAGE_KEY":
                value = value.strip().strip('"').strip("'")
                if value:
                    return value, str(env_file)
    return "", ""


def parse_size(text):
    """把 1024x1024 / 1024*1024 归一化成 '1024x1024'，非法则退出。"""
    normalized = text.strip().lower().replace("*", "x").replace("×", "x")
    match = re.fullmatch(r"(\d{3,4})x(\d{3,4})", normalized)
    if not match:
        eprint("[genimg] size 格式应为 宽x高，例如 1024x1024（收到：%s）" % text)
        sys.exit(EXIT_USAGE)
    width, height = int(match.group(1)), int(match.group(2))
    if max(width, height) > 3840:
        eprint("[genimg] 网关限制长边 ≤ 3840，收到 %dx%d" % (width, height))
        sys.exit(EXIT_USAGE)
    return "%dx%d" % (width, height)


def sanitize_slug(text):
    """把描述变成可用文件名，保留中文。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", text).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned[:40] or "image"


def post_image(key, body):
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            # 默认 UA 是 Python-urllib/3.x，会被网关前面的 Cloudflare 拦成 403 error code: 1010
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        eprint("[genimg] HTTP %s" % exc.code)
        eprint(detail[:2000])
        sys.exit(EXIT_HTTP)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        eprint("[genimg] 网络失败：%s" % exc)
        sys.exit(EXIT_NETWORK)


def download(url, dest):
    request = urllib.request.Request(url, headers={"User-Agent": "genimg/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            dest.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        eprint("[genimg] 图片下载失败：%s" % exc)
        eprint("[genimg] 接口已计费，图片地址保留在同名 .meta.json 里，可直接用 curl 补下载")
        sys.exit(EXIT_NETWORK)


def main():
    parser = argparse.ArgumentParser(
        description="调用 fastaitoken gpt-image-2 生成图片并保存到本地",
    )
    parser.add_argument("--prompt", required=True, help="图片描述（建议英文为主）")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="宽x高，默认 1024x1024")
    parser.add_argument(
        "--quality", choices=QUALITY_CHOICES, default="low",
        help="画质，默认 low（先出草稿）",
    )
    parser.add_argument("--n", type=int, default=1, help="张数，默认 1")
    parser.add_argument("--slug", default="", help="文件名后缀，默认取 prompt 前若干字符")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="输出目录")
    parser.add_argument(
        "--force-large", action="store_true",
        help="确认接受超过 1024 的尺寸（计费档位会从 $0.10 升到 $0.15）",
    )
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    key, key_source = load_key(skill_dir)
    if not key:
        eprint("[genimg] 未找到 API key：设置环境变量 FASTAITOKEN_IMAGE_KEY，"
               "或在 %s 写 FASTAITOKEN_IMAGE_KEY=..." % (skill_dir / ".env"))
        sys.exit(EXIT_USAGE)

    size = parse_size(args.size)
    if max(int(size.split("x")[0]), int(size.split("x")[1])) > LARGE_LIMIT and not args.force_large:
        eprint("[genimg] %s 超过 1K 计费档，可能按 $0.15/张 计费；"
               "确认要出大图请加 --force-large" % size)
        sys.exit(EXIT_USAGE)

    if args.n < 1:
        eprint("[genimg] --n 至少为 1")
        sys.exit(EXIT_USAGE)

    body = {
        "model": "gpt-image-2",
        "prompt": args.prompt,
        "size": size,
        "quality": args.quality,
        "n": args.n,
        "output_format": "png",
    }

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    stem = "%s_%s" % (stamp, sanitize_slug(args.slug or args.prompt))

    eprint("[genimg] key 来源：%s" % key_source)
    eprint("[genimg] POST %s size=%s quality=%s n=%d" % (API_URL, size, args.quality, args.n))
    started = time.time()
    status, text = post_image(key, body)
    elapsed = time.time() - started

    try:
        data = json.loads(text)
    except ValueError:
        eprint("[genimg] 响应不是 JSON（HTTP %s）：" % status)
        eprint(text[:2000])
        sys.exit(EXIT_NO_IMAGE)

    items = data.get("data") or []
    if not items:
        eprint("[genimg] 响应里没有 data 字段：")
        eprint(text[:2000])
        sys.exit(EXIT_NO_IMAGE)

    meta_path = out_dir / (stem + ".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "requested": body,
                "elapsed_seconds": round(elapsed, 1),
                "response": data,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    saved = []
    for index, item in enumerate(items, start=1):
        dest = out_dir / ("%s_%d.png" % (stem, index) if len(items) > 1 else stem + ".png")
        url = item.get("url")
        b64 = item.get("b64_json")
        if url:
            download(url, dest)
        elif b64:
            import base64
            dest.write_bytes(base64.b64decode(b64))
        else:
            eprint("[genimg] 第 %d 项既没有 url 也没有 b64_json，跳过" % index)
            continue
        saved.append(dest)

    if not saved:
        eprint("[genimg] 没有任何图片落盘，响应存到 %s" % meta_path)
        sys.exit(EXIT_NO_IMAGE)

    for dest in saved:
        print("LOCAL=%s" % dest)
    eprint("[genimg] 完成：%d 张，%.1fs，meta: %s" % (len(saved), elapsed, meta_path))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
