#!/usr/bin/env bash
# Install what the Viaalink icon pipeline needs on Ubuntu/Debian (24.04+), without Docker.
# Blender comes from blender.org into ~/.local/opt/blender (no root needed for that part).
set -euo pipefail
BLENDER_SERIES=${BLENDER_SERIES:-5.3}
BLENDER_VERSION=${BLENDER_VERSION:-5.3.0}
JETBRAINS_MONO=${JETBRAINS_MONO:-2.304}

sudo apt-get update
sudo apt-get install -y curl xz-utils unzip zip git ffmpeg fonts-dejavu-core libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libegl1 libxkbcommon0

if ! command -v blender >/dev/null; then
  mkdir -p ~/.local/opt ~/.local/bin
  curl -fsSL "https://download.blender.org/release/Blender${BLENDER_SERIES}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" | tar -xJ -C ~/.local/opt
  ln -sf ~/.local/opt/blender-${BLENDER_VERSION}-linux-x64/blender ~/.local/bin/blender
fi
command -v just >/dev/null && just --version | grep -qE "^just 1\.(2[5-9]|[3-9][0-9])" || curl --proto "=https" --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin
command -v bun >/dev/null || curl -fsSL https://bun.sh/install | bash

FONT=~/.local/share/fonts/JetBrainsMono-Bold.ttf
if [ ! -f "$FONT" ]; then
  mkdir -p ~/.local/share/fonts
  curl -fsSL -o /tmp/jbm.zip "https://github.com/JetBrains/JetBrainsMono/releases/download/v${JETBRAINS_MONO}/JetBrainsMono-${JETBRAINS_MONO}.zip"
  unzip -oj /tmp/jbm.zip "fonts/ttf/JetBrainsMono-Bold.ttf" -d ~/.local/share/fonts && rm /tmp/jbm.zip
fi
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"
bun install
echo "Ready. Try: just icons-blender local/icons/rounds/25d-b7 --samples 16 relay && just icons-blender-gate"
