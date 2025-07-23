#!/usr/bin/env python3
"""
MCP Server with Streaming Support using Starlette and FastMCP
Main entry point for the Docker workflow
"""

from typing import Any, Dict, Optional
from datetime import datetime
import json
import asyncio
import logging
import os
import uuid
import argparse
import sys

import httpx
from simple_salesforce import Salesforce
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
import mcp.types as types
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
import uvicorn
from dotenv import load_dotenv

from datetime import datetime
from zoneinfo import ZoneInfo

# Load environment variables first to ensure they're available when needed
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Clear old handlers to avoid duplicate logs
if logger.hasHandlers():
    logger.handlers.clear()

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Initialize FastMCP server for Salesforce tools with SSE support
mcp = FastMCP("salesforce-ss")

# Salesforce Client
class SalesforceClient:
    """Salesforce client wrapper"""
    
    def __init__(self):
        self.sf = None
        self.sobjects_cache = {}
        self._initialize()
        
    def _initialize(self):
        """Initialize Salesforce connection using environment variables"""
        try:
            # Try to make a diagnostic HTTP request first using httpx (already imported)
            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.get("https://login.salesforce.com/")
                logger.info(f"CURL: Salesforce connectivity check: Status {response.status_code}")
                if not response.is_success:
                    logger.warning(f"CURL: HTTP diagnostic response: {response.text[:200]}")
            except Exception as http_err:
                logger.warning(f"CURL: Diagnostic HTTP request failed: {http_err}")
            
            self.sf = Salesforce(
                username=os.getenv('SALESFORCE_USERNAME'),
                password=os.getenv('SALESFORCE_PASSWORD'),
                security_token=os.getenv('SALESFORCE_SECURITY_TOKEN')
            )
            logger.info("Connected to Salesforce successfully")
        except Exception as e:
            now_cet = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M:%S")
            logger.error(f"[{now_cet} CET] Salesforce connection failed: {e}")
            self.sf = None
    
    def get_object_fields(self, object_name):
        """Get fields for a specific object"""
        if not self.sf:
            raise ValueError("Salesforce connection not established.")
       
        if object_name not in self.sobjects_cache:
            sf_object = getattr(self.sf, object_name)
            fields = sf_object.describe()['fields']
            filtered_fields = []
            for field in fields:
                filtered_fields.append({
                    'label': field['label'],
                    'name': field['name'],
                    'updateable': field['updateable'],
                    'type': field['type'],
                    'length': field['length'],
                    'picklistValues': field['picklistValues']
                })
            self.sobjects_cache[object_name] = filtered_fields
            
        return self.sobjects_cache[object_name]

# Initialize Salesforce client
sf_client = SalesforceClient()

@mcp.tool()
async def get_object_fields(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves field Names, labels and types for a specific Salesforce object
    
    Args:
        arguments: Dictionary containing:
            - object_name: The name of the Salesforce object (e.g., 'Account', 'Contact')
    """
    object_name = arguments.get("object_name")
    if not object_name:
        raise ValueError("Missing 'object_name' argument")
    
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    
    try:
        results = sf_client.get_object_fields(object_name)
        # The results are already a Python object, not a JSON string
        return {"fields": results}
    except Exception as e:
        logger.error(f"Error getting object fields: {e}")
        raise ValueError(f"Error getting object fields: {e}")

@mcp.tool()
async def run_soql_query(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a SOQL query against Salesforce
    
    Args:
        arguments: Dictionary containing:
            - query: The SOQL query to execute
    """
    query = arguments.get("query")
    if not query:
        raise ValueError("Missing 'query' argument")
    
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    
    try:
        results = sf_client.sf.query_all(query)
        return results
    except Exception as e:
        logger.error(f"Error executing SOQL query: {e}")
        raise ValueError(f"Error executing SOQL query: {e}")

@mcp.tool()
async def get_record(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves a specific record by ID
    
    Args:
        arguments: Dictionary containing:
            - object_name: The name of the Salesforce object (e.g., 'Account', 'Contact')
            - record_id: The ID of the record to retrieve
    """
    object_name = arguments.get("object_name")
    record_id = arguments.get("record_id")
    
    if not object_name or not record_id:
        raise ValueError("Missing 'object_name' or 'record_id' argument")
    
    if not sf_client.sf:
        raise ValueError("Salesforce connection not established.")
    
    try:
        sf_object = getattr(sf_client.sf, object_name)
        results = sf_object.get(record_id)
        return results
    except Exception as e:
        logger.error(f"Error retrieving record: {e}")
        raise ValueError(f"Error retrieving record: {e}")

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Response:
        try:
            async with sse.connect_sse(
                    request.scope,
                    request.receive,
                    request._send,
            ) as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                )
        except Exception as e:
            logger.error(f"SSE handler crashed: {e}")
        return Response(status_code=204)  # No Content
    
    async def handle_health_check(request: Request) -> Response:
        """Health check endpoint for Docker container health checks"""
        # Check if Salesforce connection is active
        if sf_client.sf is None:
            return Response(
                content=json.dumps({"status": "error", "message": "Salesforce connection not established"}),
                status_code=503,
                media_type="application/json"
            )
        
        return Response(
            content=json.dumps({"status": "ok", "service": "mcp-salesforce-server", "timestamp": datetime.now().isoformat()}),
            status_code=200,
            media_type="application/json"
        )
    
    async def handle_metrics(request: Request) -> Response:
        """Metrics endpoint for monitoring in Docker environment"""
        return Response(
            content=json.dumps({
                "service": "mcp-salesforce-server",
                "status": "active",
                "timestamp": datetime.now().isoformat(),
                "salesforce_connected": sf_client.sf is not None,
                "version": "0.1.8"  # Get this from package version
            }),
            status_code=200,
            media_type="application/json"
        )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/health", endpoint=handle_health_check),
            Route("/metrics", endpoint=handle_metrics),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

def setup_app() -> Starlette:
    """
    Set up and return the Starlette application for the Salesforce MCP Server.
    This function can be used both for direct execution and for WSGI/ASGI servers in Docker.
    """
    # Get the actual MCP server from the FastMCP wrapper
    mcp_server = mcp._mcp_server
    
    # Bind SSE request handling to MCP server
    return create_starlette_app(mcp_server, debug=True)

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Run Salesforce MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--log-level', default='info', help='Logging level (debug, info, warning, error)')
    args = parser.parse_args()
    
    # Configure logging level
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Also set root logger level
    logging.getLogger().setLevel(log_level)
    
    starlette_app = setup_app()
    
    print(f"Starting Salesforce MCP Server with streaming on http://{args.host}:{args.port}")
    print(f"SSE endpoint available at http://{args.host}:{args.port}/sse")

    try:
        uvicorn.run(starlette_app, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
