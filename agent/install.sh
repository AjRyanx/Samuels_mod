#!/usr/bin/env bash
# APEX Portable Installer for macOS and Linux
# Deploys APEX globally into ~/.gemini/config/skills/ or local project .agent/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_GLOBAL="$HOME/.gemini/config/skills/apex-optimizer"

echo "=========================================="
echo "⚡ Deploying APEX Performance Optimizer"
echo "=========================================="

# 1. Global Antigravity / Gemini Skill Deployment
mkdir -p "$TARGET_GLOBAL"
cp "$SCRIPT_DIR/SOUL.md" "$TARGET_GLOBAL/"
cp "$SCRIPT_DIR/IDENTITY.md" "$TARGET_GLOBAL/"
cp "$SCRIPT_DIR/USER.md" "$TARGET_GLOBAL/"
cp "$SCRIPT_DIR/ENGINEERING_STANDARDS.md" "$TARGET_GLOBAL/"

cat << 'EOF' > "$TARGET_GLOBAL/SKILL.md"
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

EOF
cat "$SCRIPT_DIR/APEX_SYSTEM_PROMPT.md" >> "$TARGET_GLOBAL/SKILL.md"

echo "✅ Installed globally to $TARGET_GLOBAL"
echo "   APEX is now active in your Antigravity environment!"
echo "   Portable prompt available at: $SCRIPT_DIR/APEX_SYSTEM_PROMPT.md"
echo "=========================================="
