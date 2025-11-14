#!/usr/bin/env python3
"""
Scan all repositories for vulnerabilities using Trivy.

This script reads repos.json, clones each repository, scans it with Trivy,
and saves the results to vulnerability-reports/.
"""

import os
import json
import subprocess
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Import security utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security_utils import (
    sanitize_path, validate_org_name, validate_repo_name,
    validate_repo_full_name, sanitize_error_message, secure_git_clone
)

def main():
    # Validate inputs
    try:
        org_name = validate_org_name(os.environ['GITHUB_ORG'])
        current_repo = os.environ.get('GITHUB_REPOSITORY', '')
        scan_date = datetime.now().strftime('%Y%m%d')
        installation_token = os.environ.get('GITHUB_APP_TOKEN', '')
        if not installation_token:
            raise ValueError("GITHUB_APP_TOKEN environment variable is not set")
    except (KeyError, ValueError) as e:
        print(f"Error: Invalid input - {str(e)}")
        sys.exit(1)
    
    tokens_to_sanitize = [installation_token]
    
    # Read repos list (validate path)
    try:
        base_dir = Path.cwd()
        repos_file = sanitize_path('repos.json', base_dir)
        with open(repos_file, 'r') as f:
            repos = json.load(f)
    except Exception as e:
        print(f"Error: Failed to read repos file - {sanitize_error_message(str(e), tokens_to_sanitize)}")
        sys.exit(1)
    
    # Validate and sanitize reports directory path
    try:
        base_dir = Path.cwd()
        reports_base = sanitize_path('vulnerability-reports', base_dir)
        reports_dir = sanitize_path(org_name, reports_base)
        reports_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error: Invalid reports directory path - {sanitize_error_message(str(e), tokens_to_sanitize)}")
        sys.exit(1)
    
    for repo in repos:
        try:
            # Validate repository data
            repo_name = validate_repo_name(repo['name'])
            repo_full_name = validate_repo_full_name(repo.get('full_name', ''))
            default_branch = repo.get('default_branch', 'main') or 'main'
        except (KeyError, ValueError) as e:
            print(f"Warning: Skipping invalid repository data: {sanitize_error_message(str(e), tokens_to_sanitize)}")
            continue
        
        # Skip cloning Sparta repo since we're already in it
        if repo_full_name == current_repo:
            print(f"\n{'='*60}")
            print(f"Skipping clone for {repo_full_name} (already in this repository)")
            print(f"Scanning current repository...")
            print(f"{'='*60}")
            
            # Use current directory for scan
            repo_dir = Path('.')
            try:
                report_dir = sanitize_path(repo_name, reports_dir) / scan_date
                report_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Error: Invalid report directory path - {sanitize_error_message(str(e), tokens_to_sanitize)}")
                continue
            
            # Run Trivy scan on current directory
            result = subprocess.run(
                [
                    'trivy', 'fs',
                    '--format', 'json',
                    '--output', str(report_dir / 'trivy-report.json'),
                    '--timeout', '120m0s',
                    '--ignore-unfixed',
                    '--scanners', 'vuln',
                    '--vuln-type', 'os,library',
                    '--severity', 'CRITICAL,HIGH,MEDIUM,LOW',
                    '--cache-dir', f'{os.environ.get("GITHUB_WORKSPACE", ".")}/.cache/trivy',
                    '.'
                ],
                capture_output=True,
                text=True,
                timeout=900
            )
            
            if result.returncode == 0:
                print(f"✓ Scan completed for {repo_full_name}")
            else:
                print(f"⚠ Scan completed with warnings for {repo_full_name}")
                if result.stderr:
                    print(result.stderr)
            continue
        
        print(f"\n{'='*60}")
        print(f"Scanning: {repo_full_name}")
        print(f"{'='*60}")
        
        # Validate and create repo directory path
        try:
            base_dir = Path.cwd()
            repo_dir_name = f'tmp-{repo_name}'
            # Sanitize repo_dir_name to prevent path traversal
            repo_dir_name = repo_dir_name.replace('..', '').replace('/', '').replace('\\', '')
            repo_dir = sanitize_path(repo_dir_name, base_dir)
            
            # Validate and create report directory
            report_dir = sanitize_path(repo_name, reports_dir) / scan_date
            report_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error: Invalid directory path - {sanitize_error_message(str(e), tokens_to_sanitize)}")
            continue
        
        try:
            # Clone repository using secure_git_clone function
            clone_url = f"https://github.com/{repo_full_name}.git"
            success, error_msg = secure_git_clone(
                repo_url=clone_url,
                target_dir=repo_dir,
                branch=default_branch,
                token=installation_token,
                timeout=300
            )
            
            if not success:
                raise Exception(f"Git clone failed: {error_msg}")
            
            # Run Trivy scan
            result = subprocess.run(
                [
                    'trivy', 'fs',
                    '--format', 'json',
                    '--output', str(report_dir / 'trivy-report.json'),
                    '--timeout', '120m0s',
                    '--ignore-unfixed',
                    '--scanners', 'vuln',
                    '--vuln-type', 'os,library',
                    '--severity', 'CRITICAL,HIGH,MEDIUM,LOW',
                    '--cache-dir', f'{os.environ.get("GITHUB_WORKSPACE", ".")}/.cache/trivy',
                    str(repo_dir)
                ],
                capture_output=True,
                text=True,
                timeout=900
            )
            
            if result.returncode == 0:
                print(f"✓ Scan completed for {repo_full_name}")
            else:
                print(f"⚠ Scan completed with warnings for {repo_full_name}")
                print(result.stderr)
            
        except subprocess.TimeoutExpired:
            error_msg = sanitize_error_message('Scan timeout', tokens_to_sanitize)
            print(f"✗ Timeout scanning {repo_full_name}")
            # Create empty report with error
            error_report = {
                'error': error_msg,
                'repository': repo_full_name,
                'timestamp': datetime.now().isoformat()
            }
            try:
                with open(report_dir / 'trivy-report.json', 'w') as f:
                    json.dump(error_report, f, indent=2)
            except Exception:
                pass
        
        except Exception as e:
            error_msg = sanitize_error_message(str(e), tokens_to_sanitize)
            print(f"✗ Error scanning {repo_full_name}: {error_msg}")
            # Create empty report with error (sanitized)
            error_report = {
                'error': error_msg,
                'repository': repo_full_name,
                'timestamp': datetime.now().isoformat()
            }
            try:
                with open(report_dir / 'trivy-report.json', 'w') as f:
                    json.dump(error_report, f, indent=2)
            except Exception:
                pass
        
        finally:
            # Cleanup
            if repo_dir.exists():
                shutil.rmtree(repo_dir, ignore_errors=True)
    
    print(f"\n{'='*60}")
    print(f"Scanning complete. Reports saved to vulnerability-reports/{org_name}/")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

