# syntax=docker/dockerfile:1

############################################
# Builder stage: create a venv with all deps
############################################
FROM python:3.10-slim AS builder

ARG REPO_URL=https://github.com/somatechlat/somafractalmemory.git
ARG BRANCH=master
ENV VENV_PATH=/opt/venv

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Clone source and create venv
RUN git clone --depth 1 --branch ${BRANCH} ${REPO_URL} /src
WORKDIR /src
RUN python -m venv ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:$PATH"

# Upgrade pip and install requirements into venv
COPY requirements.yaml /src/requirements.yaml
COPY api-requirements.yaml /src/api-requirements.yaml
# Convert the simple YAMLs to pip requirements.txt files in a robust way and install
RUN python - <<'PY'
import re,sys
def extract(path,out):
    out_lines=[]
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            m=re.match(r'^\s*-\s*(.+)$',line)
            if m:
                out_lines.append(m.group(1).strip())
    open(out,'w',encoding='utf-8').write('\n'.join(out_lines)+'\n')
extract('/src/requirements.yaml','/src/requirements.txt')
extract('/src/api-requirements.yaml','/src/api-requirements.txt')
print('Wrote requirements')
PY
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /src/requirements.txt -r /src/api-requirements.txt && \
    rm -rf /root/.cache/pip

# Remove any bundled local Qdrant DB folder that may have been present in the
# repository to avoid shipping a locked local DB and to force use of remote
# Qdrant server when SOMA_QDRANT__URL is provided.
RUN rm -rf /src/qdrant.db || true

############################################
# Final stage: smaller runtime image
############################################
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /src /app

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app /opt/venv
USER appuser

EXPOSE 9595

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9595/health || exit 1

# Default runtime mode ON_DEMAND for connecting to host Redis and Qdrant
ENV SOMA_MODE=ON_DEMAND
CMD ["sh", "-c", "uvicorn examples.api:app --host 0.0.0.0 --port 9595 --workers 2 --timeout-keep-alive 30"]
