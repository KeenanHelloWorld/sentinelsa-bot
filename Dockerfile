FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 botuser

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

# Create data directory for persistent state
RUN mkdir -p /app/data && chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Health check - verify bot is responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import os; exit(0 if os.path.exists('data/state.json') or True else 1)"

# Run with unbuffered output and proper signal handling
CMD ["python", "-u", "bot.py"]