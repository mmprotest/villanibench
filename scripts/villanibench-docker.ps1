param(
  [string]$Image = "villanibench:local",
  [switch]$Rebuild,
  [switch]$NoCache,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$BenchArgs
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")

if (-not $BenchArgs -or $BenchArgs.Count -eq 0) {
  throw "Usage: ./scripts/villanibench-docker.ps1 [--rebuild] [--no-cache] [--image villanibench:local] <villanibench args...>"
}

$imageExists = $true
try { docker image inspect $Image | Out-Null } catch { $imageExists = $false }
if ($Rebuild -or -not $imageExists) {
  $buildArgs = @("build", "-t", $Image)
  if ($NoCache) { $buildArgs += "--no-cache" }
  $buildArgs += "$repoRoot"
  & docker @buildArgs
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$dockerArgs = @("run", "--rm", "-v", "${repoRoot}:/work", "-w", "/work")
$helpText = (& docker run --help | Out-String)
if ($helpText -match "host-gateway") {
  $dockerArgs += @("--add-host", "host.docker.internal:host-gateway")
}
foreach ($name in @("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "API_KEY", "BASE_URL")) {
  $value = [Environment]::GetEnvironmentVariable($name)
  if ($value) { $dockerArgs += @("-e", "$name=$value") }
}

$dockerArgs += $Image
$dockerArgs += $BenchArgs
& docker @dockerArgs
exit $LASTEXITCODE
