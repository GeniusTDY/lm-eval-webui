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

SWE_REGISTRY_DEFAULT = "ghcr.io/epoch-research/swe-bench.eval.x86_64"
BUN_CACHE_VOLUME = "pi-bench-bun-cache"
DOCKER_DIR = OFFLINE_ROOT / "docker"
DOCKER_IMAGE_DIR = DOCKER_DIR / "images"
BUN_CACHE_ARCHIVE = DOCKER_DIR / "pi-bench-bun-cache.tar.gz"
MANIFEST_PATH = OFFLINE_ROOT / "MANIFEST.json"
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
        DOCKER_DIR,
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


def _swe_task_ids(pi_bench_dir: Path, limit: int | None) -> list[str]:
    task_dir = pi_bench_dir / "tasks" / "verified-mini"
    ids = []
    for task_file in sorted(task_dir.glob("*.json")):
        try:
            data = json.loads(task_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if task_id := str(data.get("id") or ""):
            ids.append(task_id)
    if limit:
        ids = ids[:limit]
    return ids


def _docker_available() -> bool:
    try:
        return subprocess.run(  # noqa: S603, S607
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
    except OSError:
        return False


def _bundle_docker(registry: str, pi_bench_dir: Path, limit: int | None) -> dict:
    if not _docker_available():
        raise RuntimeError(
            "docker 不可用（守护进程未运行或未安装）。"
            "如不需要离线 SWE Mini，请去掉 --with-docker 重新打包。"
        )

    task_ids = _swe_task_ids(pi_bench_dir, limit)
    if not task_ids:
        raise RuntimeError(f"未找到 SWE Mini 任务文件：{pi_bench_dir / 'tasks' / 'verified-mini'}")

    print(f"[docker] 拉取 {len(task_ids)} 个 SWE 任务镜像 …")
    images: dict[str, str] = {}
    failed: list[str] = []
    for task_id in task_ids:
        image = f"{registry}.{task_id}:latest"
        result = _run(
            ["docker", "pull", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            images[task_id] = image
        else:
            failed.append(task_id)
            print(f"  [WARN] 拉取失败，跳过：{image}")
    if not images:
        raise RuntimeError("没有任何 SWE 任务镜像拉取成功。")

    warm_image = next(iter(images.values()))
    print(f"[docker] 预热 bun 缓存卷与 node_modules（镜像 {warm_image}）…")
    _run(["docker", "volume", "create", BUN_CACHE_VOLUME], check=False,
         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    warm_script = (
        "set -e; "
        "if [ ! -f /root/.bun/bin/bun ]; then "
        "apt-get update -qq && apt-get install -y -qq unzip >/dev/null 2>&1; "
        "curl -fsSL https://bun.sh/install | bash >/dev/null 2>&1; "
        "fi; "
        "export PATH=/root/.bun/bin:$PATH; "
        "cd /pi-bench && bun install"
    )
    result = _run(
        [
            "docker", "run", "--rm", "--network", "host",
            "-v", f"{pi_bench_dir}:/pi-bench:z",
            "-v", f"{BUN_CACHE_VOLUME}:/root/.bun",
            warm_image,
            "bash", "-c", warm_script,
        ],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("bun 缓存预热失败，无法保证离线 SWE Mini 可用。")

    DOCKER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[docker] 导出 {len(images)} 个镜像到 {DOCKER_IMAGE_DIR} …")
    for task_id, image in images.items():
        tar_path = DOCKER_IMAGE_DIR / f"{task_id}.tar"
        with tar_path.open("wb") as tar_file:
            result = _run(
                ["docker", "save", image],
                stdout=tar_file,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        if result.returncode != 0:
            tar_path.unlink(missing_ok=True)
            print(f"  [WARN] 导出失败：{image}")
            failed.append(task_id)

    print("[docker] 导出 bun 缓存卷 …")
    with BUN_CACHE_ARCHIVE.open("wb") as archive_file:
        result = _run(
            [
                "docker", "run", "--rm",
                "-v", f"{BUN_CACHE_VOLUME}:/data",
                warm_image,
                "bash", "-c", "tar czf - -C /data .",
            ],
            stdout=archive_file,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    if result.returncode != 0:
        BUN_CACHE_ARCHIVE.unlink(missing_ok=True)
        print("  [WARN] bun 缓存卷导出失败。")

    return {
        "registry": registry,
        "images": images,
        "failed_tasks": failed,
        "bun_cache_exported": BUN_CACHE_ARCHIVE.is_file(),
        "node_modules_warmed": (pi_bench_dir / "node_modules").is_dir(),
    }


def cmd_prepare(args: argparse.Namespace) -> int:
    print(f"== 离线打包：{REPO_ROOT} ==")
    if args.with_docker and not _docker_available():
        print("[ERROR] --with-docker 需要 docker（守护进程未运行或未安装）。")
        print("        如不需要离线 SWE Mini，请去掉 --with-docker 重新运行。")
        return 1
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

    docker_info: dict = {"bundled": False}
    if args.with_docker:
        registry = os.environ.get("SWE_BENCH_IMAGE_REGISTRY", SWE_REGISTRY_DEFAULT)
        pi_bench_dir = REPO_ROOT / "third_party" / "pi-bench"
        docker_info = {"bundled": True, **_bundle_docker(registry, pi_bench_dir, args.docker_limit)}

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
        "docker": docker_info,
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
    print(f"  Docker    {'是' if docker_info.get('bundled') else '否'}")
    if bad_tasks:
        print(f"  失败任务  {', '.join(bad_tasks)}")
    print()
    print("把整个项目目录拷到离线机器后：")
    print("  1) python3 scripts/prepare_offline.py activate   # 导入 Docker 资产（如已打包）")
    print("  2) 正常启动 WebUI —— 自动进入离线模式")
    return 0


def cmd_activate(args: argparse.Namespace) -> int:
    if not OFFLINE_READY_MARKER.is_file():
        print("[ERROR] 未发现 offline/READY —— 请先把完整项目目录拷贝过来。")
        return 1

    docker_files = sorted(DOCKER_IMAGE_DIR.glob("*.tar")) if DOCKER_IMAGE_DIR.is_dir() else []
    need_docker = bool(docker_files or BUN_CACHE_ARCHIVE.is_file())
    if need_docker and not _docker_available():
        print("[ERROR] 捆绑包含 Docker 资产但 docker 不可用，无法激活。")
        return 1

    loaded = 0
    for tar_path in docker_files:
        if _run(["docker", "load", "-i", str(tar_path)], check=False,
                 stdout=subprocess.DEVNULL).returncode == 0:
            loaded += 1
        else:
            print(f"  [WARN] 镜像导入失败：{tar_path.name}")
    if docker_files:
        print(f"[docker] 已导入 {loaded}/{len(docker_files)} 个镜像")

    if BUN_CACHE_ARCHIVE.is_file():
        manifest = {}
        if MANIFEST_PATH.is_file():
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        warm_image = next(
            iter((manifest.get("docker") or {}).get("images", {}).values()), None
        )
        if warm_image:
            _run(["docker", "volume", "create", BUN_CACHE_VOLUME], check=False,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with BUN_CACHE_ARCHIVE.open("rb") as archive_file:
                result = _run(
                    [
                        "docker", "run", "--rm", "-i",
                        "-v", f"{BUN_CACHE_VOLUME}:/data",
                        warm_image,
                        "bash", "-c", "tar xzf - -C /data",
                    ],
                    stdin=archive_file,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            print(
                "[docker] bun 缓存卷导入成功"
                if result.returncode == 0
                else "[WARN] bun 缓存卷导入失败"
            )
        else:
            print("[WARN] 清单中无镜像信息，跳过 bun 缓存卷导入。")

    print("[INFO] 离线环境已激活，可直接启动 WebUI。")
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
        docker = manifest.get("docker") or {}
        if docker.get("bundled"):
            print(f"SWE 镜像        {len(docker.get('images') or {})} 个，"
                  f"bun 缓存卷 {'已导出' if docker.get('bun_cache_exported') else '缺失'}")
    else:
        print("清单            无（未打包或打包失败）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="联网机器上运行：打包离线捆绑")
    p_prepare.add_argument("--with-docker", action="store_true",
                           help="同时打包 SWE Mini 容器镜像与 bun 缓存（体积较大）")
    p_prepare.add_argument("--python", help="评测用 python 解释器路径（默认自动探测）")
    p_prepare.add_argument("--tasks", help="逗号分隔的任务列表（默认内置全部常用任务）")
    p_prepare.add_argument("--lcb-source", help="lcb.jsonl 源路径（默认自动探测）")
    p_prepare.add_argument("--docker-limit", type=int, default=None,
                           help="仅打包前 N 个 SWE 任务镜像（试用）")
    p_prepare.add_argument("--strict", action="store_true",
                           help="任何任务缓存失败则不写入 READY 标记")
    p_prepare.set_defaults(func=cmd_prepare)

    p_activate = sub.add_parser("activate", help="离线机器上运行：导入 Docker 资产")
    p_activate.set_defaults(func=cmd_activate)

    p_status = sub.add_parser("status", help="查看离线捆绑状态")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
