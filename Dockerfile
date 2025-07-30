FROM python:3.11-alpine

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY uv.lock .
COPY README.md ./README.md

# Install necessary build dependencies
# RUN apk add --no-cache gcc musl-dev python3-dev
RUN apk add --no-cache gcc musl-dev python3-dev ca-certificates
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/

# Ensure scripts are executable
RUN chmod +x ./scripts/*.py ./scripts/*.sh 2>/dev/null || true

# Expose the port the MCP server will run on
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_DEBUG=true

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Use the streaming MCP server as the main entry point
ENTRYPOINT ["/app/entrypoint.sh"]