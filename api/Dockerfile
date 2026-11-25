# API de inferencia BeanCass AI (TensorFlow CPU)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    MODELS_DIR=/app/models

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
# Los modelos se montan como volumen de solo lectura (ver docker-compose.yml);
# se copian también para que la imagen funcione de forma autónoma.
COPY models ./models

RUN useradd --create-home --uid 10001 beancass
USER beancass

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-keep-alive", "5"]
