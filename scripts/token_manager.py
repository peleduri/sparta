#!/usr/bin/env python3
"""
Token management for GitHub App authentication.

Handles generation of installation access tokens for single or multiple organizations.
"""

import os
import json
import jwt
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


def generate_jwt(app_id: str, private_key: str) -> str:
    """Generate JWT for GitHub App authentication."""
    now = datetime.utcnow()
    payload = {
        'iat': now - timedelta(seconds=60),
        'exp': now + timedelta(minutes=10),
        'iss': app_id
    }
    return jwt.encode(payload, private_key, algorithm='RS256')


def get_installation_token(jwt_token: str, org_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get installation access token for an organization.
    
    Returns:
        Tuple of (token, error_message). If successful, token is returned and error is None.
        If failed, token is None and error contains the error message.
    """
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Try to get installation for this org
    try:
        response = requests.get(
            f'https://api.github.com/orgs/{org_name}/installation',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 404:
            return None, f"GitHub App not installed on {org_name}"
        elif response.status_code != 200:
            return None, f"Error checking installation: {response.status_code}"
        
        installation_id = response.json()['id']
        
        # Generate installation access token
        response = requests.post(
            f'https://api.github.com/app/installations/{installation_id}/access_tokens',
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 201:
            return None, f"Error generating token: {response.status_code}"
        
        return response.json()['token'], None
    except requests.RequestException as e:
        return None, f"Network error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def generate_tokens_for_orgs(
    orgs: List[str],
    app_id: str,
    private_key: str,
    fallback_token: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate installation access tokens for multiple organizations.
    
    Args:
        orgs: List of organization names
        app_id: GitHub App ID
        private_key: GitHub App private key (PEM format)
        fallback_token: Optional fallback token to use if org-specific token generation fails
    
    Returns:
        Dictionary mapping org names to tokens: {"org1": "token1", "org2": "token2"}
    """
    token_map = {}
    failed_orgs = []
    
    # Generate JWT once
    try:
        jwt_token = generate_jwt(app_id, private_key)
    except Exception as e:
        print(f"Error generating JWT: {e}")
        if fallback_token:
            print("Using fallback token for all orgs")
            return {org: fallback_token for org in orgs}
        raise
    
    # Generate token for each org
    for org in orgs:
        org = org.strip()
        if not org:
            continue
            
        token, error = get_installation_token(jwt_token, org)
        if token:
            token_map[org] = token
            print(f"✓ Token generated for {org}")
        else:
            print(f"⚠ Warning: {error}")
            failed_orgs.append(org)
            # Use fallback token if available
            if fallback_token:
                token_map[org] = fallback_token
                print(f"  Using fallback token for {org}")
    
    # If no tokens generated and we have a fallback, use it for all
    if not token_map and fallback_token:
        print("Warning: No org-specific tokens generated, using fallback token for all orgs")
        token_map = {org: fallback_token for org in orgs}
    
    if failed_orgs:
        print(f"\n⚠ Warning: Failed to generate tokens for: {', '.join(failed_orgs)}")
        print("  Make sure the GitHub App is installed on these organizations")
    
    return token_map


def get_token_for_org(org_name: str, token_map: Optional[Dict[str, str]], default_token: str) -> str:
    """
    Get the appropriate token for an organization from the token map.
    
    Args:
        org_name: Organization name
        token_map: Dictionary mapping org names to tokens
        default_token: Default token to use if org not in map
    
    Returns:
        Token for the organization
    """
    if token_map:
        return token_map.get(org_name, default_token)
    return default_token

