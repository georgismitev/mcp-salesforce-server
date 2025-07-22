import subprocess
import json
import sys
import os
import time
import select
import uuid

class MCPServerTest:
    """Test harness for MCP Server interactions"""
    
    def __init__(self):
        """Initialize the test harness."""
        self.proc = None
        self.returncode = None
        
    def start_server(self):
        """Start the MCP server process"""
        server_path = "src/salesforce/server.py"
        
        # Start the server subprocess with more debug information
        self.proc = subprocess.Popen(
            [sys.executable, server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,           # Use text mode for stdin/stdout
            bufsize=1            # Line buffering is now supported
        )
        
        # Give the server a brief moment to start up (shortened to 0.5s)
        time.sleep(0.5)
        print(f"Server process started with PID: {self.proc.pid}")
        
        # Check if we can get any initial output without blocking
        ready_to_read, _, _ = select.select([self.proc.stdout, self.proc.stderr], [], [], 0.5)
        if self.proc.stderr in ready_to_read:
            initial_stderr = self.proc.stderr.readline()
            if initial_stderr:
                print(f"Initial stderr from server: {initial_stderr.strip()}")
        
        if self.proc.stdout in ready_to_read:
            initial_stdout = self.proc.stdout.readline()
            if initial_stdout:
                print(f"Initial stdout from server: {initial_stdout.strip()}")
                
        # Check if process is still running
        if self.proc.poll() is not None:
            print(f"WARNING: Server exited immediately with code {self.proc.returncode}")
            print("Stderr:", self.proc.stderr.read())
            print("Stdout:", self.proc.stdout.read())
            
        return self.proc
    
    def stop_server(self):
        """Stop the server process"""
        if not self.proc:
            return
            
        print("Terminating server...")
        self.proc.terminate()
        try:
            exit_code = self.proc.wait(timeout=5)
            print(f"Server process exited with code: {exit_code}")
        except subprocess.TimeoutExpired:
            print("ERROR: Server did not terminate in time, killing process")
            self.proc.kill()
            self.proc.wait()
        
        print("Server stderr output:")
        stderr_output = self.proc.stderr.read()
        print(stderr_output if stderr_output else "[No stderr output]")
        
        print("Server stdout (remaining):")
        stdout_output = self.proc.stdout.read()
        print(stdout_output if stdout_output else "[No remaining stdout output]")
    
    def send_recv(self, message, timeout=5):
        """Send a message to the server and receive the response (with 5-second timeout)"""
        if not self.proc:
            raise ValueError("Server not started")
        
        # Check if process is still running
        if self.proc.poll() is not None:
            print(f"ERROR: Server is not running (exit code: {self.proc.returncode})")
            return {"error": "server_not_running", "exit_code": self.proc.returncode}
            
        print(f"Sending message: {message}")
        try:
            self.proc.stdin.write(json.dumps(message) + '\n')
            self.proc.stdin.flush()
            print("Message sent successfully")
        except BrokenPipeError:
            print("ERROR: Broken pipe - server probably crashed")
            return {"error": "broken_pipe"}
            
        # First check stderr for errors
        ready_stderr, _, _ = select.select([self.proc.stderr], [], [], 0.1)
        if ready_stderr:
            stderr_output = self.proc.stderr.read()
            if stderr_output:
                print(f"Server stderr before response: {stderr_output}")
        
        # Use a more generous timeout strategy with polling
        print(f"Waiting up to {timeout} seconds for response...")
        start_time = time.time()
        
        # Poll for data availability with shorter timeouts
        while time.time() - start_time < timeout:
            ready_to_read, _, _ = select.select([self.proc.stdout], [], [], 1.0)  # Check every second
            if ready_to_read:
                elapsed = time.time() - start_time
                print(f"Response detected after {elapsed:.2f} seconds")
                break
                
        if not ready_to_read:
            elapsed = time.time() - start_time
            print(f"ERROR: Timeout after {elapsed:.2f} seconds waiting for server response")
            return {"error": "timeout"}
            
        # Read lines from response until we find a valid JSON response
        # (MCP protocol is line-delimited JSON, but there might be debug output first)
        start_reading = time.time()
        while time.time() - start_reading < timeout:
            line = self.proc.stdout.readline()
            if not line:
                print("ERROR: Empty line received from server")
                time.sleep(0.1)  # Brief pause before trying again
                continue
                
            print("Raw line from server:", repr(line))
            
            try:
                # Try to parse as JSON - if successful, this is our response
                response = json.loads(line)
                return response
            except json.JSONDecodeError:
                print(f"Line is not JSON, treating as debug output: {line.strip()}")
                # This is probably debug output, not the JSON response
                continue
                
        print("ERROR: No valid JSON response found within timeout")
        return {"error": "no_valid_json_response"}

def test_initialize():
    """Test initializing the MCP server"""
    test = MCPServerTest()
    try:
        test.start_server()
        print("Sending initialize request...")
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            }
        }
        response = test.send_recv(init_msg, timeout=5)
        print("Initialize response:", response)
        if "error" in response:
            print("❌ Initialize failed")
            return False
        print("✅ Initialize test passed")
        return True
    except Exception as e:
        print(f"❌ Initialize test failed: {e}")
        raise
    finally:
        # Always clean up the server, regardless of test outcome
        if test and test.proc and test.proc.stdin:
            print("Cleaning up: closing connection and stopping server...")
            test.proc.stdin.close()
        test.stop_server()

def test_list_tools():
    """Test listing available tools from the MCP server"""
    test = MCPServerTest()
    try:
        # Start a new server instance for this test
        test.start_server()
        
        # Initialize the server first (required before other operations)
        print("Initializing server first...")
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",  # Use the correct protocol version
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            }
        }
        init_response = test.send_recv(init_msg, timeout=5)
        if "error" in init_response:
            test.stop_server()
            return None
            
        # Send initialization completed notification
        print("Sending initialized notification...")
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        test.proc.stdin.write(json.dumps(initialized_notification) + '\n')
        test.proc.stdin.flush()
        time.sleep(1)  # Give server time to process notification
        
        # Sending tools/list request with empty params (required by MCP protocol)
        print("Sending tools/list request...")
        request_id = str(uuid.uuid4())
        list_tools_msg = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {}
        }
        response = test.send_recv(list_tools_msg, timeout=10)
        # Just return the raw response
        return response
    except Exception as e:
        print(f"❌ List tools test failed: {e}")
        raise
    finally:
        # Always clean up the server, regardless of test outcome
        if test and test.proc and test.proc.stdin:
            print("Cleaning up: closing connection and stopping server...")
            test.proc.stdin.close()
        test.stop_server()

def run_all_tests():
    """Run all tests in sequence"""
    # First run the initialization test
    print("\n=== Running Initialization Test ===\n")
    init_result = test_initialize()
    
    # Then run the tools list test
    print("\n=== Running Tools List Test ===\n")
    tools_response = test_list_tools()
    print(json.dumps(tools_response, indent=2))
    
    # Return overall success/failure
    # init_result is already a boolean (True/False) from the test_initialize function
    # For tools_response, we need to check if it exists and has no errors
    tools_test_passed = tools_response and "error" not in tools_response
    
    return init_result and tools_test_passed

if __name__ == "__main__":
    print("\n=== MCP Salesforce Server Tests ===\n")
    success = run_all_tests()
    print("\n=== Test Results Summary ===")
    if success:
        print("✅ All tests passed successfully!")
    else:
        print("❌ Some tests failed. Please check the logs above for details.")
    # Return appropriate exit code
    sys.exit(0 if success else 1)
