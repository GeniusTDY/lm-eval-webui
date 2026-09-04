#!/usr/bin/env bash
set -euo pipefail

# One-command offline install + launch helper for lm-eval-webui.
#
# Assumes:
#   * the whole project directory (including offline/) was copied to the
#     disconnected machine, and it was prepared once with
#     `python3 scripts/prepare_offline.py packages` on an online machine;
#   * Python 3.13+ (recommended 3.14) is available on the offline machine.
#
# Runs strictly offline: packages are installed from the local wheelhouse.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="${OFFLINE_VENV_DIR:-.venv}"
WHEELS="offline/pip"
REQ_OFFLINE="$WHEELS/requirements.offline.txt"
TB_DIR="offline/vendor/tinyBenchmarks"
OFFLINE_MARKER="offline/READY"

echo "== 离线安装 / 启动辅助（全程免网） =="
echo "  仓库目录   $REPO_ROOT"
echo "  虚拟环境   $VENV_DIR"

# 1. Verify the offline bundle was present.
if [ ! -f "$REQ_OFFLINE" ]; then
  echo "[ERROR] 缺少 $REQ_OFFLINE。" >&2
  echo "        请先在联网机器上运行: python3 scripts/prepare_offline.py packages，再拷贝整个目录。" >&2
  exit 1
fi

# 2. Resolve a Python 3.13+ interpreter.
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
  echo "[ERROR] 未找到 python3 —— 离线机器需自带 Python 3.14。" >&2
  exit 1
fi
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)'; then
  echo "[ERROR] 需要 Python 3.13+（推荐 3.14），当前为 $("$PYTHON" --version 2>&1)。" >&2
  exit 1
fi

# 3. Create / reuse the virtualenv.
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[venv] 创建 $VENV_DIR …"
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "[venv] 复用 $VENV_DIR"
fi
PY="$VENV_DIR/bin/python"

# 4. Install all pinned dependencies from the local wheelhouse only.
if [ ! -e "$VENV_DIR/.offline-installed" ]; then
  echo "[pip] 从本地 wheelhouse 安装依赖（--no-index）…"
  "$PY" -m pip install --no-index --no-cache-dir --upgrade pip >/dev/null 2>&1 || true
  "$PY" -m pip install --no-index --find-links "$WHEELS" -r "$REQ_OFFLINE"
  if [ -f "$TB_DIR/pyproject.toml" ] || [ -f "$TB_DIR/setup.py" ]; then
    echo "[pip] 安装 tinyBenchmarks（内置源码）…"
    "$PY" -m pip install --no-index --find-links "$WHEELS" "$TB_DIR"
  fi
  touch "$VENV_DIR/.offline-installed"
else
  echo "[pip] 依赖已安装，跳过"
fi

# 5. Verify the offline bundle marker (optional; WebUI auto-detects it).
if [ -f "$OFFLINE_MARKER" ]; then
  "$PY" scripts/prepare_offline.py activate
fi

echo
echo "== 安装完成 =="
if [ -f "$OFFLINE_MARKER" ]; then
  echo "  offline/READY 存在，WebUI 将自动以全离线模式运行。"
  echo "  启动（模型接口地址请改成你的局域网模型主机）:"
  echo "    $VENV_DIR/bin/python -m lm_eval_webui \\"
  echo "      --openai-base-url http://<LAN-模型主机>:11434/v1"
else
  echo "  提示：未检测到 offline/READY，WebUI 将以联网模式运行。"
fi