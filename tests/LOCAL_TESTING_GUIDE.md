# Local Testing Guide for Multi-Org Token Support

This guide explains how to test and simulate all scenarios locally without requiring actual GitHub App setup.

## Quick Start

Run all tests:
```bash
bash tests/run_local_tests.sh
```

Or run individual test suites:
```bash
# Unit tests
python3 tests/test_multi_org_tokens.py

# Integration scenarios
python3 tests/test_integration_scenarios.py

# Workflow simulation
python3 tests/simulate_workflow_token_generation.py
```

## Test Coverage

### Unit Tests (`test_multi_org_tokens.py`)

1. **Token Map Parsing** ✓
   - Valid JSON parsing
   - Invalid JSON handling

2. **Get Token for Org Function** ✓
   - Token selection from map
   - Fallback to default token
   - Empty/None map handling

3. **Multi-Org Format Detection** ✓
   - Detects multi-org format correctly
   - Distinguishes from single-org format

4. **Token Selection Scenarios** ✓
   - All orgs have tokens
   - Some orgs missing tokens
   - Empty token map
   - None token map

5. **Error Handling** ✓
   - Missing tokens handled gracefully
   - Fallback behavior verified

6. **Backward Compatibility** ✓
   - Single org mode works without token map
   - Default token used when map not provided

### Integration Tests (`test_integration_scenarios.py`)

1. **All Orgs Have Tokens** ✓
   - All organizations successfully retrieve their tokens
   - Token map correctly used

2. **Some Orgs Missing Tokens** ✓
   - Missing orgs fall back to default token
   - Other orgs continue to work

3. **No Token Map (Backward Compat)** ✓
   - Single org mode works
   - All orgs use default token

4. **Invalid Token Map JSON** ✓
   - Invalid JSON handled gracefully
   - Falls back to default token

5. **Multi-Org Repos JSON Format** ✓
   - Multi-org format correctly processed
   - Token map applied per org

6. **Single Org Mode** ✓
   - Backward compatibility maintained
   - Works without token map

7. **Large Org with Batching** ✓
   - Large orgs processed correctly
   - Token map works with batching

8. **Mixed Success/Failure** ✓
   - Some orgs succeed, some fail
   - Graceful degradation

### Workflow Simulation (`simulate_workflow_token_generation.py`)

1. **App Installed on All Organizations** ✓
   - JWT generation simulated
   - Tokens generated for all orgs
   - Token map created successfully

2. **App Not Installed on Some Organizations** ✓
   - Missing installations detected
   - Partial token map created
   - Failed orgs logged

3. **App Not Installed on Any Organization** ✓
   - All token generations fail
   - Empty token map created
   - Fallback to base token

4. **Token Map Usage in Scripts** ✓
   - Token map correctly used
   - Fallback behavior verified

## Test Results Summary

**All Tests Passed:**
- Unit Tests: 9/9 passed
- Integration Scenarios: 8/8 passed
- Workflow Simulations: 4/4 passed

**Total: 21/21 tests passed** ✓

## Simulated Scenarios

### Scenario 1: Perfect Setup
- All organizations have GitHub App installed
- All tokens generated successfully
- Token map: `{"org1": "token1", "org2": "token2", "org3": "token3"}`
- **Result**: All orgs scanned successfully

### Scenario 2: Partial Installation
- Some organizations have app installed, some don't
- Token map: `{"org1": "token1", "org3": "token3"}` (org2 missing)
- **Result**: org1 and org3 scanned, org2 skipped with warning

### Scenario 3: No Installation
- GitHub App not installed on any target org
- Token map: `{}`
- **Result**: Falls back to base token, may fail if base token doesn't have access

### Scenario 4: Backward Compatibility
- Single org mode, no token map provided
- **Result**: Uses default token, works as before

### Scenario 5: Invalid Token Map
- Malformed JSON in `GITHUB_APP_TOKEN_MAP`
- **Result**: Falls back to default token, warning logged

## Manual Testing

You can also test manually by setting environment variables:

```bash
# Test with token map
export GITHUB_APP_TOKEN="default_token"
export GITHUB_APP_TOKEN_MAP='{"org1": "token1", "org2": "token2"}'
export GITHUB_ORGS="org1,org2"

# Test get_repos.py (will fail without actual GitHub API, but tests parsing)
python3 scripts/get_repos.py
```

## What's Not Tested Locally

These require actual GitHub App setup:
- Actual JWT generation with real private key
- Real GitHub API calls to get installation IDs
- Actual token generation from GitHub API
- Real repository cloning with tokens

## Next Steps

After local testing passes:
1. Test in GitHub Actions with real GitHub App
2. Verify token generation works for each org
3. Test with actual multi-org scanning
4. Monitor logs for any token-related errors

