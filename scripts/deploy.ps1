# One-click deploy for Windows (PowerShell) using an in-LAN pip index (no public internet).
#
# Preconditions:
#   * Python 3.13+ (recommended 3.14) is installed, with "Add to PATH" enabled.
#   * a LAN pip index is reachable. Provide it one of these ways (highest wins):
#       $env:LMEVAL_WEBUI_PIP_INDEX, $env:PIP_INDEX_URL, or the 1st argument:
#           powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 http://pip-mirror.lan/simple
#     If none is set, the global pip config is used (internal mirror).
#   * the offline/ bundle ships in the repo (vendored tinyBenchmarks, Lemonade
#     CLI, cached datasets). The pip wheelhouse (offline/pip) is NOT required
#     because packages are fetched from the LAN index.
#
# Runs strictly against the LAN pip source; nothing is pulled from the public
# internet.

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RepoRoot

$VenvDir = if ($env:OFFLINE_VENV_DIR) { $env:OFFLINE_VENV_DIR } else { ".venv" }
$Py = Join-Path $VenvDir "Scripts\python.exe"
if ($args.Count -gt 0) { $Index = $args[0] }
elseif ($env:LMEVAL_WEBUI_PIP_INDEX) { $Index = $env:LMEVAL_WEBUI_PIP_INDEX }
elseif ($env:PIP_INDEX_URL) { $Index = $env:PIP_INDEX_URL }
else { $Index = $null }

Write-Host "== 局域网 pip 源一键部署 =="
Write-Host "  仓库目录   $RepoRoot"
Write-Host "  虚拟环境   $VenvDir"

# 1. Resolve a Python 3.13+ interpreter (python then py launcher).
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) { $PythonCmd = Get-Command py -ErrorAction SilentlyContinue }
if (-not $PythonCmd) { throw "[ERROR] 未找到 Python。请安装 Python 3.14 并勾选 'Add to PATH'。" }
$Python = $PythonCmd.Source

& $Python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)"
if ($LASTEXITCODE -ne 0) {
  throw "[ERROR] 需要 Python 3.13+（推荐 3.14），当前版本见: cmd /c `"$Python`" --version"
}

# 2. Create / reuse the virtualenv (stored in the project tree).
if (-not (Test-Path $Py)) {
  Write-Host "[venv] 创建 $VenvDir ..."
  & $Python -m venv $VenvDir
} else {
  Write-Host "[venv] 复用 $VenvDir"
}

# 3. Build the pip index flags.
$IndexArgs = @()
if ($Index) {
  $IndexArgs = @("--index-url", $Index)
  Write-Host "[pip] 使用局域网源: $Index"
} else {
  Write-Host "[pip] 未指定 --index-url，将使用全局 pip 配置（局域网镜像）。"
}

# 4. Install dependencies from the LAN index. Drop the git+ tinyBenchmarks line
#    (needs public GitHub); the vendored copy is installed from disk next.
$Req = Get-Content requirements.txt | Where-Object { $_ -notmatch '^git\+' }
$ReqFile = Join-Path $env:TEMP "lmeval-reqs-$PID.txt"
$Req | Set-Content $ReqFile
Write-Host "[pip] 从局域网源安装依赖（跳过 git+ tinyBenchmarks）..."
& $Py -m pip install @IndexArgs --no-cache-dir -r $ReqFile
Remove-Item $ReqFile -ErrorAction SilentlyContinue

# 5. Install the vendored tinyBenchmarks from disk (no network needed).
if ((Test-Path "offline\vendor\tinyBenchmarks\pyproject.toml") -or
    (Test-Path "offline\vendor\tinyBenchmarks\setup.py")) {
  Write-Host "[pip] 安装 vendored tinyBenchmarks ..."
  & $Py -m pip install @IndexArgs --no-cache-dir "offline\vendor\tinyBenchmarks"
}

# 6. Verify offline mode if the bundle marker ships with the repo.
if (Test-Path "offline\READY") {
  Write-Host "[activate] 校验离线环境（自动全离线运行）..."
  & $Py "scripts\prepare_offline.py" activate 2>$null
}

Write-Host ""
Write-Host "== 安装完成 =="
Write-Host "  全离线数据标记（offline/READY）已随仓库就绪，WebUI 自动以全离线模式运行。"
Write-Host "  启动（把模型接口改成你的局域网模型主机）:"
Write-Host "    & $Py -m lm_eval_webui --host 0.0.0.0 --port 8080 `
  --openai-base-url http://<LAN-模型主机>:11434/v1"