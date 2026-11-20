param([switch]$Apply,[string]$Only)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectExe = (Resolve-Path (Join-Path $projectRoot 'work/emulator/duckstation/duckstation-qt-x64-ReleaseLTCG.exe')).Path
$projectCue = (Resolve-Path (Join-Path $projectRoot 'work/output/GetterRoboDaikessen_EN_v0.1.6.cue')).Path
$settingsPath = Join-Path (Split-Path -Parent $projectExe) 'settings.ini'
$previewNames = @('ANNO02','ANNO03','ANNO04','ANNO05','ANNO06','ANNO06A','ANNO06B','ANNO07A','ANNO07B','ANNO08','ANNO09','ANNO10','ANNO11','ANNO12','ANNO13','ANNO14','ANNO15','ANNO16','ANNO17','ANNO18','ANNO19','ANNO20','ANNO21')
if ($Only) {
    $requested = $Only -split ','
    if ($requested | Where-Object {$_ -notin $previewNames}) { throw 'Unknown preview name' }
    $previewNames = $requested
}
if (-not $Apply) {
    Write-Output ('Muted native preview test: '+($previewNames -join ', '))
    Write-Output 'Fresh project emulator per preview; capture at 1 second, plus 10 seconds for branch/final previews and 29 seconds for preview 19. Stop only the process this script starts.'
    exit 0
}
if ((Get-Content -Raw -LiteralPath $settingsPath) -notmatch 'OutputMuted\s*=\s*true') { throw 'Project emulator must be muted' }
if (Get-Process -Name 'duckstation-qt-x64-ReleaseLTCG' -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq $projectExe}) { throw 'Project test emulator is already running' }
$results = @()
foreach ($previewName in $previewNames) {
    $testProcess = Start-Process -FilePath $projectExe -ArgumentList @('-batch','-nofullscreen','--',('"'+$projectCue+'"')) -WorkingDirectory (Split-Path -Parent $projectExe) -WindowStyle Hidden -PassThru
    try {
        Start-Sleep -Seconds 2
        $captureTimes = @('1')
        if ($previewName -in @('ANNO06B','ANNO21')) { $captureTimes += '10' }
        if ($previewName -eq 'ANNO19') { $captureTimes += '29' }
        & py -3.11 (Join-Path $PSScriptRoot 'preview_capture.py') $previewName --apply --output-dir (Join-Path $projectRoot 'work/ui/episode_previews/v016-final') --seconds @captureTimes
        $passed = $LASTEXITCODE -eq 0
        $results += [pscustomobject]@{preview=$previewName;passed=$passed}
        Write-Output ('Native check '+$previewName+': '+$passed)
    } finally {
        if (-not $testProcess.HasExited) { Stop-Process -InputObject $testProcess; $testProcess.WaitForExit() }
    }
}
$summaryPath = Join-Path $projectRoot 'work/ui/episode_previews/v016-final/summary.json'
if ($Only -and (Test-Path -LiteralPath $summaryPath)) {
    $previous = Get-Content -Raw -LiteralPath $summaryPath | ConvertFrom-Json
    $results = @($previous | Where-Object {$_.preview -notin $previewNames}) + $results
}
$results | ConvertTo-Json | Set-Content -LiteralPath $summaryPath -Encoding utf8
if ($results | Where-Object {-not $_.passed}) { throw 'One or more native preview checks failed' }
