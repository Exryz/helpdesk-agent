FROM python:3.11-slim

WORKDIR /app

# Create a non-root system user and group
RUN groupadd -r helpdesk && useradd -r -g helpdesk helpdesk

# Install build dependencies if needed, copy project definitions
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY data/ ./data/

# Install the package with UI dependencies
RUN pip install --no-cache-dir .[ui]

# Ensure appropriate permissions for application directory
RUN chown -R helpdesk:helpdesk /app

USER helpdesk

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "helpdesk.api.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
