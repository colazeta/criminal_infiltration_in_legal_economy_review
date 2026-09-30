param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{40}$')]
    [string]$ExpectedCommit,
    [string]$Checkout,
    [string]$CliDist = (Join-Path $env:APPDATA 'npm\node_modules\@kora-platform\cli\dist')
)
$ErrorActionPreference = 'Stop'
if (-not $Checkout) {
    $Checkout = Join-Path $env:USERPROFILE ('Documents\Codex\2026-09-19\riprendi-il-setup-kora-del-progetto\work\cile-kora-' + $ExpectedCommit.Substring(0,8))
}
$repository = 'https://github.com/colazeta/criminal_infiltration_in_legal_economy_review.git'
if (-not (Test-Path -LiteralPath $Checkout)) {
    git clone --no-checkout $repository $Checkout
    if ($LASTEXITCODE -ne 0) { throw 'Clone failed; no tests executed.' }
    git -C $Checkout checkout --detach $ExpectedCommit
    if ($LASTEXITCODE -ne 0) { throw 'Checkout failed; no tests executed.' }
}
$actualCommit = git -C $Checkout rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or "$actualCommit".Trim() -ne $ExpectedCommit) {
    throw 'Checkout is not the required commit. Nothing was reset or overwritten.'
}
$dirty = git -C $Checkout status --porcelain
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Checkout is not clean; no tests executed.' }
$workspace = Join-Path $Checkout 'integrations\kora\control-plane'
$inspector = Join-Path $Checkout 'integrations\kora\replay\inspect-native-selection.mjs'
if (-not (Test-Path -LiteralPath (Join-Path $workspace 'kora.yaml'))) { throw 'Kora manifest missing.' }
# Use the installed CLI's read-only packager; fail before auth if not all 154 tests are present.
node $inspector $workspace $CliDist
if ($LASTEXITCODE -ne 0) { throw 'Native bundle selection check failed; no tests executed.' }
Write-Host "Selected native suite: $workspace\tests (154 fixtures, no name filter; historical archive excluded)."
Push-Location $workspace
try {
    kora auth whoami --json
    if ($LASTEXITCODE -ne 0) { throw 'Authentication failed; no tests executed.' }
    # Minimal native compatibility probe on the SAME process bundle: both numeric
    # observations omitted. Expected BLOCKED/undetermined. No full suite on failure.
    $probeName = 'replay-A-starvation-missing-both'
    $probeRaw = @(& kora test suite --workspace $workspace --name $probeName --environment production --org oltre --json)
    $probeExit = $LASTEXITCODE
    $probeRaw | Write-Output
    if ($probeExit -ne 0) { throw "Schema compatibility probe failed (exit $probeExit); full suite NOT started." }
    $probe = ($probeRaw -join "`n") | ConvertFrom-Json
    $suite = $probe.data.suite
    if ($suite.status -ne 'passed' -or $suite.testCount -ne 1 -or $suite.gatePassed -ne $true -or $suite.gateable -ne 1 -or $suite.gatePassing -ne 1) {
        throw 'Compatibility probe did not report one executed, passed, gateable test; full suite NOT started.'
    }
    Write-Host 'Minimal native probe passed (1/1). Starting full 154-fixture suite.'
    kora test suite --workspace $workspace --environment production --org oltre --json
    $nativeExit = $LASTEXITCODE
    Write-Host "Native suite exit code: $nativeExit; source commit: $ExpectedCommit"
    if ($nativeExit -ne 0) { throw "Native suite failed (exit $nativeExit)." }
} finally {
    Pop-Location
}
