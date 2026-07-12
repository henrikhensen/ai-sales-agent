FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY alembic.ini .

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# PORT defaults to 8000 for local/docker-compose use; Railway (and most
# PaaS hosts) inject their own PORT at runtime, which this default is
# overridden by — the CMD/HEALTHCHECK below must read it via shell
# expansion (not Docker exec-form) for that override to take effect.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request,sys; p=os.environ.get('PORT','8000'); sys.exit(0 if urllib.request.urlopen(f'http://localhost:{p}/', timeout=3).status == 200 else 1)"

CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
