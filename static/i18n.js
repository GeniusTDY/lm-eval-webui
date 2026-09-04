"use strict";

const I18N_ZH = {
	Refresh: "刷新",
	"Run Lemonade Bench and lm-eval against installed models and compare each suite on its own leaderboard.":
		"对已安装的模型运行 Lemonade Bench 与 lm-eval 基准测试，并在各自的排行榜中比较结果。",

	"Lemonade Bench scenarios": "Lemonade Bench 场景",
	"lm-eval tasks": "lm-eval 任务",

	"Benchmark setup": "基准测试设置",
	"OpenAI-compatible base URL": "OpenAI 兼容基础 URL",
	"Installed models": "已安装模型",
	"Refresh models": "刷新模型",
	"Filter models": "筛选模型",
	"Type to search models": "输入关键词筛选模型",
	"Type to search benchmark scenarios": "输入关键词筛选基准场景",
	"Type to search 14k+ tasks": "输入关键词筛选 1.4 万+ 任务",
	"Loading models…": "正在加载模型…",
	"Loading tasks…": "正在加载任务…",
	"Loading job details…": "正在加载作业详情…",
	"Loading log output…": "正在加载日志输出…",
	"Benchmark suite": "基准测试套件",
	"Balanced benchmark profiles": "均衡基准配置方案",
	"Apply a repeatable task set and benchmark recipe without changing the selected models or runtime backend.":
		"应用可复现的任务集合与基准测试配方，且不改变已选模型或运行时后端。",
	"Profile: Custom": "配置方案：自定义",
	"Task view": "任务视图",
	"Leaf tasks": "叶子任务",
	"Groups / tags": "分组 / 标签",
	"Filter tasks": "筛选任务",
	Previous: "上一页",
	Next: "下一页",
	"hide incompatible": "隐藏不兼容任务",
	"hide gated": "隐藏受限任务",
	"hide non-English": "隐藏非英语任务",
	"Lemonade Bench measures TTFT, token throughput, request duration, and memory use. Long-context scenarios are opt-in and can run for a long time.": "Lemonade Bench 度量首 Token 延迟（TTFT）、Token 吞吐量、请求耗时与内存占用。长上下文场景需手动启用，且可能运行较长时间。",
	"Selected scenarios": "已选场景",
	"No scenarios selected.": "尚未选择任何场景。",
	"Model runtime options": "模型运行时选项",
	"llama.cpp backend": "llama.cpp 后端",
	"Auto / endpoint default": "自动 / 端点默认",
	"Benchmark options": "基准测试选项",
	"Backends (blank = each model's configured backend)":
		"后端（留空 = 使用各模型已配置的后端）",
	"Override: rocm, vulkan": "覆盖设置：rocm、vulkan",
	"Context sizes (blank = model default)": "上下文长度（留空 = 模型默认值）",
	"Example: 4096, 32768": "示例：4096、32768",
	"Measurement runs": "测量次数",
	"Warmup runs": "预热次数",
	"Request timeout seconds": "请求超时（秒）",
	"Track VRAM and RAM": "追踪显存与内存",
	"Reload between runs": "运行之间重载模型",
	"Save response log": "保存响应日志",
	"Limit (blank = all)": "样本上限（留空 = 全部）",
	"All samples": "全部样本",
	"Few-shot (blank = task default)": "少样本数（留空 = 任务默认值）",
	"Task default": "任务默认值",
	"Generation token limit": "生成 Token 上限",
	"Timeout seconds": "超时（秒）",
	"Concurrent requests": "并发请求数",
	"Concurrent jobs": "并发作业数",
	"Batch size": "批大小",
	"Task batch size": "任务批大小",
	"Apply chat template": "应用对话模板",
	"Few-shot as multiturn": "少样本以多轮对话方式提供",
	"Log samples": "记录样本日志",
	"Judge model": "评审模型",
	"Timeout minutes": "超时（分钟）",
	"Pass attempts": "尝试次数",
	"Context window": "上下文窗口",
	"Maximum output tokens": "最大输出 Token 数",
	"Provider timeout minutes": "服务提供方超时（分钟）",
	"Provider retries": "服务提供方重试次数",
	"Use Lemonade recipe unchanged": "原样使用 Lemonade 配方",
	"Run benchmark": "运行基准测试",

	Leaderboard: "排行榜",
	"Leaderboard suite": "排行榜套件",
	"Lemonade Bench leaderboard": "Lemonade Bench 排行榜",
	"lm-eval leaderboard": "lm-eval 排行榜",
	"No leaderboard results yet.": "排行榜暂无结果。",
	"Profile": "配置方案",
	"All profiles": "全部配置方案",
	"Lemonade Bench compares average TTFT, token throughput, duration, and peak memory for each backend/context combination. Select any column heading to sort; select it again to reverse the order.":
		"Lemonade Bench 针对每种后端/上下文组合比较平均首 Token 延迟（TTFT）、Token 吞吐量、耗时与峰值内存。点击任意列标题可排序，再次点击可切换排序方向。",
	"Balanced Overall gives equal weight to reasoning, math, instruction following, and structured output. Rankings are kept separate by profile. Select any column heading to sort; select it again to reverse the order.":
		"均衡综合得分对推理、数学、指令遵循与结构化输出赋予相同权重，排名按配置方案分别统计。点击任意列标题可排序，再次点击可切换排序方向。",

	"Detailed result filters": "详细结果筛选器",
	Models: "模型",
	"All models": "全部模型",
	"Models: All": "模型：全部",
	Scenarios: "场景",
	"All scenarios": "全部场景",
	"Scenarios: All": "场景：全部",
	"All tasks": "全部任务",
	Metrics: "指标",
	"All metrics": "全部指标",
	"Models tested": "受测模型",
	"Scenarios or tasks run": "运行的场景或任务",
	"Metrics for selected tasks": "所选任务的指标",
	"Metrics: First available": "指标：首个可用项",
	"No numeric results yet.": "暂无数值结果。",
	"No numeric results match the selected filters.": "没有符合所选筛选条件的数值结果。",
	Model: "模型",
	Scenario: "场景",
	Category: "类别",
	"Backend / context": "后端 / 上下文",
	Metric: "指标",
	Value: "数值",
	Runs: "运行次数",
	Job: "作业",
	Task: "任务",
	Samples: "样本",
	Runtime: "运行时长",

	Jobs: "作业",
	Show: "显示",
	"Filter jobs by benchmark suite": "按基准测试套件筛选作业",
	"All jobs": "全部作业",
	"Select all visible jobs": "选中全部可见作业",
	"Cancel active": "取消进行中的作业",
	"Clear selected": "清除所选",
	"Rerun selected": "重新运行所选",
	"Clear failed jobs": "清除失败作业",
	"Refresh jobs": "刷新作业",
	"No jobs yet.": "暂无作业。",
	"0 jobs": "0 个作业",
	"0 selected": "已选 0 项",
	"{0} job": "{0} 个作业",
	"{0} jobs": "{0} 个作业",
	"{0} of {1}": "{0} / {1}",
	"{0} selected": "已选 {0} 项",
	"{0} selected · {1} active": "已选 {0} 项 · {1} 项进行中",
	"No {0} jobs.": "暂无 {0} 作业。",
	"Job {0} · {1} · {2} {3}": "作业 {0} · {1} · {2} 个{3}",
	"Live output": "实时输出",
	"Live output for job {0}": "作业 {0} 的实时输出",
	"No log output yet.": "暂无日志输出。",
	Cancel: "取消",
	"Stopping…": "正在停止…",
	"Stop this job and mark it cancelled": "停止此作业并标记为已取消",
	Rerun: "重新运行",
	"Cancel this job before rerunning it": "重新运行前请先取消此作业",
	"Clear this job and start it again with the same options":
		"清除此作业并以相同选项重新启动",
	"Live job activity; refreshed every five seconds": "作业实时状态，每 5 秒自动刷新",

	queued: "排队中",
	running: "运行中",
	cancelling: "取消中",
	succeeded: "已成功",
	failed: "已失败",
	cancelled: "已取消",
	incomplete: "未完成",
	partial: "部分完成",
	"Runtime {0}": "运行时长 {0}",
	"{0} requests": "{0} 个请求",
	"Batch {0}/{1}": "批次 {0}/{1}",
	Running: "运行中",
	Waiting: "等待中",
	Stopping: "停止中",
	items: "项",
	batches: "批",
	tasks: "任务",
	task: "任务",
	requests: "请求",
	scenario: "场景",
	scenarios: "场景",

	"Suite: {0}": "套件：{0}",
	"Profile: {0}": "配置方案：{0}",
	"Progress: {0}": "进度：{0}",
	"Current task batch: {0}/{1}": "当前任务批次：{0}/{1}",
	"Current task": "当前任务",
	"Current tasks": "当前任务",
	"Current batch requests: {0}": "当前批次请求数：{0}",
	"Elapsed: {0}": "已用时间：{0}",
	"Runtime: {0}": "运行时长：{0}",
	"Rerun of: {0}": "重新运行自：{0}",
	"Task batch size: {0}": "任务批大小：{0}",
	"Completed task batches: {0}/{1}": "已完成任务批次：{0}/{1}",
	"Model protection: {0}": "模型保护：{0}",
	pinning: "固定中",
	pinned: "已固定",
	releasing: "释放中",
	released: "已释放",
	release_failed: "释放失败",
	released_after_restart: "重启后已释放",
	unsupported: "不支持",
	"Judge: {0}": "评审模型：{0}",
	"Pass attempts: {0}": "尝试次数：{0}",
	"Agent context: {0}": "智能体上下文：{0}",
	"Max output: {0}": "最大输出：{0}",
	"Provider timeout: {0}m": "服务超时：{0} 分钟",
	"Provider retries: {0}": "服务重试次数：{0}",
	"Recipe policy: Lemonade unchanged": "配方策略：原样使用 Lemonade",
	"Runs: {0}": "测量次数：{0}",
	"Warmups: {0}": "预热次数：{0}",
	"Backends: {0}": "后端：{0}",
	"Backend source: {0}": "后端来源：{0}",
	"Contexts: {0}": "上下文：{0}",
	"Runtime backend: {0}": "运行时后端：{0}",

	"Stopping selected job(s)…": "正在停止所选作业…",
	"Cancellation requested for {0} job(s).": "已请求取消 {0} 个作业。",
	"Cleared {0} selected job(s).": "已清除 {0} 个所选作业。",
	"Cleared {0} failed job(s).": "已清除 {0} 个失败作业。",
	"Rerunning job…": "正在重新运行作业…",
	"Started {0} rerun job(s).": "已启动 {0} 个重新运行的作业。",
	"Starting…": "正在启动…",
	"Started {0} job(s).": "已启动 {0} 个作业。",
	"Applied {0}: {1} tasks": "已应用 {0}：{1} 个任务",
	"{0}/task": "{0}/任务",
	"Select at least one model and one {0} {1}.": "请至少选择一个模型和一个{0}{1}。",
	"Maximum output tokens cannot exceed the context window.":
		"最大输出 Token 数不能超过上下文窗口。",

	"Could not load models: {0}": "无法加载模型：{0}",
	"Could not load tasks: {0}": "无法加载任务：{0}",
	"Could not load results: {0}": "无法加载结果：{0}",
	"Could not load job details: {0}": "无法加载作业详情：{0}",
	"Loading {0} {1}…": "正在加载 {0} {1}…",
	"Loading {0} result details…": "正在加载 {0} 结果详情…",
	"No {0} leaderboard results yet.": "{0} 排行榜暂无结果。",
	"Showing {0} of {1} models.": "正在显示 {0}/{1} 个模型。",
	"Showing {0} of {1} matching {2} ({3} total).": "正在显示 {0}/{1} 个匹配的{2}（总计 {3} 项）。",
	"Page {0} of {1}": "第 {0} / {1} 页",
	"No models returned by the OpenAI-compatible endpoint.":
		"OpenAI 兼容端点未返回任何模型。",
	"Invalid response from {0}": "来自 {0} 的响应无效",
	"Request timed out: {0}": "请求超时：{0}",
	"unknown model": "未知模型",
	unknown: "未知",
	Custom: "自定义",
	"Custom (legacy)": "自定义（旧版）",
	default: "默认",

	Status: "状态",
	Tasks: "任务",
	Backend: "后端",
	"Runtime backend": "运行时后端",
	Context: "上下文",
	"Prompt tok/s": "提示词 Token/s",
	"Tok/s": "Token/s",
	TTFT: "TTFT",
	Overall: "综合得分",
	"Balanced Overall": "均衡综合得分",
	"Equal-weight mean of reasoning, math, instruction following, and structured output":
		"推理、数学、指令遵循与结构化输出的等权平均值",
	"Avg TTFT": "平均 TTFT",
	"Avg tok/s": "平均 Token/s",
	"Peak VRAM": "峰值显存",
	"Peak RAM": "峰值内存",
	Failed: "失败次数",
	Judge: "评审模型",
	"Max output": "最大输出",
	Passed: "通过数",
	Success: "成功率",
	"Avg duration": "平均耗时",
	Coding: "代码",
	Reasoning: "推理",
	Math: "数学",
	"Coding / Structured Output": "代码 / 结构化输出",
	"Instruction Following": "指令遵循",
	"LiveCodeBench code generation pass@1": "LiveCodeBench 代码生成 pass@1",
	Other: "其他",
	Chat: "对话",
	"Long context": "长上下文",
	Embeddings: "嵌入",
	"Image generation": "图像生成",
	Vision: "视觉",
	General: "通用",
	"Coding / SWE": "代码 / 软件工程",
	"up to {0} output tokens": "最多 {0} 个输出 Token",
	compatible: "兼容",
	incompatible: "不兼容",
	gated: "受限",
	group: "分组",
	tag: "标签",
	rank: "排名",

	"{0}: None available": "{0}：无可用项",
	"{0}: All ({1})": "{0}：全部（{1} 项）",
	"{0}: {1}": "{0}：{1}",
	"{0}: {1} of {2}": "{0}：{1} / {2}",
	"Sort by {0}, {1}": "按{0}排序，{1}",
	"Sort by {0} ({1})": "按{0}排序（{1}）",
	ascending: "升序",
	descending: "降序",
	"{0} chart": "{0} 图表",
	"{0} ctx": "{0} 上下文",
	"{0}s": "{0} 秒",
	"{0}m": "{0} 分",
	"{0}h {1}m": "{0} 小时 {1} 分",
	"{0}d {1}h": "{0} 天 {1} 小时",

	"{0} detailed metric comparison": "{0} 详细指标对比",
	"{0} detailed results": "{0} 详细结果",
	"Lemonade Bench detailed metric comparison":
		"Lemonade Bench 详细指标对比",
	"Lemonade Bench detailed results": "Lemonade Bench 详细结果",
	"Selected {0}": "已选{0}",
	"Select visible {0}": "选中可见{0}",
	"Unselect visible {0}": "取消选中可见{0}",
	"Select visible": "选中可见项",
	"Unselect visible": "取消选中可见项",
	"No {0} selected.": "尚未选择任何{0}。",
	"OpenAI-compatible chat backends are generation oriented. Use generate_until tasks first.":
		"OpenAI 兼容对话后端面向文本生成，建议优先选择 generate_until 类任务。",

	"Quick Screen": "快速筛选",
	"Standard Compare": "标准对比",
	"Full Validation": "完整验证",
	"Up to 50 examples from each balanced task.": "每个均衡任务最多取 50 个样本。",
	"Up to 200 examples from each balanced task.":
		"每个均衡任务最多取 200 个样本。",
	"Every available example from each balanced task.":
		"每个均衡任务的全部可用样本。",
	"Full validation can take multiple days per model.":
		"完整验证每个模型可能耗时数天。",

	"all samples": "全部样本",
};

function detectLanguage() {
	const languages = navigator.languages || [navigator.language || "en"];
	return languages.some((language) =>
		String(language).toLowerCase().startsWith("zh"),
	)
		? "zh"
		: "en";
}

let I18N_LANG = detectLanguage();

function t(key) {
	if (I18N_LANG === "zh" && Object.prototype.hasOwnProperty.call(I18N_ZH, key))
		return I18N_ZH[key];
	return key;
}

function tf(key, ...args) {
	return args.reduce(
		(text, value, index) => text.split(`{${index}}`).join(String(value)),
		t(key),
	);
}

function applyStaticI18n(root = document) {
	root.querySelectorAll("[data-i18n]").forEach((element) => {
		element.textContent = t(element.dataset.i18n);
	});
	root.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
		element.placeholder = t(element.dataset.i18nPlaceholder);
	});
	root.querySelectorAll("[data-i18n-title]").forEach((element) => {
		element.title = t(element.dataset.i18nTitle);
	});
	root.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
		element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
	});
	document.documentElement.lang = I18N_LANG === "zh" ? "zh-CN" : "en";
}

document.addEventListener("DOMContentLoaded", () => {
	applyStaticI18n();
});
