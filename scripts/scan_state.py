#!/usr/bin/env python3
"""
State management utilities for tracking scan progress.

This script manages scan state files to enable resume capability and track
completed/failed repositories across workflow runs.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import security utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security_utils import sanitize_path, sanitize_error_message, validate_org_name, validate_repo_name

class ScanState:
    """Manages scan state for tracking progress."""
    
    def __init__(self, org_name: str, scan_date: str, state_file: Optional[Path] = None):
        self.org_name = validate_org_name(org_name)
        self.scan_date = scan_date
        self.batch_size = int(os.environ.get('BATCH_SIZE', '100'))
        self.max_retries = int(os.environ.get('MAX_RETRIES', '3'))
        
        if state_file is None:
            base_dir = Path.cwd()
            state_file = sanitize_path(f'scan-state-{org_name}-{scan_date}.json', base_dir)
        
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load state from file or create new state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                # Validate state structure
                if not isinstance(state, dict) or state.get('org') != self.org_name:
                    print(f"Warning: State file exists but has invalid structure. Creating new state.")
                    return self._create_new_state()
                return state
            except Exception as e:
                print(f"Warning: Failed to load state file: {sanitize_error_message(str(e), [])}. Creating new state.")
                return self._create_new_state()
        else:
            return self._create_new_state()
    
    def _create_new_state(self) -> Dict:
        """Create a new state structure."""
        return {
            'org': self.org_name,
            'scan_date': self.scan_date,
            'batch_size': self.batch_size,
            'total_repos': 0,
            'completed_repos': [],
            'failed_repos': [],
            'pending_repos': [],
            'batches': {},
            'last_updated': datetime.now().isoformat()
        }
    
    def initialize(self, total_repos: int, repos: List[Dict]):
        """Initialize state with repository list."""
        repo_names = [validate_repo_name(repo['name']) for repo in repos]
        self.state['total_repos'] = total_repos
        self.state['pending_repos'] = repo_names
        self.state['last_updated'] = datetime.now().isoformat()
        self.save()
    
    def mark_completed(self, repo_name: str):
        """Mark a repository as completed."""
        repo_name = validate_repo_name(repo_name)
        if repo_name in self.state['pending_repos']:
            self.state['pending_repos'].remove(repo_name)
        if repo_name in self.state['failed_repos']:
            # Remove from failed repos if it was previously failed
            self.state['failed_repos'] = [
                f for f in self.state['failed_repos']
                if isinstance(f, dict) and f.get('repo') != repo_name
            ]
        if repo_name not in self.state['completed_repos']:
            self.state['completed_repos'].append(repo_name)
        self.state['last_updated'] = datetime.now().isoformat()
        self.save()
    
    def mark_failed(self, repo_name: str, error: str, retry_count: int = 0):
        """Mark a repository as failed."""
        repo_name = validate_repo_name(repo_name)
        if repo_name in self.state['pending_repos']:
            self.state['pending_repos'].remove(repo_name)
        
        # Remove existing entry if present
        self.state['failed_repos'] = [
            f for f in self.state['failed_repos']
            if isinstance(f, dict) and f.get('repo') != repo_name
        ]
        
        # Add new failed entry
        self.state['failed_repos'].append({
            'repo': repo_name,
            'error': error,
            'retry_count': retry_count,
            'timestamp': datetime.now().isoformat()
        })
        self.state['last_updated'] = datetime.now().isoformat()
        self.save()
    
    def mark_batch_completed(self, batch_id: str, repos: List[str]):
        """Mark a batch as completed."""
        self.state['batches'][batch_id] = {
            'status': 'completed',
            'repos': [validate_repo_name(r) for r in repos],
            'completed_at': datetime.now().isoformat()
        }
        self.state['last_updated'] = datetime.now().isoformat()
        self.save()
    
    def mark_batch_failed(self, batch_id: str, repos: List[str]):
        """Mark a batch as failed."""
        self.state['batches'][batch_id] = {
            'status': 'failed',
            'repos': [validate_repo_name(r) for r in repos],
            'failed_at': datetime.now().isoformat()
        }
        self.state['last_updated'] = datetime.now().isoformat()
        self.save()
    
    def get_pending_repos(self) -> List[str]:
        """Get list of pending repositories."""
        return self.state['pending_repos'].copy()
    
    def get_failed_repos(self) -> List[Dict]:
        """Get list of failed repositories with retry information."""
        return [
            f for f in self.state['failed_repos']
            if isinstance(f, dict) and f.get('retry_count', 0) < self.max_retries
        ]
    
    def get_completed_repos(self) -> List[str]:
        """Get list of completed repositories."""
        return self.state['completed_repos'].copy()
    
    def should_retry(self, repo_name: str) -> bool:
        """Check if a repository should be retried."""
        repo_name = validate_repo_name(repo_name)
        for failed_repo in self.state['failed_repos']:
            if isinstance(failed_repo, dict) and failed_repo.get('repo') == repo_name:
                return failed_repo.get('retry_count', 0) < self.max_retries
        return False
    
    def increment_retry_count(self, repo_name: str):
        """Increment retry count for a failed repository."""
        repo_name = validate_repo_name(repo_name)
        for failed_repo in self.state['failed_repos']:
            if isinstance(failed_repo, dict) and failed_repo.get('repo') == repo_name:
                failed_repo['retry_count'] = failed_repo.get('retry_count', 0) + 1
                failed_repo['timestamp'] = datetime.now().isoformat()
                self.state['last_updated'] = datetime.now().isoformat()
                self.save()
                return
    
    def save(self):
        """Save state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save state file: {sanitize_error_message(str(e), [])}")
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total = self.state['total_repos']
        completed = len(self.state['completed_repos'])
        failed = len(self.state['failed_repos'])
        pending = len(self.state['pending_repos'])
        
        return {
            'org': self.org_name,
            'scan_date': self.scan_date,
            'total_repos': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'progress_percent': round((completed / total * 100) if total > 0 else 0, 2),
            'last_updated': self.state['last_updated']
        }

def main():
    """CLI interface for scan state management."""
    if len(sys.argv) < 2:
        print("Usage: scan_state.py <command> [args...]")
        print("Commands:")
        print("  init <org> <scan_date> <total_repos> - Initialize state")
        print("  completed <org> <scan_date> <repo> - Mark repo as completed")
        print("  failed <org> <scan_date> <repo> <error> - Mark repo as failed")
        print("  summary <org> <scan_date> - Show summary")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        if len(sys.argv) < 5:
            print("Error: init requires org, scan_date, and total_repos")
            sys.exit(1)
        org_name = sys.argv[2]
        scan_date = sys.argv[3]
        total_repos = int(sys.argv[4])
        state = ScanState(org_name, scan_date)
        state.state['total_repos'] = total_repos
        state.save()
        print(f"Initialized state for {org_name} on {scan_date}: {total_repos} repos")
    
    elif command == 'completed':
        if len(sys.argv) < 5:
            print("Error: completed requires org, scan_date, and repo")
            sys.exit(1)
        org_name = sys.argv[2]
        scan_date = sys.argv[3]
        repo_name = sys.argv[4]
        state = ScanState(org_name, scan_date)
        state.mark_completed(repo_name)
        print(f"Marked {repo_name} as completed")
    
    elif command == 'failed':
        if len(sys.argv) < 6:
            print("Error: failed requires org, scan_date, repo, and error")
            sys.exit(1)
        org_name = sys.argv[2]
        scan_date = sys.argv[3]
        repo_name = sys.argv[4]
        error = sys.argv[5]
        retry_count = int(sys.argv[6]) if len(sys.argv) > 6 else 0
        state = ScanState(org_name, scan_date)
        state.mark_failed(repo_name, error, retry_count)
        print(f"Marked {repo_name} as failed: {error}")
    
    elif command == 'summary':
        if len(sys.argv) < 4:
            print("Error: summary requires org and scan_date")
            sys.exit(1)
        org_name = sys.argv[2]
        scan_date = sys.argv[3]
        state = ScanState(org_name, scan_date)
        summary = state.get_summary()
        print(f"Scan State Summary for {org_name} on {scan_date}:")
        print(f"  Total repos: {summary['total_repos']}")
        print(f"  Completed: {summary['completed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Pending: {summary['pending']}")
        print(f"  Progress: {summary['progress_percent']}%")
        print(f"  Last updated: {summary['last_updated']}")
    
    else:
        print(f"Error: Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()

