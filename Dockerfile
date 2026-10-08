FROM tensorflow/tensorflow:2.18.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN grep -v '^tensorflow==' requirements.txt > /tmp/container-requirements.txt \
    && python -m pip install --no-cache-dir -r /tmp/container-requirements.txt \
    && python -c "import tensorflow as tf; assert tf.__version__ == '2.18.0'"

COPY federated/ ./federated/
COPY simulator/ ./simulator/
COPY edc-connectors/scripts/run_file_pipeline.py ./edc-connectors/scripts/
COPY edc-connectors/scripts/run_federated_round.py ./edc-connectors/scripts/

CMD ["python", "-m", "federated.server"]
