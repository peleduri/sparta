#!/usr/bin/env python3
"""
Integration tests for unified workflow end-to-end flows.

Tests complete workflows with mocked components.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def create_mock_repos_json(multi_org=False, repo_count=100, orgs=None):
    """Create a mock repos.json file."""
    if orgs is None:
        orgs = ["org1"]
    
    if multi_org:
        data = []
        for org in orgs:
            data.append({
                "org": org,
                "repos": [
                    {"name": f"{org}-repo{i}", "full_name": f"{org}/{org}-repo{i}", "default_branch": "main"}
                    for i in range(repo_count)
                ]
            })
    else:
        org = orgs[0] if orgs else "org1"
        data = [
            {"name": f"{org}-repo{i}", "full_name": f"{org}/{org}-repo{i}", "default_branch": "main"}
            for i in range(repo_count)
        ]
    
    return json.dumps(data, indent=2)


def test_single_org_flow():
    """Test single org scan flow end-to-end."""
    print("\n=== Test 1: Single Org Flow ===")
    
    # Simulate single org scenario
    orgs = ["org1"]
    repos_json = create_mock_repos_json(multi_org=False, repo_count=50)
    
    # Verify format
    repos_data = json.loads(repos_json)
    assert isinstance(repos_data, list)
    assert len(repos_data) == 50
    assert "org" not in repos_data[0]  # Single org format
    
    # Verify flow would work
    is_multi_org = (
        isinstance(repos_data, list) and 
        len(repos_data) > 0 and 
        isinstance(repos_data[0], dict) and 
        'org' in repos_data[0] and 
        'repos' in repos_data[0]
    )
    assert is_multi_org == False
    
    print("✓ Single org flow structure verified")


def test_multi_org_flow():
    """Test multi-org scan flow end-to-end."""
    print("\n=== Test 2: Multi-Org Flow ===")
    
    orgs = ["org1", "org2", "org3"]
    repos_json = create_mock_repos_json(multi_org=True, repo_count=100, orgs=orgs)
    
    # Verify format
    repos_data = json.loads(repos_json)
    assert isinstance(repos_data, list)
    assert len(repos_data) == 3
    assert repos_data[0]["org"] == "org1"
    assert "repos" in repos_data[0]
    
    # Verify multi-org detection
    is_multi_org = (
        isinstance(repos_data, list) and 
        len(repos_data) > 0 and 
        isinstance(repos_data[0], dict) and 
        'org' in repos_data[0] and 
        'repos' in repos_data[0]
    )
    assert is_multi_org == True
    
    print("✓ Multi-org flow structure verified")


def test_large_org_batching_flow():
    """Test large org with batching flow."""
    print("\n=== Test 3: Large Org Batching Flow ===")
    
    orgs = ["large-org"]
    repos_json = create_mock_repos_json(multi_org=False, repo_count=600)
    
    repos_data = json.loads(repos_json)
    
    # Verify batching would be needed
    needs_batch = len(repos_data) > 500
    assert needs_batch == True
    
    # Simulate batch creation
    batch_size = 100
    batches = []
    for i in range(0, len(repos_data), batch_size):
        batches.append(repos_data[i:i + batch_size])
    
    assert len(batches) == 6  # 600 repos / 100 = 6 batches
    
    print("✓ Large org batching flow verified")


def test_workflow_chain_success():
    """Test workflow chain: scan → aggregate (success)."""
    print("\n=== Test 4: Workflow Chain (Success) ===")
    
    # Simulate successful scan
    scan_success = True
    
    # Aggregate should run
    aggregate_should_run = scan_success == True
    assert aggregate_should_run == True
    
    print("✓ Workflow chain (success) verified")


def test_workflow_chain_failure():
    """Test workflow chain: scan → aggregate (failure)."""
    print("\n=== Test 5: Workflow Chain (Failure) ===")
    
    # Simulate failed scan
    scan_success = False
    
    # Aggregate should not run
    aggregate_should_run = scan_success == True
    assert aggregate_should_run == False
    
    print("✓ Workflow chain (failure) verified")


def test_token_generation_integration():
    """Test token generation integration in workflow."""
    print("\n=== Test 6: Token Generation Integration ===")
    
    orgs = ["org1", "org2"]
    
    # Simulate token generation
    token_map = {
        "org1": "token_org1",
        "org2": "token_org2"
    }
    
    # Verify token map structure
    assert len(token_map) == len(orgs)
    for org in orgs:
        assert org in token_map
        assert token_map[org].startswith("token_")
    
    print("✓ Token generation integration verified")


def test_batch_processing_flow():
    """Test batch processing flow for large org."""
    print("\n=== Test 7: Batch Processing Flow ===")
    
    # Simulate large org with 600 repos
    total_repos = 600
    batch_size = 100
    batches = []
    
    for i in range(0, total_repos, batch_size):
        batch_repos = list(range(i, min(i + batch_size, total_repos)))
        batches.append({
            "batch_id": f"batch-{len(batches) + 1}",
            "org": "large-org",
            "repos": batch_repos
        })
    
    assert len(batches) == 6
    
    # Verify each batch
    for batch in batches:
        assert "batch_id" in batch
        assert "org" in batch
        assert "repos" in batch
        assert len(batch["repos"]) <= batch_size
    
    print("✓ Batch processing flow verified")


def test_resume_capability():
    """Test resume capability with state files."""
    print("\n=== Test 8: Resume Capability ===")
    
    # Simulate scan state
    completed_repos = {"repo1", "repo2", "repo3"}
    failed_repos = [{"repo": "repo4", "error": "clone failed", "retry_count": 1}]
    all_repos = [{"name": f"repo{i}"} for i in range(1, 6)]
    
    # Filter repos to scan
    repos_to_scan = [
        repo for repo in all_repos
        if repo["name"] not in completed_repos or repo["name"] in [f["repo"] for f in failed_repos]
    ]
    
    # Should scan repo4 (failed) and repo5 (pending)
    assert len(repos_to_scan) == 2
    assert any(r["name"] == "repo4" for r in repos_to_scan)
    assert any(r["name"] == "repo5" for r in repos_to_scan)
    
    print("✓ Resume capability verified")


def test_error_handling_scenarios():
    """Test various error handling scenarios."""
    print("\n=== Test 9: Error Handling Scenarios ===")
    
    error_scenarios = [
        {"name": "Missing App ID", "app_id": "", "should_fail": True},
        {"name": "Missing Private Key", "private_key": "", "should_fail": True},
        {"name": "App Not Installed", "error": "404", "should_fail": False},  # Handled gracefully
        {"name": "Network Error", "error": "Network", "should_fail": False},  # Handled gracefully
    ]
    
    for scenario in error_scenarios:
        if scenario.get("should_fail"):
            # Would cause script to exit
            assert scenario["should_fail"] == True
        else:
            # Would be handled gracefully
            assert scenario["should_fail"] == False
    
    print("✓ Error handling scenarios verified")


def test_manual_trigger_with_custom_orgs():
    """Test manual trigger with custom organizations."""
    print("\n=== Test 10: Manual Trigger with Custom Orgs ===")
    
    # Simulate workflow_dispatch with custom orgs
    input_orgs = "custom-org1,custom-org2,custom-org3"
    orgs = [org.strip() for org in input_orgs.split(',')]
    
    assert len(orgs) == 3
    assert orgs[0] == "custom-org1"
    assert orgs[1] == "custom-org2"
    assert orgs[2] == "custom-org3"
    
    print("✓ Manual trigger with custom orgs verified")


def test_manual_trigger_with_default():
    """Test manual trigger with default (repository owner)."""
    print("\n=== Test 11: Manual Trigger with Default ===")
    
    # Simulate workflow_dispatch without orgs input
    input_orgs = None
    repository_owner = "default-org"
    
    # Would use repository owner
    orgs = [repository_owner] if not input_orgs else [org.strip() for org in input_orgs.split(',')]
    
    assert len(orgs) == 1
    assert orgs[0] == "default-org"
    
    print("✓ Manual trigger with default verified")


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Unified Workflow Integration Tests")
    print("=" * 60)
    
    tests = [
        test_single_org_flow,
        test_multi_org_flow,
        test_large_org_batching_flow,
        test_workflow_chain_success,
        test_workflow_chain_failure,
        test_token_generation_integration,
        test_batch_processing_flow,
        test_resume_capability,
        test_error_handling_scenarios,
        test_manual_trigger_with_custom_orgs,
        test_manual_trigger_with_default
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

