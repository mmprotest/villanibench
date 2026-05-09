FROM python:3.11-slim

ARG INSTALL_VILLANI_CODE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

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

# Optional: install Villani Code if a public package exists in your environment.
# If unavailable, leave INSTALL_VILLANI_CODE=false and extend this image yourself.
RUN if [ "$INSTALL_VILLANI_CODE" = "true" ]; then \
      echo "INSTALL_VILLANI_CODE=true requested. Install step must be customized for your environment." >&2; \
      exit 1; \
    fi

ENTRYPOINT ["villanibench"]
