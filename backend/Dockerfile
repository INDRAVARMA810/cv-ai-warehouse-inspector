# syntax=docker/dockerfile:1.7

# =====================================================================
# AI Warehouse Safety Inspector — backend
#
# Builds the FastAPI service together with the detection pipeline it
# drives. The same image runs on CPU or GPU: the application already
# selects its device via torch.cuda.is_available(), so a container
# started without the NVIDIA runtime simply falls back to CPU.
#
# GPU builds need CUDA-enabled Torch wheels, which are selected at build
# time rather than baked in:
#
# Built from the REPOSITORY ROOT, not from backend/, because
# requirements.txt lives at the root. The root .dockerignore keeps the
# context small.
#
#   CPU (default):
#     docker build -f backend/Dockerfile -t warehouse-backend .
#
#   GPU (CUDA 12.1 wheels, ~2.5 GB larger):
#     docker build -f backend/Dockerfile \
#                  --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121 \
#                  -t warehouse-backend:gpu .
# =====================================================================

# ---------------------------------------------------------------------
# Stage 1 — builder: compile wheels into an isolated virtualenv
# ---------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build-only toolchain. Kept out of the runtime stage entirely.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

COPY requirements.txt ./requirements.raw

# The checked-in requirements file was produced by `pip freeze` under
# PowerShell, which writes UTF-16LE with a BOM. pip on Linux cannot read
# that, so it is normalised to UTF-8 here rather than requiring the
# repository file to change.
RUN python - <<'PY'
from pathlib import Path

raw = Path("requirements.raw").read_bytes()
encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
text = raw.decode(encoding)

# Torch is resolved from the index chosen by TORCH_INDEX_URL, and the
# Windows-only helper has no meaning on Linux.
keep = [
    line.strip()
    for line in text.splitlines()
    if line.strip() and not line.strip().lower().startswith("win32_setctime")
]

Path("requirements.txt").write_text("\n".join(keep) + "\n", encoding="utf-8")
print(f"Normalised {len(keep)} requirement(s) from {encoding}.")
PY

RUN pip install --upgrade pip setuptools wheel

# Torch first, from the index matching the target accelerator, so the
# ultralytics dependency resolution below reuses it instead of pulling
# the default CUDA build.
RUN pip install --index-url "${TORCH_INDEX_URL}" torch torchvision

# `lap` is required by Ultralytics' ByteTrack for linear assignment but
# is absent from requirements.txt: on a developer machine Ultralytics
# auto-installs it at first use, which happened after the `pip freeze`
# that produced the file. That fallback cannot work here — the image
# runs unprivileged and /opt/venv is not writable — so it is installed
# explicitly and auto-install is disabled in the runtime stage.
RUN pip install -r requirements.txt "lap>=0.5.12"

# ---------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Ultralytics writes settings and downloads weights here; pointing it
    # at a writable, mountable location stops it re-downloading on every
    # container start.
    YOLO_CONFIG_DIR=/app/.cache/ultralytics \
    MPLCONFIGDIR=/app/.cache/matplotlib

# Every dependency is baked in at build time. With auto-install left on,
# Ultralytics attempts a `pip install` on first inference — which cannot
# succeed for an unprivileged user against a root-owned virtualenv, and
# burns ~30s on retries before failing anyway.
ENV YOLO_AUTOINSTALL=false

# Runtime shared libraries. The project pins `opencv-python` (not the
# headless variant), which links against libGL and glib even when no
# window is ever opened — so they must be present.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY backend/ /app/

COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Run unprivileged. The cache and log directories are created and handed
# over before dropping privileges, since the application writes to both.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.cache/ultralytics /app/.cache/matplotlib /app/logs /app/models \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Uses the API's own health endpoint, which reports 503 when the
# database is unreachable — so an unhealthy container genuinely means
# the service cannot serve requests. urllib avoids installing curl.
HEALTHCHECK --interval=20s --timeout=5s --start-period=90s --retries=5 \
    CMD python -c "import sys,urllib.request;\
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)" \
    || exit 1

# tini reaps the threads the detection pipeline spawns and forwards
# signals, so `docker stop` shuts the stream down cleanly.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
