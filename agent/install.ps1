# APEX Portable Installer for Windows (PowerShell)
# Deploys APEX globally into $HOME\.gemini\config\skills\apex-optimizer

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetGlobal = Join-Path $HOME ".gemini\config\skills\apex-optimizer"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "⚡ Deploying APEX Performance Optimizer" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $TargetGlobal | Out-Null
Copy-Item (Join-Path $ScriptDir "SOUL.md") -Destination $TargetGlobal -Force
Copy-Item (Join-Path $ScriptDir "IDENTITY.md") -Destination $TargetGlobal -Force
Copy-Item (Join-Path $ScriptDir "USER.md") -Destination $TargetGlobal -Force
Copy-Item (Join-Path $ScriptDir "ENGINEERING_STANDARDS.md") -Destination $TargetGlobal -Force

$SkillHeader = @"
---
name: apex-optimizer
description: >-
  Autonomous Performance Engineering & Systems Architecture Specialist (APEX).
  Optimizes codebases, CLI tools, native hooks, game engine scripts, backend APIs,
  and Flutter UIs for extreme performance and sub-millisecond execution while strictly
  maintaining production-grade readability, developer productivity, and zero regressions.
  Activate when optimizing code, accelerating tools/builds, profiling bottlenecks,
  eliminating frame drops, reducing memory footprint, or conducting benchmark-driven refactoring.
---

"@

$PromptContent = Get-Content (Join-Path $ScriptDir "APEX_SYSTEM_PROMPT.md") -Raw
Set-Content -Path (Join-Path $TargetGlobal "SKILL.md") -Value ($SkillHeader + "`n" + $PromptContent)

Write-Host "✅ Installed globally to $TargetGlobal" -ForegroundColor Green
Write-Host "   APEX is now active in your Antigravity environment!" -ForegroundColor Green
Write-Host "   Portable prompt available at: $ScriptDir\APEX_SYSTEM_PROMPT.md" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
