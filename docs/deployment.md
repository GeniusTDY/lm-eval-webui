# 部署方案

面向 **Linux / Windows** 的部署指南，按网络条件选一条路径即可。

## 场景速查

| 网络约束 | pip 依赖来源 | 推荐路径 | 一键脚本 |
| --- | --- | --- | --- |
| 无外网，有局域网 pip 源 | 局域网源 | **场景一**（首选） | `deploy.sh` / `deploy.ps1` |
| 完全无网络 | 打包机预生成的 `offline/pip` | 场景二 | `install_offline.sh` |
| 可访问公网 | PyPI | 场景三 | 手动安装 |

> 代码与可离线数据（tinyBenchmarks、Lemonade CLI、缓存数据集、NLTK）已内置 `offline/`；平台相关的 `offline/pip` wheel 库需按场景一从局域网源装，或场景二由打包机预生成。

## 目录

- [1. 总体架构](#1-总体架构)
- [2. 场景一：局域网 pip 源一键部署（推荐）](#2-场景一局域网-pip-源一键部署推荐)
- [3. 场景二：完全离线](#3-场景二完全离线)
- [4. 公网 / Docker / K8s](#4-公网--docker--k8s)
- [5. 常见问题](#5-常见问题)

---

## 1. 总体架构

```
┌──────────────┐    OpenAI    ┌──────────────┐
│ 模型后端(独立)  │────────────▶│ WebUI        │
│ llama.cpp/Ollama/vLLM │ 兼容接口 │ 编排·打分·排行 │
└──────────────┘            └──────────────┘
```

- **模型后端**：加载模型的 OpenAI 兼容服务，需自行独立运行。
- **WebUI**：负责任务编排、评测、结果入库与排行榜，**不帮你启动模型**。

---

## 2. 场景一：局域网 pip 源一键部署（推荐）

适用「无外网、有私有 pip 镜像」。依赖统一从局域网源拉取；仅 `tinyBenchmarks`（`git+` 源）从自带副本本地安装。

**前置**：Windows 或 Linux；Python 3.13+（推荐 3.14）；局域网源最好为完整 PyPI 同步。

**Linux／macOS**

```bash
# 第 1 参数为局域网源；也可用 $LMEVAL_WEBUI_PIP_INDEX 或 $PIP_INDEX_URL
./scripts/deploy.sh http://<局域网pip源>/simple
```

**Windows**（PowerShell）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 http://<局域网pip源>/simple
```

**脚本做了**：建 `.venv` → 从局域网源装依赖（跳过 `git+` 行）→ 本地装 vendored tinyBenchmarks → 校验 `offline/READY` 进入全离线模式。

> pip 源优先级：命令行参数 > `LMEVAL_WEBUI_PIP_INDEX` > `PIP_INDEX_URL` > 全局 pip 配置。

**启动 WebUI**

```bash
# Linux
.venv/bin/python -m lm_eval_webui --host 0.0.0.0 --port 8080 --openai-base-url http://<模型主机>:11434/v1
```

```powershell
# Windows（PowerShell）
.\.venv\Scripts\python.exe -m lm_eval_webui --host 0.0.0.0 --port 8080 --openai-base-url http://<模型主机>:11434/v1
```

打开 `http://<机器IP>:8080`。本场景**不依赖 `offline/pip`**。

---

## 3. 场景二：完全离线

适用「完全无网络、无内网镜像」。依赖在联网打包机预生成后随项目整体拷贝。

### 前置（目标机）

| 项 | 要求 | 说明 |
| --- | --- | --- |
| 操作系统 | Linux x86_64 | wheel 为 manylinux x86_64 专用 |
| Python | 3.13+（推荐 3.14） | 需目标机自带解释器 |
| 编译器 | 不需要 | wheel 已预制 |
| 磁盘 | ≥ 40 GB | 容纳 `offline/` |

### 联网打包机（仅一次）

```bash
python3 scripts/prepare_offline.py packages   # wheels + tinyBenchmarks + Lemonade CLI
python3 scripts/prepare_offline.py prepare    # 数据集 + LiveCodeBench 本地数据
python3 scripts/prepare_offline.py status     # 检查各任务均为 ok
```

可选参数：`--tasks ifeval,gsm8k`（自定义任务集）、`HF_ENDPOINT=https://hf-mirror.com`（私有镜像）、`--strict`（任一任务失败则不生成 READY）。

> ⚠️ `prepare` 前先装目标任务扩展包才能预热全部任务：IFEval 需 `langdetect`、`immutabledict`；minerva_math500 需 `sympy`、`math_verify`、`antlr4-python3-runtime`；jsonschema_bench 需 `jsonschema`。

### 拷贝到断网机后安装

拷贝整个项目目录（含 `offline/`），无需 `.venv/`、`data/`。

```bash
python3 scripts/install_offline.sh                                  # 建 venv + 本地 --no-index 安装
OFFLINE_VENV_DIR=/srv/venv python3 scripts/install_offline.sh       # 自定义 venv 位置

.venv/bin/python -m lm_eval_webui --host 0.0.0.0 --port 8080 --data-dir data --openai-base-url http://<模型主机>:11434/v1
```

### 全离线模式如何生效

存在 `offline/READY` 时：子进程带 `HF_HOME=<项目>/offline/hf-home`、`HF_HUB_OFFLINE=HF_DATASETS_OFFLINE=TRANSFORMERS_OFFLINE=1`，只读内置缓存、绝不重试网络；`NLTK_DATA` 指向 `offline/nltk_data/`；`livecodebench_local` 自动指向 `offline/livecodebench/lcb.jsonl`。删除 `offline/READY` 即切回联网。

自检：`.venv/bin/python scripts/prepare_offline.py activate`（就绪检查）/ `status`（各依赖状态）。

---

## 4. 公网 / Docker / K8s

适用可访问公网（pip 走 PyPI）。

```bash
cd lm-eval-webui
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install offline/vendor/tinyBenchmarks   # git+ 源改本地目录
OPENAI_BASE_URL="https://host" .venv/bin/python -m lm_eval_webui
```

Windows 将 `.venv/bin/*` 换成 `.venv\Scripts\*`。

**Docker Compose**

```bash
OPENAI_BASE_URL="http://host.docker.internal:11434/v1" \
  docker compose -f deploy/docker-compose.yml up --build
```

**Kubernetes**

```bash
docker build -f deploy/Dockerfile -t savagemindz/lm-eval-webui:latest . && docker push ...
kubectl -n lm-eval-webui create secret generic huggingface-token --from-literal=token="$HF_TOKEN"   # 可选：提升 HF 带宽
kubectl apply -f deploy/k8s/namespace.yaml deploy/k8s/pvc.yaml deploy/k8s/service.yaml deploy/k8s/statefulset.yaml
```

在 `statefulset.yaml` 设 `OPENAI_BASE_URL`。HF 调优：`LMEVAL_WEBUI_HF_RETRIES`、`..._RETRY_DELAY`、`..._RETRY_MAX_DELAY`。

---

## 5. 常见问题

| 症状 | 处理 |
| --- | --- |
| 局域网 pip 装不上/超时 | 确认 `--index-url`/`$LMEVAL_WEBUI_PIP_INDEX` 指向内网镜像且为完整 PyPI 同步；必要时 `--extra-index-url` 合并多源 |
| `git+...tinyBenchmarks` 下载失败 | 无外网属正常；`deploy.sh`/`deploy.ps1` 已跳过该行，改装本地 `offline/vendor/tinyBenchmarks` |
| Windows 找不到 `python` | 未加 PATH；用 `py -3` 启动器，或重装时勾选 Add to PATH |
| `No module named 'requests'`/`aiohttp` | 用一键脚本生成的 `.venv` 重装依赖 |
| 无法加载模型 | 后端未启动或 `--openai-base-url` 不对；确认 `http://<后端>:11434/v1/models` 可访问 |
| `datasets 5.x` 不支持脚本式数据集 | 在线脚本式数据集已禁用；改用本地任务 `livecodebench_local` |
| 需要更小并发 | `--max-request-workers 8`（默认 16）、`--max-concurrent-jobs 1`（默认） |