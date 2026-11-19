#Requires -Version 5.1
<#
.SYNOPSIS
    One-Click Automated Installer for Dynamic Kit & Sponsor Mod (PES 2021 / SP Football Life 2027)

.DESCRIPTION
    Automates prerequisite verification, SiderAddons synchronization, sider.ini registration,
    directory scaffolding, and optional world pre-generation.

.PARAMETER GamePath
    Path to SP Football Life 2027 / PES 2021 game directory containing SiderAddons.

.PARAMETER SkipPreGen
    Skip the bulk world kit pre-generation step.

.PARAMETER PreGen
    Force pre-generation of all 587 clubs (outfield + GK kits).

.PARAMETER RunTests
    Execute test suite (tests/test_ml_only_kits.py, etc.) to verify architecture.

.PARAMETER Uninstall
    Remove KitGenerator entries from sider.ini and unregister mod module.
#>
[CmdletBinding()]
param(
    [string]$GamePath = "",
    [switch]$SkipPreGen,
    [switch]$PreGen,
    [switch]$RunTests,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor White
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host " [*] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host " [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host " [!] $Message" -ForegroundColor Magenta
}

function Write-Fail {
    param([string]$Message)
    Write-Host " [ERROR] $Message" -ForegroundColor Red
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Header "DYNAMIC KIT & SPONSOR MOD - AUTOMATED INSTALLER"
Write-Host " Target Game: PES 2021 / SP Football Life 2026/2027" -ForegroundColor DarkGray
Write-Host " Mod Source : $ScriptDir" -ForegroundColor DarkGray

# 1. Locate Game and Sider Directory
Write-Step "Detecting Sider installation directory..."
$CandidatePaths = @(
    $GamePath,
    $ScriptDir,
    (Split-Path -Parent (Split-Path -Parent $ScriptDir)),
    "C:\Games\SP Football Life 2027",
    "C:\Games\SP Football Life 2026",
    "C:\Program Files (x86)\Steam\steamapps\common\eFootball PES 2021"
)

$ResolvedGameRoot = $null
foreach ($cand in $CandidatePaths) {
    if (-not [string]::IsNullOrWhiteSpace($cand) -and (Test-Path (Join-Path $cand "SiderAddons"))) {
        $ResolvedGameRoot = (Resolve-Path $cand).Path
        break
    }
}

if (-not $ResolvedGameRoot) {
    Write-Fail "Could not locate 'SiderAddons' directory. Please specify -GamePath 'C:\Path\To\Game'."
}

$SiderDir = Join-Path $ResolvedGameRoot "SiderAddons"
$SiderIni = Join-Path $SiderDir "sider.ini"
if (-not (Test-Path $SiderIni)) {
    # Check parent directory
    $SiderIniAlt = Join-Path $ResolvedGameRoot "sider.ini"
    if (Test-Path $SiderIniAlt) {
        $SiderIni = $SiderIniAlt
    } else {
        Write-Fail "Found SiderAddons at $SiderDir but sider.ini is missing!"
    }
}

Write-Success "Located Game Root : $ResolvedGameRoot"
Write-Success "Located Sider Config: $SiderIni"

# 2. Check Python Environment
Write-Step "Checking Python runtime and dependencies..."
$PythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Fail "Python 3 is not found in PATH! Please install Python 3.8+ from python.org (ensure 'Add to PATH' is checked)."
}

$PyVer = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
Write-Success "Python version: $PyVer"

# Verify Pillow & NumPy
$DepCheck = & python -c "
try:
    import PIL, numpy
    print('OK')
except ImportError as e:
    print('MISSING:' + str(e))
" 2>$null

if ($DepCheck -ne "OK") {
    Write-Warn "Required Python libraries (Pillow, numpy) missing. Installing from requirements.txt..."
    & python -m pip install --quiet -r (Join-Path $ScriptDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Failed to install Python dependencies via pip. Run: pip install Pillow numpy"
    }
    Write-Success "Installed Python dependencies successfully."
} else {
    Write-Success "Python dependencies (Pillow, NumPy) are ready."
}

# 3. Handle Uninstall Mode
if ($Uninstall) {
    Write-Header "UNINSTALLING DYNAMIC KIT & SPONSOR MOD"
    if (Test-Path $SiderIni) {
        $iniLines = Get-Content $SiderIni
        $newIni = $iniLines | Where-Object { 
            $_ -notmatch "KitGenerator\.lua" -and $_ -notmatch 'livecpk\\KitGenerator'
        }
        Set-Content -Path $SiderIni -Value $newIni -Encoding utf8
        Write-Success "Unregistered KitGenerator from $SiderIni"
    }
    Write-Success "Uninstallation complete. Authentic game state restored."
    exit 0
}

# 4. Scaffolding Target Directories
Write-Step "Scaffolding runtime directory hierarchy..."
$TargetContent = Join-Path $SiderDir "content\KitGenerator"
$TargetActive  = Join-Path $TargetContent "active"
$TargetLogos   = Join-Path $TargetContent "logos"
$TargetBadges  = Join-Path $TargetContent "badges"
$TargetModules = Join-Path $SiderDir "modules"
$TargetGen     = Join-Path $SiderDir "KitGenerator\generator"
$TargetLiveCPK = Join-Path $SiderDir "livecpk\KitGenerator"

foreach ($dir in @($TargetActive, $TargetLogos, $TargetBadges, $TargetModules, $TargetGen, $TargetLiveCPK)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Success "Runtime directories verified."

# 5. Synchronizing Mod Files
Write-Step "Synchronizing module and generator assets..."

# Module
Copy-Item (Join-Path $ScriptDir "modules\KitGenerator.lua") -Destination (Join-Path $TargetModules "KitGenerator.lua") -Force

# Generator Python scripts
Copy-Item (Join-Path $ScriptDir "generator\*") -Destination $TargetGen -Recurse -Force

# Content (Logos & Badges)
$SourceContent = Join-Path $ScriptDir "content\KitGenerator"
if (Test-Path (Join-Path $SourceContent "logos")) {
    Copy-Item (Join-Path $SourceContent "logos\*") -Destination $TargetLogos -Recurse -Force
}
if (Test-Path (Join-Path $SourceContent "badges")) {
    Copy-Item (Join-Path $SourceContent "badges\*") -Destination $TargetBadges -Recurse -Force
}
if (Test-Path (Join-Path $SourceContent "deals.txt")) {
    Copy-Item (Join-Path $SourceContent "deals.txt") -Destination (Join-Path $TargetContent "deals.txt") -Force
}
if (Test-Path (Join-Path $SourceContent "brands.txt")) {
    Copy-Item (Join-Path $SourceContent "brands.txt") -Destination (Join-Path $TargetContent "brands.txt") -Force
}

Write-Success "Files synchronized to SiderAddons."

# 6. Configure sider.ini
Write-Step "Configuring sider.ini hooks..."
$iniContent = Get-Content $SiderIni
$iniModified = $false

# A. Register lua.module = "KitGenerator.lua"
if ($iniContent -notmatch "KitGenerator\.lua") {
    $newLines = @()
    $inserted = $false
    foreach ($line in $iniContent) {
        # Preferred location: right before common\kits.lua or after modmenu.lua
        if (-not $inserted -and ($line -match "common\\kits\.lua" -or $line -match "lua\.module\s*=\s*`"modmenu\.lua`"")) {
            if ($line -match "modmenu\.lua") {
                $newLines += $line
                $newLines += 'lua.module = "KitGenerator.lua"'
                $inserted = $true
                continue
            } else {
                $newLines += 'lua.module = "KitGenerator.lua"'
                $newLines += $line
                $inserted = $true
                continue
            }
        }
        $newLines += $line
    }
    if (-not $inserted) {
        $newLines += 'lua.module = "KitGenerator.lua"'
    }
    $iniContent = $newLines
    $iniModified = $true
    Write-Success "Added 'lua.module = `"KitGenerator.lua`"' to sider.ini"
} else {
    Write-Success "Module 'KitGenerator.lua' already registered in sider.ini."
}

# B. Register cpk.root = ".\livecpk\KitGenerator"
if ($iniContent -notmatch 'livecpk\\KitGenerator') {
    $newLines = @()
    $inserted = $false
    foreach ($line in $iniContent) {
        if (-not $inserted -and $line -match "cpk\.root") {
            $newLines += 'cpk.root = ".\livecpk\KitGenerator"'
            $newLines += $line
            $inserted = $true
            continue
        }
        $newLines += $line
    }
    if (-not $inserted) {
        $newLines += 'cpk.root = ".\livecpk\KitGenerator"'
    }
    $iniContent = $newLines
    $iniModified = $true
    Write-Success "Added 'cpk.root = `".\livecpk\KitGenerator`"' to sider.ini"
} else {
    Write-Success "CPK root 'KitGenerator' already registered in sider.ini."
}

if ($iniModified) {
    Set-Content -Path $SiderIni -Value $iniContent -Encoding utf8
    Write-Success "Updated sider.ini successfully."
}

# 7. Optional World Pre-Generation
if ($PreGen -or (-not $SkipPreGen -and (Get-ChildItem -Path $TargetActive -Filter "*.ftex" | Measure-Object).Count -lt 50)) {
    Write-Header "PRE-GENERATING MASTER LEAGUE KITS"
    Write-Step "Generating authentic dynamic kits for all clubs in clubs.csv..."
    $GenScript = Join-Path $ScriptDir "generator\build_all_clubs.py"
    & python $GenScript --skip-existing --outdir $TargetActive
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Pre-generation finished successfully."
    } else {
        Write-Warn "Pre-generation encountered an issue (can be re-run at any time with generator/build_all_clubs.py)."
    }
} else {
    Write-Step "Active kit directory already populated with $((Get-ChildItem -Path $TargetActive -Filter '*.ftex' | Measure-Object).Count) textures."
}

# 8. Optional Test Suite
if ($RunTests) {
    Write-Header "RUNNING REGRESSION TEST SUITE"
    $TestScript = Join-Path $ScriptDir "tests\test_ml_only_kits.py"
    & python $TestScript
}

Write-Header "INSTALLATION COMPLETE - READY TO PLAY"
Write-Host " The Dynamic Kit & Sponsor Mod is now fully active in your game!" -ForegroundColor Green
Write-Host ""
Write-Host " Quick Start Guide:" -ForegroundColor White
Write-Host "  1. Launch Sider (sider.exe) and start SP Football Life 2027 / PES 2021." -ForegroundColor Gray
Write-Host "  2. Load or start your Master League career." -ForegroundColor Gray
Write-Host "  3. Press F1 (or F7) to open the Sider Mod Menu overlay." -ForegroundColor Gray
Write-Host "  4. Navigate to 'Kit Generator / Sponsor Office' to review offers and sign deals." -ForegroundColor Gray
Write-Host "  5. Enjoy dynamic multi-season sponsor changes, budget injection, and bespoke kits!" -ForegroundColor Gray
Write-Host ""
Write-Host " Scope Guarantee:" -ForegroundColor Cyan
Write-Host "  Exhibition, Friendlies, and Edit Mode remain 100% authentic licensed default kits." -ForegroundColor DarkCyan
Write-Host "================================================================================" -ForegroundColor Cyan
