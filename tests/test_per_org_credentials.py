#!/usr/bin/env python3
"""
Unit tests for per-organization GitHub App credentials support.

Tests credential parsing, normalization, and token generation with per-org credentials.
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from orchestrate_scan import (
    normalize_org_name_for_secret,
    parse_org_credentials
)
from token_manager import (
    generate_tokens_for_orgs_with_credentials,
    generate_tokens_for_orgs
)


def test_normalize_org_name_for_secret():
    """Test org name normalization for secret names."""
    print("\n=== Test 1: Normalize Org Name for Secret ===")
    
    assert normalize_org_name_for_secret("my-org") == "MY_ORG"
    assert normalize_org_name_for_secret("acme-corp") == "ACME_CORP"
    assert normalize_org_name_for_secret("my_org") == "MY_ORG"
    assert normalize_org_name_for_secret("MyOrg") == "MYORG"
    assert normalize_org_name_for_secret("org1") == "ORG1"
    
    print("✓ Org name normalization works correctly")


def test_parse_org_credentials_all_default():
    """Test parsing when only default credentials exist."""
    print("\n=== Test 2: Parse Org Credentials (All Default) ===")
    
    # Clear environment
    for key in list(os.environ.keys()):
        if key.startswith('SPARTA_APP_ID_') or key.startswith('SPARTA_APP_PRIVATE_KEY_'):
            del os.environ[key]
    
    orgs = ["org1", "org2"]
    default_app_id = "default_app_id"
    default_private_key = "default_private_key"
    
    creds_map = parse_org_credentials(orgs, default_app_id, default_private_key)
    
    assert len(creds_map) == 0  # No per-org credentials found
    print("✓ Correctly detected no per-org credentials")


def test_parse_org_credentials_some_per_org():
    """Test parsing when some orgs have per-org credentials."""
    print("\n=== Test 3: Parse Org Credentials (Some Per-Org) ===")
    
    # Clear environment
    for key in list(os.environ.keys()):
        if key.startswith('SPARTA_APP_ID_') or key.startswith('SPARTA_APP_PRIVATE_KEY_'):
            del os.environ[key]
    
    # Set per-org credentials for org1
    os.environ['SPARTA_APP_ID_ORG1'] = 'org1_app_id'
    os.environ['SPARTA_APP_PRIVATE_KEY_ORG1'] = 'org1_private_key'
    
    orgs = ["org1", "org2"]
    default_app_id = "default_app_id"
    default_private_key = "default_private_key"
    
    creds_map = parse_org_credentials(orgs, default_app_id, default_private_key)
    
    assert len(creds_map) == 1
    assert "org1" in creds_map
    assert creds_map["org1"]["app_id"] == "org1_app_id"
    assert creds_map["org1"]["private_key"] == "org1_private_key"
    
    # Cleanup
    del os.environ['SPARTA_APP_ID_ORG1']
    del os.environ['SPARTA_APP_PRIVATE_KEY_ORG1']
    
    print("✓ Correctly parsed per-org credentials for org1")


def test_parse_org_credentials_with_hyphens():
    """Test parsing with org names containing hyphens."""
    print("\n=== Test 4: Parse Org Credentials (With Hyphens) ===")
    
    # Clear environment
    for key in list(os.environ.keys()):
        if key.startswith('SPARTA_APP_ID_') or key.startswith('SPARTA_APP_PRIVATE_KEY_'):
            del os.environ[key]
    
    # Set per-org credentials for my-org (normalized to MY_ORG)
    os.environ['SPARTA_APP_ID_MY_ORG'] = 'my_org_app_id'
    os.environ['SPARTA_APP_PRIVATE_KEY_MY_ORG'] = 'my_org_private_key'
    
    orgs = ["my-org"]
    default_app_id = "default_app_id"
    default_private_key = "default_private_key"
    
    creds_map = parse_org_credentials(orgs, default_app_id, default_private_key)
    
    assert len(creds_map) == 1
    assert "my-org" in creds_map
    assert creds_map["my-org"]["app_id"] == "my_org_app_id"
    assert creds_map["my-org"]["private_key"] == "my_org_private_key"
    
    # Cleanup
    del os.environ['SPARTA_APP_ID_MY_ORG']
    del os.environ['SPARTA_APP_PRIVATE_KEY_MY_ORG']
    
    print("✓ Correctly handled org names with hyphens")


def test_parse_org_credentials_partial():
    """Test parsing when only one credential (app_id or private_key) is provided."""
    print("\n=== Test 5: Parse Org Credentials (Partial) ===")
    
    # Clear environment
    for key in list(os.environ.keys()):
        if key.startswith('SPARTA_APP_ID_') or key.startswith('SPARTA_APP_PRIVATE_KEY_'):
            del os.environ[key]
    
    # Set only app_id (missing private_key)
    os.environ['SPARTA_APP_ID_ORG1'] = 'org1_app_id'
    
    orgs = ["org1"]
    default_app_id = "default_app_id"
    default_private_key = "default_private_key"
    
    creds_map = parse_org_credentials(orgs, default_app_id, default_private_key)
    
    # Should not add to map if both credentials not present
    assert len(creds_map) == 0
    
    # Cleanup
    del os.environ['SPARTA_APP_ID_ORG1']
    
    print("✓ Correctly ignored partial credentials")


def test_generate_tokens_with_per_org_credentials():
    """Test token generation with per-org credentials."""
    print("\n=== Test 6: Generate Tokens (Per-Org Credentials) ===")
    
    orgs = ["org1", "org2"]
    org_credentials_map = {
        "org1": {
            "app_id": "org1_app_id",
            "private_key": "org1_private_key"
        }
    }
    default_app_id = "default_app_id"
    default_private_key = "default_private_key"
    
    # Mock JWT generation and token retrieval
    mock_jwt_org1 = "mock_jwt_org1"
    mock_jwt_default = "mock_jwt_default"
    mock_token_org1 = "ghs_token_org1"
    mock_token_org2 = "ghs_token_org2"
    
    def mock_generate_jwt(app_id, private_key):
        if app_id == "org1_app_id":
            return mock_jwt_org1
        return mock_jwt_default
    
    def mock_get_token(jwt, org):
        if jwt == mock_jwt_org1 and org == "org1":
            return mock_token_org1, None
        elif jwt == mock_jwt_default and org == "org2":
            return mock_token_org2, None
        return None, "Error"
    
    with patch('token_manager.generate_jwt', side_effect=mock_generate_jwt), \
         patch('token_manager.get_installation_token', side_effect=mock_get_token):
        token_map = generate_tokens_for_orgs_with_credentials(
            orgs, org_credentials_map, default_app_id, default_private_key
        )
        
        assert len(token_map) == 2
        assert token_map["org1"] == mock_token_org1
        assert token_map["org2"] == mock_token_org2
    
    print("✓ Token generation with per-org credentials works correctly")


def test_generate_tokens_fallback_to_default():
    """Test token generation falls back to default credentials."""
    print("\n=== Test 7: Generate Tokens (Fallback to Default) ===")
    
    orgs = ["org1", "org2"]
    org_credentials_map = {}  # No per-org credentials
    default_app_id = "default_app_id"
    default_private_key = "default_private_key"
    
    mock_jwt = "mock_jwt"
    mock_token_org1 = "ghs_token_org1"
    mock_token_org2 = "ghs_token_org2"
    
    def mock_generate_jwt(app_id, private_key):
        return mock_jwt
    
    def mock_get_token(jwt, org):
        if org == "org1":
            return mock_token_org1, None
        elif org == "org2":
            return mock_token_org2, None
        return None, "Error"
    
    with patch('token_manager.generate_jwt', side_effect=mock_generate_jwt), \
         patch('token_manager.get_installation_token', side_effect=mock_get_token):
        token_map = generate_tokens_for_orgs_with_credentials(
            orgs, org_credentials_map, default_app_id, default_private_key
        )
        
        assert len(token_map) == 2
        assert token_map["org1"] == mock_token_org1
        assert token_map["org2"] == mock_token_org2
    
    print("✓ Fallback to default credentials works correctly")


def test_generate_tokens_mixed_credentials():
    """Test token generation with mixed per-org and default credentials."""
    print("\n=== Test 8: Generate Tokens (Mixed Credentials) ===")
    
    orgs = ["org1", "org2", "org3"]
    org_credentials_map = {
        "org1": {
            "app_id": "org1_app_id",
            "private_key": "org1_private_key"
        },
        "org3": {
            "app_id": "org3_app_id",
            "private_key": "org3_private_key"
        }
        # org2 uses default
    }
    default_app_id = "default_app_id"
    default_private_key = "default_private_key"
    
    mock_jwt_org1 = "mock_jwt_org1"
    mock_jwt_org3 = "mock_jwt_org3"
    mock_jwt_default = "mock_jwt_default"
    
    jwt_cache = {}
    
    def mock_generate_jwt(app_id, private_key):
        if app_id not in jwt_cache:
            if app_id == "org1_app_id":
                jwt_cache[app_id] = mock_jwt_org1
            elif app_id == "org3_app_id":
                jwt_cache[app_id] = mock_jwt_org3
            else:
                jwt_cache[app_id] = mock_jwt_default
        return jwt_cache[app_id]
    
    def mock_get_token(jwt, org):
        if org == "org1" and jwt == mock_jwt_org1:
            return "ghs_token_org1", None
        elif org == "org2" and jwt == mock_jwt_default:
            return "ghs_token_org2", None
        elif org == "org3" and jwt == mock_jwt_org3:
            return "ghs_token_org3", None
        return None, "Error"
    
    with patch('token_manager.generate_jwt', side_effect=mock_generate_jwt), \
         patch('token_manager.get_installation_token', side_effect=mock_get_token):
        token_map = generate_tokens_for_orgs_with_credentials(
            orgs, org_credentials_map, default_app_id, default_private_key
        )
        
        assert len(token_map) == 3
        assert token_map["org1"] == "ghs_token_org1"
        assert token_map["org2"] == "ghs_token_org2"
        assert token_map["org3"] == "ghs_token_org3"
    
    print("✓ Mixed credentials (per-org + default) work correctly")


def run_all_tests():
    """Run all per-org credentials tests."""
    print("=" * 60)
    print("Per-Organization Credentials Tests")
    print("=" * 60)
    
    tests = [
        test_normalize_org_name_for_secret,
        test_parse_org_credentials_all_default,
        test_parse_org_credentials_some_per_org,
        test_parse_org_credentials_with_hyphens,
        test_parse_org_credentials_partial,
        test_generate_tokens_with_per_org_credentials,
        test_generate_tokens_fallback_to_default,
        test_generate_tokens_mixed_credentials
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

