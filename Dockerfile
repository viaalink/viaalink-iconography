# Viaalink icons: the whole pipeline in one image (Blender headless, Bun, just, ffmpeg, the fonts).
#   docker build -t viaalink-icons .
#   docker run --rm -v "$PWD":/work viaalink-icons just icons-blender local/icons/rounds/25d-b7 --samples 48 relay
# GPU (optional, NVIDIA): add `--gpus all`; without it Blender renders on the CPU (slower, same result).
FROM ubuntu:24.04

ARG BLENDER_SERIES=5.3
ARG BLENDER_VERSION=5.3.0
ARG JETBRAINS_MONO=2.304
ENV DEBIAN_FRONTEND=noninteractive \
    BUN_INSTALL=/opt/bun \
    PATH=/opt/blender:/opt/bun/bin:$PATH \
    VIA_ICON_FONT=/usr/share/fonts/truetype/jetbrains/JetBrainsMono-Bold.ttf

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl xz-utils unzip zip git ffmpeg fonts-dejavu-core \
      libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libegl1 libxkbcommon0 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/*

# Blender (official Linux build)
RUN curl -fsSL "https://download.blender.org/release/Blender${BLENDER_SERIES}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
      | tar -xJ -C /opt && mv /opt/blender-${BLENDER_VERSION}-linux-x64 /opt/blender

# just (apt's is too old for this justfile)
RUN curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# Bun
RUN curl -fsSL https://bun.sh/install | bash

# JetBrains Mono Bold (OFL) for the "> via" prompts on screens
RUN mkdir -p /usr/share/fonts/truetype/jetbrains \
    && curl -fsSL -o /tmp/jbm.zip "https://github.com/JetBrains/JetBrainsMono/releases/download/v${JETBRAINS_MONO}/JetBrainsMono-${JETBRAINS_MONO}.zip" \
    && unzip -j /tmp/jbm.zip "fonts/ttf/JetBrainsMono-Bold.ttf" -d /usr/share/fonts/truetype/jetbrains \
    && rm /tmp/jbm.zip

WORKDIR /work
# The repo is mounted at /work at run time, which hides anything installed there while building, so the
# entrypoint installs the dependencies (sharp, linux-x64) into the mounted repo once, on first use.
RUN printf '#!/bin/sh\nset -e\n[ -d node_modules/sharp ] || bun install\nexec "$@"\n' > /usr/local/bin/via-icons-entry \
    && chmod +x /usr/local/bin/via-icons-entry
ENTRYPOINT ["via-icons-entry"]
CMD ["just", "--list"]
