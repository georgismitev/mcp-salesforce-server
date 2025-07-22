#!/usr/bin/env python3
"""
MCP Server with Streaming Support using Starlette and FastMCP
"""

from typing import Any, Dict, Optional
from datetime import datetime
import json
import asyncio
import logging
import os
import uuid
import argparse

import httpx
from simple_salesforce import Salesforce
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
import mcp.types as types
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
import uvicorn
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server for Salesforce tools with SSE support
mcp = FastMCP("salesforce-ss")

load_dotenv()

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
            logger.info("Connected to Salesforce successfully")
        except Exception as e:
            logger.error(f"Salesforce connection failed: {e}")
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
        return json.loads(results)  # Convert JSON string to dict if needed
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

    async def handle_sse(request: Request) -> None:
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

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Salesforce MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Get the actual MCP server from the FastMCP wrapper
    mcp_server = mcp._mcp_server

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)
    
    print(f"Starting Salesforce MCP Server with streaming on http://{args.host}:{args.port}")
    print(f"SSE endpoint available at http://{args.host}:{args.port}/sse")

    uvicorn.run(starlette_app, host=args.host, port=args.port)
