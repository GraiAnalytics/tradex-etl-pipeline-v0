FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# System deps commonly needed for numpy/pandas/pyarrow/lxml/faiss/etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
    git curl \
    libffi-dev libssl-dev \
    zlib1g-dev \
    libxml2-dev libxslt1-dev \
    libopenblas-dev \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# Copy the project (for non-mounted runs). In dev, compose will mount your repo over /app.
COPY . /app

CMD ["bash"]