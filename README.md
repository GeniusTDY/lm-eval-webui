# Lemonade Benchmark WebUI

纯 Python 标准库实现的轻量 WebUI，用于对模型运行 **Lemonade Bench** 与 **lm-eval** 两种基准测试，各自有独立排行榜与明细结果视图。

> **文档**：部署见 [`docs/deployment.md`](docs/deployment.md)（局域网 pip 源 / 全离线 / 公网）；使用见 [`docs/tutorial.md`](docs/tutorial.md)。一键脚本：`scripts/deploy.sh`（Linux）。

## 目录

- [1. 快速上手](#1-快速上手)
- [2. 模型后端](#2-模型后端)
- [3. Lemonade Bench](#3-lemonade-bench)
- [4. 离线部署](#4-离线部署)
- [5. Docker / Kubernetes](#5-docker--kubernetes)
- [6. 任务与 API](#6-任务与-api)
- [7. 均衡方案与打分](#7-均衡方案与打分)

---

## 1. 快速上手

```bash
cd lm-eval-webui
python -m lm_eval_webui    # 打开 http://127.0.0.1:8080
```

依赖安装方式见[部署文档](docs/deployment.md)。

## 2. 模型后端

默认后端 `http://localhost:11434/v1`，可用环境变量或命令行参数覆盖：

```bash
OPENAI_BASE_URL="https://host" python -m lm_eval_webui
python -m lm_eval_webui --openai-base-url "https://host"
```

WebUI 界面中也可在刷新模型前直接改地址。

## 3. Lemonade Bench

第一套件，封装 `lemonade bench`，记录 TTFT、每秒 Token 吞吐、请求耗时、峰值显存/内存、失败数、后端与上下文长度。场景覆盖 chat、coding、long-context、embedding、image。

选项支持：后端×上下文的矩阵、测量/预热次数、请求超时、内存追踪、运行间重载模型、是否记录响应。后端留空时使用各模型已注册的后端（仅跨后端对比才需显式填写）。

- 请求超时默认 **1800 秒**（避免 64K/128K 与 image 场景受 CLI 五分钟限制）。
- CLI 退出码 0 但无成功请求的作业仍判失败。
- Lemonade Bench 作业**始终串行**（CLI 在共享服务端负责模型加载/卸载）。
- 镜像内置校验和固定的 Lemonade 11.6 CLI；源码本地运行由 `LEMONADE_CLI` 指定，缺省取 `PATH`。

## 4. 离线部署

无外网点到端评测。HuggingFace 数据集、LiveCodeBench 数据、NLTK 资源均捆绑于 `offline/`，拷贝整个项目目录即可部署。完整步骤见[部署文档](docs/deployment.md)。

```bash
# 联网打包机（一次）
python3 scripts/prepare_offline.py packages   # pip wheels + tinyBenchmarks + Lemonade CLI
python3 scripts/prepare_offline.py prepare    # 数据集 + LiveCodeBench
python3 scripts/prepare_offline.py status     # 检查捆绑状态

# 断网机
python3 scripts/install_offline.sh
.venv/bin/python -m lm_eval_webui --openai-base-url http://<模型主机>:11434/v1
```

存在 `offline/READY` 时进入全离线模式：子进程带 `HF_HOME/HF_*_OFFLINE` 等环境变量，只读内置缓存；`NLTK_DATA`、`livecodebench_local` 自动指向本地。删除 `offline/READY` 即切回联网。

## 5. Docker / Kubernetes

```bash
# Compose
OPENAI_BASE_URL="http://host.docker.internal:11434/v1" \
  docker compose -f deploy/docker-compose.yml up --build

# K8s：构建镜像后按需创建 namespace / secret / pvc / service / statefulset
docker build -f deploy/Dockerfile -t savagemindz/lm-eval-webui:latest .
kubectl apply -f deploy/k8s/namespace.yaml deploy/k8s/pvc.yaml deploy/k8s/service.yaml deploy/k8s/statefulset.yaml
```

在 `statefulset.yaml` 设 `OPENAI_BASE_URL`。HF 缓存调优：`LMEVAL_WEBUI_HF_RETRIES`、`..._RETRY_DELAY`、`..._RETRY_MAX_DELAY`。

## 6. 任务与 API

- 排队/运行中作业可在 Jobs 面板取消，需先取消才能清空或重跑。重启后排队作业恢复、中断作业标记失败。
- 请求并发默认 16 worker：`--max-request-workers 8`。

| 接口 | 说明 |
| --- | --- |
| `GET /api/jobs` | 作业摘要 |
| `GET /api/jobs/<id>` | 作业详情 |
| `GET /api/jobs/<id>/log` | 日志尾部 |
| `GET /api/leaderboard` | 排行榜 |
| `GET /api/results?limit=1000&suite=lemonade_bench` | Lemonade 明细 |
| `GET /api/results?limit=1000&suite=lm_eval` | lm-eval 明细 |

## 7. 均衡方案与打分

lm-eval 选择器内置三档 **Strix Balanced** 方案，共用 8 个生成式任务与 32,768 token 预算，仅每任务样本数不同：

| 方案 | 每任务样本上限 | 每模型请求量级 |
| --- | --- | --- |
| Quick Screen | 50 | ≤400 |
| Standard Compare | 200 | ≤1600 |
| Full Validation | 全部 | — |

任务集含 IFEval、GSM8K、MATH-500、MMLU-Pro(CS/Eng)、BBH 逻辑、ARC Chat、JSON Schema。套用方案自动设 few-shot、批大小 1、并发 2、超时 7200s、任务批次 4、对话模板、样本日志、单作业；**改动任一设置即变为 Custom**，不计入内置方案排名。

**Balanced Overall** 为推理/数学/指令遵循/编码四类等权均值。

> 关键提示：〔思维链支持 / 模型锁定 / 大规模预检等〕细节见[使用教程](docs/tutorial.md)，此处不再赘述。