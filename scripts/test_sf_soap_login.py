#!/usr/bin/env python3
"""
Test script to mimic the raw SOAP login request that simple-salesforce makes.
This helps debug authentication issues by isolating just the login request.
"""

import sys
import requests
from xml.parsers.expat import ExpatError

from dotenv import load_dotenv

load_dotenv()

def get_unique_element_value(xml_string, element_name):
    """Extract value from XML element"""
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(xml_string)
    
    # Define namespaces
    namespaces = {
        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
        'urn': 'urn:partner.soap.sforce.com',
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'sf': 'urn:fault.partner.soap.sforce.com'
    }
    
    # Try various namespace combinations
    for ns in namespaces:
        path = f'.//{{{namespaces[ns]}}}{element_name}'
        elements = root.findall(path)
        if elements:
            return elements[0].text
    
    # If no namespaces worked, try without namespace
    elements = root.findall(f'.//{element_name}')
    if elements:
        return elements[0].text
    
    return None

def salesforce_soap_login(username, password, security_token, domain="login", api_version="59.0", client_id="simple-salesforce"):
    """
    Perform a raw SOAP login request to Salesforce exactly as simple-salesforce does
    
    Args:
        username: Salesforce username
        password: Salesforce password
        security_token: Salesforce security token
        domain: Domain to connect to (default: login)
        api_version: API version (default: 59.0)
        client_id: Client ID (default: simple-salesforce)
    
    Returns:
        tuple: (session_id, sf_instance) if successful
        
    Raises:
        Exception with details if login fails
    """
    # Construct the SOAP request body
    login_soap_request_body = f"""<?xml version="1.0" encoding="utf-8" ?>
<env:Envelope
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:env="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:urn="urn:partner.soap.sforce.com">
    <env:Header>
        <urn:CallOptions>
            <urn:client>{client_id}</urn:client>
            <urn:defaultNamespace>sf</urn:defaultNamespace>
        </urn:CallOptions>
    </env:Header>
    <env:Body>
        <n1:login xmlns:n1="urn:partner.soap.sforce.com">
            <n1:username>{username}</n1:username>
            <n1:password>{password}{security_token}</n1:password>
        </n1:login>
    </env:Body>
</env:Envelope>"""

    # Set up the request headers
    login_soap_request_headers = {
        'content-type': 'text/xml',
        'charset': 'UTF-8',
        'SOAPAction': 'login'
    }
    
    # Construct the SOAP URL
    soap_url = f'https://{domain}.salesforce.com/services/Soap/u/{api_version}'
    
    print(f"Making SOAP login request to: {soap_url}")
    print(f"Using username: {username}")
    print(f"Password length: {len(password)} chars")
    print(f"Security token length: {len(security_token)} chars")
    
    try:
        # Send the request
        response = requests.post(soap_url, 
                                data=login_soap_request_body, 
                                headers=login_soap_request_headers)
        
        print(f"Response status code: {response.status_code}")
        print(f"Response ========")
        print(response.content)
        print(f"Response ========")
        
        # Check for successful response
        if response.status_code != 200:
            try:
                except_code = get_unique_element_value(response.content, 'exceptionCode')
                except_msg = get_unique_element_value(response.content, 'exceptionMessage') or response.content.decode()
                print(f"Authentication failed: {except_code}: {except_msg}")
                return None
            except ExpatError:
                print(f"Authentication failed: {response.status_code}: {response.content.decode()}")
                return None
        
        # Extract session_id and server_url from response
        session_id = get_unique_element_value(response.content, 'sessionId')
        server_url = get_unique_element_value(response.content, 'serverUrl')
        
        if session_id is None or server_url is None:
            except_code = get_unique_element_value(response.content, 'exceptionCode') or "UNKNOWN_EXCEPTION_CODE"
            except_msg = get_unique_element_value(response.content, 'exceptionMessage') or "UNKNOWN_EXCEPTION_MESSAGE"
            print(f"Failed to extract session information: {except_code}: {except_msg}")
            return None
        
        # Parse instance from server URL
        sf_instance = (server_url
                      .replace('http://', '')
                      .replace('https://', '')
                      .split('/')[0]
                      .replace('-api', ''))
        
        print("Authentication successful!")
        print(f"Instance: {sf_instance}")
        print(f"Session ID length: {len(session_id)} chars")
        
        return session_id, sf_instance
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    import os
    
    # Get credentials from environment variables or prompt for them
    username = os.environ.get('SALESFORCE_USERNAME')
    password = os.environ.get('SALESFORCE_PASSWORD')
    security_token = os.environ.get('SALESFORCE_SECURITY_TOKEN')
    domain = os.environ.get('SALESFORCE_DOMAIN', 'login')
    
    if not username:
        username = input("Salesforce Username: ")
    
    if not password:
        import getpass
        password = getpass.getpass("Salesforce Password: ")
    
    if not security_token:
        security_token = getpass.getpass("Salesforce Security Token (press Enter if none): ")
    
    # Call the login function
    result = salesforce_soap_login(username, password, security_token, domain)
    
    if result:
        session_id, sf_instance = result
        print("=" * 50)
        print("SUCCESS! Use these values to connect to Salesforce:")
        print(f"Session ID: {session_id[:10]}... (truncated)")
        print(f"Instance: {sf_instance}")
        sys.exit(0)
    else:
        print("=" * 50)
        print("FAILED! Authentication to Salesforce failed.")
        sys.exit(1)
