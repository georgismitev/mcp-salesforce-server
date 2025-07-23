#!/usr/bin/env python3
"""
MCP Server with Streaming Support using Starlette and FastMCP
Main entry point for the Docker workflow
"""

# Fix module loading issues - define this before any other imports
import sys
import os
import logging.config

# Set environment variable to indicate that we're in the main module
# This will help prevent duplicate initialization
os.environ["MCP_SERVER_ALREADY_RUNNING"] = "1"

# Silence the RuntimeWarning about module loading
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")

# Dedicated flag for tracking initialization
_is_initialized = False

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

# Configure logging once - with deduplicated setup
def setup_logging(log_level=logging.INFO):
    """Set up logging with deduplication controls"""
    # Clear all existing handlers from the root logger to avoid duplicates
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Get our module logger
    logger = logging.getLogger(__name__)
    
    # Clear any existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Ensure we're using the correct level
    logger.setLevel(log_level)
    
    return logger

# Set up initial logging
logger = setup_logging(logging.INFO)

# Initialize FastMCP server for Salesforce tools with SSE support
mcp = FastMCP("salesforce-ss")

# Module-level variable to track if we've already initialized the client
__sf_client = None

# Salesforce Client
class SalesforceClient:
    """Salesforce client wrapper"""
    
    def __init__(self):
        self.sf = None
        self.sobjects_cache = {}
        self._initialize()
        
    def _initialize(self):
        """Initialize Salesforce connection using environment variables"""
        # If already initialized, don't re-initialize
        if self.sf is not None:
            return
        
        # Use a flag file to prevent duplicate logging
        connection_logged = os.environ.get("SALESFORCE_CONNECTION_LOGGED") == "1"
            
        try:
            access_token = os.getenv('SALESFORCE_ACCESS_TOKEN')
            instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
            
            if access_token and instance_url:
                self.sf = Salesforce(
                    instance_url=instance_url,
                    session_id=access_token
                )
            else:
                self.sf = Salesforce(
                    username=os.getenv('SALESFORCE_USERNAME'),
                    password=os.getenv('SALESFORCE_PASSWORD'),
                    security_token=os.getenv('SALESFORCE_SECURITY_TOKEN')
                )
            
            # Only log the first time, and only if we're in the main process
            # Set the environment variable to mark that we've logged
            if not connection_logged and os.environ.get("MCP_SERVER_ALREADY_RUNNING") == "1":
                logger.info("Connected to Salesforce successfully")
                os.environ["SALESFORCE_CONNECTION_LOGGED"] = "1"
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

# Initialize Salesforce client (only once)
def get_salesforce_client():
    """Get or create the Salesforce client instance"""
    global __sf_client
    if __sf_client is None:
        __sf_client = SalesforceClient()
    return __sf_client

sf_client = get_salesforce_client()

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
    global _is_initialized, logger
    
    # Avoid double execution
    if _is_initialized:
        return
    
    parser = argparse.ArgumentParser(description='Run Salesforce MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--log-level', default='info', help='Logging level (debug, info, warning, error)')
    args = parser.parse_args()
    
    # Configure logging level
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    
    # Reset logging completely with the specified log level
    logger = setup_logging(log_level)
    
    # Mark as initialized to prevent duplicate log messages
    _is_initialized = True
    
    starlette_app = setup_app()
    
    # Only log startup messages if we're the main module
    if os.environ.get("MCP_SERVER_ALREADY_RUNNING") == "1":
        logger.info(f"Starting Salesforce MCP Server with streaming on http://{args.host}:{args.port}")
        logger.info(f"SSE endpoint available at http://{args.host}:{args.port}/sse")

    # Suppress Uvicorn's default logging
    uvicorn_log_config = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
            }
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "WARNING", "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": "ERROR", "propagate": False},
            "uvicorn.access": {"level": "WARNING", "propagate": False},
        }
    }
    
    try:
        # Run with minimal logging from uvicorn
        uvicorn.run(
            starlette_app, 
            host=args.host, 
            port=args.port,
            log_config=uvicorn_log_config,
            access_log=False
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
