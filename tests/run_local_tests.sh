#!/bin/bash
# Run all local tests for multi-org token scenarios

set -e

echo "=========================================="
echo "Running Local Tests for Multi-Org Tokens"
echo "=========================================="
echo ""

# Test 1: Unit tests for token handling
echo "1. Running unit tests..."
python3 tests/test_multi_org_tokens.py
echo ""

# Test 2: Integration scenario tests
echo "2. Running integration scenario tests..."
python3 tests/test_integration_scenarios.py
echo ""

# Test 3: Test token map parsing with actual JSON
echo "3. Testing token map JSON parsing..."
python3 << 'EOF'
import json
import sys

# Test valid token map
valid_map = '{"org1": "token1", "org2": "token2"}'
try:
    parsed = json.loads(valid_map)
    assert parsed["org1"] == "token1"
    assert parsed["org2"] == "token2"
    print("✓ Valid token map JSON parsed correctly")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test invalid token map
invalid_map = '{"org1": "token1"'
try:
    json.loads(invalid_map)
    print("✗ Should have failed on invalid JSON")
    sys.exit(1)
except json.JSONDecodeError:
    print("✓ Invalid token map JSON correctly rejected")
EOF

echo ""
echo "=========================================="
echo "All Local Tests Completed"
echo "=========================================="

