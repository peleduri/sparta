#!/usr/bin/env python3
"""
Split repositories into batches for parallel processing.

This script reads repos.json (single-org or multi-org format) and splits repos
into batches for parallel processing via GitHub Actions matrix strategy.
"""

import os
import json
import sys
import math
from pathlib import Path

# Import security utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from security_utils import sanitize_path, sanitize_error_message

def split_into_batches(items, batch_size):
    """Split a list into batches of specified size."""
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])
    return batches

def main():
    # Get batch size from environment (default: 100)
    batch_size = int(os.environ.get('BATCH_SIZE', '100'))
    if batch_size < 1:
        print("Error: BATCH_SIZE must be at least 1")
        sys.exit(1)
    
    # Read repos list (validate path)
    try:
        base_dir = Path.cwd()
        repos_file = sanitize_path('repos.json', base_dir)
        with open(repos_file, 'r') as f:
            repos_data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to read repos file - {sanitize_error_message(str(e), [])}")
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
        # Multi-org format: create batches per org
        all_batches = []
        batch_info = []
        
        for org_data in repos_data:
            org_name = org_data['org']
            repos = org_data['repos']
            
            if len(repos) == 0:
                continue
            
            # Split repos for this org into batches
            batches = split_into_batches(repos, batch_size)
            
            for batch_idx, batch in enumerate(batches):
                batch_id = f"{org_name}-batch-{batch_idx + 1}"
                all_batches.append({
                    'batch_id': batch_id,
                    'org': org_name,
                    'repos': batch,
                    'batch_index': batch_idx,
                    'total_batches': len(batches)
                })
                batch_info.append({
                    'batch_id': batch_id,
                    'org': org_name,
                    'size': len(batch),
                    'batch_index': batch_idx,
                    'total_batches': len(batches)
                })
        
        # Save batches to file
        batches_file = sanitize_path('repo-batches.json', base_dir)
        with open(batches_file, 'w') as f:
            json.dump(all_batches, f, indent=2)
        
        # Print summary
        total_repos = sum(len(org_data['repos']) for org_data in repos_data)
        total_batches = len(all_batches)
        print(f"Split {total_repos} repositories across {len(repos_data)} organization(s) into {total_batches} batch(es)")
        for info in batch_info:
            print(f"  - {info['batch_id']}: {info['size']} repos (batch {info['batch_index'] + 1}/{info['total_batches']} for {info['org']})")
        
        # Set GitHub Actions output for matrix strategy
        github_output = os.environ.get('GITHUB_OUTPUT', '/dev/stdout')
        with open(github_output, 'a') as f:
            # Create matrix include list
            matrix_include = json.dumps([{'batch_id': b['batch_id']} for b in all_batches])
            f.write(f"matrix={matrix_include}\n")
            f.write(f"total_batches={total_batches}\n")
            f.write(f"total_repos={total_repos}\n")
    else:
        # Single org format: backward compatible
        repos = repos_data
        
        if len(repos) == 0:
            print("Error: No repositories found")
            sys.exit(1)
        
        # Split repos into batches
        batches = split_into_batches(repos, batch_size)
        
        all_batches = []
        for batch_idx, batch in enumerate(batches):
            batch_id = f"batch-{batch_idx + 1}"
            all_batches.append({
                'batch_id': batch_id,
                'repos': batch,
                'batch_index': batch_idx,
                'total_batches': len(batches)
            })
        
        # Save batches to file
        batches_file = sanitize_path('repo-batches.json', base_dir)
        with open(batches_file, 'w') as f:
            json.dump(all_batches, f, indent=2)
        
        # Print summary
        total_repos = len(repos)
        total_batches = len(batches)
        print(f"Split {total_repos} repositories into {total_batches} batch(es) (batch size: {batch_size})")
        for batch in all_batches:
            print(f"  - {batch['batch_id']}: {len(batch['repos'])} repos (batch {batch['batch_index'] + 1}/{total_batches})")
        
        # Set GitHub Actions output for matrix strategy
        github_output = os.environ.get('GITHUB_OUTPUT', '/dev/stdout')
        with open(github_output, 'a') as f:
            # Create matrix include list
            matrix_include = json.dumps([{'batch_id': b['batch_id']} for b in all_batches])
            f.write(f"matrix={matrix_include}\n")
            f.write(f"total_batches={total_batches}\n")
            f.write(f"total_repos={total_repos}\n")

if __name__ == '__main__':
    main()

