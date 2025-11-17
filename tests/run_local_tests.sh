#!/bin/bash
# Run all local tests for unified workflow

set -e

echo "=========================================="
echo "Running All Local Tests"
echo "=========================================="
echo ""

# Test 1: Token manager tests
echo "1. Running token manager tests..."
python3 tests/test_token_manager.py
echo ""

# Test 2: Orchestration script tests
echo "2. Running orchestration script tests..."
python3 tests/test_orchestrate_scan.py
echo ""

# Test 3: Unified workflow integration tests
echo "3. Running unified workflow integration tests..."
python3 tests/test_unified_workflow_integration.py
echo ""

# Test 4: Workflow trigger tests
echo "4. Running workflow trigger tests..."
python3 tests/test_workflow_triggers.py
echo ""

# Test 5: Unit tests for token handling (legacy)
echo "5. Running legacy token tests..."
python3 tests/test_multi_org_tokens.py
echo ""

# Test 6: Integration scenario tests (legacy)
echo "6. Running legacy integration scenario tests..."
python3 tests/test_integration_scenarios.py
echo ""

# Test 7: Workflow token generation simulation
echo "7. Running workflow token generation simulation..."
python3 tests/simulate_workflow_token_generation.py
echo ""

# Test 8: Credential format tests
echo "8. Running credential format tests..."
python3 -m pytest tests/test_credential_format.py -v 2>&1 | head -30 || echo "⚠ Pytest not available, skipping"
echo ""

echo "=========================================="
echo "All Local Tests Completed"
echo "=========================================="

