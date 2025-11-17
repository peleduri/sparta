#!/usr/bin/env python3
"""
Main orchestration script for organization vulnerability scanning.

This script handles the complete scanning workflow:
- Detects single vs multi-org mode
- Generates tokens per organization
- Gets repositories
- Detects batching needs
- Runs scans (with or without batching)
- Commits results
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules (will import as needed to avoid circular dependencies)
from token_manager import generate_tokens_for_orgs, get_token_for_org
from batch_repos import split_into_batches


def parse_orgs(orgs_input: Optional[str], repository_owner: Optional[str] = None) -> List[str]:
    """Parse organization names from input string."""
    if orgs_input:
        orgs = [org.strip() for org in orgs_input.split(',') if org.strip()]
        if orgs:
            return orgs
    
    # Fallback to repository owner or environment variable
    if repository_owner:
        return [repository_owner]
    
    # Try environment variable
    orgs_env = os.environ.get('GITHUB_ORGS', '').strip()
    if orgs_env:
        return [org.strip() for org in orgs_env.split(',') if org.strip()]
    
    org_env = os.environ.get('GITHUB_ORG', '').strip()
    if org_env:
        return [org_env]
    
    raise ValueError("No organizations specified. Provide --orgs or set GITHUB_ORG/GITHUB_ORGS")


def detect_scan_mode(orgs: List[str]) -> str:
    """Detect if we're in single-org or multi-org mode."""
    return 'multi-org' if len(orgs) > 1 else 'single-org'


def needs_batching(repos_file: Path, threshold: int = 500) -> bool:
    """Check if batching is needed based on repository count."""
    try:
        with open(repos_file, 'r') as f:
            repos_data = json.load(f)
        
        # Check if multi-org format
        is_multi_org = (
            isinstance(repos_data, list) and 
            len(repos_data) > 0 and 
            isinstance(repos_data[0], dict) and 
            'org' in repos_data[0] and 
            'repos' in repos_data[0]
        )
        
        if is_multi_org:
            # Check if any org has more than threshold repos
            for org_data in repos_data:
                if len(org_data.get('repos', [])) > threshold:
                    return True
            return False
        else:
            # Single org format
            repos = repos_data if isinstance(repos_data, list) else []
            return len(repos) > threshold
    except Exception as e:
        print(f"Warning: Could not determine batching needs: {e}")
        return False


def normalize_org_name_for_secret(org_name: str) -> str:
    """
    Normalize organization name for use in secret names.
    
    Converts org name to uppercase and replaces hyphens with underscores.
    Example: "my-org" -> "MY_ORG"
    """
    return org_name.upper().replace('-', '_')


def parse_org_credentials(orgs: List[str], default_app_id: str, default_private_key: str) -> Dict[str, Dict[str, str]]:
    """
    Parse per-organization GitHub App credentials from environment variables.
    
    Looks for secrets in format: SPARTA_APP_ID_<ORG> and SPARTA_APP_PRIVATE_KEY_<ORG>
    Falls back to default credentials if org-specific not found.
    
    Args:
        orgs: List of organization names
        default_app_id: Default GitHub App ID
        default_private_key: Default GitHub App private key
    
    Returns:
        Dictionary mapping org names to credentials:
        {"org1": {"app_id": "...", "private_key": "..."}, ...}
    """
    org_credentials_map = {}
    
    for org in orgs:
        org_normalized = normalize_org_name_for_secret(org)
        
        # Look for org-specific credentials
        org_app_id_key = f"SPARTA_APP_ID_{org_normalized}"
        org_private_key_key = f"SPARTA_APP_PRIVATE_KEY_{org_normalized}"
        
        org_app_id = os.environ.get(org_app_id_key, '').strip()
        org_private_key = os.environ.get(org_private_key_key, '').strip()
        
        # If both org-specific credentials found, use them
        if org_app_id and org_private_key:
            org_credentials_map[org] = {
                'app_id': org_app_id,
                'private_key': org_private_key
            }
            print(f"✓ Found org-specific credentials for {org}")
        # Otherwise, will use default credentials (no entry in map)
    
    return org_credentials_map


def generate_tokens(
    orgs: List[str],
    app_id: str,
    private_key: str,
    fallback_token: Optional[str] = None,
    org_credentials_map: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, str]:
    """Generate tokens for organizations."""
    print(f"\n{'='*60}")
    print("Generating GitHub App tokens")
    print(f"{'='*60}")
    
    if org_credentials_map:
        orgs_with_custom = [org for org in orgs if org in org_credentials_map]
        orgs_with_default = [org for org in orgs if org not in org_credentials_map]
        if orgs_with_custom:
            print(f"Using org-specific credentials for: {', '.join(orgs_with_custom)}")
        if orgs_with_default:
            print(f"Using default credentials for: {', '.join(orgs_with_default)}")
    
    token_map = generate_tokens_for_orgs(
        orgs, app_id, private_key, fallback_token, org_credentials_map
    )
    
    if not token_map:
        raise RuntimeError("Failed to generate tokens for any organization")
    
    print(f"✓ Generated tokens for {len(token_map)} organization(s)")
    return token_map


def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(description='Orchestrate organization vulnerability scanning')
    parser.add_argument('--orgs', type=str, help='Comma-separated list of organizations (defaults to GITHUB_ORG/GITHUB_ORGS or repository owner)')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for parallel processing (default: 100)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum retry attempts (default: 3)')
    parser.add_argument('--app-id', type=str, help='GitHub App ID (defaults to SPARTA_APP_ID env var)')
    parser.add_argument('--app-private-key', type=str, help='GitHub App private key (defaults to SPARTA_APP_PRIVATE_KEY env var)')
    parser.add_argument('--skip-commit', action='store_true', help='Skip committing results')
    parser.add_argument('--skip-aggregate', action='store_true', help='Skip aggregation (for testing)')
    
    args = parser.parse_args()
    
    # Get repository owner from environment
    repository_owner = os.environ.get('GITHUB_REPOSITORY', '').split('/')[0] if os.environ.get('GITHUB_REPOSITORY') else None
    
    # Parse organizations
    try:
        orgs = parse_orgs(args.orgs, repository_owner)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("Sparta - Organization Vulnerability Scan")
    print(f"{'='*60}")
    print(f"Organizations: {', '.join(orgs)}")
    print(f"Mode: {detect_scan_mode(orgs)}")
    print(f"Batch size: {args.batch_size}")
    print(f"Max retries: {args.max_retries}")
    print(f"{'='*60}\n")
    
    # Get default GitHub App credentials
    app_id = args.app_id or os.environ.get('SPARTA_APP_ID', '')
    private_key = args.app_private_key or os.environ.get('SPARTA_APP_PRIVATE_KEY', '')
    
    if not app_id or not private_key:
        print("Error: GitHub App credentials not provided")
        print("  Set SPARTA_APP_ID and SPARTA_APP_PRIVATE_KEY environment variables")
        print("  Or provide --app-id and --app-private-key arguments")
        print("  For per-org credentials, use SPARTA_APP_ID_<ORG> and SPARTA_APP_PRIVATE_KEY_<ORG>")
        sys.exit(1)
    
    # Parse per-org credentials from environment
    org_credentials_map = parse_org_credentials(orgs, app_id, private_key)
    
    # Generate base token for repository owner (fallback)
    fallback_token = os.environ.get('GITHUB_APP_TOKEN', '')
    
    # Generate tokens for all orgs
    try:
        token_map = generate_tokens(orgs, app_id, private_key, fallback_token, org_credentials_map)
    except Exception as e:
        print(f"Error generating tokens: {e}")
        sys.exit(1)
    
    # Set environment variables for get_repos
    os.environ['GITHUB_APP_TOKEN'] = fallback_token or list(token_map.values())[0]
    os.environ['GITHUB_APP_TOKEN_MAP'] = json.dumps(token_map)
    
    if len(orgs) > 1:
        os.environ['GITHUB_ORGS'] = ','.join(orgs)
        if 'GITHUB_ORG' in os.environ:
            del os.environ['GITHUB_ORG']
    else:
        os.environ['GITHUB_ORG'] = orgs[0]
        if 'GITHUB_ORGS' in os.environ:
            del os.environ['GITHUB_ORGS']
    
    # Get repositories
    print(f"\n{'='*60}")
    print("Getting organization repositories")
    print(f"{'='*60}\n")
    
    try:
        # Import and call get_repos
        import get_repos
        get_repos.main()
    except Exception as e:
        print(f"Error getting repositories: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Check if repos.json was created
    repos_file = Path('repos.json')
    if not repos_file.exists():
        print("Error: repos.json was not created")
        sys.exit(1)
    
    # Detect batching needs
    batch_needed = needs_batching(repos_file, threshold=500)
    
    # Handle batching if needed
    if batch_needed:
        print(f"\n{'='*60}")
        print("Batching enabled (large organization detected)")
        print(f"{'='*60}\n")
        
        # Set batch size
        os.environ['BATCH_SIZE'] = str(args.batch_size)
        
        # Import and run batch_repos to create batch files
        try:
            import batch_repos
            batch_repos.main()
        except Exception as e:
            print(f"Error creating batches: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # For batching, we'll process batches sequentially
        # (For true parallel execution, use GitHub Actions matrix strategy)
        batch_file = Path('repo-batches.json')
        if batch_file.exists():
            with open(batch_file, 'r') as f:
                batches = json.load(f)
            
            print(f"Processing {len(batches)} batch(es) sequentially...\n")
            
            # Process each batch
            for batch in batches:
                batch_id = batch.get('batch_id', 'unknown')
                org_name = batch.get('org', '')
                batch_repos = batch.get('repos', [])
                
                print(f"\n{'='*60}")
                print(f"Processing batch: {batch_id}")
                print(f"Organization: {org_name}")
                print(f"Repositories: {len(batch_repos)}")
                print(f"{'='*60}\n")
                
                # Create temporary repos.json for this batch
                with open('repos.json', 'w') as f:
                    json.dump(batch_repos, f, indent=2)
                
                # Set org environment for this batch
                if org_name:
                    os.environ['GITHUB_ORG'] = org_name
                    if 'GITHUB_ORGS' in os.environ:
                        del os.environ['GITHUB_ORGS']
                
                # Scan this batch
                try:
                    import scan_repos
                    scan_repos.main()
                except Exception as e:
                    print(f"Error scanning batch {batch_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue with next batch instead of failing completely
                    continue
            
            # Restore original repos.json (for commit-results)
            # Re-run get_repos to restore full repos.json
            try:
                import get_repos
                get_repos.main()
            except Exception as e:
                print(f"Warning: Could not restore repos.json: {e}")
        
        # Skip the regular scan since we already scanned batches
        print(f"\n{'='*60}")
        print("Batch scanning complete")
        print(f"{'='*60}\n")
    
    # Set max retries
    os.environ['MAX_RETRIES'] = str(args.max_retries)
    
    # Run scans (only if not already done via batching)
    if not batch_needed:
        print(f"\n{'='*60}")
        print("Scanning repositories")
        print(f"{'='*60}\n")
        
        try:
            # Import and call scan_repos
            import scan_repos
            scan_repos.main()
        except Exception as e:
            print(f"Error during scanning: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Commit results
    if not args.skip_commit:
        print(f"\n{'='*60}")
        print("Committing scan results")
        print(f"{'='*60}\n")
        
        try:
            # Import and call commit_results
            import commit_results
            commit_results.main()
        except Exception as e:
            print(f"Error committing results: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print("Scan orchestration complete!")
    print(f"{'='*60}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

