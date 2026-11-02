#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文生图：默认走本机 Strata 的 Qwen-Image-2.1-Turbo；--backend gateway 走 fastaitoken 网关的 gpt-image-2。落盘到本地。

只用 Python 3.9+ 标准库。契约见同 skill 的 references/api.md。

两种发法：
  单张   --prompt "…" [--size … --n … --seed …]
  一批   --jobs jobs.json          # JSON 数组或 JSONL，每条一个作业；命令行参数当默认值
         --skip-done               # 已经在 out 目录里出过的（prompt+size+n+seed 相同）跳过，补跑用
         --retries 2               # 网络断连 / 上游 5xx 重试次数（实测网关偶发 SSL EOF，重试能过）

退出码：
  0 成功（批量：全部成功）
  1 响应里没有图片（结构变化或被风控拦截）
  2 参数错误 / 缺少 API key
  3 HTTP 错误（状态码与错误体原样打印）
  4 网络错误或超时（local 的 --check 探活不通也算）
  5 批量里至少一条失败（前面成功的仍算数，摘要里写清几条没成）

计费与代价：网关按张计费，但「没出图」的 5xx 与断连不产出图，重试不重复付。
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
DEFAULT_RETRIES = 2  # 总共 3 次尝试；实测网关出现过连断 4 次，但 3 次尝试内基本能过

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

# 作业字段（--jobs 里每条允许的键）
JOB_KEYS = ("slug", "prompt", "size", "n", "seed", "quality", "backend")

EXIT_OK = 0
EXIT_NO_IMAGE = 1
EXIT_USAGE = 2
EXIT_HTTP = 3
EXIT_NETWORK = 4
EXIT_PARTIAL = 5

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
    normalized = str(text).strip().lower().replace("*", "x").replace("×", "x")
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


def read_jobs(path):
    """读 --jobs 文件：JSON 数组、JSONL，或每行「slug<TAB>prompt」的 txt。

    允许 markdown 代码围栏（从整篇笔记里直接取用）。返回作业字典列表。
    """
    text = Path(path).expanduser().read_text(encoding="utf-8")
    fence = re.findall(r"```(?:json|jsonl)?\s*\n(.*?)```", text, re.S)
    if fence:
        text = "\n".join(fence)
    stripped = text.strip()
    jobs = []
    if stripped.startswith("["):
        jobs = json.loads(stripped)
    else:
        for line_no, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("{"):
                jobs.append(json.loads(line))
            elif "\t" in line:
                slug, prompt = line.split("\t", 1)
                jobs.append({"slug": slug.strip(), "prompt": prompt.strip()})
            else:
                eprint("[genimg] %s 第 %d 行看不懂：要 JSON 对象、JSON 数组，或「slug<TAB>prompt」"
                       % (path, line_no))
                sys.exit(EXIT_USAGE)
    if not jobs:
        eprint("[genimg] %s 里没有作业" % path)
        sys.exit(EXIT_USAGE)
    bad = [j for j in jobs if not isinstance(j, dict) or not j.get("prompt")]
    if bad:
        eprint("[genimg] %s 里有作业缺 prompt（每条至少要有 prompt）" % path)
        sys.exit(EXIT_USAGE)
    unknown = sorted({k for j in jobs for k in j if k not in JOB_KEYS})
    if unknown:
        eprint("[genimg] %s 里有不认识的字段：%s（可用字段：%s）"
               % (path, ", ".join(unknown), ", ".join(JOB_KEYS)))
        sys.exit(EXIT_USAGE)
    return jobs


def job_identity(job):
    """用来判断「这条是不是已经出过」的身份：这四样相同 → 输出逐字节相同（本机实测）。"""
    return (job.get("backend"), job.get("prompt"), job.get("size"),
            job.get("n"), job.get("seed"))


def already_done(out_dir, job):
    """扫 out 目录里的 .meta.json，找到身份相同的就返回它的图片文件名。"""
    want = job_identity(job)
    for meta in sorted(out_dir.glob("*.meta.json")):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        requested = data.get("requested") or {}
        got = (data.get("backend"), requested.get("prompt"), requested.get("size"),
               requested.get("n"), requested.get("seed"))
        if got == want:
            stem = meta.name[: -len(".meta.json")]
            for png in out_dir.glob(stem + "*.png"):
                return png.name
    return None


def build_body(job, size, quality):
    """按后端拼请求体。本机端点照收 model/quality 但会忽略，发出去只会误导，所以不发。"""
    if job["backend"] == "local":
        body = {
            "prompt": job["prompt"],
            "size": size,
            "n": job["n"],
            # 服务端默认就是 b64_json；返回的 url 是绝对地址且重启后 404，所以明确要 b64
            "response_format": "b64_json",
        }
        if job["seed"] is not None:
            body["seed"] = job["seed"]
        return body
    return {
        "model": "gpt-image-2",
        "prompt": job["prompt"],
        "size": size,
        "quality": quality,
        "n": job["n"],
        "output_format": "png",
    }


class Retryable(Exception):
    """可以重试的失败：网络断连、超时、上游 5xx。"""

    def __init__(self, why, kind):
        super(Retryable, self).__init__(why)
        self.why = why
        self.kind = kind  # "network" 或 "http5xx"


def request_json(url, key, body, timeout, retries):
    """POST 一个 JSON 请求，返回 (状态码, 文本)。

    可重试的情况（实测）：SSL UNEXPECTED_EOF / 连接被重置 / HTTP 500 "Upstream gateway error"。
    这两种都不产出图，所以重试不重复计费。参数错（400）不重试——那是我的请求写错了。
    """
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        # 默认 UA 是 Python-urllib/3.x，会被网关前面的 Cloudflare 拦成 403 error code: 1010
        "User-Agent": USER_AGENT,
    }
    for attempt in range(retries + 1):
        last = None
        request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            if exc.code >= 500:
                last = Retryable("HTTP %s %s" % (exc.code, detail[:200]), "http5xx")
            else:
                eprint("[genimg] HTTP %s" % exc.code)
                eprint(detail[:2000])
                sys.exit(EXIT_HTTP)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = Retryable("网络失败：%s" % exc, "network")
        if attempt < retries:
            eprint("[genimg] 第 %d 次尝试失败（%s），不产出图所以不重复计费，重试…"
                   % (attempt + 1, last.why))
            time.sleep(min(5, 2 * (attempt + 1)))
            continue
        raise last
    raise Retryable("未知失败", "network")


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
    """本机后端的真实代价：不是钱，是独占 GPU 和会话被打断（实测见 SKILL.md / references/api.md）。"""
    eprint("[genimg] 本机后端：这一张会独占单生成令牌 FIFO，期间所有 chat 排队（实测等了 107.2 s）。")
    eprint("[genimg] gpu_policy=unload 会卸掉引擎（会话 KV 必丢）→ 本轮之后的第一个请求多付实测 60–66 s 重载"
           " + 按上下文长度的重读（≈2.1k tok/s：44.4k tokens 21 s，200K 上下文 ~61 s）。"
           "一次 1024² 的完整打断 ≈115 s、2048² ≈232 s。")
    eprint("[genimg] 一轮只付一次重载：要几张就连着发完，中间别穿插 chat / 工具调用"
           "（穿插一次 = 多付一轮，实测 80–120 s）。同 prompt 的候选用 --n（到 %d）。" % LOCAL_N_MAX)


def resolve_backend(cli_backend, env_map):
    """后端：命令行 > .env 的 GENIMG_BACKEND > 默认本机。"""
    if cli_backend is not None:
        return cli_backend, "命令行"
    env_backend, backend_source = lookup_setting(BACKEND_NAMES, env_map)
    env_backend = (env_backend or "").strip().lower()
    if env_backend and env_backend not in BACKEND_CHOICES:
        eprint("[genimg] GENIMG_BACKEND 只认 %s，收到 %r"
               % (" / ".join(BACKEND_CHOICES), env_backend))
        sys.exit(EXIT_USAGE)
    if env_backend:
        return env_backend, backend_source
    return DEFAULT_BACKEND, "默认"


def backend_endpoint(backend, env_map, skill_dir):
    """返回 (key, key_source, endpoint, base_url, timeout, billed_note)。base_url 只给 /health 用。"""
    if backend == "local":
        key, key_source = lookup_setting(LOCAL_KEY_NAMES, env_map)
        if not key:
            eprint("[genimg] 未找到本机 api key：在 %s 写 STRATA_LOCAL_KEY=..."
                   "（取自远端 /data/Strata/strata-iq3_s.json 的 api_key）" % (skill_dir / ".env"))
            sys.exit(EXIT_USAGE)
        base_url, _ = lookup_setting(LOCAL_URL_NAMES, env_map)
        base_url = (base_url or DEFAULT_LOCAL_URL).rstrip("/")
        return key, key_source, base_url + "/v1/images/generations", base_url, LOCAL_TIMEOUT, \
            "本机端点不收费，但作业已经跑完"
    key, key_source = lookup_setting(GATEWAY_KEY_NAMES, env_map)
    if not key:
        eprint("[genimg] 未找到 API key：在 %s 写 GENIMG_API_KEY=...（或 FASTAITOKEN_IMAGE_KEY=...）"
               % (skill_dir / ".env"))
        sys.exit(EXIT_USAGE)
    return key, key_source, API_URL, API_URL, TIMEOUT, "接口已计费"


def check_job(job, force_large):
    """逐条校验参数；不合法就退出 2（批量的任一条错都不该半发）。"""
    backend = job["backend"]
    if job["seed"] is not None and backend != "local":
        eprint("[genimg] --seed 只在本机后端实测过（同 seed 逐字节可复现）；"
               "网关的 seed 行为未测，要用请用 local")
        sys.exit(EXIT_USAGE)
    if job["seed"] is not None and job["seed"] < 0:
        eprint("[genimg] --seed 需要非负整数，收到 %s" % job["seed"])
        sys.exit(EXIT_USAGE)
    if backend == "local":
        if job["n"] < 1 or job["n"] > LOCAL_N_MAX:
            # 报错文案照抄服务端实测原文：n: a whole number from 1 to 4
            eprint("[genimg] n: a whole number from 1 to %d（收到 %d）" % (LOCAL_N_MAX, job["n"]))
            sys.exit(EXIT_USAGE)
    elif job["n"] < 1:
        eprint("[genimg] n 至少为 1")
        sys.exit(EXIT_USAGE)
    job["size"] = parse_size(job["size"], backend)
    if max(int(job["size"].split("x")[0]), int(job["size"].split("x")[1])) > LARGE_LIMIT \
            and not force_large:
        if backend == "local":
            # 本机用时间成本代替金额成本做护栏，数字是实测，见 references/api.md
            eprint("[genimg] %s 超过 1024：本机实测 2048x2048 要 112.0–116.3 s（1024x1024 是 27.6 s），"
                   "且会卸掉正在用的 LLM（下一个请求再付 66 s 重载 + 按上下文重读）。"
                   "确认要出大图请加 --force-large" % job["size"])
        else:
            eprint("[genimg] %s 超过 1K 计费档，可能按 $0.15/张 计费；确认要出大图请加 --force-large"
                   % job["size"])
        sys.exit(EXIT_USAGE)


def run_job(job, ctx, out_dir, stem):
    """发一条作业并落盘。返回落盘路径列表；失败抛 SystemExit 或 Retryable。"""
    quality = job["quality"] or "low"
    body = build_body(job, job["size"], quality)
    eprint("[genimg] POST %s size=%s n=%d slug=%s"
           % (ctx["endpoint"], job["size"], job["n"], job["slug"] or "(取 prompt)"))
    started = time.time()
    status, text = request_json(ctx["endpoint"], ctx["key"], body, ctx["timeout"], ctx["retries"])
    elapsed = time.time() - started

    try:
        data = json.loads(text)
    except ValueError:
        eprint("[genimg] 响应不是 JSON（HTTP %s）：" % status)
        eprint(text[:2000])
        sys.exit(EXIT_NO_IMAGE)

    if job["backend"] == "local":
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
                "backend": job["backend"],
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
            download(url, dest, ctx["billed_note"])
        else:
            eprint("[genimg] 第 %d 项既没有 url 也没有 b64_json，跳过" % index)
            continue
        saved.append(dest)

    if not saved:
        eprint("[genimg] 没有任何图片落盘，响应存到 %s" % meta_path)
        sys.exit(EXIT_NO_IMAGE)

    eprint("[genimg] 完成：%d 张，%.1fs，meta: %s" % (len(saved), elapsed, meta_path))
    return [{"file": str(dest), "seconds": round(elapsed, 1), "index": index}
            for index, dest in enumerate(saved, start=1)]


def main():
    parser = argparse.ArgumentParser(
        description="生成图片并保存到本地（默认本机 Strata 的 Qwen-Image-2.1-Turbo，--backend gateway 走 fastaitoken 的 gpt-image-2）",
        epilog="一批的用法：--jobs jobs.json（JSON 数组 / JSONL / 每行「slug\\tprompt」），"
               "补跑加 --skip-done；切好的小图用同目录的 slice.py 从整张网格图里切。",
    )
    parser.add_argument("--prompt", help="图片描述（建议英文为主）；与 --jobs 二选一")
    parser.add_argument("--jobs", help="一批作业：JSON 数组、JSONL，或每行「slug<TAB>prompt」的文本")
    parser.add_argument("--skip-done", action="store_true",
                        help="跳过 --out 目录里已出过的作业（按 prompt+size+n+seed 比对 .meta.json）")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help="断连 / 上游 5xx 的重试次数，默认 %d（不产出图所以不重复计费）"
                             % DEFAULT_RETRIES)
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

    if bool(args.prompt) == bool(args.jobs):
        eprint("[genimg] --prompt 与 --jobs 二选一（单张用 --prompt，一批用 --jobs）")
        sys.exit(EXIT_USAGE)
    if args.retries < 0:
        eprint("[genimg] --retries 不能为负")
        sys.exit(EXIT_USAGE)

    skill_dir = Path(__file__).resolve().parent.parent
    env_map = read_env_file(skill_dir)

    default_backend, backend_source = resolve_backend(args.backend, env_map)
    if args.backend is None:
        eprint("[genimg] 后端：%s（来自 %s；只有明确要 gpt-image-2 才加 --backend gateway）"
               % ("本机 Strata qwen-image-2.1" if default_backend == "local"
                  else "fastaitoken 网关 gpt-image-2", backend_source))

    # 组装作业列表：--jobs 的每条继承命令行默认值
    raw_jobs = read_jobs(args.jobs) if args.jobs else [{}]
    jobs = []
    for raw in raw_jobs:
        job = {
            "slug": raw.get("slug") or (args.slug or ""),
            "prompt": raw.get("prompt") or args.prompt,
            "size": raw.get("size") or args.size,
            "n": int(raw.get("n", args.n)),
            "seed": raw["seed"] if raw.get("seed") is not None else args.seed,
            "quality": raw.get("quality") or args.quality,
            "backend": (raw.get("backend") or default_backend),
        }
        if not job["prompt"]:
            eprint("[genimg] 有一条作业没有 prompt")
            sys.exit(EXIT_USAGE)
        if job["backend"] not in BACKEND_CHOICES:
            eprint("[genimg] backend 只认 %s，收到 %r" % (" / ".join(BACKEND_CHOICES), job["backend"]))
            sys.exit(EXIT_USAGE)
        if job["backend"] == "local" and args.quality is not None:
            eprint("[genimg] 本机后端固定 8 步（Turbo sigmas），没有 quality 阶梯，quality 已忽略")
        check_job(job, args.force_large)
        jobs.append(job)

    # key/endpoint 按后端取；混合批次两边都要能取到
    ctxs = {}
    for job in jobs:
        backend = job["backend"]
        if backend not in ctxs:
            key, key_source, endpoint, base_url, timeout, billed_note = backend_endpoint(
                backend, env_map, skill_dir)
            ctxs[backend] = {"key": key, "key_source": key_source, "endpoint": endpoint,
                             "base_url": base_url,
                             "timeout": timeout, "billed_note": billed_note,
                             "retries": args.retries}
    ctx = ctxs[jobs[0]["backend"]]

    if args.check:
        seen = set()
        for job in jobs:
            backend = job["backend"]
            if backend in seen:
                continue
            seen.add(backend)
            print("BACKEND=%s" % backend)
            print("KEY_SOURCE=%s" % ctxs[backend]["key_source"])
            print("KEY_LEN=%d" % len(ctxs[backend]["key"]))
            if backend == "local":
                print("URL=%s SIZE=%s N=%d SEED=%s"
                      % (ctxs[backend]["endpoint"], job["size"], job["n"], job["seed"]))
                get_health(ctxs[backend]["base_url"], ctxs[backend]["key"])
            else:
                print("SIZE=%s QUALITY=%s" % (job["size"], job["quality"] or "low"))
        eprint("[genimg] 配置与参数检查通过（%d 条），未请求生图接口（不占 GPU、不花钱）" % len(jobs))
        return EXIT_OK

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")

    if "local" in ctxs:
        warn_local_cost()

    manifest = []
    failed = []
    for number, job in enumerate(jobs, start=1):
        ctx = ctxs[job["backend"]]
        if args.skip_done:
            hit = already_done(out_dir, job)
            if hit:
                eprint("[genimg] 跳过（%d/%d）：同样的 prompt+size+n+seed 已出过 → %s"
                       % (number, len(jobs), hit))
                manifest.append({"slug": job["slug"], "file": str(out_dir / hit),
                                 "skipped": True})
                continue
        stem = "%s_%02d_%s" % (stamp, number, sanitize_slug(job["slug"] or job["prompt"])) \
            if len(jobs) > 1 else "%s_%s" % (stamp, sanitize_slug(job["slug"] or job["prompt"]))
        eprint("[genimg] (%d/%d) slug=%s size=%s backend=%s"
               % (number, len(jobs), job["slug"] or "(取 prompt)", job["size"], job["backend"]))
        try:
            rows = run_job(job, ctx, out_dir, stem)
        except (SystemExit, Retryable) as exc:
            if isinstance(exc, Retryable):
                eprint("[genimg] 第 %d 条最终失败：%s" % (number, exc.why))
            else:
                eprint("[genimg] 第 %d 条失败（退出码 %s）" % (number, exc.code))
            failed.append({"number": number, "slug": job["slug"]})
            if len(jobs) == 1:
                raise
            continue
        manifest.append({"slug": job["slug"], "size": job["size"], "backend": job["backend"],
                         "seed": job["seed"], "files": [r["file"] for r in rows]})

    for entry in manifest:
        for path in ([entry["file"]] if "file" in entry else entry.get("files", [])):
            print("LOCAL=%s" % path)

    if len(jobs) > 1:
        manifest_path = out_dir / ("batch-%s.manifest.json" % stamp)
        manifest_path.write_text(json.dumps(
            {"jobs": len(jobs), "failed": failed, "entries": manifest},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print("MANIFEST=%s" % manifest_path)

    if failed:
        eprint("[genimg] 这批 %d 条里 %d 条没成：%s。"
               "补跑加 --skip-done（已出过的会跳过，不重复付费）"
               % (len(jobs), len(failed), ", ".join(str(f["slug"] or f["number"]) for f in failed)))
        return EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
