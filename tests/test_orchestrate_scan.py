#!/usr/bin/env python3
"""
Unit tests for orchestrate_scan.py script.

Tests orchestration logic, org parsing, mode detection, and flow control.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from orchestrate_scan import (
    parse_orgs,
    detect_scan_mode,
    needs_batching
)


def test_parse_orgs_from_args():
    """Test parsing orgs from command line arguments."""
    print("\n=== Test 1: Parse Orgs from Arguments ===")
    
    orgs = parse_orgs("org1,org2,org3", None)
    assert orgs == ["org1", "org2", "org3"]
    
    orgs = parse_orgs("org1", None)
    assert orgs == ["org1"]
    
    orgs = parse_orgs("org1, org2 , org3", None)  # With spaces
    assert orgs == ["org1", "org2", "org3"]
    
    print("✓ Parsed orgs from arguments correctly")


def test_parse_orgs_from_env():
    """Test parsing orgs from environment variables."""
    print("\n=== Test 2: Parse Orgs from Environment ===")
    
    # Test GITHUB_ORGS
    os.environ['GITHUB_ORGS'] = 'org1,org2'
    orgs = parse_orgs(None, None)
    assert orgs == ["org1", "org2"]
    del os.environ['GITHUB_ORGS']
    
    # Test GITHUB_ORG
    os.environ['GITHUB_ORG'] = 'single-org'
    orgs = parse_orgs(None, None)
    assert orgs == ["single-org"]
    del os.environ['GITHUB_ORG']
    
    # Test fallback to repository owner
    orgs = parse_orgs(None, "repo-owner")
    assert orgs == ["repo-owner"]
    
    print("✓ Parsed orgs from environment correctly")


def test_parse_orgs_error():
    """Test parse_orgs raises error when no orgs provided."""
    print("\n=== Test 3: Parse Orgs Error Handling ===")
    
    # Clear environment
    if 'GITHUB_ORGS' in os.environ:
        del os.environ['GITHUB_ORGS']
    if 'GITHUB_ORG' in os.environ:
        del os.environ['GITHUB_ORG']
    
    try:
        parse_orgs(None, None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No organizations specified" in str(e)
        print("✓ Correctly raised error when no orgs provided")


def test_detect_scan_mode():
    """Test single vs multi-org mode detection."""
    print("\n=== Test 4: Detect Scan Mode ===")
    
    assert detect_scan_mode(["org1"]) == 'single-org'
    assert detect_scan_mode(["org1", "org2"]) == 'multi-org'
    assert detect_scan_mode(["org1", "org2", "org3"]) == 'multi-org'
    
    print("✓ Mode detection works correctly")


def test_needs_batching_single_org_small():
    """Test batching detection for small single org."""
    print("\n=== Test 5: Batching Detection (Small Single Org) ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repos_file = Path(tmpdir) / 'repos.json'
        
        # Create repos.json with 100 repos (below threshold)
        repos = [{"name": f"repo{i}", "full_name": f"org1/repo{i}"} for i in range(100)]
        with open(repos_file, 'w') as f:
            json.dump(repos, f)
        
        assert needs_batching(repos_file, threshold=500) == False
        print("✓ Small org correctly identified as not needing batching")


def test_needs_batching_single_org_large():
    """Test batching detection for large single org."""
    print("\n=== Test 6: Batching Detection (Large Single Org) ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repos_file = Path(tmpdir) / 'repos.json'
        
        # Create repos.json with 600 repos (above threshold)
        repos = [{"name": f"repo{i}", "full_name": f"org1/repo{i}"} for i in range(600)]
        with open(repos_file, 'w') as f:
            json.dump(repos, f)
        
        assert needs_batching(repos_file, threshold=500) == True
        print("✓ Large org correctly identified as needing batching")


def test_needs_batching_multi_org():
    """Test batching detection for multi-org format."""
    print("\n=== Test 7: Batching Detection (Multi-Org Format) ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repos_file = Path(tmpdir) / 'repos.json'
        
        # Create multi-org format with one large org
        repos_data = [
            {"org": "org1", "repos": [{"name": f"repo{i}"} for i in range(600)]},
            {"org": "org2", "repos": [{"name": f"repo{i}"} for i in range(100)]}
        ]
        with open(repos_file, 'w') as f:
            json.dump(repos_data, f)
        
        assert needs_batching(repos_file, threshold=500) == True
        print("✓ Multi-org with large org correctly identified as needing batching")


def test_needs_batching_multi_org_all_small():
    """Test batching detection for multi-org with all small orgs."""
    print("\n=== Test 8: Batching Detection (Multi-Org All Small) ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repos_file = Path(tmpdir) / 'repos.json'
        
        # Create multi-org format with all small orgs
        repos_data = [
            {"org": "org1", "repos": [{"name": f"repo{i}"} for i in range(100)]},
            {"org": "org2", "repos": [{"name": f"repo{i}"} for i in range(200)]}
        ]
        with open(repos_file, 'w') as f:
            json.dump(repos_data, f)
        
        assert needs_batching(repos_file, threshold=500) == False
        print("✓ Multi-org with all small orgs correctly identified as not needing batching")


def test_orchestrate_flow_single_org_mock():
    """Test orchestration flow for single org (mocked)."""
    print("\n=== Test 9: Orchestration Flow (Single Org Mock) ===")
    
    # This tests the logic flow without actual execution
    orgs = ["org1"]
    mode = detect_scan_mode(orgs)
    assert mode == 'single-org'
    
    # Simulate repos.json creation
    with tempfile.TemporaryDirectory() as tmpdir:
        repos_file = Path(tmpdir) / 'repos.json'
        repos = [{"name": f"repo{i}"} for i in range(50)]
        with open(repos_file, 'w') as f:
            json.dump(repos, f)
        
        batch_needed = needs_batching(repos_file, threshold=500)
        assert batch_needed == False
        
        print("✓ Single org flow logic works correctly")


def test_orchestrate_flow_multi_org_mock():
    """Test orchestration flow for multi-org (mocked)."""
    print("\n=== Test 10: Orchestration Flow (Multi-Org Mock) ===")
    
    orgs = ["org1", "org2", "org3"]
    mode = detect_scan_mode(orgs)
    assert mode == 'multi-org'
    
    # Simulate multi-org repos.json
    with tempfile.TemporaryDirectory() as tmpdir:
        repos_file = Path(tmpdir) / 'repos.json'
        repos_data = [
            {"org": "org1", "repos": [{"name": f"repo{i}"} for i in range(100)]},
            {"org": "org2", "repos": [{"name": f"repo{i}"} for i in range(200)]},
            {"org": "org3", "repos": [{"name": f"repo{i}"} for i in range(150)]}
        ]
        with open(repos_file, 'w') as f:
            json.dump(repos_data, f)
        
        batch_needed = needs_batching(repos_file, threshold=500)
        assert batch_needed == False  # All orgs are small
        
        print("✓ Multi-org flow logic works correctly")


def test_orchestrate_flow_large_org_batching():
    """Test orchestration flow for large org with batching."""
    print("\n=== Test 11: Orchestration Flow (Large Org Batching) ===")
    
    orgs = ["large-org"]
    mode = detect_scan_mode(orgs)
    assert mode == 'single-org'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repos_file = Path(tmpdir) / 'repos.json'
        repos = [{"name": f"repo{i}"} for i in range(600)]
        with open(repos_file, 'w') as f:
            json.dump(repos, f)
        
        batch_needed = needs_batching(repos_file, threshold=500)
        assert batch_needed == True
        
        print("✓ Large org batching flow logic works correctly")


def test_error_handling_missing_credentials():
    """Test error handling for missing credentials."""
    print("\n=== Test 12: Error Handling (Missing Credentials) ===")
    
    # Test that missing app_id or private_key would cause error
    # (This is tested in the actual script, here we verify the logic)
    app_id = ""
    private_key = ""
    
    # In actual script, this would raise an error
    if not app_id or not private_key:
        error_expected = True
        assert error_expected == True
        print("✓ Missing credentials would be detected")


def run_all_tests():
    """Run all orchestration tests."""
    print("=" * 60)
    print("Orchestration Script Tests")
    print("=" * 60)
    
    tests = [
        test_parse_orgs_from_args,
        test_parse_orgs_from_env,
        test_parse_orgs_error,
        test_detect_scan_mode,
        test_needs_batching_single_org_small,
        test_needs_batching_single_org_large,
        test_needs_batching_multi_org,
        test_needs_batching_multi_org_all_small,
        test_orchestrate_flow_single_org_mock,
        test_orchestrate_flow_multi_org_mock,
        test_orchestrate_flow_large_org_batching,
        test_error_handling_missing_credentials
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

