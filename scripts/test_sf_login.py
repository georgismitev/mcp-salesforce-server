#!/usr/bin/env python3
"""
Test Salesforce Login Script

This script extracts just the Salesforce login functionality from streaming_mcp_server.py
to test authentication independently from the rest of the application.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# Import Salesforce
try:
    from simple_salesforce import Salesforce
except ImportError:
    print("Error: simple-salesforce not installed. Install with: pip install simple-salesforce")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("sf_login_test")

def test_salesforce_login():
    """
    Test Salesforce login functionality extracted from streaming_mcp_server.py
    """
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment
    username = os.getenv('SALESFORCE_USERNAME')
    password = os.getenv('SALESFORCE_PASSWORD')
    security_token = os.getenv('SALESFORCE_SECURITY_TOKEN')
    access_token = os.getenv('SALESFORCE_ACCESS_TOKEN')
    instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
    
    # Print credential info (without revealing sensitive data)
    logger.info("=== Salesforce Login Test ===")
    
    if username:
        logger.info(f"Username: {username}")
    else:
        logger.warning("Username not set")
        
    if password:
        logger.info(f"Password: {'*' * len(password)}")
    else:
        logger.warning("Password not set")
        
    if security_token:
        logger.info(f"Security Token: {'*' * len(security_token)}")
    else:
        logger.info("Security Token not set")
        
    if access_token:
        logger.info(f"Access Token: {'*' * 10}... ({len(access_token)} chars)")
    else:
        logger.info("Access Token not set")
        
    if instance_url:
        logger.info(f"Instance URL: {instance_url}")
    else:
        logger.info("Instance URL not set")
    
    # Try to connect to Salesforce
    try:
        logger.info("\n=== Attempting Salesforce Login ===")
        
        if access_token and instance_url:
            logger.info("Using token-based authentication")
            sf = Salesforce(
                instance_url=instance_url,
                session_id=access_token
            )
        else:
            logger.info("Using username/password authentication")
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token
            )
        
        # Test the connection by making a simple API call
        logger.info("Attempting API call to test connection...")
        result = sf.query("SELECT Id, Name FROM User LIMIT 1")
        
        # Get the API version and URL information
        logger.info(f"Connected to Salesforce successfully!")
        logger.info(f"API Version: {sf.api_version}")
        
        # Safely access the instance URL to avoid AttributeError
        instance_url_value = "Unknown"
        try:
            if hasattr(sf, 'session') and sf.session is not None:
                if hasattr(sf.session, 'auth') and sf.session.auth is not None:
                    if hasattr(sf.session.auth, 'instance_url'):
                        instance_url_value = sf.session.auth.instance_url
            # Fallback to the directly provided instance_url if available
            elif hasattr(sf, 'instance_url') and sf.instance_url is not None:
                instance_url_value = sf.instance_url
        except Exception:
            pass
            
        logger.info(f"Instance URL: {instance_url_value}")
        logger.info(f"Test Query Result: Retrieved {result['totalSize']} User records")
        
        # Print session information
        logger.info(f"Session ID: {sf.session_id[:10]}... (length: {len(sf.session_id)})")
        
        return True
        
    except Exception as e:
        now_cet = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M:%S")
        logger.error(f"[{now_cet} CET] Salesforce connection failed: {e}")
        
        # Include the exception type for better debugging
        logger.error(f"Exception type: {type(e).__name__}")
        
        # Print traceback for debugging
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        return False

def main():
    """Main function to run the test"""
    # Run the test
    success = test_salesforce_login()
    
    # Create a clear success/failure message that will be easily visible in logs
    if success:
        logger.info("\n")
        logger.info("========================================")
        logger.info("=== SALESFORCE LOGIN TEST SUCCESSFUL ===")
        logger.info("========================================")
        logger.info("The Salesforce authentication is working correctly.")
        logger.info("You can now use this configuration with your MCP server.")
        logger.info("\n")
        sys.exit(0)
    else:
        logger.error("\n")
        logger.error("======================================")
        logger.error("=== SALESFORCE LOGIN TEST FAILED ===")
        logger.error("======================================")
        logger.error("Please check your credentials and network connectivity.")
        logger.error("See the error details above for more information.")
        logger.error("\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
