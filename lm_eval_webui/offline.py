from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OFFLINE_ROOT = PROJECT_ROOT / "offline"
OFFLINE_HF_HOME = OFFLINE_ROOT / "hf-home"
OFFLINE_READY_MARKER = OFFLINE_ROOT / "READY"
OFFLINE_LIVECODEBENCH_DATA = OFFLINE_ROOT / "livecodebench" / "lcb.jsonl"
OFFLINE_NLTK_DATA = OFFLINE_ROOT / "nltk_data"

_LCB_DATA_FILES_RE = re.compile(
    r"(?P<prefix>data_files:\s*\n(?:\s*\w+:\s*)?)(?P<path>\S+)"
)


def offline_bundle_ready() -> bool:
    return OFFLINE_READY_MARKER.is_file()


def apply_offline_env(env: dict[str, str]) -> dict[str, str]:
    if not offline_bundle_ready():
        return env
    env["HF_HOME"] = str(OFFLINE_HF_HOME)
    env["HF_HUB_OFFLINE"] = "1"
    env["HF_DATASETS_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    if OFFLINE_NLTK_DATA.is_dir():
        env["NLTK_DATA"] = os.pathsep.join(
            [str(OFFLINE_NLTK_DATA), *(
                [env["NLTK_DATA"]] if env.get("NLTK_DATA") else []
            )]
        )
    ensure_livecodebench_local_data()
    return env


def build_offline_launch_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    return apply_offline_env(dict(base_env if base_env is not None else os.environ))


def _installed_livecodebench_yaml() -> Path | None:
    try:
        import lm_eval
    except ImportError:
        return None
    path = (
        Path(lm_eval.__file__).resolve().parent
        / "tasks"
        / "livecodebench"
        / "livecodebench_local.yaml"
    )
    return path if path.is_file() else None


def ensure_livecodebench_local_data() -> Path | None:
    if not offline_bundle_ready() or not OFFLINE_LIVECODEBENCH_DATA.is_file():
        return None
    target = str(OFFLINE_LIVECODEBENCH_DATA.resolve())
    yaml_path = _installed_livecodebench_yaml()
    if yaml_path is None:
        return None
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if target in text:
        return OFFLINE_LIVECODEBENCH_DATA
    if "data_files:" not in text:
        return None
    new_text, count = _LCB_DATA_FILES_RE.subn(
        lambda match: f"{match.group('prefix')}{target}", text, count=1
    )
    if not count:
        return None
    try:
        yaml_path.write_text(new_text, encoding="utf-8")
    except OSError:
        return None
    return OFFLINE_LIVECODEBENCH_DATA
