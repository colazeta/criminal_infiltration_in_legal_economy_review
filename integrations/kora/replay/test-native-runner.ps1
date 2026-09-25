# Offline control-flow test: git, node and kora are mocked functions. No auth/network.
param([Parameter(Mandatory=$true)][string]$ScratchDirectory)
$ErrorActionPreference = 'Stop'
$scratch = [System.IO.Path]::GetFullPath($ScratchDirectory)
$manifest = Join-Path $scratch 'integrations\kora\control-plane\kora.yaml'
New-Item -ItemType Directory -Path (Split-Path $manifest -Parent) -Force | Out-Null
Set-Content -LiteralPath $manifest -Value '# offline mock only'
$expected = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
function git {
    $global:LASTEXITCODE = 0
    if ($args -contains 'rev-parse') { return 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' }
}
function node { $global:LASTEXITCODE = 0 }
function kora {
    $global:LASTEXITCODE = 0
    if ($args[0] -eq 'auth') { return '{}' }
    if ($args -contains '--name') {
        $global:KoraNativeRunnerTestState.probeCalls++
        $global:LASTEXITCODE = $global:KoraNativeRunnerTestState.probeExit
        return $global:KoraNativeRunnerTestState.json
    }
    $global:KoraNativeRunnerTestState.fullCalls++
    $global:LASTEXITCODE = $global:KoraNativeRunnerTestState.fullExit
    return '{}'
}
$valid = '{"data":{"suite":{"status":"passed","testCount":1,"gatePassed":true,"gateable":1,"gatePassing":1}}}'
$scenarios = @(
    @{name='setup-error'; probeExit=1; json='{"data":{"suite":{"testCount":0}}}'; fullExit=0; wantFull=0; wantThrow=$true},
    @{name='zero-tests-with-exit-zero'; probeExit=0; json='{"data":{"suite":{"status":"passed","testCount":0,"gatePassed":true,"gateable":0,"gatePassing":0}}}'; fullExit=0; wantFull=0; wantThrow=$true},
    @{name='gate-failed-with-exit-zero'; probeExit=0; json='{"data":{"suite":{"status":"passed","testCount":1,"gatePassed":false,"gateable":1,"gatePassing":0}}}'; fullExit=0; wantFull=0; wantThrow=$true},
    @{name='invalid-json'; probeExit=0; json='not-json'; fullExit=0; wantFull=0; wantThrow=$true},
    @{name='one-real-pass'; probeExit=0; json=$valid; fullExit=0; wantFull=1; wantThrow=$false},
    @{name='full-suite-failure-propagates'; probeExit=0; json=$valid; fullExit=1; wantFull=1; wantThrow=$true}
)
$results = @()
foreach ($case in $scenarios) {
    $global:KoraNativeRunnerTestState = @{probeExit=$case.probeExit; json=$case.json; fullExit=$case.fullExit; probeCalls=0; fullCalls=0}
    $thrown=$false
    try { & (Join-Path $PSScriptRoot 'run-native.ps1') -ExpectedCommit $expected -Checkout $scratch *> $null }
    catch { $thrown=$true }
    if ($global:KoraNativeRunnerTestState.probeCalls -ne 1 -or $global:KoraNativeRunnerTestState.fullCalls -ne $case.wantFull -or $thrown -ne $case.wantThrow) {
        throw "Native runner control-flow regression: $($case.name)"
    }
    $results += @{name=$case.name; passed=$true; fullSuiteCalls=$global:KoraNativeRunnerTestState.fullCalls; threw=$thrown}
}
@{scope='Offline mocked control flow only, no Kora execution'; passed=$results.Count; total=$scenarios.Count; results=$results} | ConvertTo-Json -Depth 5
