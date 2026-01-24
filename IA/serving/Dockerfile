FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# uv installs to ~/.local/bin by default; include both common install locations
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY serving/ ./serving
COPY agent/ ./agent
COPY dgsi_scraper/ ./dgsi_scraper
COPY tfidf_svm/ ./tfidf_svm
COPY models/ ./models

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]