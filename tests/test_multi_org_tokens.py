#!/usr/bin/env python3
"""
Local tests for multi-org token handling and scenarios.

This test suite simulates various scenarios without requiring actual GitHub App setup.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from get_repos import get_token_for_org
from scan_repos import get_token_for_org as scan_get_token_for_org


def test_token_map_parsing():
    """Test parsing of GITHUB_APP_TOKEN_MAP JSON."""
    print("\n=== Test 1: Token Map Parsing ===")
    
    token_map_json = '{"org1": "token1", "org2": "token2", "org3": "token3"}'
    token_map = json.loads(token_map_json)
    
    assert len(token_map) == 3
    assert token_map["org1"] == "token1"
    assert token_map["org2"] == "token2"
    assert token_map["org3"] == "token3"
    
    print("✓ Token map parsing works correctly")


def test_get_token_for_org():
    """Test get_token_for_org function with various scenarios."""
    print("\n=== Test 2: Get Token for Org Function ===")
    
    token_map = {"org1": "token1", "org2": "token2"}
    default_token = "default_token"
    
    # Test with token map
    assert get_token_for_org("org1", token_map, default_token) == "token1"
    assert get_token_for_org("org2", token_map, default_token) == "token2"
    
    # Test with org not in map (should use default)
    assert get_token_for_org("org3", token_map, default_token) == default_token
    
    # Test with empty token map (should use default)
    assert get_token_for_org("org1", {}, default_token) == default_token
    
    # Test with None token map (should use default)
    assert get_token_for_org("org1", None, default_token) == default_token
    
    print("✓ get_token_for_org function works correctly for all scenarios")


def test_multi_org_format_detection():
    """Test detection of multi-org vs single-org repos.json format."""
    print("\n=== Test 3: Multi-Org Format Detection ===")
    
    # Multi-org format
    multi_org_data = [
        {"org": "org1", "repos": [{"name": "repo1"}, {"name": "repo2"}]},
        {"org": "org2", "repos": [{"name": "repo3"}]}
    ]
    
    is_multi_org = (
        isinstance(multi_org_data, list) and 
        len(multi_org_data) > 0 and 
        isinstance(multi_org_data[0], dict) and 
        'org' in multi_org_data[0] and 
        'repos' in multi_org_data[0]
    )
    assert is_multi_org == True, "Should detect multi-org format"
    
    # Single-org format
    single_org_data = [
        {"name": "repo1", "full_name": "org1/repo1"},
        {"name": "repo2", "full_name": "org1/repo2"}
    ]
    
    is_multi_org = (
        isinstance(single_org_data, list) and 
        len(single_org_data) > 0 and 
        isinstance(single_org_data[0], dict) and 
        'org' in single_org_data[0] and 
        'repos' in single_org_data[0]
    )
    assert is_multi_org == False, "Should not detect single-org format as multi-org"
    
    print("✓ Multi-org format detection works correctly")


def test_token_selection_scenarios():
    """Test token selection for various scenarios."""
    print("\n=== Test 4: Token Selection Scenarios ===")
    
    scenarios = [
        {
            "name": "All orgs have tokens",
            "token_map": {"org1": "token1", "org2": "token2"},
            "org": "org1",
            "expected": "token1"
        },
        {
            "name": "Org missing from map",
            "token_map": {"org1": "token1"},
            "org": "org2",
            "expected": "default_token"
        },
        {
            "name": "Empty token map",
            "token_map": {},
            "org": "org1",
            "expected": "default_token"
        },
        {
            "name": "None token map",
            "token_map": None,
            "org": "org1",
            "expected": "default_token"
        }
    ]
    
    for scenario in scenarios:
        result = get_token_for_org(
            scenario["org"],
            scenario["token_map"],
            "default_token"
        )
        assert result == scenario["expected"], \
            f"Failed scenario: {scenario['name']}"
        print(f"  ✓ {scenario['name']}")
    
    print("✓ All token selection scenarios work correctly")


def test_error_handling_missing_tokens():
    """Test error handling when tokens are missing."""
    print("\n=== Test 5: Error Handling - Missing Tokens ===")
    
    # Simulate missing token for one org
    token_map = {"org1": "token1"}  # org2 missing
    default_token = "default_token"
    
    # org1 should get its token
    assert get_token_for_org("org1", token_map, default_token) == "token1"
    
    # org2 should fall back to default
    assert get_token_for_org("org2", token_map, default_token) == default_token
    
    print("✓ Error handling for missing tokens works correctly")


def test_backward_compatibility():
    """Test backward compatibility with single org mode."""
    print("\n=== Test 6: Backward Compatibility ===")
    
    # Simulate single org mode (no token map)
    token_map = None
    default_token = "default_token"
    
    # Should use default token
    assert get_token_for_org("org1", token_map, default_token) == default_token
    
    # Empty token map should also work
    assert get_token_for_org("org1", {}, default_token) == default_token
    
    print("✓ Backward compatibility maintained")


def test_token_map_json_parsing():
    """Test parsing token map from JSON string (as it comes from env var)."""
    print("\n=== Test 7: Token Map JSON Parsing ===")
    
    # Simulate what comes from GITHUB_APP_TOKEN_MAP env var
    token_map_json = '{"org1": "token1", "org2": "token2"}'
    
    try:
        token_map = json.loads(token_map_json)
        assert token_map["org1"] == "token1"
        assert token_map["org2"] == "token2"
        print("  ✓ Valid JSON parsing works")
    except json.JSONDecodeError:
        assert False, "Should parse valid JSON"
    
    # Test invalid JSON
    invalid_json = '{"org1": "token1"'  # Missing closing brace
    try:
        token_map = json.loads(invalid_json)
        assert False, "Should raise JSONDecodeError"
    except json.JSONDecodeError:
        print("  ✓ Invalid JSON handling works (raises error)")
    
    print("✓ Token map JSON parsing works correctly")


def test_multi_org_token_usage_flow():
    """Test the complete flow of using tokens in multi-org scenario."""
    print("\n=== Test 8: Multi-Org Token Usage Flow ===")
    
    # Simulate multi-org scenario
    orgs = ["org1", "org2", "org3"]
    token_map = {
        "org1": "token_for_org1",
        "org2": "token_for_org2",
        "org3": "token_for_org3"
    }
    default_token = "default_token"
    
    # Simulate processing each org
    for org in orgs:
        token = get_token_for_org(org, token_map, default_token)
        assert token == f"token_for_{org}", f"Should get correct token for {org}"
        print(f"  ✓ {org} uses token: {token[:10]}...")
    
    print("✓ Multi-org token usage flow works correctly")


def test_partial_token_map():
    """Test scenario where only some orgs have tokens in the map."""
    print("\n=== Test 9: Partial Token Map ===")
    
    # Some orgs have tokens, some don't
    token_map = {"org1": "token1", "org3": "token3"}  # org2 missing
    default_token = "default_token"
    orgs = ["org1", "org2", "org3"]
    
    results = {}
    for org in orgs:
        results[org] = get_token_for_org(org, token_map, default_token)
    
    assert results["org1"] == "token1"
    assert results["org2"] == default_token  # Should fall back
    assert results["org3"] == "token3"
    
    print("✓ Partial token map handling works correctly")
    print(f"  - org1: {results['org1'][:10]}... (from map)")
    print(f"  - org2: {results['org2'][:10]}... (fallback)")
    print(f"  - org3: {results['org3'][:10]}... (from map)")


def run_all_tests():
    """Run all test scenarios."""
    print("=" * 60)
    print("Local Testing: Multi-Org Token Scenarios")
    print("=" * 60)
    
    tests = [
        test_token_map_parsing,
        test_get_token_for_org,
        test_multi_org_format_detection,
        test_token_selection_scenarios,
        test_error_handling_missing_tokens,
        test_backward_compatibility,
        test_token_map_json_parsing,
        test_multi_org_token_usage_flow,
        test_partial_token_map
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
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

