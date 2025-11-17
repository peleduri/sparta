#!/usr/bin/env python3
"""
Integration tests simulating full workflow scenarios.

These tests simulate end-to-end scenarios without requiring actual GitHub API access.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def create_mock_repos_json(multi_org=True, orgs=None):
    """Create a mock repos.json file."""
    if orgs is None:
        orgs = ["org1", "org2"]
    
    if multi_org:
        data = []
        for org in orgs:
            data.append({
                "org": org,
                "repos": [
                    {"name": f"{org}-repo1", "full_name": f"{org}/{org}-repo1", "default_branch": "main"},
                    {"name": f"{org}-repo2", "full_name": f"{org}/{org}-repo2", "default_branch": "main"}
                ]
            })
    else:
        # Single org format
        org = orgs[0] if orgs else "org1"
        data = [
            {"name": f"{org}-repo1", "full_name": f"{org}/{org}-repo1", "default_branch": "main"},
            {"name": f"{org}-repo2", "full_name": f"{org}/{org}-repo2", "default_branch": "main"}
        ]
    
    return json.dumps(data, indent=2)


def test_scenario_1_all_orgs_have_tokens():
    """Scenario 1: All organizations have tokens in the map."""
    print("\n=== Scenario 1: All Orgs Have Tokens ===")
    
    token_map = {
        "org1": "token_org1_12345",
        "org2": "token_org2_67890"
    }
    token_map_json = json.dumps(token_map)
    
    # Simulate environment
    os.environ['GITHUB_APP_TOKEN'] = "default_token"
    os.environ['GITHUB_APP_TOKEN_MAP'] = token_map_json
    os.environ['GITHUB_ORGS'] = "org1,org2"
    
    # Test token retrieval
    from get_repos import get_token_for_org
    
    assert get_token_for_org("org1", token_map, "default_token") == "token_org1_12345"
    assert get_token_for_org("org2", token_map, "default_token") == "token_org2_67890"
    
    print("✓ All orgs successfully retrieve their tokens")
    print(f"  - org1: token_org1_12345")
    print(f"  - org2: token_org2_67890")


def test_scenario_2_some_orgs_missing_tokens():
    """Scenario 2: Some organizations missing from token map."""
    print("\n=== Scenario 2: Some Orgs Missing Tokens ===")
    
    token_map = {
        "org1": "token_org1_12345"
        # org2 missing
    }
    token_map_json = json.dumps(token_map)
    
    from get_repos import get_token_for_org
    
    # org1 should get its token
    assert get_token_for_org("org1", token_map, "default_token") == "token_org1_12345"
    
    # org2 should fall back to default
    assert get_token_for_org("org2", token_map, "default_token") == "default_token"
    
    print("✓ Missing orgs fall back to default token")
    print(f"  - org1: token_org1_12345 (from map)")
    print(f"  - org2: default_token (fallback)")


def test_scenario_3_no_token_map():
    """Scenario 3: No token map provided (backward compatibility)."""
    print("\n=== Scenario 3: No Token Map (Backward Compat) ===")
    
    token_map = None
    default_token = "default_token"
    
    from get_repos import get_token_for_org
    
    # All orgs should use default token
    assert get_token_for_org("org1", token_map, default_token) == default_token
    assert get_token_for_org("org2", token_map, default_token) == default_token
    
    print("✓ Backward compatibility: all orgs use default token")
    print(f"  - org1: {default_token}")
    print(f"  - org2: {default_token}")


def test_scenario_4_invalid_token_map_json():
    """Scenario 4: Invalid JSON in token map."""
    print("\n=== Scenario 4: Invalid Token Map JSON ===")
    
    invalid_json = '{"org1": "token1"'  # Missing closing brace
    
    try:
        token_map = json.loads(invalid_json)
        assert False, "Should raise JSONDecodeError"
    except json.JSONDecodeError:
        # Should fall back to default token
        token_map = {}
        default_token = "default_token"
        
        from get_repos import get_token_for_org
        assert get_token_for_org("org1", token_map, default_token) == default_token
        
        print("✓ Invalid JSON handled gracefully, falls back to default token")


def test_scenario_5_multi_org_repos_json_format():
    """Scenario 5: Multi-org repos.json format with token map."""
    print("\n=== Scenario 5: Multi-Org Repos JSON Format ===")
    
    repos_data = json.loads(create_mock_repos_json(multi_org=True, orgs=["org1", "org2"]))
    
    # Verify format
    assert isinstance(repos_data, list)
    assert len(repos_data) == 2
    assert repos_data[0]["org"] == "org1"
    assert repos_data[1]["org"] == "org2"
    assert "repos" in repos_data[0]
    
    # Simulate token map
    token_map = {
        "org1": "token_org1",
        "org2": "token_org2"
    }
    
    # Simulate processing each org
    for org_data in repos_data:
        org_name = org_data["org"]
        from get_repos import get_token_for_org
        token = get_token_for_org(org_name, token_map, "default")
        assert token == f"token_{org_name}"
        print(f"  ✓ {org_name}: {len(org_data['repos'])} repos, token: {token[:10]}...")
    
    print("✓ Multi-org format correctly processed with token map")


def test_scenario_6_single_org_backward_compat():
    """Scenario 6: Single org mode (backward compatibility)."""
    print("\n=== Scenario 6: Single Org Mode (Backward Compat) ===")
    
    repos_data = json.loads(create_mock_repos_json(multi_org=False, orgs=["org1"]))
    
    # Verify single org format
    assert isinstance(repos_data, list)
    assert "org" not in repos_data[0]  # No org field in single-org format
    
    # Should work without token map
    token_map = None
    default_token = "default_token"
    
    from get_repos import get_token_for_org
    token = get_token_for_org("org1", token_map, default_token)
    assert token == default_token
    
    print("✓ Single org mode works without token map")
    print(f"  - Uses default token: {default_token}")


def test_scenario_7_large_org_batching():
    """Scenario 7: Large org with batching and token map."""
    print("\n=== Scenario 7: Large Org with Batching ===")
    
    # Simulate large org with 600 repos
    large_org_repos = [
        {"name": f"repo{i}", "full_name": f"org1/repo{i}", "default_branch": "main"}
        for i in range(600)
    ]
    
    repos_data = [{"org": "org1", "repos": large_org_repos}]
    
    # Token map
    token_map = {"org1": "token_org1_large"}
    
    # Simulate batching (100 repos per batch)
    batch_size = 100
    batches = []
    for i in range(0, len(large_org_repos), batch_size):
        batches.append(large_org_repos[i:i + batch_size])
    
    assert len(batches) == 6  # 600 repos / 100 = 6 batches
    
    from get_repos import get_token_for_org
    token = get_token_for_org("org1", token_map, "default")
    assert token == "token_org1_large"
    
    print(f"✓ Large org processed: {len(large_org_repos)} repos in {len(batches)} batches")
    print(f"  - Token: {token[:15]}...")


def test_scenario_8_mixed_success_failure():
    """Scenario 8: Mixed success and failure (some orgs work, some don't)."""
    print("\n=== Scenario 8: Mixed Success/Failure ===")
    
    orgs = ["org1", "org2", "org3", "org4"]
    token_map = {
        "org1": "token_org1",  # Has token
        "org3": "token_org3"   # Has token
        # org2 and org4 missing
    }
    default_token = "default_token"
    
    from get_repos import get_token_for_org
    
    results = {}
    for org in orgs:
        token = get_token_for_org(org, token_map, default_token)
        results[org] = token
        status = "✓" if token != default_token else "⚠ (fallback)"
        print(f"  {status} {org}: {token[:15]}...")
    
    # Verify
    assert results["org1"] == "token_org1"
    assert results["org2"] == default_token
    assert results["org3"] == "token_org3"
    assert results["org4"] == default_token
    
    print("✓ Mixed scenario handled correctly")


def run_all_scenarios():
    """Run all integration test scenarios."""
    print("=" * 60)
    print("Integration Tests: Multi-Org Token Scenarios")
    print("=" * 60)
    
    scenarios = [
        test_scenario_1_all_orgs_have_tokens,
        test_scenario_2_some_orgs_missing_tokens,
        test_scenario_3_no_token_map,
        test_scenario_4_invalid_token_map_json,
        test_scenario_5_multi_org_repos_json_format,
        test_scenario_6_single_org_backward_compat,
        test_scenario_7_large_org_batching,
        test_scenario_8_mixed_success_failure
    ]
    
    passed = 0
    failed = 0
    
    for scenario in scenarios:
        try:
            scenario()
            passed += 1
        except AssertionError as e:
            print(f"✗ {scenario.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {scenario.__name__} error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Scenario Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_scenarios()
    sys.exit(0 if success else 1)

