#!/bin/sh
# entrypoint.sh - Wrapper script for MCP server to handle initialization and errors

# Set up proper signal handling
trap 'echo "Received SIGTERM, shutting down gracefully..."; exit 0' TERM
trap 'echo "Received SIGINT, shutting down gracefully..."; exit 0' INT

# Echo environment for debugging (remove sensitive info)
echo "Starting MCP Salesforce server on port $PORT"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Check if environment variables are set
if [ -z "$SALESFORCE_USERNAME" ] && [ -z "$SALESFORCE_ACCESS_TOKEN" ]; then
    echo "WARNING: Neither SALESFORCE_USERNAME nor SALESFORCE_ACCESS_TOKEN are set."
    echo "The server will start, but connections to Salesforce will fail."
fi

# Create a script to keep the server running and handle multiple requests
echo "Creating startup script..."
cat > /app/run_server.py << 'EOF'
#!/usr/bin/env python3
import sys
import subprocess
import threading
import time
import os
import signal
import atexit

# Function to handle server process
def run_server():
    print("Starting MCP server process...", file=sys.stderr)
    
    # Create a filter for stdout to ensure only valid JSON is passed through
    class OutputFilter:
        def __init__(self, original_stdout, original_stderr):
            self.original_stdout = original_stdout
            self.original_stderr = original_stderr
            self.buffer = ""
        
        def write(self, data):
            # Check if it looks like JSON (starts with { or [)
            stripped_data = data.strip()
            if stripped_data and (stripped_data[0] == '{' or stripped_data[0] == '['):
                # Looks like JSON, send to stdout
                return self.original_stdout.write(data)
            else:
                # Not JSON, redirect to stderr
                return self.original_stderr.write(data)
        
        def flush(self):
            self.original_stdout.flush()
            self.original_stderr.flush()
    
    # Redirect stderr to a file for logging
    log_file = open("/tmp/mcp_server.log", "a")
    
    # Start the MCP server process with filtered output
    process = subprocess.Popen(
        ["python", "-u", "src/salesforce/server.py"],
        stdin=sys.stdin,
        stdout=OutputFilter(sys.stdout, log_file),
        stderr=log_file,
        bufsize=0
    )
    
    # Set up cleanup
    def cleanup():
        if process.poll() is None:
            print("Terminating server process...", file=sys.stderr)
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    atexit.register(cleanup)
    
    # Wait for the process to complete
    exit_code = process.wait()
    print(f"Server process exited with code {exit_code}", file=sys.stderr)
    
    # Keep container alive for debugging
    if exit_code != 0:
        print("Server crashed. Container will continue running for debugging.", file=sys.stderr)
    
    return exit_code

# Set up signal handlers
def handle_signal(signum, frame):
    print(f"Received signal {signum}, exiting...", file=sys.stderr)
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# Run the server
try:
    exit_code = run_server()
    # Keep container running
    print("Server process complete. Keeping container alive for connection...", file=sys.stderr)
    while True:
        time.sleep(3600)
except KeyboardInterrupt:
    print("Interrupted by user, shutting down...", file=sys.stderr)
    sys.exit(0)
EOF

chmod +x /app/run_server.py

# Start the server with our wrapper
echo "Starting MCP server..."
python -u /app/run_server.py

# This will only execute if the server exits
EXIT_CODE=$?
echo "Server exited with code $EXIT_CODE"

# Keep container running if there was an error, to allow debugging
if [ $EXIT_CODE -ne 0 ]; then
    echo "Server crashed. Keeping container running for debugging..."
    # Sleep indefinitely to keep container alive
    tail -f /dev/null
else
    echo "Server shut down gracefully."
fi
