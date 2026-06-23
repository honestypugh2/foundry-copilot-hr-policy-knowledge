FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY src/hosted_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY src/hosted_agent/ ./

# Foundry Hosted Agents serve on port 8088
EXPOSE 8088

CMD ["python", "server.py"]
