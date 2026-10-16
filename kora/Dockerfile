FROM python:3.12-slim

LABEL project=kora

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/kora/.cache/huggingface

RUN useradd --create-home --uid 10001 kora \
    && mkdir /app && chown kora:kora /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

USER kora
# Bake the embedding model into the image so KORA and its tests run without network access.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
ENV HF_HUB_OFFLINE=1

COPY --chown=kora:kora . .

CMD ["python", "main.py"]
