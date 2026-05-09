[CmdletBinding(PositionalBinding = $false)]
param()

$Image = "villanibench:local"
$Rebuild = $false
$NoCache = $false
$BenchArgs = @()

for ($i = 0; $i -lt $args.Count; $i++) {
  $arg = $args[$i]
  switch ($arg) {
    "-Rebuild" { $Rebuild = $true; continue }
    "--rebuild" { $Rebuild = $true; continue }
    "-NoCache" { $NoCache = $true; continue }
    "--no-cache" { $NoCache = $true; continue }
    "-Image" {
      if ($i + 1 -ge $args.Count) { throw "Missing value for -Image" }
      $i++
      $Image = $args[$i]
      continue
    }
    "--image" {
      if ($i + 1 -ge $args.Count) { throw "Missing value for --image" }
      $i++
      $Image = $args[$i]
      continue
    }
    "--" {
      if ($i + 1 -lt $args.Count) {
        $BenchArgs = @($args[($i + 1)..($args.Count - 1)])
      }
      break
    }
    default {
      $BenchArgs = @($args[$i..($args.Count - 1)])
      break
    }
  }
}

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
