FROM python:3.11-slim

WORKDIR /app

# Install Node.js (required for Claude Code CLI)
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# The app will automatically setup Claude credentials from env vars on startup
CMD uvicorn main:app --host 0.0.0.0 --port $PORT