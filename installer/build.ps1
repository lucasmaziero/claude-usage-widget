<#
.SYNOPSIS
    Builds the icon, the frozen app and the Windows installer.

.DESCRIPTION
    One command from a clean checkout:

        uv sync
        .\installer\build.ps1

    Produces build\ClaudeUsage-Setup-<version>.exe. Pass -SkipInstaller to stop
    after the frozen app (build\dist\ClaudeUsage), which is the portable form.

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

try {
    # The version lives in pyproject.toml; nothing else may declare it.
    $version = (Select-String -Path 'pyproject.toml' -Pattern '^version\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
    Write-Host "Claude Usage Widget $version" -ForegroundColor Cyan

    if ($Clean -and (Test-Path 'build')) {
        Write-Host '==> clean' -ForegroundColor Cyan
        Remove-Item 'build' -Recurse -Force
    }

    Write-Host '==> icon' -ForegroundColor Cyan
    uv run python tools/gen_icon.py installer/claude-usage.ico
    if ($LASTEXITCODE -ne 0) { throw 'icon generation failed' }

    Write-Host '==> frozen app' -ForegroundColor Cyan
    uv run --extra build pyinstaller installer/claude-usage.spec `
        --noconfirm --distpath build/dist --workpath build/work --log-level WARN
    if ($LASTEXITCODE -ne 0) { throw 'pyinstaller failed' }

    $exe = Join-Path $root 'build\dist\ClaudeUsage\ClaudeUsage.exe'
    if (-not (Test-Path $exe)) { throw "expected $exe" }
    $mb = [math]::Round((Get-ChildItem 'build\dist\ClaudeUsage' -Recurse |
        Measure-Object Length -Sum).Sum / 1MB, 1)
    Write-Host "    build\dist\ClaudeUsage ($mb MB)" -ForegroundColor DarkGray

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
    Get-ChildItem 'build' -Filter 'ClaudeUsage-Setup-*.exe' -File -ErrorAction SilentlyContinue |
        Remove-Item -Force

    # ISCC writes the setup and then reopens it to patch in the icons. Real-time
    # antivirus scanning that fresh file makes the second step fail with
    # "EndUpdateResource failed (110)". It is transient, so retry once.
    foreach ($attempt in 1..2) {
        & $iscc "/DMyAppVersion=$version" 'installer\claude-usage.iss' | Select-Object -Last 4
        if ($LASTEXITCODE -eq 0) { break }
        if ($attempt -eq 2) { throw 'iscc failed' }
        Write-Host '    compile failed, retrying in 3s' -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }

    $setup = Get-Item "build\ClaudeUsage-Setup-$version.exe"
    Write-Host ("    {0} ({1} MB)" -f $setup.Name, [math]::Round($setup.Length / 1MB, 1)) `
        -ForegroundColor Green
}
finally {
    Pop-Location
}
