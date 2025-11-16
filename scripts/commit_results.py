#!/usr/bin/env python3
"""
Commit and push scan results to the Sparta repository.

This script verifies we're in the correct repository, commits the vulnerability-reports/
directory, and pushes to the main branch.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Import security utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security_utils import sanitize_error_message, secure_git_clone

def main():
    # Verify we're in the Sparta repository (not a cloned repo)
    current_repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not current_repo:
        print("Error: GITHUB_REPOSITORY environment variable is not set")
        sys.exit(1)
    
    # Verify we're in the correct directory (Sparta repo, not a cloned repo)
    # Check that we're not in a temporary cloned repo directory
    current_dir = Path.cwd()
    if current_dir.name.startswith('tmp-') or 'tmp-' in str(current_dir):
        print(f"Error: Appears to be in a temporary cloned repository directory: {current_dir}")
        print("This should not happen - commit should only run in Sparta repository")
        sys.exit(1)
    
    # Verify git remote points to Sparta repository
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode != 0:
        print("Error: Failed to get git remote URL")
        sys.exit(1)
    
    remote_url = result.stdout.strip()
    expected_repo = current_repo.lower()
    
    # Verify remote URL contains the Sparta repository name
    if expected_repo not in remote_url.lower():
        print(f"Error: Git remote does not match Sparta repository")
        print(f"Expected repository: {expected_repo}")
        installation_token = os.environ.get('GITHUB_APP_TOKEN', '')
        print(f"Remote URL: {remote_url.replace(installation_token, '***')}")
        print("Aborting commit to prevent pushing to wrong repository")
        sys.exit(1)
    
    print(f"Verified: Committing to Sparta repository: {current_repo}")
    
    # Configure git
    subprocess.run(['git', 'config', '--local', 'user.email', 'action@github.com'], check=True)
    subprocess.run(['git', 'config', '--local', 'user.name', 'GitHub Action'], check=True)
    
    # Stage changes
    result = subprocess.run(['git', 'add', 'vulnerability-reports/'], check=False)
    
    # Check if there are changes
    result = subprocess.run(['git', 'diff', '--staged', '--quiet'], check=False)
    if result.returncode == 0:
        print("No changes to commit")
        sys.exit(0)
    
    # Commit
    commit_msg = f"Daily vulnerability scan results - {datetime.now().strftime('%Y-%m-%d')}"
    subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
    
    # Push using token from environment variable
    installation_token = os.environ.get('GITHUB_APP_TOKEN', '')
    if not installation_token:
        print("Error: GITHUB_APP_TOKEN environment variable is not set")
        sys.exit(1)
    
    # Use git credential helper for push (similar to secure_git_clone)
    import tempfile
    cred_fd, cred_file = tempfile.mkstemp(text=True)
    try:
        # Write credential in format: https://x-access-token:TOKEN@github.com
        # This format is required for GitHub App installation tokens per:
        # https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
        with os.fdopen(cred_fd, 'w') as f:
            f.write(f"https://x-access-token:{installation_token}@github.com\n")
        
        # Configure git to use credential file
        subprocess.run(
            ['git', 'config', '--local', 'credential.helper', f'store --file={cred_file}'],
            check=True,
            capture_output=True,
            timeout=10
        )
        
        # Update remote URL (without token)
        repo_url = f"https://github.com/{current_repo}.git"
        subprocess.run(
            ['git', 'remote', 'set-url', 'origin', repo_url],
            check=True,
            capture_output=True,
            timeout=10
        )
        
        # Push
        result = subprocess.run(
            ['git', 'push', 'origin', 'main'],
            check=False,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Clean up credential file
        if os.path.exists(cred_file):
            os.unlink(cred_file)
        
        # Reset credential helper
        subprocess.run(
            ['git', 'config', '--local', '--unset', 'credential.helper'],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"Successfully pushed scan results to Sparta repository: {current_repo}")
        else:
            # Sanitize error message
            error_msg = sanitize_error_message(result.stderr, [installation_token])
            print(f"Push failed: {error_msg}")
            sys.exit(1)
    except Exception as e:
        # Clean up credential file on error
        if os.path.exists(cred_file):
            try:
                os.unlink(cred_file)
            except Exception:
                pass
        error_msg = sanitize_error_message(str(e), [installation_token])
        print(f"Error during push: {error_msg}")
        sys.exit(1)

if __name__ == '__main__':
    main()

