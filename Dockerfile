FROM python:3.11-alpine

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY uv.lock .
COPY README.md ./README.md

# Install necessary build dependencies
RUN apk add --no-cache gcc musl-dev python3-dev

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/

# Create a default .env file
RUN echo "# Salesforce credentials" > .env && \
    echo "SALESFORCE_USERNAME=placeholder" >> .env && \
    echo "SALESFORCE_PASSWORD=placeholder" >> .env && \
    echo "SALESFORCE_SECURITY_TOKEN=placeholder" >> .env && \
    echo "SALESFORCE_DOMAIN=login" >> .env && \
    echo "PORT=8000" >> .env

# Expose the port the MCP server will run on
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_STDIO_ENABLED=true
ENV MCP_DEBUG=true

# Copy and set entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Use entrypoint script to run the server
ENTRYPOINT ["/app/entrypoint.sh"]
