#!/usr/bin/env python3
"""
Get all organization repositories using GitHub App token.

This script lists all repositories in the organization and saves them to repos.json.
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

def main():
    # Validate and sanitize inputs
    try:
        org_name = validate_org_name(os.environ['GITHUB_ORG'])
        installation_token = os.environ.get('GITHUB_APP_TOKEN', '')
        if not installation_token:
            raise ValueError("GITHUB_APP_TOKEN environment variable is not set")
    except (KeyError, ValueError) as e:
        print(f"Error: Invalid input - {str(e)}")
        sys.exit(1)
    
    # Tokens to sanitize in error messages
    tokens_to_sanitize = [installation_token]
    
    try:
        # Use installation token to access organization via PyGithub
        token_auth = Token(installation_token)
        g = Github(auth=token_auth)
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
                print(f"Warning: Skipping invalid repository {repo.name}: {sanitize_error_message(str(e), tokens_to_sanitize)}")
                continue
        
        print(f"Found {len(repos)} repositories")
        
        # Save repos list to file
        # Try to write to workspace first, if that fails write to /tmp/workspace (mounted temp dir)
        base_dir = Path.cwd()
        repos_file = sanitize_path('repos.json', base_dir)
        tmp_workspace_file = Path('/tmp/workspace/repos.json')
        
        # Try to write to workspace first
        try:
            with open(repos_file, 'w') as f:
                json.dump(repos, f, indent=2)
        except PermissionError:
            # If we can't write to workspace, write to /tmp/workspace (mounted temp dir)
            # The workflow will copy it to workspace after container exits
            try:
                tmp_workspace_file.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_workspace_file, 'w') as f:
                    json.dump(repos, f, indent=2)
                print(f"Warning: Cannot write to workspace, file saved to {tmp_workspace_file} (will be copied by workflow)")
            except Exception as e:
                print(f"Error: Failed to write repos file - {sanitize_error_message(str(e), tokens_to_sanitize)}")
                raise
        
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

