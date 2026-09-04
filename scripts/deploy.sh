#!/usr/bin/env bash
# One-click deploy for Linux/macOS using an in-LAN pip index (no public internet).
#
# Preconditions:
#   * python3 >= 3.13 (recommended 3.14) is installed.
#   * a LAN pip index is reachable. Provide it one of these ways (highest wins):
#       LMEVAL_WEBUI_PIP_INDEX env, PIP_INDEX_URL env, or the 1st argument:
#           ./scripts/deploy.sh http://pip-mirror.lan/simple
#     If none is set, the global pip config is used (e.g. /etc/pip.conf pointing
#     at the internal mirror).
#   * the offline/ bundle ships in the repo (vendored tinyBenchmarks, Lemonade
#     CLI, cached datasets). The pip wheelhouse (offline/pip) is NOT required
#     because packages are fetched from the LAN index.
#
# Runs strictly against the LAN pip source; nothing is pulled from the public
# internet.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_DIR="${OFFLINE_VENV_DIR:-.venv}"
PY="${VENV_DIR}/bin/python"
INDEX="${1:-${LMEVAL_WEBUI_PIP_INDEX:-${PIP_INDEX_URL:-}}}"

echo "== 局域网 pip 源一键部署 =="
echo "  仓库目录   $REPO_ROOT"
echo "  虚拟环境   $VENV_DIR"

# 1. Resolve a Python 3.13+ interpreter.
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
  echo "[ERROR] 未找到 python3 —— 请先安装 Python 3.14（指定 3.13+）。" >&2
  exit 1
fi
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1);'; then
  echo "[ERROR] 需要 Python 3.13+（推荐 3.14），当前为 $("$PYTHON" --version 2>&1)。" >&2
  exit 1
fi

# 2. Create / reuse the virtualenv.
if [ ! -x "$PY" ]; then
  echo "[venv] 创建 $VENV_DIR …"
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "[venv] 复用 $VENV_DIR"
fi

# 3. Build the pip index flags.
INDEX_ARGS=()
if [ -n "$INDEX" ]; then
  INDEX_ARGS=(--index-url "$INDEX")
  echo "[pip] 使用局域网源: $INDEX"
else
  echo "[pip] 未指定 --index-url，将使用全局 pip 配置（局域网镜像）。"
fi

# 4. Install dependencies from the LAN index. Drop the git+ tinyBenchmarks line
#    (needs public GitHub); the vendored copy is installed from disk next.
REQ="$(mktemp)"
grep -v '^git+' requirements.txt > "$REQ"
echo "[pip] 从局域网源安装依赖（跳过 git+ tinyBenchmarks）…"
"$PY" -m pip install "${INDEX_ARGS[@]}" --no-cache-dir -r "$REQ"
rm -f "$REQ"

# 5. Install the vendored tinyBenchmarks from disk (no network needed).
if [ -f offline/vendor/tinyBenchmarks/pyproject.toml ] || [ -f offline/vendor/tinyBenchmarks/setup.py ]; then
  echo "[pip] 安装 vendored tinyBenchmarks …"
  "$PY" -m pip install "${INDEX_ARGS[@]}" --no-cache-dir offline/vendor/tinyBenchmarks
fi

# 6. Verify offline mode if the bundle marker ships with the repo.
if [ -f offline/READY ]; then
  echo "[activate] 校验离线环境（自动全离线运行）…"
  "$PY" scripts/prepare_offline.py activate || true
fi

echo
echo "== 安装完成 =="
echo "  全离线数据标记（offline/READY）已随仓库就绪，WebUI 自动以全离线模式运行。"
echo "  启动（把模型接口改成你的局域网模型主机）:"
echo "    ${PY} -m lm_eval_webui \\"
echo "      --host 0.0.0.0 --port 8080 \\"
echo "      --openai-base-url http://<LAN-模型主机>:11434/v1"