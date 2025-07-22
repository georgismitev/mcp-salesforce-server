import http.server
import socketserver
import threading
import os
import subprocess
import signal
import sys
import time
import json
from io import BytesIO

# Port for the health check server
HEALTH_PORT = int(os.environ.get('PORT', 8000))

# Global MCP server process
MCP_PROCESS = None

# Simple HTTP request handler
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK - MCP Salesforce Server Health Check')
        
    def do_POST(self):
        global MCP_PROCESS
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        print(f"Received MCP request: {post_data.decode('utf-8')[:200]}...")
        
        # Initialize MCP server process if not already running
        if MCP_PROCESS is None:
            print("Starting MCP server subprocess...")
            MCP_PROCESS = subprocess.Popen(
                ["python", "-u", "-m", "src.salesforce.server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False  # Use binary mode
            )
        
        # Forward the request to the MCP server
        try:
            # Write request to MCP server's stdin
            MCP_PROCESS.stdin.write(post_data + b'\n')
            MCP_PROCESS.stdin.flush()
            
            # Read response from MCP server's stdout
            response_line = MCP_PROCESS.stdout.readline()
            
            # Send the response back to the client
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(response_line)
            
        except Exception as e:
            error_response = json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": None
            }).encode('utf-8')
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error_response)
            
            # Reset the process on error
            if MCP_PROCESS:
                try:
                    MCP_PROCESS.terminate()
                except:
                    pass
                MCP_PROCESS = None
        
    def log_message(self, format, *args):
        # Suppress logging for cleaner output
        return

def start_health_server():
    """Start a simple HTTP server for health checks and MCP requests"""
    print(f"Starting HTTP server on port {HEALTH_PORT}")
    with socketserver.TCPServer(("0.0.0.0", HEALTH_PORT), HealthCheckHandler) as httpd:
        try:
            httpd.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            httpd.server_close()
            print("HTTP server stopped")
            
            # Clean up the MCP process if it exists
            global MCP_PROCESS
            if MCP_PROCESS:
                try:
                    MCP_PROCESS.terminate()
                except:
                    pass

if __name__ == "__main__":
    print("Starting MCP HTTP Server for Cloud Run on port 8000...")
    print("This server will handle both health checks (GET) and MCP requests (POST)")
    
    # Run the HTTP server in the main thread
    try:
        start_health_server()
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)
