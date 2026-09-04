# 使用教程（Usage Tutorial）

本教程介绍如何用 WebUI 对已安装模型运行 **Lemonade Bench** 与 **lm-eval** 测评，并查看排行榜与明细结果。

## 1. 启动与访问

```bash
cd lm-eval-webui
.venv/bin/python -m lm_eval_webui \
  --host 0.0.0.0 \
  --port 8080 \
  --openai-base-url http://localhost:11434/v1
```

浏览器打开 <http://127.0.0.1:8080>（远程机器用 `http://<机器IP>:8080`）。

> 模型后端需独立运行且已就绪（llama.cpp、Ollama、vLLM 等任意 OpenAI 兼容服务）。WebUI 不会替你启动模型。

## 2. 首页布局

- **头部**：标题 + `Refresh` 刷新按钮。
- **Benchmark setup（基准测试设置）**：模型后端地址、已安装模型列表、套件与基准选项、`Run benchmark` 按钮。
- **Leaderboard（排行榜）**：按套件分页展示历史结果，可排序。
- **Jobs（作业）**：队列与运行状态、日志、取消/清空。

## 3. 选模型与配置

### 3.1 连接模型后端

- 在 **OpenAI-compatible base URL** 填入模型后端地址（如 `http://localhost:11434/v1`），点击 **Refresh models**。
- 列表会显示后端已加载的模型；可用 **Filter models** 关键词过滤。

### 3.2 选择基准套件

在任务区顶部切换：

- **Lemonade Bench scenarios** —— 执行 `lemonade bench`，度量 TTFT、Token 吞吐、请求耗时、峰值显存/内存，覆盖 chat / coding / long-context / embedding / image 等场景。
- **lm-eval tasks** —— 执行 lm-evaluation-harness，按叶子任务评分。

### 3.3 任务视图与选择

- 两种视图：**叶子任务**（可直接运行并单列分数的任务）与 **分组 / 标签**（聚合节点，便于一键圈选多个下层任务）。
- 切换视图时会自动滤除不匹配的已选项。
- 选中任务出现在 **Selected** 区；可用关键词过滤。

### 3.4 内置均衡方案（lm-eval）

任务选择器提供三个 **Strix Balanced** 均衡方案，共用同一组 8 个任务与 32,768 token 推理预算，仅样本数不同：

- **Quick Screen** —— 每任务最多 50 例（每模型至多约 400 次请求）
- **Standard Compare** —— 每任务最多 200 例（约 1,600 次请求）
- **Full Validation** —— 每任务全部样本

应用方案会一并设定 task-default few-shot、batch 1、并发 2、超时 7200s、task batch 4、对话模板、样本日志与单作业并发。**改动任一任务或设置会标记为 Custom。**

## 4. 运行测评

1. 选择模型（可多选）。
2. 选择套件与任务（或直接套用均衡方案）。
3. 按需调整：**后端/上下文矩阵**、测量/预热次数、请求超时、显存追踪、重载、响应日志、**Limit（样本上限）**、few-shot、生成 token 上限、并发、批大小、是否应用对话模板等。
4. 点击 **Run benchmark**。

> 未设 **Limit** 的全量运行可能非常昂贵——正式跑前可先用
> `python scripts/smoke-all-models.py --webui-url <URL> --openai-base-url <URL> --run` 做预检。

## 5. 查看结果与排行榜

- **Leaderboard** 按套件分页：`lemonade_bench`、`lm_eval`；可用 **Profile** 过滤。
- 点任一列标题可排序，再点一次反向。**Balanced Overall** 为推理/数学/指令遵循/结构化输出的等权均值，分类内多任务不会静默加权。
- 只有完整覆盖某个内置方案所有任务的作业才会参与该方案的排名；Custom 与不完整运行保留指标但不排名。
- **Jobs** 面板查看作业状态、运行时长徽标、`<id>/log` 日志尾；运行中/排队作业可取消，作业取消后才能清空/重跑。

## 6. 数据与接口

结果持久化在 `data/`（`--data-dir`）。常用只读接口：

- `GET /api/jobs` —— 轻量作业摘要
- `GET /api/jobs/<id>` —— 作业详情
- `GET /api/jobs/<id>/log` —— 高效日志尾
- `GET /api/leaderboard` —— 紧凑排行榜条目
- `GET /api/results?offset=0&limit=1000&suite=lm_eval` —— 分页明细

## 7. 常见使用提醒

- **生成式后端最稳的任务**：`generate_until` 类（如 gsm8k）比 `loglikelihood` 类更适合 chat 后端；任务搜索框内有 `Type to search 14k+ tasks` 提示。
- **大范围全量扫描**：把 **Task batch size** 设为默认 `1`，让每个子进程跑完即退出释放内存。
- **LiveCodeBench** 走本地数据（`livecodebench_local`），结果进入 **lm-eval 排行榜**；单纯跑它属于 Custom 方案，不参与内置排名。
- **删除 offline/READY** 可随时从全离线模式切回联网模式。