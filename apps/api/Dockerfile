FROM python:3.11-slim

# git is required to clone repositories for indexing
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Required at startup: init_db() runs `alembic upgrade head`, which needs the
# config and the versions directory. Without these the container crashes on boot.
COPY alembic.ini .
COPY migrations ./migrations

# Hosting platforms (Render, Fly, Cloud Run) inject $PORT and route to it.
# Fall back to 8000 for plain `docker run` locally.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
