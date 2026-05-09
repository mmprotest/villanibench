FROM python:3.11-slim

ARG VILLANI_CODE_INSTALL_SPEC=""

RUN apt-get update     && apt-get install -y --no-install-recommends         bash         ca-certificates         curl         git         nodejs         npm     && rm -rf /var/lib/apt/lists/*

WORKDIR /work
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1
ENV PYTHONIOENCODING=utf-8

COPY pyproject.toml README.md ./
COPY villanibench ./villanibench
COPY suites ./suites
COPY docs ./docs
COPY tests ./tests

RUN pip install --no-cache-dir -e ".[dev]"

RUN if [ -n "$VILLANI_CODE_INSTALL_SPEC" ]; then       npm install -g "$VILLANI_CODE_INSTALL_SPEC" && villani-code --help >/dev/null;     fi

ENTRYPOINT ["villanibench"]
