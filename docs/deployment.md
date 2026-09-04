# 部署方案（Deployment Guide）

本方案覆盖主流部署场景，并同时提供 **Windows 与 Linux** 两种系统的教程与一键脚本：

| 场景 | 外网 | pip 来源 | 适用 |
| --- | --- | --- | --- |
| 局域网 pip 源一键部署 | 无 | 局域网私有 pip 源 | **推荐**：无外网但有内网镜像 |
| 完全离线（内置 wheel 库） | 无 | 打包机预生成的 `offline/pip` | 无任何网络、仅有目标机 |
| 常规本地 / Docker / K8s | 有 | PyPI | 可访问公网 |

项目代码与数据依赖已内置在 `offline/`（vendored tinyBenchmarks、Lemonade CLI、缓存数据集、nltk），仅 `offline/pip`（平台特定 wheel 库）按需选择内置或改走局域网 pip 源。

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

## 2. 场景一：局域网 pip 源一键部署（Windows / Linux）

适合「**无外网、但内网有私有 pip 镜像**」的环境。Python 包一律从局域网 pip 源拉取；仅 vendored tinyBenchmarks 从本地磁盘安装（它是 `git+` 源，无法用 pip 直接下载）。

**前置条件**
- 目标机为 **Windows 或 Linux**，已安装 **Python 3.13+（推荐 3.14）**
- 局域网 pip 源可访问
- 已拿到整个项目目录（含 `offline/`）

### 2.1 Linux / macOS 一键部署

```bash
# 局域网源作为第 1 个参数（也可用 $LMEVAL_WEBUI_PIP_INDEX 或 $PIP_INDEX_URL）
./scripts/deploy.sh http://<局域网pip源>/simple
```

### 2.2 Windows 一键部署

在 PowerShell 中执行（需右键「以管理员身份」或放开执行策略）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 http://<局域网pip源>/simple
```

### 2.3 脚本做了什么

1. 选择 Python ≥3.13，创建虚拟环境 `.venv`（可用 `$env:OFFLINE_VENV_DIR` 换路径）。
2. 从局域网 pip 源安装 `requirements.txt` 全部依赖（**跳过 `git+` 的 tinyBenchmarks 行**）。
3. 从本地 `offline/vendor/tinyBenchmarks` 安装 vendored 版本（免公网）。
4. 校验 `offline/READY`，WebUI 自动进入全离线模式。

**pip 源优先级**：命令行参数 > `LMEVAL_WEBUI_PIP_INDEX` > `PIP_INDEX_URL` > 全局 pip 配置。都不指定时使用系统全局 pip 配置（如 `/etc/pip.conf` 或 Windows 用户 pip.ini 指向内网镜像）。

### 2.4 启动 WebUI

Linux／macOS：

```bash
.venv/bin/python -m lm_eval_webui \
  --host 0.0.0.0 --port 8080 \
  --openai-base-url http://<LAN模型主机>:11434/v1
```

Windows（PowerShell）：

```powershell
.\.venv\Scripts\python.exe -m lm_eval_webui --host 0.0.0.0 --port 8080 --openai-base-url http://<LAN模型主机>:11434/v1
```

Windows（CMD）：

```bat
.venv\Scripts\python -m lm_eval_webui --host 0.0.0.0 --port 8080 --openai-base-url http://<LAN模型主机>:11434/v1
```

浏览器打开 `http://<机器IP>:8080`。该方案无需 `offline/pip`（wheel 库未内置也可）。

## 3. 场景二：完全离线（内置 wheel 库，需联网打包机）

适合内网隔离环境。依赖全部内置，全程不需要互联网。

### 3.1 前置条件

只影响目标机，仅一个硬性前提：

| 项 | 要求 | 说明 |
| --- | --- | --- |
| 目标机操作系统 | Linux x86_64 | 内置 wheel 为 `manylinux x86_64` 专用 |
| Python 解释器 | 3.13+，推荐 3.14 | 离线包不含解释器本体，需目标机自带 |
| 编译器 | 不需要 | wheel 已预制，无源码编译 |
| 磁盘 | ≥ 40 GB 空闲 | 含 `offline/` 全部依赖 |

### 3.2 联网打包机上的准备（仅一次）

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

### 3.3 拷贝到断网机器

把整个项目目录（含 `offline/`）拷贝到目标机。无需拷贝 `.venv/`、`data/` 等本地产物。

### 3.4 断网机器安装

```bash
# 一条命令完成：建 venv + 从本地 wheelhouse 装依赖，全程 --no-index
python3 scripts/install_offline.sh

# 可选：自定义 venv 位置
OFFLINE_VENV_DIR=/srv/lm-webui-venv python3 scripts/install_offline.sh
```

脚本会校验离线包是否完整、Python 版本是否 ≥3.13，并严格从 `offline/pip/` 安装（不联网）。

### 3.5 启动 WebUI

```bash
# 连接局域网模型后端（默认 http://localhost:11434/v1，改成实际地址）
.venv/bin/python -m lm_eval_webui \
  --host 0.0.0.0 \
  --port 8080 \
  --data-dir data \
  --openai-base-url http://<LAN-模型主机>:11434/v1
```

浏览器打开 `http://<机器IP>:8080`。

### 3.6 全离线模式是如何生效的

当存在 `offline/READY` 标记（由 `prepare` 成功生成，`activate` 校验）时，WebUI 自动进入全离线模式：

- 每个 lm-eval 子进程都带上 `HF_HOME=<项目>/offline/hf-home`、`HF_HUB_OFFLINE=HF_DATASETS_OFFLINE=TRANSFORMERS_OFFLINE=1`，数据只从内置缓读取，绝不重试网络。
- `NLTK_DATA` 指向 `offline/nltk_data/`（含 `punkt_tab`），IFEval 打分不会联网下载。
- `livecodebench_local` 自动指向 `offline/livecodebench/lcb.jsonl`。

删除 `offline/READY` 即可随时切回联网模式。

### 3.7 离线部署清单核对

```bash
.venv/bin/python scripts/prepare_offline.py activate   # 就绪检查
.venv/bin/python scripts/prepare_offline.py status     # 查看各依赖状态
```

## 4. 场景三：常规本地部署（联网）

Linux／macOS：

```bash
cd lm-eval-webui
python -m lm_eval_webui                 # 打开 http://127.0.0.1:8080
```

Windows（PowerShell）：

```powershell
cd lm-eval-webui
python -m lm_eval_webui
```

> 本地部署前建议先建虚拟环境（`python -m venv .venv`）并 `pip install -r requirements.txt`，装完 `tinyBenchmarks` 需
> `pip install offline/vendor/tinyBenchmarks`，本地测试可去掉该 `git+` 行。

指定模型后端：

```bash
# 环境变量方式
OPENAI_BASE_URL="https://your-model-host.com" python -m lm_eval_webui
# 或命令行参数方式
python -m lm_eval_webui --openai-base-url "https://your-model-host.com"
```

## 5. 场景四：Docker Compose

```bash
OPENAI_BASE_URL="http://host.docker.internal:11434/v1" \
  docker compose -f deploy/docker-compose.yml up --build
```

打开 <http://127.0.0.1:8080>。

## 6. 场景五：Kubernetes

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

## 7. 常见问题排查

| 症状 | 原因 / 处理 |
| --- | --- |
| 局域网 pip 源安装失败／找不到包/超时 | 确认 `--index-url`/`$LMEVAL_WEBUI_PIP_INDEX`/`$PIP_INDEX_URL` 指向内网镜像；内网源是否为完整 PyPI 同步（是否含 torch/transformers 等大包）；必要时加 `--extra-index-url` 合并多个源 |
| `git+https://github.com/...tinyBenchmarks` 无法下载 | 无外网时正常；`deploy.sh`/`deploy.ps1` 已跳过该行，改为安装 `offline/vendor/tinyBenchmarks`（本地目录） |
| Windows 下 `python` 命令不存在 | 未将 Python 加入 PATH；或用 `py -3` 启动器（`deploy.ps1` 会自动回退到 `py`），或重装 Python 时勾选 “Add to PATH” |
| 报 `No module named 'requests'` / `aiohttp` | 运行环境依赖缺失；局域网部署应使用 `deploy.sh`/`deploy.ps1` 生成的 `.venv`，并确认依赖可从局域网源装齐 |
| 无法加载模型 | 模型后端未启动，或 `--openai-base-url` 未指向实际地址；确认 `http://<后端>:11434/v1/models` 可访问 |
| `datasets 5.x 不再支持脚本式数据集` | 在线脚本式数据集（如 `livecodebench`）已被禁用；改用本地任务 `livecodebench_local` |
| `prepare` 报缺库 | 先安装目标任务所需扩展包（见 3.2 备注）再打包 |
| 需要更小并发 | `--max-request-workers 8`（默认 16），`--max-concurrent-jobs 1`（默认）控制任务并发 |