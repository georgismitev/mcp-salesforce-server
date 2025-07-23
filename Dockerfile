FROM python:3.11-alpine

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY uv.lock .
COPY README.md ./README.md

# Install necessary build dependencies
RUN apk add --no-cache gcc musl-dev python3-dev git

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    # First install project dependencies with pip (this is more reliable in Docker than using UV)
    pip install --no-cache-dir -e . && \
    # Then install the latest simple-salesforce from GitHub
    pip install --no-cache-dir --force-reinstall git+https://github.com/simple-salesforce/simple-salesforce.git

# Copy source code
COPY src/ ./src/

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