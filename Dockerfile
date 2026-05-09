FROM python:3.11-slim

ARG VILLANI_CODE_INSTALL_MODE=github
ARG VILLANI_CODE_INSTALL_SPEC=git+https://github.com/mmprotest/villani-code.git
ARG VILLANI_CODE_SOURCE_IN_CONTEXT=""

RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /work
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8
COPY pyproject.toml README.md ./
COPY villanibench ./villanibench
COPY suites ./suites
COPY docs ./docs
COPY tests ./tests
COPY .docker_build/villani-code-src /tmp/villani-code-src
RUN pip install --no-cache-dir -e ".[dev]"
RUN set -eux; \
    if [ "$VILLANI_CODE_INSTALL_MODE" = "github" ]; then \
      pip install --no-cache-dir "git+https://github.com/mmprotest/villani-code.git"; \
    elif [ "$VILLANI_CODE_INSTALL_MODE" = "spec" ]; then \
      [ -n "$VILLANI_CODE_INSTALL_SPEC" ] || (echo "VILLANI_CODE_INSTALL_SPEC is required for spec mode" >&2; exit 2); \
      pip install --no-cache-dir "$VILLANI_CODE_INSTALL_SPEC"; \
    elif [ "$VILLANI_CODE_INSTALL_MODE" = "local" ]; then \
      SRC="${VILLANI_CODE_SOURCE_IN_CONTEXT:-/tmp/villani-code-src}"; \
      [ -d "$SRC" ] || (echo "Local Villani source directory not found in build context: $SRC" >&2; exit 2); \
      if [ -f "$SRC/package.json" ]; then \
        cd "$SRC"; npm install; \
        npm run | grep -q " build" && npm run build || true; \
        npm install -g .; \
      elif [ -f "$SRC/pyproject.toml" ] || [ -f "$SRC/setup.py" ]; then \
        pip install --no-cache-dir "$SRC"; \
      else \
        echo "Local Villani source must contain package.json, pyproject.toml, or setup.py" >&2; exit 2; \
      fi; \
    elif [ "$VILLANI_CODE_INSTALL_MODE" = "none" ]; then \
      echo "Skipping Villani Code install"; \
    else \
      echo "Unknown VILLANI_CODE_INSTALL_MODE=$VILLANI_CODE_INSTALL_MODE" >&2; exit 2; \
    fi; \
    if [ "$VILLANI_CODE_INSTALL_MODE" != "none" ]; then villani-code --help >/dev/null; fi
ENTRYPOINT ["villanibench"]
