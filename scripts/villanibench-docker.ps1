[CmdletBinding(PositionalBinding = $false)]
param(
  [switch]$Rebuild,
  [switch]$NoCache,
  [switch]$EnableNestedDocker,
  [string]$Image = "villanibench:local",
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$BenchArgs
)

$forward = @($BenchArgs)
$parsed = @()
for ($i = 0; $i -lt $forward.Count; $i++) {
  $arg = $forward[$i]
  switch ($arg) {
    "--rebuild" { $Rebuild = $true; continue }
    "--no-cache" { $NoCache = $true; continue }
    "--enable-nested-docker" { $EnableNestedDocker = $true; continue }
    "--image" { $i++; $Image = $forward[$i]; continue }
    "--" { if ($i + 1 -lt $forward.Count) { $parsed += @($forward[($i + 1)..($forward.Count - 1)]) }; break }
    default { $parsed += @($forward[$i..($forward.Count - 1)]); break }
  }
}
$BenchArgs = @($parsed)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
$sandboxHostRoot = Join-Path $repoRoot ".villanibench_sandboxes"
New-Item -ItemType Directory -Force -Path $sandboxHostRoot | Out-Null

if (-not $BenchArgs -or $BenchArgs.Count -eq 0) { throw "Usage: ./scripts/villanibench-docker.ps1 [--rebuild] [--no-cache] [--image villanibench:local] [--enable-nested-docker] <villanibench args...>" }

$imageExists = $true
try { docker image inspect $Image | Out-Null } catch { $imageExists = $false }
if ($Rebuild -or -not $imageExists) {
  $buildArgs = @("build", "-t", $Image)
  if ($NoCache) { $buildArgs += "--no-cache" }
  $buildArgs += $repoRoot
  & docker @buildArgs
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$dockerArgs = @("run", "--rm", "--mount", "type=bind,src=$repoRoot,dst=/work,rw", "--mount", "type=bind,src=$sandboxHostRoot,dst=/sandboxes,rw", "-w", "/work")
if ($EnableNestedDocker) {
  $dockerArgs += @("--mount", "type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock")
  $dockerArgs += @("-e", "VILLANIBENCH_ENABLE_NESTED_DOCKER=1")
}
$dockerArgs += @("-e", "VILLANIBENCH_HOST_SANDBOX_ROOT=$sandboxHostRoot")
$dockerArgs += @("-e", "VILLANIBENCH_CONTAINER_SANDBOX_ROOT=/sandboxes")

$helpText = (& docker run --help | Out-String)
if ($helpText -match "host-gateway") { $dockerArgs += @("--add-host", "host.docker.internal:host-gateway") }
foreach ($name in @("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "API_KEY", "BASE_URL")) {
  $value = [Environment]::GetEnvironmentVariable($name)
  if ($value) { $dockerArgs += @("-e", "$name=$value") }
}
$dockerArgs += $Image
$dockerArgs += $BenchArgs
& docker @dockerArgs
exit $LASTEXITCODE
