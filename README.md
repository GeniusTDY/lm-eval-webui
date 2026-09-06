# Lemonade Benchmark WebUI

纯 Python 标准库实现的轻量 WebUI，用于对模型运行 **Lemonade Bench** 与 **lm-eval** 两种基准测试，各自有独立排行榜与明细结果视图。

## 目录

- [1. 快速上手](#1-快速上手)
- [2. 部署](#2-部署)
- [3. 使用教程](#3-使用教程)
- [4. 任务与 API](#4-任务与-api)
- [5. 常见问题](#5-常见问题)

---

## 1. 快速上手

```bash
cd lm-eval-webui
python -m lm_eval_webui    # 打开 http://127.0.0.1:8080
```

依赖安装见[部署](#2-部署)。默认模型后端 `http://localhost:11434/v1`，可用环境变量或命令行参数覆盖：

```bash
OPENAI_BASE_URL="https://host" python -m lm_eval_webui
python -m lm_eval_webui --openai-base-url "https://host"
```

WebUI 界面中也可在刷新模型前直接改地址。

---

## 2. 部署

面向 **Linux**（Python 3.13+，推荐 3.14）。模型由独立的 OpenAI 兼容服务（llama.cpp/Ollama/vLLM 等）加载运行，WebUI 只负责编排、评测与排行，**不帮你启动模型**。

### 场景速查

| 网络约束 | pip 依赖来源 | 方式 | 一键脚本 |
| --- | --- | --- | --- |
| 无外网，有局域网 pip 源 | 局域网源 | 场景一（首选） | `deploy.sh` |
| 完全无网络 | 打包机预生成的 `offline/pip` | 场景二 | `install_offline.sh` |
| 可访问公网 | PyPI | 场景三 | 手动安装 |

> 代码与可离线数据（tinyBenchmarks、Lemonade CLI、缓存数据集、NLTK）已内置 `offline/`；平台相关的 `offline/pip` wheel 库需按场景一从局域网源装，或场景二由打包机预生成。

### 场景一：局域网 pip 源（首选）

依赖统一从局域网源拉取；`tinyBenchmarks`（`git+` 源）从自带副本本地安装。

```bash
# 第 1 参数为局域网源；也可用 $LMEVAL_WEBUI_PIP_INDEX 或 $PIP_INDEX_URL
./scripts/deploy.sh http://<局域网pip源>/simple
```

脚本会建 `.venv` → 从局域网源装依赖（跳过 `git+` 行）→ 本地装 vendored tinyBenchmarks → 校验 `offline/READY` 进入全离线模式。本场景**不依赖 `offline/pip`**。pip 源优先级：命令行参数 > `LMEVAL_WEBUI_PIP_INDEX` > `PIP_INDEX_URL` > 全局 pip 配置。

### 场景二：完全离线

依赖在联网打包机预生成后随项目整体拷贝。目标机要求：**Linux x86_64**、Python 3.13+、磁盘 ≥ 40 GB。

联网打包机（仅一次）：

```bash
python3 scripts/prepare_offline.py packages   # wheels + tinyBenchmarks + Lemonade CLI
python3 scripts/prepare_offline.py prepare    # 数据集 + LiveCodeBench 本地数据
python3 scripts/prepare_offline.py status     # 检查各任务均为 ok
```

可选参数：`--tasks ifeval,gsm8k`（自定义任务集）、`--strict`（任一任务失败则不生成 READY）。

断网机安装（拷贝整个项目目录，含 `offline/`，无需 `.venv/`、`data/`）：

```bash
python3 scripts/install_offline.sh            # 建 venv + 本地 --no-index 安装
OFFLINE_VENV_DIR=/srv/venv python3 scripts/install_offline.sh
```

存在 `offline/READY` 时进入全离线模式：子进程带 `HF_HOME/HF_*_OFFLINE` 等环境变量只读内置缓存、绝不重试网络；`NLTK_DATA`、`livecodebench_local` 自动指向本地。删除 `offline/READY` 即切回联网。

### 场景三：公网 / Docker / K8s

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install offline/vendor/tinyBenchmarks   # git+ 源改本地目录
OPENAI_BASE_URL="https://host" .venv/bin/python -m lm_eval_webui
```

Docker Compose：

```bash
OPENAI_BASE_URL="http://host.docker.internal:11434/v1" \
  docker compose -f deploy/docker-compose.yml up --build
```

Kubernetes（在 `statefulset.yaml` 设 `OPENAI_BASE_URL`）：

```bash
docker build -f deploy/Dockerfile -t savagemindz/lm-eval-webui:latest .
kubectl apply -f deploy/k8s/namespace.yaml deploy/k8s/pvc.yaml deploy/k8s/service.yaml deploy/k8s/statefulset.yaml
```

---

## 3. 使用教程

### 启动

```bash
.venv/bin/python -m lm_eval_webui --host 0.0.0.0 --port 8080 --openai-base-url http://localhost:11434/v1
```

打开 `http://127.0.0.1:8080`（远程则用 `http://<机器IP>:8080`）。

### 界面布局

| 区域 | 作用 |
| --- | --- |
| **Benchmark setup**（设置） | 配后端地址、选模型/套件/参数、发起 `` Run benchmark `` |
| **Leaderboard**（排行榜） | 按套件分页展示历史结果，可排序 |
| **Jobs**（作业） | 队列/运行状态、日志；可取消/清空 |

### 选模型与配置

1. 在 **OpenAI-compatible base URL** 填入后端地址，点 `` Refresh models ``（刷新模型）。
2. 切换套件：**Lemonade Bench scenarios**（测 TTFT、Token 吞吐、峰值内存等）或 **lm-eval tasks**（逐任务评分）。
3. lm-eval 内置三档 **Strix Balanced** 均衡方案（共用 8 个任务与 32,768 token 预算，仅样本数不同），任务集含 IFEval、GSM8K、MATH-500、MMLU-Pro、BBH 逻辑、ARC Chat、JSON Schema：

| 方案 | 每任务样本上限 | 每模型请求量级 |
| --- | --- | --- |
| `` Quick Screen ``（快速筛查） | 50 | ≤ 400 |
| `` Standard Compare ``（标准对比） | 200 | ≤ 1,600 |
| `` Full Validation ``（完整校验） | 全部 | — |

> 套用方案自动设 few-shot、批大小 1、并发 2、超时 7200s、对话模板等。**一旦改动任一任务或参数即变为自定义（Custom），不计入内置方案排名。**

### 运行基准

1. 选模型（可多选）→ 选套件/任务（或直接套用均衡方案）。
2. 按需调参数：后端/上下文矩阵、测量/预热次数、请求超时、显存追踪、是否重载/记录响应、**Limit 样本上限**、few-shot、生成 Token 上限、并发、批大小、对话模板。
3. 点 `` Run benchmark ``。

> ⚠️ 不设 **Limit** 的全量运行成本极高。正式开跑前建议抽样预检：`python scripts/smoke-all-models.py --webui-url http://<WebUI> --openai-base-url http://<后端>/v1 --run`

Lemonade Bench 要点：请求超时默认 **1800 秒**；CLI 退出码 0 但无成功请求的作业仍判失败；作业**始终串行**；镜像内置校验和固定的 Lemonade 11.6 CLI，源码本地运行由 `LEMONADE_CLI` 指定。

### 结果与排行榜

- **Leaderboard** 按套件分页（`lemonade_bench`、`lm_eval`），可用 **Profile** 过滤；点列头排序。
- **Balanced Overall**（均衡综合分）为推理/数学/指令遵循/结构化输出四类等权均值。
- 只有完整覆盖某内置方案全部任务的作业才进入该方案排名；Custom 与不完整运行保留指标但不参与排名。

### 使用提醒

- **生成式后端最稳妥**：优先 `generate_until` 类任务（如 gsm8k）。
- **全量扫描**：任务批大小保持默认 `1`，子进程跑完即退、及时释放内存。
- **LiveCodeBench**：用自带本地数据（`livecodebench_local`），结果计入 lm-eval 排行榜；单独运行时属 Custom，不参与内置方案排名。
- **离线/联网切换**：删除 `offline/READY` 即可切回联网。

---

## 4. 任务与 API

- 排队/运行中作业可在 Jobs 面板取消，需先取消才能清空或重跑。重启后排队作业恢复、中断作业标记失败。
- 请求并发默认 16 worker：`--max-request-workers 8`。
- 结果存于 `data/`（由 `` --data-dir `` 指定）。

| 接口 | 说明 |
| --- | --- |
| `GET /api/jobs` | 作业摘要 |
| `GET /api/jobs/<id>` | 作业详情 |
| `GET /api/jobs/<id>/log` | 日志尾部 |
| `GET /api/leaderboard` | 排行榜 |
| `GET /api/results?limit=1000&suite=lemonade_bench` | Lemonade 明细 |
| `GET /api/results?limit=1000&suite=lm_eval` | lm-eval 明细 |

---

## 5. 常见问题

| 症状 | 处理 |
| --- | --- |
| 局域网 pip 装不上/超时 | 确认 `--index-url`/`$LMEVAL_WEBUI_PIP_INDEX` 指向内网镜像且为完整 PyPI 同步 |
| `git+...tinyBenchmarks` 下载失败 | 无外网属正常；`deploy.sh` 已跳过该行，改装本地 `offline/vendor/tinyBenchmarks` |
| 无法加载模型 | 后端未启动或 `--openai-base-url` 不对；确认 `http://<后端>:11434/v1/models` 可访问 |
| `datasets 5.x` 不支持脚本式数据集 | 在线脚本式数据集已禁用；改用本地任务 `livecodebench_local` |
| 需要更小并发 | `--max-request-workers 8`（默认 16）、`--max-concurrent-jobs 1`（默认） |
