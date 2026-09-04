#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lm_eval_webui.offline import (  # noqa: E402
    OFFLINE_HF_HOME,
    OFFLINE_LIVECODEBENCH_DATA,
    OFFLINE_NLTK_DATA,
    OFFLINE_READY_MARKER,
    OFFLINE_ROOT,
)
from lm_eval_webui.results import BALANCED_PROFILE_TASKS  # noqa: E402
from lm_eval_webui.runner import find_lm_eval_python  # noqa: E402

MANIFEST_PATH = OFFLINE_ROOT / "MANIFEST.json"
PIP_WHEELS_DIR = OFFLINE_ROOT / "pip"
OFFLINE_VENDOR_DIR = OFFLINE_ROOT / "vendor"
OFFLINE_BIN_DIR = OFFLINE_ROOT / "bin"
REQUIREMENTS_TXT = REPO_ROOT / "requirements.txt"
TINY_BENCHMARKS_URL = "https://github.com/felipemaiapolo/tinyBenchmarks"
TINY_BENCHMARKS_DIR = OFFLINE_VENDOR_DIR / "tinyBenchmarks"
LEMONADE_CLI_VERSION = "11.6.0"
LEMONADE_CLI_URL = ("https://github.com/lemonade-sdk/lemonade/releases/download/"
                    f"v{LEMONADE_CLI_VERSION}/lemonade-embeddable-{LEMONADE_CLI_VERSION}-ubuntu-"
                    "$ARCH.tar.gz")
LCB_DEFAULT_SOURCES = (
    REPO_ROOT.parent / "lm-eval-webui-lcb" / "data" / "lcb.jsonl",
    REPO_ROOT / "data" / "lcb.jsonl",
)
DEFAULT_TASKS = list(
    dict.fromkeys(
        [
            *BALANCED_PROFILE_TASKS,
            "livecodebench",
            "livecodebench_local",
            "truthfulqa_gen",
            "bbh_cot_zeroshot",
        ]
    )
)

_WARMUP_SCRIPT = r"""
import importlib
import json
import os
import sys
import time

offline_home = sys.argv[1]
tasks = sys.argv[2:]

os.environ["HF_HOME"] = offline_home
for var in (
    "HF_HUB_OFFLINE",
    "HF_DATASETS_OFFLINE",
    "TRANSFORMERS_OFFLINE",
    "HF_DATASETS_CACHE",
    "HF_HUB_CACHE",
    "HUGGINGFACE_HUB_CACHE",
):
    os.environ.pop(var, None)

if os.environ.get("LM_EVAL_WEBUI_WARMUP_PRELOAD"):
    importlib.import_module(os.environ["LM_EVAL_WEBUI_WARMUP_PRELOAD"])

import lm_eval
from lm_eval.tasks import TaskManager

tm = TaskManager()
results = {}
for task in tasks:
    last_error = None
    for attempt in range(3):
        try:
            tm.load_task_or_group(task)
            results[task] = "ok"
            last_error = None
            break
        except Exception as error:  # noqa: BLE001
            last_error = f"{type(error).__name__}: {error}"
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    if last_error:
        results[task] = last_error

payload = {
    "results": results,
    "versions": {
        "python": sys.version.split()[0],
        "lm_eval": getattr(lm_eval, "__version__", "unknown"),
    },
}
print("@@WARMUP@@" + json.dumps(payload, ensure_ascii=False))
"""


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(str(part) for part in command)}")
    return subprocess.run(command, **kwargs)  # noqa: S603


def _clean_bundle() -> None:
    if OFFLINE_READY_MARKER.exists():
        OFFLINE_READY_MARKER.unlink()
    for stale in (
        OFFLINE_HF_HOME,
        OFFLINE_ROOT / "livecodebench",
        OFFLINE_NLTK_DATA,
    ):
        if stale.exists():
            shutil.rmtree(stale)
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()


def _find_lcb_source(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None
    for candidate in LCB_DEFAULT_SOURCES:
        if candidate.is_file():
            return candidate
    return None


def _bundle_nltk(eval_python: Path) -> dict:
    script = (
        "import sys, nltk; "
        "ok = nltk.download('punkt_tab', download_dir=sys.argv[1]); "
        "sys.exit(0 if ok else 1)"
    )
    env = os.environ.copy()
    env.setdefault("NLTK_ALLOW_PROXIED_URLOPEN", "1")
    result = subprocess.run(  # noqa: S603
        [str(eval_python), "-c", script, str(OFFLINE_NLTK_DATA)],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print("  [WARN] NLTK punkt_tab 下载失败，离线机器上 IFEval 打分可能不可用。")
        return {"bundled": False}
    return {"bundled": True, "resources": ["punkt_tab"]}


def _lemonade_arch() -> str:
    machine = os.uname().machine
    if machine in ("x86_64", "amd64"):
        return "x64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    raise RuntimeError(f"不受支持的架构：{machine}（仅 x86_64 / arm64）")


def _strip_git_requirements() -> Path:
    PIP_WHEELS_DIR.mkdir(parents=True, exist_ok=True)
    out = PIP_WHEELS_DIR / "requirements.offline.txt"
    kept: list[str] = []
    if REQUIREMENTS_TXT.is_file():
        for line in REQUIREMENTS_TXT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("git+"):
                continue
            kept.append(line)
    out.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return out


def _bundle_pip_wheels() -> dict:
    req = _strip_git_requirements()
    print(f"[pip] 下载 {REQUIREMENTS_TXT.name} 音到的 wheels 到 {PIP_WHEELS_DIR} …")
    result = _run(
        [
            sys.executable, "-m", "pip", "download",
            "-r", str(req),
            "-d", str(PIP_WHEELS_DIR),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    wheels = sorted(PIP_WHEELS_DIR.glob("*.whl"))
    sdists = sorted(PIP_WHEELS_DIR.glob("*.tar.gz"))
    print(result.stdout[-3000:] if result.returncode != 0 else f"[pip] 下载完成：{len(wheels)} 个 wheel, {len(sdists)} 个源码包")
    return {
        "bundled": result.returncode == 0,
        "wheels": len(wheels),
        "sdists": len(sdists),
        "total_bytes": sum(2 + p.stat().st_size for p in PIP_WHEELS_DIR.iterdir()),
    }


def _bundle_tinybenchmarks() -> dict:
    if TINY_BENCHMARKS_DIR.is_dir():
        shutil.rmtree(TINY_BENCHMARKS_DIR)
    TINY_BENCHMARKS_DIR.parent.mkdir(parents=True, exist_ok=True)
    print(f"[tinyBenchmarks] 克隆 {TINY_BENCHMARKS_URL} …")
    result = _run(
        ["git", "clone", "--depth", "1", TINY_BENCHMARKS_URL, str(TINY_BENCHMARKS_DIR)],
        check=False,
    )
    if result.returncode != 0:
        shutil.rmtree(TINY_BENCHMARKS_DIR, ignore_errors=True)
        return {"bundled": False}
    if (TINY_BENCHMARKS_DIR / ".git").exists():
        shutil.rmtree(TINY_BENCHMARKS_DIR / ".git")
    return {"bundled": True, "path": str(TINY_BENCHMARKS_DIR)}


def _bundle_lemonade_cli(version: str | None = None) -> dict:
    version = version or LEMONADE_CLI_VERSION
    arch = _lemonade_arch()
    filename = (f"lemonade-embeddable-{version}-ubuntu-{arch}.tar.gz")
    url = LEMONADE_CLI_URL.replace("$ARCH", arch).replace(LEMONADE_CLI_VERSION, version)
    dest = OFFLINE_BIN_DIR / filename
    OFFLINE_BIN_DIR.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    print(f"[lemonade] 下载 {url} …")
    result = _run(
        ["curl", "-fsSL", url, "-o", str(dest)],
        check=False,
    )
    if result.returncode != 0:
        dest.unlink(missing_ok=True)
        return {"bundled": False}
    return {"bundled": True, "file": dest.name, "url": url}


def cmd_packages(args: argparse.Namespace) -> int:
    print(f"== 内置 Python 依赖（离线机器免网络安装）==\n  目标：{OFFLINE_ROOT}")
    pip_info = _bundle_pip_wheels()
    if not pip_info["bundled"]:
        print("[ERROR] pip wheels 下载失败，中止。请检查网络/PyPI 可用性。")
        return 1
    tb_info = _bundle_tinybenchmarks()
    if not tb_info["bundled"]:
        print("[ERROR] tinyBenchmarks 内置失败。")
        return 1
    lem_info = _bundle_lemonade_cli(args.lemonade_version)

    manifest = {}
    if MANIFEST_PATH.is_file():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest.update({
        "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "packaged_on": str(REPO_ROOT),
        "pip": pip_info,
        "tinyBenchmarks": tb_info,
        "lemonade": lem_info,
    })
    OFFLINE_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\n== 打包完成 ==")
    print(f"  wheels/sdists  {pip_info['wheels']}/{pip_info['sdists']}（{pip_info['total_bytes']//1024//1024} MB）")
    print(f"  tinyBenchmarks {'是' if tb_info.get('bundled') else '否'}")
    print(f"  Lemonade CLI   {'是' if lem_info.get('bundled') else '否'}"
          + (f"（{lem_info.get('file')}）" if lem_info.get('bundled') else ""))
    print("\n在离线机器上运行:")
    print("  1) python3 -m venv .venv")
    print("  2) pip install --no-index --find-links offline/pip -r offline/pip/requirements.offline.txt")
    print("  3) pip install --no-index --find-links offline/pip offline/vendor/tinyBenchmarks")
    print("  4) 启动 WebUI（见 scripts/install_offline.sh 一键完成）")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    print(f"== 离线打包：{REPO_ROOT} ==")
    _clean_bundle()

    eval_python = Path(args.python or find_lm_eval_python())
    if not eval_python.exists():
        print(f"[ERROR] 评测 python 不存在：{eval_python}")
        return 1
    tasks = [t.strip() for t in (args.tasks or DEFAULT_TASKS) if t.strip()]
    print(f"[datasets] 用 {eval_python} 实例化 {len(tasks)} 个任务以预热缓存：")
    print(f"          {', '.join(tasks)}")
    OFFLINE_HF_HOME.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(  # noqa: S603
        [str(eval_python), "-c", _WARMUP_SCRIPT, str(OFFLINE_HF_HOME), *tasks],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )
    warmup: dict = {}
    for line in result.stdout.splitlines():
        if line.startswith("@@WARMUP@@"):
            warmup = json.loads(line[len("@@WARMUP@@"):])
    if not warmup:
        print("[ERROR] 数据集预热失败：")
        print(result.stdout[-4000:] or "(无 stdout)")
        print(result.stderr[-4000:] or "(无 stderr)")
        return 1
    task_results: dict[str, str] = warmup.get("results", {})
    ok_tasks = [t for t, r in task_results.items() if r == "ok"]
    bad_tasks = {t: r for t, r in task_results.items() if r != "ok"}
    for task, reason in bad_tasks.items():
        print(f"  [WARN] 任务 {task} 缓存失败：{reason}")
    print(f"[datasets] 成功 {len(ok_tasks)} / {len(tasks)}，缓存写入 {OFFLINE_HF_HOME}")

    lcb_source = _find_lcb_source(args.lcb_source)
    lcb_info: dict = {"bundled": False}
    if lcb_source:
        dest = OFFLINE_LIVECODEBENCH_DATA
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lcb_source, dest)
        with dest.open("rb") as handle:
            problems = sum(1 for _ in handle)
        lcb_info = {"bundled": True, "source": str(lcb_source), "problems": problems}
        print(f"[livecodebench] 已内置 {problems} 题：{dest}")
    elif "livecodebench_local" in tasks:
        print(
            "[WARN] 未找到 lcb.jsonl（--lcb-source 指定），"
            "离线机器上 livecodebench_local 任务将不可用。"
        )

    if "ifeval" in tasks:
        nltk_info = _bundle_nltk(eval_python)
        print(f"[nltk] punkt_tab {'已内置' if nltk_info['bundled'] else '未内置'}")
    else:
        nltk_info = {"bundled": False}

    datasets_cached = sorted(
        p.name for p in (OFFLINE_HF_HOME / "datasets").glob("*") if p.is_dir()
    ) if (OFFLINE_HF_HOME / "datasets").is_dir() else []
    manifest = {
        "created": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "packaged_on": str(REPO_ROOT),
        "eval_python": str(eval_python),
        "versions": warmup.get("versions", {}),
        "tasks": task_results,
        "datasets_cached": datasets_cached,
        "livecodebench": lcb_info,
        "nltk": nltk_info,
    }
    OFFLINE_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.strict and bad_tasks:
        print("[ERROR] --strict 模式下存在失败任务，不写入 READY 标记。")
        return 1
    if not ok_tasks:
        print("[ERROR] 没有任何任务缓存成功，不写入 READY 标记。")
        return 1

    OFFLINE_READY_MARKER.write_text(
        f"offline bundle created at {manifest['created']}\n", encoding="utf-8"
    )
    print()
    print("== 打包完成 ==")
    print(f"  清单      {MANIFEST_PATH}")
    print(f"  数据集    {len(datasets_cached)} 个（HF_HOME={OFFLINE_HF_HOME}）")
    print(f"  LCB 本地  {'是' if lcb_info['bundled'] else '否'}")
    print(f"  NLTK      {'是' if nltk_info.get('bundled') else '否'}")
    if bad_tasks:
        print(f"  失败任务  {', '.join(bad_tasks)}")
    print()
    print("把整个项目目录拷到离线机器后：")
    print("  正常启动 WebUI —— 自动进入离线模式")
    return 0


def cmd_activate(args: argparse.Namespace) -> int:
    if not OFFLINE_READY_MARKER.is_file():
        print("[ERROR] 未发现 offline/READY —— 请先把完整项目目录拷贝过来。")
        return 1
    print("[INFO] 离线环境已就绪，可直接启动 WebUI。")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    ready = OFFLINE_READY_MARKER.is_file()
    print(f"READY 标记      {'存在（离线模式开启）' if ready else '不存在（联网模式）'}")
    if MANIFEST_PATH.is_file():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        print(f"打包时间        {manifest.get('created')}")
        print(f"打包机器路径    {manifest.get('packaged_on')}")
        print(f"评测 python     {manifest.get('eval_python')}")
        print(f"lm-eval 版本    {(manifest.get('versions') or {}).get('lm_eval')}")
        tasks = manifest.get("tasks") or {}
        bad = [t for t, r in tasks.items() if r != "ok"]
        print(f"任务缓存        {sum(1 for r in tasks.values() if r == 'ok')}/{len(tasks)}"
              + (f"（失败: {', '.join(bad)}）" if bad else ""))
        print(f"数据集          {', '.join(manifest.get('datasets_cached') or []) or '无'}")
        print(f"LCB 本地数据    {'是' if (manifest.get('livecodebench') or {}).get('bundled') else '否'}")
        print(f"NLTK 资源       {'是' if (manifest.get('nltk') or {}).get('bundled') else '否'}")
    else:
        print("清单            无（未打包或打包失败）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="联网机器上运行：打包离线捆绑")
    p_prepare.add_argument("--python", help="评测用 python 解释器路径（默认自动探测）")
    p_prepare.add_argument("--tasks", help="逗号分隔的任务列表（默认内置全部常用任务）")
    p_prepare.add_argument("--lcb-source", help="lcb.jsonl 源路径（默认自动探测）")
    p_prepare.add_argument("--strict", action="store_true",
                           help="任何任务缓存失败则不写入 READY 标记")
    p_prepare.set_defaults(func=cmd_prepare)

    p_packages = sub.add_parser(
        "packages",
        help="内置 Python/源码依赖（pip wheels、tinyBenchmarks、Lemonade CLI）",
    )
    p_packages.add_argument("--lemonade-version", default=LEMONADE_CLI_VERSION,
                            help=f"Lemonade CLI 版本（默认 {LEMONADE_CLI_VERSION}）")
    p_packages.set_defaults(func=cmd_packages)

    p_activate = sub.add_parser("activate", help="离线机器上运行：校验离线环境已就绪")
    p_activate.set_defaults(func=cmd_activate)

    p_status = sub.add_parser("status", help="查看离线捆绑状态")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
