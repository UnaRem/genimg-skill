#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文生图：默认走本机 Strata 的 Qwen-Image-2.1-Turbo；--backend gateway 走 fastaitoken 网关的 gpt-image-2。落盘到本地。

仅用 Python 3.9 标准库。契约见同 skill 的 references/api.md。

退出码：
  0 成功
  1 响应里没有图片（结构变化或被风控拦截）
  2 参数错误 / 缺少 API key
  3 HTTP 错误（状态码与错误体原样打印）
  4 网络错误或超时（local 的 --check 探活不通也算）

按次计费：脚本不自动重试，失败就是失败，是否再试由人决定。
本机后端不花钱，但会独占 GPU 并卸掉正在用的 LLM，代价见 SKILL.md。
"""

import argparse
import base64
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

# 本机 Strata（实测契约见 references/api.md，2026-10-30）
DEFAULT_LOCAL_URL = "http://192.168.1.21:8080"
LOCAL_TIMEOUT = 900  # 2048² 实测 112–116 s，排队时 300 s 不够；客户端断开服务端会取消作业
LOCAL_SIZE_MIN = 256
LOCAL_SIZE_MAX = 2048
LOCAL_SIZE_STEP = 32
LOCAL_N_MAX = 4

# 默认走本机 Strata；只有明确要 gpt-image-2 时才用网关（.env 的 GENIMG_BACKEND 可改默认值）
DEFAULT_BACKEND = "local"
BACKEND_NAMES = ("GENIMG_BACKEND",)
BACKEND_CHOICES = ("gateway", "local")

EXIT_OK = 0
EXIT_NO_IMAGE = 1
EXIT_USAGE = 2
EXIT_HTTP = 3
EXIT_NETWORK = 4

# Windows 控制台默认 cp936，中文诊断信息会被上层当成二进制。固定按 UTF-8 输出。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def eprint(msg):
    print(msg, file=sys.stderr)


GATEWAY_KEY_NAMES = ("GENIMG_API_KEY", "FASTITOKEN_IMAGE_KEY")
LOCAL_KEY_NAMES = ("STRATA_LOCAL_KEY",)
LOCAL_URL_NAMES = ("STRATA_LOCAL_URL",)


def read_env_file(skill_dir):
    """把 skill 目录下的 .env 读成字典（后面的键覆盖前面的）。"""
    result = {}
    env_file = skill_dir / ".env"
    if not env_file.exists():
        return result
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            result[name.strip()] = value
    return result


def lookup_setting(names, env_map):
    """环境变量优先，其次 .env。返回 (值, 来源说明)。

    注意：实测 FASTAITOKEN_IMAGE_KEY 这个名字会被本机 shell 链路从子进程环境里剥掉，
    命令行临时覆盖要用 GENIMG_API_KEY。详见 references/api.md。
    """
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value, "环境变量 " + name
    for name in names:
        if env_map.get(name):
            return env_map[name], ".env 的 " + name
    return "", ""


def parse_size(text, backend):
    """把 1024x1024 / 1024*1024 归一化成 '1024x1024'，按后端校验后退出或返回。"""
    normalized = text.strip().lower().replace("*", "x").replace("×", "x")
    match = re.fullmatch(r"(\d{3,4})x(\d{3,4})", normalized)
    if not match:
        eprint("[genimg] size 格式应为 宽x高，例如 1024x1024（收到：%s）" % text)
        sys.exit(EXIT_USAGE)
    width, height = int(match.group(1)), int(match.group(2))
    if backend == "local":
        # 报错文案照抄服务端实测原文：size 1023x1024: each side a multiple of 32 from 256 to 2048
        bad = (
            width % LOCAL_SIZE_STEP or height % LOCAL_SIZE_STEP
            or not LOCAL_SIZE_MIN <= width <= LOCAL_SIZE_MAX
            or not LOCAL_SIZE_MIN <= height <= LOCAL_SIZE_MAX
        )
        if bad:
            eprint("[genimg] size %dx%d: each side a multiple of %d from %d to %d"
                   % (width, height, LOCAL_SIZE_STEP, LOCAL_SIZE_MIN, LOCAL_SIZE_MAX))
            sys.exit(EXIT_USAGE)
    elif max(width, height) > 3840:
        eprint("[genimg] 网关限制长边 ≤ 3840，收到 %dx%d" % (width, height))
        sys.exit(EXIT_USAGE)
    return "%dx%d" % (width, height)


def sanitize_slug(text):
    """把描述变成可用文件名，保留中文。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", text).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    return cleaned[:40] or "image"


def build_body(args, size, quality):
    """按后端拼请求体。本机端点照收 model/quality 但会忽略，发出去只会误导，所以不发。"""
    if args.backend == "local":
        body = {
            "prompt": args.prompt,
            "size": size,
            "n": args.n,
            # 服务端默认就是 b64_json；返回的 url 是绝对地址且重启后 404，所以明确要 b64
            "response_format": "b64_json",
        }
        if args.seed is not None:
            body["seed"] = args.seed
        return body
    return {
        "model": "gpt-image-2",
        "prompt": args.prompt,
        "size": size,
        "quality": quality,
        "n": args.n,
        "output_format": "png",
    }


def request_json(url, key, body, timeout):
    """POST 一个 JSON 请求，返回 (状态码, 文本)。HTTP 错误退出 3，网络错误退出 4。"""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        # 默认 UA 是 Python-urllib/3.x，会被网关前面的 Cloudflare 拦成 403 error code: 1010
        "User-Agent": USER_AGENT,
    }
    request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        eprint("[genimg] HTTP %s" % exc.code)
        eprint(detail[:2000])
        sys.exit(EXIT_HTTP)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        eprint("[genimg] 网络失败：%s" % exc)
        sys.exit(EXIT_NETWORK)


def get_health(base_url, key):
    """本机 /health 探活：免费、不占 GPU。非 200 或不通都算「不通」。"""
    request = urllib.request.Request(
        base_url.rstrip("/") + "/health",
        headers={"Authorization": "Bearer " + key, "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print("HEALTH=%s" % response.status)
            if response.status != 200:
                eprint("[genimg] /health 返回 %s，服务状态异常" % response.status)
                sys.exit(EXIT_NETWORK)
    except urllib.error.HTTPError as exc:
        print("HEALTH=%s" % exc.code)
        eprint("[genimg] /health 返回 %s，服务状态异常" % exc.code)
        sys.exit(EXIT_NETWORK)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print("HEALTH=unreachable")
        eprint("[genimg] /health 连不上：%s" % exc)
        eprint("[genimg] 服务可能没起，或地址不对。确认 unaserver 在跑、端口对，再重试。")
        sys.exit(EXIT_NETWORK)


def download(url, dest, billed_note):
    request = urllib.request.Request(url, headers={"User-Agent": "genimg/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            dest.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        eprint("[genimg] 图片下载失败：%s" % exc)
        eprint("[genimg] %s，图片地址保留在同名 .meta.json 里，可直接用 curl 补下载" % billed_note)
        sys.exit(EXIT_NETWORK)


def warn_local_cost():
    """本机后端的真实代价：不是钱，是独占 GPU 和会话被打断（实测见 SKILL.md）。"""
    eprint("[genimg] 本机后端：这一张会独占单生成令牌 FIFO，期间所有 chat 排队（实测等了 107.2 s）。")
    eprint("[genimg] gpu_policy=unload 会卸掉引擎（会话 KV 必丢）→ 下一个请求多付实测 66 s 重载"
           " + 按上下文长度的重读（44.4k tokens 21 s）。一次 2048² 生图的完整打断 ≈232 s。")
    eprint("[genimg] 要出多张请这次一次出完（--n 到 %d），重载只付一次。" % LOCAL_N_MAX)


def main():
    parser = argparse.ArgumentParser(
        description="生成图片并保存到本地（默认本机 Strata 的 Qwen-Image-2.1-Turbo，--backend gateway 走 fastaitoken 的 gpt-image-2）",
    )
    parser.add_argument("--prompt", required=True, help="图片描述（建议英文为主）")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="宽x高，默认 1024x1024")
    parser.add_argument(
        "--quality", choices=QUALITY_CHOICES, default=None,
        help="画质，默认 low（先出草稿）。本机后端不支持，会被忽略",
    )
    parser.add_argument("--n", type=int, default=1, help="张数，默认 1（本机后端 1–%d）" % LOCAL_N_MAX)
    parser.add_argument(
        "--seed", type=int, default=None,
        help="随机种子，仅本机后端可用：同 prompt + 同 seed → PNG 逐字节相同",
    )
    parser.add_argument(
        "--backend", choices=BACKEND_CHOICES, default=None,
        help="local=本机 Strata（默认，不花钱，独占 GPU）；gateway=fastaitoken 网关的 gpt-image-2（按次计费）。"
             "默认值也可由 .env 的 GENIMG_BACKEND 改",
    )
    parser.add_argument("--slug", default="", help="文件名后缀，默认取 prompt 前若干字符")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="输出目录")
    parser.add_argument(
        "--force-large", action="store_true",
        help="确认接受超过 1024 的尺寸（网关：计费升到 $0.15/张；本机：耗时和打断成本大幅上升）",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="只检查 key 和参数是否可用（不花钱）；本机后端还会额外探一次 /health（不占 GPU）",
    )
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    env_map = read_env_file(skill_dir)

    # 后端：命令行 > .env 的 GENIMG_BACKEND > 默认本机
    if args.backend is None:
        env_backend, backend_source = lookup_setting(BACKEND_NAMES, env_map)
        env_backend = (env_backend or "").strip().lower()
        if env_backend and env_backend not in BACKEND_CHOICES:
            eprint("[genimg] GENIMG_BACKEND 只认 %s，收到 %r"
                   % (" / ".join(BACKEND_CHOICES), env_backend))
            sys.exit(EXIT_USAGE)
        args.backend = env_backend or DEFAULT_BACKEND
        backend_source = backend_source or "默认"
        eprint("[genimg] 后端：%s（来自 %s；要 gpt-image-2 加 --backend gateway）"
               % ("本机 Strata" if args.backend == "local" else "fastaitoken 网关 gpt-image-2",
                  backend_source))

    if args.backend == "local":
        key, key_source = lookup_setting(LOCAL_KEY_NAMES, env_map)
        if not key:
            eprint("[genimg] 未找到本机 api key：在 %s 写 STRATA_LOCAL_KEY=..."
                   "（取自远端 /data/Strata/strata-iq3_s.json 的 api_key）" % (skill_dir / ".env"))
            sys.exit(EXIT_USAGE)
        base_url, _ = lookup_setting(LOCAL_URL_NAMES, env_map)
        base_url = (base_url or DEFAULT_LOCAL_URL).rstrip("/")
        timeout = LOCAL_TIMEOUT
        billed_note = "本机端点不收费，但作业已经跑完"
    else:
        key, key_source = lookup_setting(GATEWAY_KEY_NAMES, env_map)
        if not key:
            eprint("[genimg] 未找到 API key：在 %s 写 GENIMG_API_KEY=...（或 FASTAITOKEN_IMAGE_KEY=...）"
                   % (skill_dir / ".env"))
            sys.exit(EXIT_USAGE)
        base_url, timeout = API_URL, TIMEOUT
        billed_note = "接口已计费"

    quality = args.quality or "low"
    if args.backend == "local" and args.quality is not None:
        eprint("[genimg] 本机后端固定 8 步（Turbo sigmas），没有 quality 阶梯，--quality 已忽略")

    if args.seed is not None:
        if args.backend != "local":
            eprint("[genimg] --seed 只在本机后端实测过（同 seed 逐字节可复现）；"
                   "网关的 seed 行为未测，要用请加 --backend local")
            sys.exit(EXIT_USAGE)
        if args.seed < 0:
            eprint("[genimg] --seed 需要非负整数，收到 %d" % args.seed)
            sys.exit(EXIT_USAGE)

    if args.backend == "local":
        if args.n < 1 or args.n > LOCAL_N_MAX:
            # 报错文案照抄服务端实测原文：n: a whole number from 1 to 4
            eprint("[genimg] n: a whole number from 1 to %d（收到 %d）" % (LOCAL_N_MAX, args.n))
            sys.exit(EXIT_USAGE)
    elif args.n < 1:
        eprint("[genimg] --n 至少为 1")
        sys.exit(EXIT_USAGE)

    size = parse_size(args.size, args.backend)
    if max(int(size.split("x")[0]), int(size.split("x")[1])) > LARGE_LIMIT and not args.force_large:
        if args.backend == "local":
            # 本机用时间成本代替金额成本做护栏，数字是实测，见 references/api.md
            eprint("[genimg] %s 超过 1024：本机实测 2048x2048 要 112.0–116.3 s（1024x1024 是 27.6 s），"
                   "且会卸掉正在用的 LLM（下一个请求再付 66 s 重载 + 按上下文重读）。"
                   "确认要出大图请加 --force-large" % size)
        else:
            eprint("[genimg] %s 超过 1K 计费档，可能按 $0.15/张 计费；"
                   "确认要出大图请加 --force-large" % size)
        sys.exit(EXIT_USAGE)

    if args.check:
        print("BACKEND=%s" % args.backend)
        print("KEY_SOURCE=%s" % key_source)
        print("KEY_LEN=%d" % len(key))
        if args.backend == "local":
            print("URL=%s SIZE=%s N=%d SEED=%s" % (base_url, size, args.n, args.seed))
            get_health(base_url, key)
            eprint("[genimg] 配置与连通性检查通过，未请求生图接口（不占 GPU）")
        else:
            print("SIZE=%s QUALITY=%s" % (size, quality))
            eprint("[genimg] 配置检查通过，未请求接口")
        return EXIT_OK

    body = build_body(args, size, quality)

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    stem = "%s_%s" % (stamp, sanitize_slug(args.slug or args.prompt))

    if args.backend == "local":
        warn_local_cost()
        eprint("[genimg] key 来源：%s" % key_source)
        eprint("[genimg] POST %s/v1/images/generations size=%s n=%d（超时 %d s，中途断开服务端会取消作业）"
               % (base_url, size, args.n, timeout))
        endpoint = base_url + "/v1/images/generations"
    else:
        eprint("[genimg] key 来源：%s" % key_source)
        eprint("[genimg] POST %s size=%s quality=%s n=%d" % (API_URL, size, quality, args.n))
        endpoint = API_URL
    started = time.time()
    status, text = request_json(endpoint, key, body, timeout)
    elapsed = time.time() - started

    try:
        data = json.loads(text)
    except ValueError:
        eprint("[genimg] 响应不是 JSON（HTTP %s）：" % status)
        eprint(text[:2000])
        sys.exit(EXIT_NO_IMAGE)

    if args.backend == "local":
        # 服务端自报的耗时与策略，用来核对本机代价是不是落在预期区间
        diag = data.get("strata") or {}
        if diag:
            eprint("[genimg] strata: seconds=%s sampling_s=%s vae_decode_s=%s gpu_policy=%s "
                   "steps=%s seed=%s" % (
                       diag.get("seconds"), diag.get("sampling_s"), diag.get("vae_decode_s"),
                       diag.get("gpu_policy"), diag.get("steps"), diag.get("seed")))
        else:
            eprint("[genimg] 响应里没有 strata 字段（服务端版本可能变了）")

    items = data.get("data") or []
    if not items:
        eprint("[genimg] 响应里没有 data 字段：")
        eprint(text[:2000])
        sys.exit(EXIT_NO_IMAGE)

    meta_path = out_dir / (stem + ".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "backend": args.backend,
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
        if b64:
            dest.write_bytes(base64.b64decode(b64))
        elif url:
            download(url, dest, billed_note)
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
