# Lemonade Benchmark WebUI

A small stdlib Python WebUI for running Lemonade Bench and lm-evaluation-harness
against installed models. Each suite has its own leaderboard and detailed
result view.

> **详细文档**：部署方案见
> [`docs/deployment.md`](docs/deployment.md)（含全离线开箱即用部署），使用教程见
> [`docs/tutorial.md`](docs/tutorial.md)。

## Run

```bash
cd lm-eval-webui
python -m lm_eval_webui
```

Then open <http://127.0.0.1:8080>.

The default OpenAI-compatible endpoint is `http://localhost:11434/v1`.
Set a different startup default with either:

```bash
OPENAI_BASE_URL="https://your-openai-compatible-host" python -m lm_eval_webui
# or
python -m lm_eval_webui --openai-base-url "https://your-openai-compatible-host"
```

The WebUI also lets you edit the OpenAI-compatible base URL before refreshing
models or starting benchmark jobs.

## Lemonade Bench

Lemonade Bench is the first suite in the setup and result tabs. It wraps the
upstream `lemonade bench` command and records TTFT, output tokens per second,
request duration, peak VRAM/RAM, failed runs, backend, and context size. Its
scenario picker is populated from Lemonade's bundled scenario catalog and
includes chat, coding, long-context, embedding, and image-generation workloads.
Long-context scenarios remain opt-in.

The benchmark options support backend and context-size matrices, measurement
and warmup counts, request timeout, memory tracking, model reloads between runs,
and optional response logging. With the backend field blank, the WebUI uses each
llama.cpp model's registered backend instead of asking the CLI to try every
installed backend; enter explicit backends only for a cross-backend comparison.
These per-run selections use Lemonade's non-persistent `save_options=false`
behavior and do not rewrite model registrations. The CLI runs through a
loopback-only HTTP bridge so Python handles the remote TLS connection; this
avoids Lemonade CLI 11.6 `Failed to read connection` errors on valid responses
without changing the Lemonade server or benchmark result format. The WebUI uses
a 1,800-second request timeout by default so the opt-in 64K/128K and image
scenarios are not constrained by the CLI's five-minute default. A CLI exit code
of zero is still classified as a failed job when its result contains no
successful requests. Lemonade Bench jobs are always serialized because the CLI controls
model loading and unloading on a shared Lemonade server. The
container image includes the checksum-pinned Lemonade 11.6 CLI and supports both
amd64 and arm64 builds. Source-based local runs require a compatible `lemonade`
CLI on `PATH`; override its location with `LEMONADE_CLI=/path/to/lemonade`.

## Docker Compose

```bash
OPENAI_BASE_URL="http://host.docker.internal:11434/v1" \
  docker compose -f deploy/docker-compose.yml up --build
```

Then open <http://127.0.0.1:8080>.

## Kubernetes

Build and push the image:

```bash
docker build -f deploy/Dockerfile -t savagemindz/lm-eval-webui:latest .
docker push savagemindz/lm-eval-webui:latest
```

Edit `deploy/k8s/statefulset.yaml` to use that image, then deploy:

```bash
kubectl apply -f deploy/k8s/namespace.yaml
# Optional, improves Hugging Face dataset download bandwidth/rate limits:
kubectl -n lm-eval-webui create secret generic huggingface-token \
  --from-literal=token="$HF_TOKEN"
kubectl apply -f deploy/k8s/pvc.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/statefulset.yaml
```

Set `OPENAI_BASE_URL` in `deploy/k8s/statefulset.yaml` to the OpenAI-compatible
endpoint reachable from the pod. The example runs as a
single-replica StatefulSet with `/data` mounted from the `lm-eval-data` PVC. It
also points Hugging Face
caches at `/data/huggingface` so downloaded lm-eval datasets persist across pod
restarts. Authenticated Hugging Face downloads are optional: if the
`huggingface-token` Secret exists, Kubernetes exposes it as `HF_TOKEN` and
`HUGGING_FACE_HUB_TOKEN` inside the WebUI container. Transient Hugging Face
dataset API failures are retried by default, and corrupt cached dataset metadata
is removed before retrying. Tune retries with `LMEVAL_WEBUI_HF_RETRIES`,
`LMEVAL_WEBUI_HF_RETRY_DELAY`, and `LMEVAL_WEBUI_HF_RETRY_MAX_DELAY`.

## Job control and API behavior

Queued and running jobs can be cancelled from the Jobs panel. Running
subprocess groups receive `SIGTERM` and then `SIGKILL` after a grace period.
Active jobs must be cancelled before they can be cleared or rerun. After an
application restart, queued jobs are resumed and jobs interrupted while running
are marked failed instead of remaining stuck.

The browser polls only lightweight job summaries and never overlaps polling
requests. Leaderboard data is refreshed when jobs reach a terminal state, while
detailed rows are loaded lazily in paginated requests. The backend builds each
result summary once, persists compact per-job summaries under the data directory,
and caches serialized ETag/gzip responses. HTTP request concurrency is bounded
to 16 workers by default; override it with:

```bash
python -m lm_eval_webui --max-request-workers 8
```

The relevant read APIs are:

- `GET /api/jobs` — lightweight job summaries
- `GET /api/jobs/<id>` — full job details
- `GET /api/jobs/<id>/log` — an efficient log tail
- `GET /api/leaderboard` — compact leaderboard entries
- `GET /api/results?offset=0&limit=1000&suite=lemonade_bench` — paginated Lemonade Bench rows
- `GET /api/results?offset=0&limit=1000&suite=lm_eval` — paginated lm-eval rows

## Balanced lm-eval profiles and scoring

The lm-eval task picker includes three versioned **Strix Balanced** profiles.
They use the same eight generation-compatible tasks and the same 32,768-token
reasoning budget so results remain comparable; only the number of examples per
task changes:

- **Quick Screen** — up to 50 examples per task (up to 400 requests per model)
- **Standard Compare** — up to 200 examples per task (up to 1,600 requests)
- **Full Validation** — every example from every profile task

The shared task set covers IFEval, GSM8K, MATH-500, MMLU-Pro computer science
and engineering, BBH logical deduction, ARC Challenge Chat, and JSON Schema
Bench. Applying a profile also selects task-default few-shot settings, batch size
1, request concurrency 2, a 7,200-second timeout, task batches of 4, chat
templating, sample logging, and one concurrent job. Changing any profile task or
setting marks the job as **Custom**. The backend verifies and persists the
profile rather than trusting a label sent by the browser, and older jobs are
shown as **Custom (legacy)**.

Leaderboard ranking is kept separate by profile. **Balanced Overall** is the
equal-weight mean of four category scores—Reasoning, Math, Instruction
Following, and Coding / Structured Output—so categories with more tasks do not
silently dominate. Recognized profile runs are ranked only after every required
task produced its canonical score. Custom and incomplete runs retain their
metrics but are not assigned a profile rank. Generation throughput and TTFT stay
separate from the quality percentage. Result tables also show each job's
wall-clock runtime from start through final cleanup, and completed job cards keep
that duration visible in a runtime badge. Legacy results fall back to lm-eval's
recorded evaluation time when full job timestamps are unavailable.

## Thinking models and quality preflight

Normal benchmark jobs are unlimited by default and preserve each task's own
few-shot setting. The OpenAI-compatible adapter allows at least 32,768 output
tokens, removes server-side task stop strings so they cannot terminate an
internal thinking block, and applies those stop strings locally to the final
answer. It accepts the `reasoning`, `reasoning_content`, and `analysis` stream
fields used by current vLLM, llama.cpp, and other compatible providers. Only
final `content` is scored; an unfinished reasoning trace is never treated as an
answer.

For performance telemetry, streaming requests ask OpenAI-compatible providers
for the final usage chunk. Native server timings are preferred; when vLLM does
not emit them, output tokens per second is calculated from completion-token
usage and the client-observed generation interval. Model context comes from the
advertised maximum or, for vLLM registry entries, the effective `ctx_size`
recipe setting. Runs completed before this telemetry was captured cannot be
reliably backfilled with tokens-per-second data.

A full run without **Limit** can be extremely expensive. Before starting one,
dry-run the all-model preflight:

```bash
python scripts/smoke-all-models.py \
  --webui-url https://lm-eval.example.net \
  --openai-base-url https://llm.example.net/v1
```

Review the discovered models and payload, then add `--run` to enqueue serial
GSM8K, generative MMLU, and IFEval jobs for every downloaded chat model
(non-chat TTS/transcription models are skipped). The preflight uses three
samples per task, enables sample logging, and fails any model that does not
return final answer content for every request or still reaches its generation
cap. Use repeated
`--model MODEL_ID` options to test a subset.

lm-eval jobs load and pin their selected model before the first request, keep it
pinned across every task batch, and unpin it when the job succeeds, fails, or is
cancelled. A competing model request receives HTTP 409 instead of evicting the
benchmark model.

Lemonade Bench is intentionally not pinned because the
upstream CLI reloads models between scenarios and backend/context combinations.
Hosts without Lemonade's lifecycle endpoints continue without model protection
and record that state in the job log. Alternatively, increase
`max_loaded_models` only when the host has enough memory for every concurrently
used model.

## Offline bundle (fully disconnected deployment)

The WebUI can run evaluation end-to-end with no internet access. All network
dependencies (HuggingFace datasets, the local LiveCodeBench data, and the NLTK
resources IFEval needs for scoring) are bundled inside the project tree under
`offline/`, so copying the project directory is enough to deploy.

On a machine **with** internet access, run:

```bash
python3 scripts/prepare_offline.py packages   # pip wheels + tinyBenchmarks + Lemonade CLI
python3 scripts/prepare_offline.py prepare    # datasets + LiveCodeBench
python3 scripts/prepare_offline.py status     # inspect what was bundled
```

`packages` bundles every pinned Python dependency as wheels (from
`requirements.txt`) into `offline/pip/`, vendors the `git+` tinyBenchmarks
source into `offline/vendor/`, and stores the Lemonade CLI archive in
`offline/bin/`. The wheelhouse is fully self-contained (wheels only, no
compilation needed on the offline machine) and covers the WebUI plus the
`lm-eval[api,tasks]` family (including torch/transformers).

On the disconnected machine, after `prepare` prepared the bundle, run the
one-command offline installer to build a working venv without any network I/O:

```bash
python3 scripts/install_offline.sh
# OFFLINE_VENV_DIR=/path python3 scripts/install_offline.sh   # custom venv path
.venv/bin/python -m lm_eval_webui --openai-base-url http://<LAN-模型主机>:11434/v1
```

`install_offline.sh` creates `.venv`, installs everything strictly from
`offline/pip` with `pip install --no-index --find-links`, installs the vendored
tinyBenchmarks, and reports the launch command. The offline machine still needs
a Python 3.14 interpreter; no compiler is required because `packages`
pre-builds any source-only dependency into a wheel.

`prepare` instantiates every bundled task through the real lm-eval task
manager, which downloads the exact dataset revisions the evaluator would use
into `offline/hf-home/`, and copies `offline/livecodebench/lcb.jsonl`. Use
`--tasks a,b` to bundle a custom task list and `HF_ENDPOINT=...` for a registry
mirror. A failed task is recorded in `offline/MANIFEST.json` instead of
aborting the whole bundle (`--strict` flips that).

Then copy the entire project directory to the offline machine and run:

```bash
python3 -m lm_eval_webui.server              # start the WebUI normally
```

Runtime behavior when `offline/READY` exists:

- Every lm-eval subprocess is launched with
  `HF_HOME=<project>/offline/hf-home`,
  `HF_HUB_OFFLINE=HF_DATASETS_OFFLINE=TRANSFORMERS_OFFLINE=1`, so all dataset
  reads come from the bundled cache and nothing retries the network.
- `NLTK_DATA` points at `offline/nltk_data/` (containing the `punkt_tab`
  tokenizer) so IFEval scoring never tries to download NLTK resources.
- `livecodebench_local` is automatically repointed at
  `offline/livecodebench/lcb.jsonl` (the task YAML carries the packaging
  machine's absolute path, which is rewritten on first use).

Delete `offline/READY` to return to normal online behavior at any time.

Prerequisite: the offline machine still needs the WebUI's Python (stdlib only)
plus the evaluation Python with `lm-eval` installed. Some bundled tasks need
extra packages in the evaluation Python — `langdetect` and `immutabledict`
(IFEval), `sympy`, `math_verify` and `antlr4-python3-runtime==4.11.*`
(minerva_math500), and `jsonschema` (jsonschema_bench) — install them before
packaging so the warmup covers every task.

## Notes

- This software was created with the help of AI coding assistants.
- Uses the `openai-compatible-chat-completions` lm-eval plugin, with the legacy
  `lemonade-chat-completions` alias retained for existing jobs.
- Generation-style (`generate_until`) tasks are the safest fit for chat
  completion backends.
- For broad/full lm-eval sweeps, **Task batch size** splits selected tasks into
  sequential subprocesses. The default `1` keeps memory lowest because each
  subprocess exits and releases loaded dataset/task state. Job cards report
  completed task batches separately from the live API-request count within the
  current task.
- Leaderboard scores use canonical primary metrics and equal-weight category
  rollups; use the profile filter when comparing models.
- Job cleanup removes selected job metadata, logs, telemetry, and run outputs.
  Legacy jobs with missing artifact paths are safely ignored instead of treating
  an empty path as `.`.