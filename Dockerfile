FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MLFLOW_DISABLE_AGENT_HINT=1 \
    LANG=C.UTF-8

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY app.py run_pipeline.py pytest.ini ./
COPY config ./config
COPY data ./data
COPY docs ./docs
COPY scripts ./scripts
COPY src ./src
COPY tests ./tests

# Los datos institucionales no se copian: se montan al ejecutar el pipeline.
# El usuario sin privilegios coincide con el que usa docker-compose.yml.
RUN useradd --create-home --uid 1000 app && mkdir -p /srv/output && chown app /srv/output
USER app

ENV PIPELINE_OUTPUT_DIR=/srv/output \
    DASH_HOST=0.0.0.0

EXPOSE 8050

CMD ["python", "app.py"]
