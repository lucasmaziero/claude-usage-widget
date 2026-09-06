<#
.SYNOPSIS
    Builds the icon, the frozen app and the Windows installer.

.DESCRIPTION
    One command from a clean checkout:

        uv sync
        .\installer\build.ps1

    Produces build\AgentGauge-<version>.exe. Pass -SkipInstaller to stop
    after the frozen app (build\dist\AgentGauge), which is the portable form.

    build\ ends up holding exactly one setup: the one just built. Old versions
    are removed, because the real cost of keeping them is grabbing the wrong
    .exe out of the folder when it is time to ship.

.PARAMETER SkipInstaller
    Skip the Inno Setup step, e.g. on a machine without ISCC.exe.

.PARAMETER Clean
    Wipe build\ first, including PyInstaller's caches. Slower, and what you want
    before cutting a release or after changing the spec.
#>
[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root

# Windows PowerShell 5.1 turns anything a native program writes to stderr into
# a terminating error while ErrorActionPreference is 'Stop', however well the
# program went. uv announces "Building agent-gauge" on stderr whenever
# the version changed since the last run, so this script aborted on the icon
# step of every release build and on none of the rebuilds in between.
#
# Exit codes are the truth for a native command, and every call below already
# checks one, so they run with the preference relaxed and the check kept.
function Invoke-Native {
    param([Parameter(Mandatory)][scriptblock]$Command, [Parameter(Mandatory)][string]$What)

    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Command } finally { $ErrorActionPreference = $previous }
    if ($LASTEXITCODE -ne 0) { throw $What }
}

try {
    # The version lives in pyproject.toml; nothing else may declare it.
    $version = (Select-String -Path 'pyproject.toml' -Pattern '^version\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
    Write-Host "Agent Gauge $version" -ForegroundColor Cyan

    if ($Clean -and (Test-Path 'build')) {
        Write-Host '==> clean' -ForegroundColor Cyan
        Remove-Item 'build' -Recurse -Force
    }

    Write-Host '==> icon' -ForegroundColor Cyan
    Invoke-Native { uv run python tools/gen_icon.py installer/agent-gauge.ico } 'icon generation failed'

    Write-Host '==> frozen app' -ForegroundColor Cyan
    Invoke-Native {
        uv run --extra build pyinstaller installer/agent-gauge.spec `
            --noconfirm --distpath build/dist --workpath build/work --log-level WARN
    } 'pyinstaller failed'

    $exe = Join-Path $root 'build\dist\AgentGauge\AgentGauge.exe'
    if (-not (Test-Path $exe)) { throw "expected $exe" }
    $mb = [math]::Round((Get-ChildItem 'build\dist\AgentGauge' -Recurse |
        Measure-Object Length -Sum).Sum / 1MB, 1)
    Write-Host "    build\dist\AgentGauge ($mb MB)" -ForegroundColor DarkGray

    if ($SkipInstaller) {
        Write-Host 'skipping installer (-SkipInstaller)' -ForegroundColor Yellow
        return
    }

    # winget installs Inno Setup per-user; a machine-wide install lands in
    # Program Files. Check both before giving up.
    $iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $iscc) {
        throw 'ISCC.exe not found. Install it with: winget install JRSoftware.InnoSetup'
    }

    Write-Host '==> installer' -ForegroundColor Cyan
    # One setup in the folder, always the current one. Stale versions from
    # earlier runs are the easiest thing in the world to ship by accident.
    Get-ChildItem 'build' -Filter 'AgentGauge-*.exe' -File -ErrorAction SilentlyContinue |
        Remove-Item -Force

    # ISCC writes the setup and then reopens it to patch in the icons. Real-time
    # antivirus scanning that fresh file makes the second step fail with
    # "EndUpdateResource failed (110)". It is transient, so retry once.
    # The retry above only helps if PowerShell lets us reach it. ISCC writes its
    # error to stderr, which under ErrorActionPreference 'Stop' is a terminating
    # error in Windows PowerShell 5.1 - so the first failure aborted the script
    # and the retry never ran. Same trap the uv calls hit, one call missed.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        foreach ($attempt in 1..2) {
            & $iscc "/DMyAppVersion=$version" 'installer\agent-gauge.iss' |
                Select-Object -Last 4
            if ($LASTEXITCODE -eq 0) { break }
            if ($attempt -eq 2) { throw 'iscc failed' }
            Write-Host '    compile failed, retrying in 3s' -ForegroundColor Yellow
            Start-Sleep -Seconds 3
        }
    }
    finally { $ErrorActionPreference = $previousPreference }

    $setup = Get-Item "build\AgentGauge-$version.exe"
    Write-Host ("    {0} ({1} MB)" -f $setup.Name, [math]::Round($setup.Length / 1MB, 1)) `
        -ForegroundColor Green
}
finally {
    Pop-Location
}
