[CmdletBinding(PositionalBinding = $false)]
param(
  [switch]$Rebuild,[switch]$NoCache,[switch]$EnableNestedDocker,
  [string]$VillaniCodeSource,[string]$VillaniCodeInstallSpec,
  [string]$Image = "villanibench:local",
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$BenchArgs)
if (-not $BenchArgs -or $BenchArgs.Count -eq 0) { throw "Usage: ./scripts/villanibench-docker.ps1 [opts] <villanibench args...>" }
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path; $repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$needsVillani = (($BenchArgs -join ' ') -match '--runner\s+villani')
$mode = "none"; if ($needsVillani) { $mode = "github"; if ($VillaniCodeInstallSpec) { $mode = "spec" }; if ($VillaniCodeSource) { $mode = "local" } }
$staged = Join-Path $repoRoot ".docker_build/villani-code-src"
if ($mode -eq "local") {
  $src = (Resolve-Path $VillaniCodeSource -ErrorAction Stop).Path
  if (-not (Test-Path (Join-Path $src "pyproject.toml")) -and -not (Test-Path (Join-Path $src "setup.py")) -and -not (Test-Path (Join-Path $src "package.json"))) { throw "Local source must contain pyproject.toml, setup.py, or package.json" }
  if (Test-Path $staged) { Remove-Item -Recurse -Force $staged }
  New-Item -ItemType Directory -Force -Path $staged | Out-Null
  robocopy $src $staged /MIR /XD .git .venv venv __pycache__ .pytest_cache .mypy_cache .ruff_cache node_modules dist build artifacts output logs /XF *.gguf *.safetensors *.bin | Out-Null
}
$imageExists = $true; try { docker image inspect $Image | Out-Null } catch { $imageExists = $false }
if ($Rebuild -or -not $imageExists) {
  $buildArgs = @("build","-t",$Image); if ($NoCache) { $buildArgs += "--no-cache" }
  $buildArgs += @("--build-arg","VILLANI_CODE_INSTALL_MODE=$mode")
  if ($mode -eq "spec") { $buildArgs += @("--build-arg","VILLANI_CODE_INSTALL_SPEC=$VillaniCodeInstallSpec") }
  if ($mode -eq "local") { $buildArgs += @("--build-arg","VILLANI_CODE_SOURCE_IN_CONTEXT=/tmp/villani-code-src") }
  $buildArgs += $repoRoot; & docker @buildArgs; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if ($mode -eq "local" -and (Test-Path $staged)) { Remove-Item -Recurse -Force $staged }
$sandboxHostRoot = Join-Path $repoRoot ".villanibench_sandboxes"; New-Item -ItemType Directory -Force -Path $sandboxHostRoot | Out-Null
$dockerArgs = @("run","--rm","--mount","type=bind,src=$repoRoot,dst=/work,rw","--mount","type=bind,src=$sandboxHostRoot,dst=/sandboxes,rw","-w","/work","-e","VILLANIBENCH_HOST_SANDBOX_ROOT=$sandboxHostRoot","-e","VILLANIBENCH_CONTAINER_SANDBOX_ROOT=/sandboxes")
if ($EnableNestedDocker) {
  if ($IsWindows) { throw "Nested Docker from native Windows PowerShell requires Docker socket access. Run from WSL or disable -EnableNestedDocker." }
  if (-not (Test-Path "/var/run/docker.sock")) { throw "Nested Docker requires /var/run/docker.sock. Run from WSL/Linux or disable -EnableNestedDocker." }
  $dockerArgs += @("--mount","type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock","-e","VILLANIBENCH_ENABLE_NESTED_DOCKER=1")
}
$helpText = (& docker run --help | Out-String); if ($helpText -match "host-gateway") { $dockerArgs += @("--add-host","host.docker.internal:host-gateway") }
$dockerArgs += $Image; $dockerArgs += $BenchArgs; & docker @dockerArgs; exit $LASTEXITCODE
