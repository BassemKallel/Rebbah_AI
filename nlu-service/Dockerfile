# syntax=docker/dockerfile:1
FROM python:3.10-slim

WORKDIR /app

# 1. Copy only requirements first to keep the cache clean
COPY requirements.txt ./

# 2. Use a cache mount to persist downloads between failed builds.
# This acts like a "resume" button for your pip downloads.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 3. Copy the rest of your Tiktak-AI code
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]