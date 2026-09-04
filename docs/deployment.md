# 部署方案（Deployment Guide）

本方案覆盖两种部署场景：**联网机器打包 → 断网机器安装**（全离线开箱即用），以及常规的本地 / Docker / Kubernetes 部署。项目代码与依赖解耦：除平台相关的 Python wheel 库（`offline/pip`）外，离线所需依赖均已内置在 `offline/` 内。

## 1. 总体架构

```
┌────────────────────────┐        ┌──────────────────────────┐
│  联网打包机（在线）      │ 拷贝   │  断网部署机（目标）        │
│  1. prepare_offline.py │ ─────▶ │  1. install_offline.sh   │
│     packages           │ 整个    │     （全程 --no-index）    │
│  2. prepare_offline.py │ 项目目录│  2. 启动 WebUI            │
│     prepare            │        │  3. 连接模型后端           │
└────────────────────────┘        └──────────────────────────┘
```

评测模型运行在独立的 OpenAI 兼容后端（如 llama.cpp 服务、Ollama、vLLM）上；WebUI 只负责任务编排、打分入库与排行榜展示。

## 2. 场景一：全离线部署（推荐）

适合内网隔离环境。依赖全部内置，全程不需要互联网。

### 2.1 前置条件

只影响目标机，仅一个硬性前提：

| 项 | 要求 | 说明 |
| --- | --- | --- |
| 目标机操作系统 | Linux x86_64 | 内置 wheel 为 `manylinux x86_64` 专用 |
| Python 解释器 | 3.13+，推荐 3.14 | 离线包不含解释器本体，需目标机自带 |
| 编译器 | 不需要 | wheel 已预制，无源码编译 |
| 磁盘 | ≥ 40 GB 空闲 | 含 `offline/` 全部依赖 |

### 2.2 联网打包机上的准备（仅一次）

先确保评测 Python 环境可运行项目全部测试任务（租户自查）：

```bash
cd lm-eval-webui

# 1) 内置 Python/源码依赖：pip wheels + tinyBenchmarks + Lemonade CLI
python3 scripts/prepare_offline.py packages

# 2) 缓存任务数据集 + LiveCodeBench 本地数据（会写入 MANIFEST，逐步检查）
python3 scripts/prepare_offline.py prepare

# 3) 检查离线捆绑状态（确认各任务为 ok）
python3 scripts/prepare_offline.py status
```

可选参数：

```bash
# 自定义任务集（逗号分隔）
python3 scripts/prepare_offline.py prepare --tasks ifeval,gsm8k

# 使用私有 HF 镜像而非公网 hub
HF_ENDPOINT=https://hf-mirror.com python3 scripts/prepare_offline.py prepare

# 严格模式：任一任务缓存失败则不生成 READY 标记
python3 scripts/prepare_offline.py prepare --strict
```

- `packages` 生成 `offline/pip/`（wheel 库）、`offline/vendor/`（tinyBenchmarks 源码）、`offline/bin/`（Lemonade CLI 归档）。
- `prepare` 通过真实 lm-eval 任务管理器把各任务所需数据集下载进 `offline/hf-home/`，并拷贝 `offline/livecodebench/lcb.jsonl`。
- 任一任务失败不会终止整个打包，而是记录在 `offline/MANIFEST.json`。

> 注意：`prepare` 阶段请先安装目标任务所需的扩展包（IFEval 需 `langdetect`、`immutabledict`；minerva_math500 需 `sympy`、`math_verify`、`antlr4-python3-runtime`；jsonschema_bench 需 `jsonschema`），确保预热覆盖全部任务。

### 2.3 拷贝到断网机器

把整个项目目录（含 `offline/`）拷贝到目标机。无需拷贝 `.venv/`、`data/` 等本地产物。

### 2.4 断网机器安装

```bash
# 一条命令完成：建 venv + 从本地 wheelhouse 装依赖，全程 --no-index
python3 scripts/install_offline.sh

# 可选：自定义 venv 位置
OFFLINE_VENV_DIR=/srv/lm-webui-venv python3 scripts/install_offline.sh
```

脚本会校验离线包是否完整、Python 版本是否 ≥3.13，并严格从 `offline/pip/` 安装（不联网）。

### 2.5 启动 WebUI

```bash
# 连接局域网模型后端（默认 http://localhost:11434/v1，改成实际地址）
.venv/bin/python -m lm_eval_webui \
  --host 0.0.0.0 \
  --port 8080 \
  --data-dir data \
  --openai-base-url http://<LAN-模型主机>:11434/v1
```

浏览器打开 `http://<机器IP>:8080`。

### 2.6 全离线模式是如何生效的

当存在 `offline/READY` 标记（由 `prepare` 成功生成，`activate` 校验）时，WebUI 自动进入全离线模式：

- 每个 lm-eval 子进程都带上 `HF_HOME=<项目>/offline/hf-home`、`HF_HUB_OFFLINE=HF_DATASETS_OFFLINE=TRANSFORMERS_OFFLINE=1`，数据只从内置缓读取，绝不重试网络。
- `NLTK_DATA` 指向 `offline/nltk_data/`（含 `punkt_tab`），IFEval 打分不会联网下载。
- `livecodebench_local` 自动指向 `offline/livecodebench/lcb.jsonl`。

删除 `offline/READY` 即可随时切回联网模式。

### 2.7 离线部署清单核对

```bash
.venv/bin/python scripts/prepare_offline.py activate   # 就绪检查
.venv/bin/python scripts/prepare_offline.py status     # 查看各依赖状态
```

## 3. 场景二：常规本地部署（联网）

```bash
cd lm-eval-webui
python -m lm_eval_webui                 # 打开 http://127.0.0.1:8080
```

指定模型后端：

```bash
# 环境变量方式
OPENAI_BASE_URL="https://your-model-host.com" python -m lm_eval_webui
# 或命令行参数方式
python -m lm_eval_webui --openai-base-url "https://your-model-host.com"
```

## 4. 场景三：Docker Compose

```bash
OPENAI_BASE_URL="http://host.docker.internal:11434/v1" \
  docker compose -f deploy/docker-compose.yml up --build
```

打开 <http://127.0.0.1:8080>。

## 5. 场景四：Kubernetes

```bash
docker build -f deploy/Dockerfile -t savagemindz/lm-eval-webui:latest .
docker push savagemindz/lm-eval-webui:latest
```

编辑 `deploy/k8s/statefulset.yaml` 使用该镜像，然后：

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl -n lm-eval-webui create secret generic huggingface-token \
  --from-literal=token="$HF_TOKEN"     # 可选：提升 HF 下载带宽/限流
kubectl apply -f deploy/k8s/pvc.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/statefulset.yaml
```

在 `statefulset.yaml` 中把 `OPENAI_BASE_URL` 设为 Pod 可达的 OpenAI 兼容端点。关联 HF 缓存的调优环境变量：`LMEVAL_WEBUI_HF_RETRIES`、`LMEVAL_WEBUI_HF_RETRY_DELAY`、`LMEVAL_WEBUI_HF_RETRY_MAX_DELAY`。

## 6. 常见问题排查

| 症状 | 原因 / 处理 |
| --- | --- |
| 报 `No module named 'requests'` / `aiohttp` | 运行环境的 WebUI 依赖缺失；离线部署应使用 `install_offline.sh` 生成的 venv，并向 `offline/pip/requirements.offline.txt` 确认依赖在清单内 |
| 无法加载模型 | 模型后端未启动，或 `--openai-base-url` 未指向实际地址；确认 `http://<后端>:11434/v1/models` 可访问 |
| `datasets 5.x 不再支持脚本式数据集` | 在线脚本式数据集（如 `livecodebench`）已被禁用；改用本地任务 `livecodebench_local` |
| `prepare` 报缺库 | 先安装目标任务所需扩展包（见 2.2 备注）再打包 |
| 需要更小并发 | `--max-request-workers 8`（默认 16），`--max-concurrent-jobs 1`（默认）控制任务并发 |