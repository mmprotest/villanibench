## supports --enable-nested-docker
[CmdletBinding(PositionalBinding = $false)]
param(
  [switch]$Rebuild,[switch]$NoCache,[switch]$EnableNestedDocker,
  [switch]$IncludeLocalVillaniCode,[string]$VillaniCodeSource,[string]$VillaniCodeInstallSpec,
  [string]$Image = "villanibench:local",[Parameter(ValueFromRemainingArguments = $true)][string[]]$BenchArgs)
if (-not $BenchArgs -or $BenchArgs.Count -eq 0) { throw "Usage: ./scripts/villanibench-docker.ps1 [opts] <villanibench args...>" }
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path; $repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
if ($Rebuild -and ($BenchArgs -join ' ') -match '--runner\s+villani' -and -not $IncludeLocalVillaniCode -and -not $VillaniCodeSource -and -not $VillaniCodeInstallSpec) {
  if (Get-Command villani-code -ErrorAction SilentlyContinue) { $IncludeLocalVillaniCode = $true } else { throw "Could not package local villani-code install for Docker. Pass -VillaniCodeSource <path> or -VillaniCodeInstallSpec <pip-or-npm-spec>." }
}
$imageExists = $true; try { docker image inspect $Image | Out-Null } catch { $imageExists = $false }
if ($Rebuild -or -not $imageExists) {
  $buildArgs = @("build","-t",$Image); if ($NoCache) { $buildArgs += "--no-cache" }
  if ($IncludeLocalVillaniCode -and -not $VillaniCodeSource -and -not $VillaniCodeInstallSpec) { $VillaniCodeInstallSpec = "villani-code" }
  if ($VillaniCodeSource) { $buildArgs += @("--build-arg","VILLANI_CODE_SOURCE=$VillaniCodeSource") }
  if ($VillaniCodeInstallSpec) { $buildArgs += @("--build-arg","VILLANI_CODE_INSTALL_SPEC=$VillaniCodeInstallSpec") }
  $buildArgs += $repoRoot; & docker @buildArgs; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$sandboxHostRoot = Join-Path $repoRoot ".villanibench_sandboxes"; New-Item -ItemType Directory -Force -Path $sandboxHostRoot | Out-Null
$dockerArgs = @("run","--rm","--mount","type=bind,src=$repoRoot,dst=/work,rw","--mount","type=bind,src=$sandboxHostRoot,dst=/sandboxes,rw","-w","/work","-e","VILLANIBENCH_HOST_SANDBOX_ROOT=$sandboxHostRoot","-e","VILLANIBENCH_CONTAINER_SANDBOX_ROOT=/sandboxes")
if ($EnableNestedDocker) { $dockerArgs += @("--mount","type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock","-e","VILLANIBENCH_ENABLE_NESTED_DOCKER=1") }
$helpText = (& docker run --help | Out-String); if ($helpText -match "host-gateway") { $dockerArgs += @("--add-host","host.docker.internal:host-gateway") }
$dockerArgs += $Image; $dockerArgs += $BenchArgs; & docker @dockerArgs; exit $LASTEXITCODE
