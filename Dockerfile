FROM python:3.11-slim

ARG VILLANI_CODE_INSTALL_SPEC=""
ARG VILLANI_CODE_SOURCE=""

RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git && rm -rf /var/lib/apt/lists/*
WORKDIR /work
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8
COPY pyproject.toml README.md ./
COPY villanibench ./villanibench
COPY suites ./suites
COPY docs ./docs
COPY tests ./tests
RUN pip install --no-cache-dir -e ".[dev]"
RUN if [ -n "$VILLANI_CODE_SOURCE" ]; then pip install --no-cache-dir "$VILLANI_CODE_SOURCE"; fi
RUN if [ -n "$VILLANI_CODE_INSTALL_SPEC" ]; then pip install --no-cache-dir "$VILLANI_CODE_INSTALL_SPEC"; fi
RUN if [ -n "$VILLANI_CODE_SOURCE" ] || [ -n "$VILLANI_CODE_INSTALL_SPEC" ]; then villani-code --help >/dev/null; fi
ENTRYPOINT ["villanibench"]
