# syntax=docker/dockerfile:1
FROM python:3.10-slim

WORKDIR /app

# Enable persistent pip cache mount
# This allows pip to 'remember' downloaded chunks even if the build fails
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.6.0+cu118 --extra-index-url https://download.pytorch.org/whl/cu118

COPY requirements.txt ./

# Build the rest of the requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .

# Use the specific port for the service (8001 or 8002)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]