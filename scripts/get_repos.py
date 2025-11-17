#!/usr/bin/env python3
"""
Get all organization repositories using GitHub App token.

This script lists all repositories in the organization(s) and saves them to repos.json.
Supports both single org (GITHUB_ORG) and multiple orgs (GITHUB_ORGS, comma-separated).
"""

import os
import json
import sys
from pathlib import Path
from github import Github
from github.Auth import Token

# Import security utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security_utils import (
    sanitize_path, validate_org_name, validate_repo_name,
    validate_repo_full_name, sanitize_error_message
)

def get_org_repos(org_name, g, tokens_to_sanitize):
    """Get all repositories for a single organization."""
    try:
        org = g.get_organization(org_name)
        repos = []
        for repo in org.get_repos():
            try:
                repo_name = validate_repo_name(repo.name)
                repo_full_name = validate_repo_full_name(repo.full_name)
                repos.append({
                    'name': repo_name,
                    'full_name': repo_full_name,
                    'private': repo.private,
                    'default_branch': repo.default_branch or 'main'
                })
            except ValueError as e:
                print(f"Warning: Skipping invalid repository {repo.name} in {org_name}: {sanitize_error_message(str(e), tokens_to_sanitize)}")
                continue
        return repos
    except Exception as e:
        error_msg = sanitize_error_message(str(e), tokens_to_sanitize)
        print(f"Error fetching repositories for {org_name}: {error_msg}")
        raise

def main():
    # Validate and sanitize inputs
    installation_token = os.environ.get('GITHUB_APP_TOKEN', '')
    if not installation_token:
        print("Error: GITHUB_APP_TOKEN environment variable is not set")
        sys.exit(1)
    
    # Tokens to sanitize in error messages
    tokens_to_sanitize = [installation_token]
    
    # Check for GITHUB_ORGS (multi-org) or GITHUB_ORG (single org, backward compatible)
    orgs_env = os.environ.get('GITHUB_ORGS', '').strip()
    org_env = os.environ.get('GITHUB_ORG', '').strip()
    
    if orgs_env:
        # Multi-org mode: GITHUB_ORGS is set
        org_names = [validate_org_name(org.strip()) for org in orgs_env.split(',') if org.strip()]
        if not org_names:
            print("Error: GITHUB_ORGS is set but contains no valid organization names")
            sys.exit(1)
        use_multi_org_format = True
    elif org_env:
        # Single org mode: GITHUB_ORG is set (backward compatible)
        org_names = [validate_org_name(org_env)]
        use_multi_org_format = False
    else:
        print("Error: Either GITHUB_ORG or GITHUB_ORGS environment variable must be set")
        sys.exit(1)
    
    try:
        # Use installation token to access organizations via PyGithub
        token_auth = Token(installation_token)
        g = Github(auth=token_auth)
        
        if use_multi_org_format:
            # Multi-org format: array of org objects
            org_repos_list = []
            total_repos = 0
            
            for org_name in org_names:
                print(f"Fetching repositories for organization: {org_name}")
                repos = get_org_repos(org_name, g, tokens_to_sanitize)
                org_repos_list.append({
                    'org': org_name,
                    'repos': repos
                })
                total_repos += len(repos)
                print(f"Found {len(repos)} repositories in {org_name}")
            
            print(f"Total: {total_repos} repositories across {len(org_names)} organization(s)")
            
            # Save repos list to file (validate path)
            base_dir = Path.cwd()
            repos_file = sanitize_path('repos.json', base_dir)
            with open(repos_file, 'w') as f:
                json.dump(org_repos_list, f, indent=2)
            
            # Set output
            github_output = os.environ.get('GITHUB_OUTPUT', '/dev/stdout')
            with open(github_output, 'a') as f:
                f.write(f"count={total_repos}\n")
                f.write(f"orgs={len(org_names)}\n")
        else:
            # Single org format: backward compatible (array of repos)
            org_name = org_names[0]
            repos = get_org_repos(org_name, g, tokens_to_sanitize)
            
            print(f"Found {len(repos)} repositories")
            
            # Save repos list to file (validate path)
            base_dir = Path.cwd()
            repos_file = sanitize_path('repos.json', base_dir)
            with open(repos_file, 'w') as f:
                json.dump(repos, f, indent=2)
            
            # Set output (using new format)
            github_output = os.environ.get('GITHUB_OUTPUT', '/dev/stdout')
            with open(github_output, 'a') as f:
                f.write(f"count={len(repos)}\n")
    except Exception as e:
        error_msg = sanitize_error_message(str(e), tokens_to_sanitize)
        print(f"Error: {error_msg}")
        sys.exit(1)

if __name__ == '__main__':
    main()

