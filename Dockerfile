# APEX Quantitative Trading System - 24/7 Cloud Engine Dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Astral uv for ultra-fast, reproducible dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project specification and dependencies
COPY pyproject.toml* requirements.txt* ./

# Install python dependencies
RUN uv pip install --system \
    nautilus_trader==1.231.0 \
    ccxt==4.5.85 \
    pandas==3.0.6 \
    scikit-learn==1.9.1 \
    duckdb==1.5.6 \
    pyarrow==26.0.0 \
    pytest==9.1.1

# Copy code & historical data
COPY apex/ ./apex/
COPY docs/ ./docs/
COPY data_real/ ./data_real/

# Default environment configurations
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080
ENV POLL_INTERVAL=5.0
ENV BINANCE_TESTNET=true

EXPOSE 8080

# Run 24/7 autonomous paper/testnet runner
CMD ["python", "apex/execution/live_paper_runner.py", "--env"]
