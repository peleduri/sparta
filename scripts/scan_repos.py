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
import time
from pathlib import Path
from datetime import datetime

# Import security utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security_utils import (
    sanitize_path, validate_org_name, validate_repo_name,
    validate_repo_full_name, sanitize_error_message, secure_git_clone
)

# Import scan state management
try:
    from scan_state import ScanState
    STATE_MANAGEMENT_AVAILABLE = True
except ImportError:
    STATE_MANAGEMENT_AVAILABLE = False

def scan_repository(repo, org_name, reports_dir, scan_date, current_repo, installation_token, tokens_to_sanitize, scan_state=None, retry_count=0):
    """Scan a single repository with optional retry logic."""
    try:
        # Validate repository data
        repo_name = validate_repo_name(repo['name'])
        repo_full_name = validate_repo_full_name(repo.get('full_name', ''))
        default_branch = repo.get('default_branch', 'main') or 'main'
    except (KeyError, ValueError) as e:
        error_msg = sanitize_error_message(str(e), tokens_to_sanitize)
        print(f"Warning: Skipping invalid repository data: {error_msg}")
        if scan_state:
            scan_state.mark_failed(repo_name, f"Invalid repository data: {error_msg}", retry_count)
        return False
    
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
            return
        
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
            if scan_state:
                scan_state.mark_completed(repo_name)
            return True
        else:
            print(f"⚠ Scan completed with warnings for {repo_full_name}")
            if result.stderr:
                print(result.stderr)
            if scan_state:
                scan_state.mark_completed(repo_name)  # Still mark as completed even with warnings
            return True
    
    print(f"\n{'='*60}")
    print(f"Scanning: {repo_full_name}")
    print(f"{'='*60}")
    
    # Validate and create repo directory path
    repo_dir = None
    report_dir = None
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
        error_msg = sanitize_error_message(str(e), tokens_to_sanitize)
        print(f"Error: Invalid directory path - {error_msg}")
        if scan_state:
            scan_state.mark_failed(repo_name, f"Invalid directory path: {error_msg}", retry_count)
        return False
    
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
            # Clone failed - create error report and handle retry logic
            error_msg_sanitized = sanitize_error_message(error_msg, tokens_to_sanitize)
            print(f"✗ Error cloning {repo_full_name}: {error_msg_sanitized}")
            
            # Check if we should retry (transient errors)
            is_transient_error = any(keyword in error_msg.lower() for keyword in ['timeout', 'network', 'connection', 'rate limit', 'temporary'])
            should_retry = is_transient_error and retry_count < int(os.environ.get('MAX_RETRIES', '3'))
            
            if should_retry:
                wait_time = min(2 ** retry_count, 60)  # Exponential backoff, max 60 seconds
                print(f"  Retrying in {wait_time} seconds (attempt {retry_count + 1}/{int(os.environ.get('MAX_RETRIES', '3'))})...")
                time.sleep(wait_time)
                return scan_repository(repo, org_name, reports_dir, scan_date, current_repo, installation_token, tokens_to_sanitize, scan_state, retry_count + 1)
            
            error_report = {
                'error': f"Git clone failed: {error_msg_sanitized}",
                'repository': repo_full_name,
                'timestamp': datetime.now().isoformat(),
                'clone_url': clone_url,
                'retry_count': retry_count
            }
            try:
                with open(report_dir / 'trivy-report.json', 'w') as f:
                    json.dump(error_report, f, indent=2)
            except Exception as write_err:
                print(f"Warning: Failed to write error report: {sanitize_error_message(str(write_err), tokens_to_sanitize)}")
            
            if scan_state:
                scan_state.mark_failed(repo_name, f"Git clone failed: {error_msg_sanitized}", retry_count)
            return False
        
        # Verify cloned directory exists and is not empty
        if not repo_dir.exists() or not any(repo_dir.iterdir()):
            error_msg = f"Cloned directory is missing or empty: {repo_dir}"
            error_msg_sanitized = sanitize_error_message(error_msg, tokens_to_sanitize)
            print(f"✗ Error: {error_msg_sanitized}")
            error_report = {
                'error': error_msg_sanitized,
                'repository': repo_full_name,
                'timestamp': datetime.now().isoformat()
            }
            try:
                with open(report_dir / 'trivy-report.json', 'w') as f:
                    json.dump(error_report, f, indent=2)
            except Exception:
                pass
            return  # Skip to next repository
        
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
            if scan_state:
                scan_state.mark_completed(repo_name)
            return True
        else:
            print(f"⚠ Scan completed with warnings for {repo_full_name}")
            if result.stderr:
                print(result.stderr)
            if scan_state:
                scan_state.mark_completed(repo_name)  # Still mark as completed even with warnings
            return True
        
    except subprocess.TimeoutExpired:
        error_msg = sanitize_error_message('Scan timeout', tokens_to_sanitize)
        print(f"✗ Timeout scanning {repo_full_name}: {error_msg}")
        
        # Check if we should retry (timeout is transient)
        should_retry = retry_count < int(os.environ.get('MAX_RETRIES', '3'))
        if should_retry:
            wait_time = min(2 ** retry_count, 60)  # Exponential backoff
            print(f"  Retrying in {wait_time} seconds (attempt {retry_count + 1}/{int(os.environ.get('MAX_RETRIES', '3'))})...")
            time.sleep(wait_time)
            return scan_repository(repo, org_name, reports_dir, scan_date, current_repo, installation_token, tokens_to_sanitize, scan_state, retry_count + 1)
        
        if report_dir:
            error_report = {
                'error': error_msg,
                'repository': repo_full_name,
                'timestamp': datetime.now().isoformat(),
                'retry_count': retry_count
            }
            try:
                with open(report_dir / 'trivy-report.json', 'w') as f:
                    json.dump(error_report, f, indent=2)
            except Exception as write_err:
                print(f"Warning: Failed to write error report: {sanitize_error_message(str(write_err), tokens_to_sanitize)}")
        
        if scan_state:
            scan_state.mark_failed(repo_name, error_msg, retry_count)
        return False
    
    except Exception as e:
        error_msg = sanitize_error_message(str(e), tokens_to_sanitize)
        print(f"✗ Error scanning {repo_full_name}: {error_msg}")
        
        # Check if we should retry (some exceptions might be transient)
        is_transient_error = any(keyword in error_msg.lower() for keyword in ['timeout', 'network', 'connection', 'rate limit', 'temporary'])
        should_retry = is_transient_error and retry_count < int(os.environ.get('MAX_RETRIES', '3'))
        
        if should_retry:
            wait_time = min(2 ** retry_count, 60)  # Exponential backoff
            print(f"  Retrying in {wait_time} seconds (attempt {retry_count + 1}/{int(os.environ.get('MAX_RETRIES', '3'))})...")
            time.sleep(wait_time)
            return scan_repository(repo, org_name, reports_dir, scan_date, current_repo, installation_token, tokens_to_sanitize, scan_state, retry_count + 1)
        
        if report_dir:
            error_report = {
                'error': error_msg,
                'repository': repo_full_name,
                'timestamp': datetime.now().isoformat(),
                'retry_count': retry_count
            }
            try:
                with open(report_dir / 'trivy-report.json', 'w') as f:
                    json.dump(error_report, f, indent=2)
            except Exception as write_err:
                print(f"Warning: Failed to write error report: {sanitize_error_message(str(write_err), tokens_to_sanitize)}")
        
        if scan_state:
            scan_state.mark_failed(repo_name, error_msg, retry_count)
        return False
    
    finally:
        # Cleanup
        if repo_dir and repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)

def main():
    # Validate inputs
    current_repo = os.environ.get('GITHUB_REPOSITORY', '')
    scan_date = datetime.now().strftime('%Y%m%d')
    installation_token = os.environ.get('GITHUB_APP_TOKEN', '')
    if not installation_token:
        print("Error: GITHUB_APP_TOKEN environment variable is not set")
        sys.exit(1)
    
    tokens_to_sanitize = [installation_token]
    
    # Read repos list (validate path)
    try:
        base_dir = Path.cwd()
        repos_file = sanitize_path('repos.json', base_dir)
        with open(repos_file, 'r') as f:
            repos_data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to read repos file - {sanitize_error_message(str(e), tokens_to_sanitize)}")
        sys.exit(1)
    
    # Auto-detect format: check if it's multi-org format (array of org objects) or single-org format (array of repos)
    is_multi_org_format = (
        isinstance(repos_data, list) and 
        len(repos_data) > 0 and 
        isinstance(repos_data[0], dict) and 
        'org' in repos_data[0] and 
        'repos' in repos_data[0]
    )
    
    if is_multi_org_format:
        # Multi-org format: array of org objects
        print(f"Detected multi-org format: {len(repos_data)} organization(s)")
        
        for org_data in repos_data:
            try:
                org_name = validate_org_name(org_data['org'])
                repos = org_data['repos']
            except (KeyError, ValueError) as e:
                print(f"Warning: Skipping invalid org data: {sanitize_error_message(str(e), tokens_to_sanitize)}")
                continue
            
            print(f"\n{'='*60}")
            print(f"Processing organization: {org_name} ({len(repos)} repositories)")
            print(f"{'='*60}")
            
            # Validate and sanitize reports directory path for this org
            try:
                base_dir = Path.cwd()
                reports_base = sanitize_path('vulnerability-reports', base_dir)
                reports_dir = sanitize_path(org_name, reports_base)
                reports_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Error: Invalid reports directory path for {org_name} - {sanitize_error_message(str(e), tokens_to_sanitize)}")
                continue
            
            # Initialize scan state if available
            scan_state = None
            if STATE_MANAGEMENT_AVAILABLE:
                try:
                    scan_state = ScanState(org_name, scan_date)
                    # Only initialize if state is new (no existing state)
                    if not scan_state.state_file.exists() or len(scan_state.get_completed_repos()) == 0:
                        scan_state.initialize(len(repos), repos)
                    else:
                        # Resume mode: update pending repos from current repos list
                        completed = set(scan_state.get_completed_repos())
                        repo_names = [validate_repo_name(repo['name']) for repo in repos]
                        scan_state.state['pending_repos'] = [r for r in repo_names if r not in completed]
                        scan_state.state['total_repos'] = len(repos)
                        scan_state.save()
                        print(f"Resuming scan: {len(completed)} already completed, {len(scan_state.state['pending_repos'])} pending")
                except Exception as e:
                    print(f"Warning: Failed to initialize scan state: {sanitize_error_message(str(e), tokens_to_sanitize)}")
            
            # Filter repos based on state (resume capability)
            repos_to_scan = repos
            if scan_state:
                completed = set(scan_state.get_completed_repos())
                failed_to_retry = {f['repo'] for f in scan_state.get_failed_repos()}
                repos_to_scan = [
                    repo for repo in repos
                    if validate_repo_name(repo['name']) not in completed or validate_repo_name(repo['name']) in failed_to_retry
                ]
                skipped_count = len(repos) - len(repos_to_scan)
                if skipped_count > 0:
                    print(f"Skipping {skipped_count} already completed repository(ies)")
            
            # Process repos for this org
            for repo in repos_to_scan:
                scan_repository(repo, org_name, reports_dir, scan_date, current_repo, installation_token, tokens_to_sanitize, scan_state)
            
            # Print summary if state management is available
            if scan_state:
                summary = scan_state.get_summary()
                print(f"\nScan Summary for {org_name}:")
                print(f"  Completed: {summary['completed']}/{summary['total_repos']} ({summary['progress_percent']}%)")
                print(f"  Failed: {summary['failed']}")
                print(f"  Pending: {summary['pending']}")
            
            print(f"\n{'='*60}")
            print(f"Completed scanning {org_name}. Reports saved to vulnerability-reports/{org_name}/")
            print(f"{'='*60}")
        
        print(f"\n{'='*60}")
        print(f"Scanning complete for all organizations.")
        print(f"{'='*60}")
    else:
        # Single org format: backward compatible (array of repos)
        # Try to get org_name from GITHUB_ORG env var, or infer from first repo
        try:
            org_name = validate_org_name(os.environ['GITHUB_ORG'])
        except (KeyError, ValueError):
            # Try to infer from first repo's full_name
            if isinstance(repos_data, list) and len(repos_data) > 0:
                try:
                    first_repo_full_name = repos_data[0].get('full_name', '')
                    if '/' in first_repo_full_name:
                        org_name = first_repo_full_name.split('/')[0]
                        org_name = validate_org_name(org_name)
                    else:
                        raise ValueError("Cannot determine organization name")
                except (ValueError, KeyError):
                    print("Error: Cannot determine organization name. Set GITHUB_ORG environment variable.")
                    sys.exit(1)
            else:
                print("Error: Cannot determine organization name. Set GITHUB_ORG environment variable.")
                sys.exit(1)
        
        repos = repos_data
        
        # Validate and sanitize reports directory path
        try:
            base_dir = Path.cwd()
            reports_base = sanitize_path('vulnerability-reports', base_dir)
            reports_dir = sanitize_path(org_name, reports_base)
            reports_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error: Invalid reports directory path - {sanitize_error_message(str(e), tokens_to_sanitize)}")
            sys.exit(1)
        
        # Initialize scan state if available
        scan_state = None
        if STATE_MANAGEMENT_AVAILABLE:
            try:
                scan_state = ScanState(org_name, scan_date)
                # Only initialize if state is new (no existing state)
                if not scan_state.state_file.exists() or len(scan_state.get_completed_repos()) == 0:
                    scan_state.initialize(len(repos), repos)
                else:
                    # Resume mode: update pending repos from current repos list
                    completed = set(scan_state.get_completed_repos())
                    repo_names = [validate_repo_name(repo['name']) for repo in repos]
                    scan_state.state['pending_repos'] = [r for r in repo_names if r not in completed]
                    scan_state.state['total_repos'] = len(repos)
                    scan_state.save()
                    print(f"Resuming scan: {len(completed)} already completed, {len(scan_state.state['pending_repos'])} pending")
            except Exception as e:
                print(f"Warning: Failed to initialize scan state: {sanitize_error_message(str(e), tokens_to_sanitize)}")
        
        # Filter repos based on state (resume capability)
        repos_to_scan = repos
        if scan_state:
            completed = set(scan_state.get_completed_repos())
            failed_to_retry = {f['repo'] for f in scan_state.get_failed_repos()}
            repos_to_scan = [
                repo for repo in repos
                if validate_repo_name(repo['name']) not in completed or validate_repo_name(repo['name']) in failed_to_retry
            ]
            skipped_count = len(repos) - len(repos_to_scan)
            if skipped_count > 0:
                print(f"Skipping {skipped_count} already completed repository(ies)")
        
        for repo in repos_to_scan:
            scan_repository(repo, org_name, reports_dir, scan_date, current_repo, installation_token, tokens_to_sanitize, scan_state)
        
        # Print summary if state management is available
        if scan_state:
            summary = scan_state.get_summary()
            print(f"\nScan Summary for {org_name}:")
            print(f"  Completed: {summary['completed']}/{summary['total_repos']} ({summary['progress_percent']}%)")
            print(f"  Failed: {summary['failed']}")
            print(f"  Pending: {summary['pending']}")
        
        print(f"\n{'='*60}")
        print(f"Scanning complete. Reports saved to vulnerability-reports/{org_name}/")
        print(f"{'='*60}")

if __name__ == '__main__':
    main()

