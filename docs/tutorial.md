# 使用教程

用 WebUI 对已安装模型运行 **Lemonade Bench** 与 **lm-eval** 两种基准，查看排行榜与明细。

> 文中「按钮」均指界面英文原文（反引号内），附中文说明便于对照。

## 目录

- [1. 启动](#1-启动)
- [2. 首页布局](#2-首页布局)
- [3. 选模型与配置](#3-选模型与配置)
- [4. 运行基准](#4-运行基准)
- [5. 结果与排行榜](#5-结果与排行榜)
- [6. 数据与接口](#6-数据与接口)
- [7. 使用提醒](#7-使用提醒)

---

## 1. 启动

```bash
.venv/bin/python -m lm_eval_webui --host 0.0.0.0 --port 8080 --openai-base-url http://localhost:11434/v1
```

打开 `http://127.0.0.1:8080`（远程则用 `http://<机器IP>:8080`）。

- **venv 路径**：`.venv/bin/python`（由 `deploy.sh` 生成）。
- **模型后端**：`http://localhost:11434/v1` 指向 llama.cpp/Ollama/vLLM 等 OpenAI 兼容服务，需自行独立运行，WebUI 不会替你启动模型。

## 2. 首页布局

| 区域 | 作用 |
| --- | --- |
| **头部** | 标题 + `` Refresh ``（刷新） |
| **Benchmark setup**（设置） | 配后端地址、选模型/套件/参数、发起 `` Run benchmark `` |
| **Leaderboard**（排行榜） | 按套件分页展示历史结果，可排序 |
| **Jobs**（作业） | 队列/运行状态、日志；可取消/清空 |

## 3. 选模型与配置

1. 在 **OpenAI-compatible base URL** 填入后端地址，点 `` Refresh models ``（刷新模型）。
2. 列表显示已加载模型，可用 `` Filter models ``（筛选）过滤。
3. 切换套件：**Lemonade Bench scenarios**（测 TTFT、Token 吞吐、峰值内存等）或 **lm-eval tasks**（逐任务评分）。
4. 任务视图：叶子任务可单独运行；分组/标签为聚合节点便于一键圈选。已选项显示在 **Selected**（已选）区。
5. lm-eval 内置三档 **Strix Balanced** 均衡方案（共用 8 个任务与 32,768 token 预算，仅样本数不同）：

| 方案 | 每任务样本上限 | 每模型请求量级 |
| --- | --- | --- |
| `` Quick Screen ``（快速筛查） | 50 | 约 400 |
| `` Standard Compare ``（标准对比） | 200 | 约 1,600 |
| `` Full Validation ``（完整校验） | 全部 | — |

> 套用方案自动设 few-shot、批大小 1、并发 2、超时 7200s、对话模板等。**一旦改动任一任务或参数即变为自定义（Custom）。**

## 4. 运行基准

1. 选模型（可多选）→ 选套件/任务（或直接套用均衡方案）。
2. 按需调参数：后端/上下文矩阵、测量与预热次数、请求超时、显存追踪、是否重载/记录响应、**Limit 样本上限**、few-shot、生成 Token 上限、并发、批大小、对话模板。
3. 点 `` Run benchmark ``。

> ⚠️ 不设 **Limit** 的全量运行成本极高。正式开跑前建议抽样预检：
>
> ```bash
> python scripts/smoke-all-models.py --webui-url http://<WebUI> --openai-base-url http://<后端>/v1 --run
> ```

## 5. 结果与排行榜

- **Leaderboard** 按套件分页（`lemonade_bench`、`lm_eval`），可用 **Profile** 过滤；点列头排序。
- **Balanced Overall**（均衡综合分）是推理/数学/指令遵循/结构化输出四类等权均值。
- **参与排名的条件**：只有完整覆盖某内置方案全部任务的作业才进入该方案排名；Custom 与不完整运行保留指标但不参与排名。
- **Jobs** 面板看状态、时长徽标、日志尾部（`` <id>/log ``）；运行中/排队作业可取消，取消后才能清空或重跑。

## 6. 数据与接口

结果存于 `data/`（由 `` --data-dir `` 指定）。常用只读接口：

| 接口 | 说明 |
| --- | --- |
| `GET /api/jobs` | 作业摘要 |
| `GET /api/jobs/<id>` | 作业详情 |
| `GET /api/jobs/<id>/log` | 日志尾部 |
| `GET /api/leaderboard` | 排行榜 |
| `GET /api/results?offset=0&limit=1000&suite=lm_eval` | 分页明细 |

## 7. 使用提醒

- **生成式后端最稳妥**：优先 `generate_until` 类任务（如 gsm8k）。
- **全量扫描**：**Task batch size**（任务批大小）保持默认 `1`，子进程跑完即退、及时释放内存。
- **LiveCodeBench**：用自带本地数据（`livecodebench_local`），结果计入 lm-eval 排行榜；单独运行时属 Custom，不参与内置方案排名。
- **离线/联网切换**：删除 `offline/READY` 即可从全离线切回联网。