# Test Plan: Multi-Organization Support and Large Org Scanning

## Overview
This test plan covers all recent changes for multi-organization support, large org handling with batching, state management, and enhanced error handling.

## Test Environment Setup

### Prerequisites
- Python 3.8+
- GitHub App token with appropriate permissions
- Access to test organizations (or use existing orgs)
- Trivy installed (for full integration tests)
- Docker (for containerized tests)

### Test Data
- Small org: 1-10 repositories
- Medium org: 50-100 repositories
- Large org: 500+ repositories (if available)
- Multiple orgs: 2-3 organizations

---

## Phase 1: Multi-Org Foundation Tests

### 1.1 `get_repos.py` - Single Org Mode (Backward Compatibility)

**Test Case 1.1.1: Single org with GITHUB_ORG**
- **Setup**: Set `GITHUB_ORG=test-org` (no `GITHUB_ORGS`)
- **Expected**: 
  - Outputs repos.json in single-org format (array of repos)
  - Each repo has: name, full_name, private, default_branch
  - GitHub output includes `count=<number>`
- **Validation**: 
  - Check repos.json structure
  - Verify all repos belong to test-org
  - Verify backward compatibility

**Test Case 1.1.2: Single org with empty repos**
- **Setup**: Use org with 0 repositories
- **Expected**: 
  - Empty array in repos.json
  - count=0 in GitHub output
- **Validation**: No errors, graceful handling

**Test Case 1.1.3: Single org with invalid org name**
- **Setup**: Set `GITHUB_ORG=invalid-org-name-12345`
- **Expected**: Error message, exit code 1
- **Validation**: Proper error handling

### 1.2 `get_repos.py` - Multi-Org Mode

**Test Case 1.2.1: Multiple orgs with GITHUB_ORGS**
- **Setup**: Set `GITHUB_ORGS=org1,org2,org3`
- **Expected**: 
  - Outputs repos.json in multi-org format (array of org objects)
  - Each org object has: org, repos
  - GitHub output includes `count=<total>` and `orgs=<number>`
- **Validation**: 
  - Check repos.json structure
  - Verify repos are grouped by org
  - Verify all orgs are processed

**Test Case 1.2.2: Multiple orgs with one empty**
- **Setup**: `GITHUB_ORGS=org1,empty-org,org2` (empty-org has 0 repos)
- **Expected**: 
  - Empty repos array for empty-org
  - Other orgs processed normally
- **Validation**: Graceful handling of empty orgs

**Test Case 1.2.3: Multiple orgs with whitespace**
- **Setup**: `GITHUB_ORGS="org1, org2 , org3"`
- **Expected**: All orgs processed correctly (whitespace trimmed)
- **Validation**: Proper parsing

**Test Case 1.2.4: GITHUB_ORG vs GITHUB_ORGS priority**
- **Setup**: Set both `GITHUB_ORG=org1` and `GITHUB_ORGS=org2,org3`
- **Expected**: GITHUB_ORGS takes precedence (multi-org mode)
- **Validation**: Multi-org format used

**Test Case 1.2.5: Invalid org in GITHUB_ORGS**
- **Setup**: `GITHUB_ORGS=valid-org,invalid-org-12345`
- **Expected**: Error for invalid org, graceful failure
- **Validation**: Proper error reporting

### 1.3 `scan_repos.py` - Format Auto-Detection

**Test Case 1.3.1: Single-org format detection**
- **Setup**: repos.json in single-org format (array of repos)
- **Expected**: 
  - Detects single-org format
  - Processes all repos under one org
  - Uses GITHUB_ORG env var or infers from repo full_name
- **Validation**: Correct format detection

**Test Case 1.3.2: Multi-org format detection**
- **Setup**: repos.json in multi-org format (array of org objects)
- **Expected**: 
  - Detects multi-org format
  - Processes orgs sequentially
  - Creates separate report directories per org
- **Validation**: Correct format detection and processing

**Test Case 1.3.3: Mixed format handling**
- **Setup**: Invalid repos.json (neither format)
- **Expected**: Error message, graceful failure
- **Validation**: Proper error handling

### 1.4 `scan_repos.py` - Multi-Org Processing

**Test Case 1.4.1: Scan multiple orgs sequentially**
- **Setup**: Multi-org repos.json with 2-3 orgs
- **Expected**: 
  - Processes org1 completely, then org2, then org3
  - Creates `vulnerability-reports/{org}/` for each org
  - Reports organized by org
- **Validation**: Sequential processing, correct directory structure

**Test Case 1.4.2: Skip Sparta repo in multi-org**
- **Setup**: Multi-org repos.json including Sparta repo
- **Expected**: 
  - Skips cloning Sparta repo
  - Scans current directory for Sparta
  - Other repos cloned and scanned normally
- **Validation**: Correct handling of self-repo

**Test Case 1.4.3: Error in one org doesn't stop others**
- **Setup**: Multi-org with one org having inaccessible repos
- **Expected**: 
  - Errors logged for problematic org
  - Other orgs continue processing
  - Partial results saved
- **Validation**: Resilient error handling

---

## Phase 2: Large Org Support Tests

### 2.1 `batch_repos.py` - Batch Creation

**Test Case 2.1.1: Single-org batching**
- **Setup**: Single-org repos.json with 250 repos, BATCH_SIZE=100
- **Expected**: 
  - Creates 3 batches (100, 100, 50)
  - repo-batches.json with batch_id, repos, batch_index, total_batches
  - GitHub output includes matrix for GitHub Actions
- **Validation**: Correct batch splitting

**Test Case 2.1.2: Multi-org batching**
- **Setup**: Multi-org repos.json, org1=150 repos, org2=80 repos, BATCH_SIZE=100
- **Expected**: 
  - org1: 2 batches (100, 50)
  - org2: 1 batch (80)
  - Batch IDs include org name: `org1-batch-1`, `org1-batch-2`, `org2-batch-1`
- **Validation**: Correct per-org batching

**Test Case 2.2.3: Custom batch size**
- **Setup**: 50 repos, BATCH_SIZE=25
- **Expected**: 2 batches of 25 repos each
- **Validation**: Custom batch size respected

**Test Case 2.2.4: Batch size larger than repos**
- **Setup**: 10 repos, BATCH_SIZE=100
- **Expected**: 1 batch with 10 repos
- **Validation**: Handles edge case

**Test Case 2.2.5: Empty repos list**
- **Setup**: Empty repos.json
- **Expected**: Error or empty batches, graceful handling
- **Validation**: No crashes

### 2.2 `scan_state.py` - State Management

**Test Case 2.2.1: Initialize state**
- **Setup**: Run `scan_state.py init org1 20250116 100`
- **Expected**: 
  - Creates `scan-state-org1-20250116.json`
  - State includes: org, scan_date, total_repos, completed_repos, failed_repos, pending_repos
  - All repos in pending_repos initially
- **Validation**: Correct state initialization

**Test Case 2.2.2: Mark completed**
- **Setup**: Initialize state, then `scan_state.py completed org1 20250116 repo1`
- **Expected**: 
  - repo1 moved from pending to completed
  - State file updated
- **Validation**: State updates correctly

**Test Case 2.2.3: Mark failed**
- **Setup**: Initialize state, then `scan_state.py failed org1 20250116 repo2 "Error message" 1`
- **Expected**: 
  - repo2 moved from pending to failed_repos
  - Failed entry includes: repo, error, retry_count, timestamp
- **Validation**: Failed repos tracked correctly

**Test Case 2.2.4: Get summary**
- **Setup**: State with some completed, failed, and pending repos
- **Expected**: 
  - Summary shows: total, completed, failed, pending, progress_percent
  - Accurate counts
- **Validation**: Summary accuracy

**Test Case 2.2.5: Resume capability**
- **Setup**: 
  - Initialize state with 10 repos
  - Mark 5 as completed, 2 as failed
  - Load state in new run
- **Expected**: 
  - Only pending repos (3) are processed
  - Failed repos can be retried
- **Validation**: Resume works correctly

**Test Case 2.2.6: Max retries**
- **Setup**: Mark repo as failed with retry_count=3, MAX_RETRIES=3
- **Expected**: 
  - `should_retry()` returns False
  - Repo not retried
- **Validation**: Max retries respected

### 2.3 Workflow Integration - `sparta-multi-org-scan.yml`

**Test Case 2.3.1: Workflow dispatch with multiple orgs**
- **Setup**: Manual trigger with `github-orgs: org1,org2`
- **Expected**: 
  - get-repos job runs
  - Creates batches
  - Matrix strategy creates jobs for each batch
  - All batches processed in parallel
- **Validation**: Workflow execution

**Test Case 2.3.2: Scheduled run**
- **Setup**: Wait for scheduled time (or trigger manually)
- **Expected**: Same as 2.3.1
- **Validation**: Scheduled execution

**Test Case 2.3.3: Batch artifact handling**
- **Setup**: Multiple batches
- **Expected**: 
  - Each batch uploads scan results as artifact
  - commit-results downloads all artifacts
  - Results merged correctly
- **Validation**: Artifact handling

**Test Case 2.3.4: Workflow summary**
- **Setup**: Complete workflow run
- **Expected**: 
  - Summary shows total orgs, repos, batches
  - Batch status table
- **Validation**: Summary accuracy

---

## Phase 3: Error Handling and Recovery Tests

### 3.1 Retry Logic

**Test Case 3.1.1: Transient error retry**
- **Setup**: Mock network timeout error
- **Expected**: 
  - Error detected as transient
  - Retry with exponential backoff (1s, 2s, 4s)
  - Max 3 retries
- **Validation**: Retry logic works

**Test Case 3.1.2: Non-transient error no retry**
- **Setup**: Mock authentication error
- **Expected**: 
  - Error not retried
  - Marked as failed immediately
- **Validation**: Only transient errors retried

**Test Case 3.1.3: Retry success**
- **Setup**: First attempt fails (timeout), second succeeds
- **Expected**: 
  - Retry attempted
  - Eventually succeeds
  - Marked as completed
- **Validation**: Retry can succeed

**Test Case 3.1.4: Retry exhaustion**
- **Setup**: All retries fail
- **Expected**: 
  - Max retries reached
  - Marked as failed with retry_count
  - Error report created
- **Validation**: Retry limits respected

### 3.2 Error Detection

**Test Case 3.2.1: Transient error keywords**
- **Setup**: Errors with keywords: timeout, network, connection, rate limit, temporary
- **Expected**: All detected as transient
- **Validation**: Keyword detection

**Test Case 3.2.2: Clone failure handling**
- **Setup**: Repo that fails to clone
- **Expected**: 
  - Error report created
  - State updated (failed)
  - Continues to next repo
- **Validation**: Clone failures handled gracefully

**Test Case 3.2.3: Scan timeout handling**
- **Setup**: Repo that times out during Trivy scan
- **Expected**: 
  - Timeout detected
  - Retry attempted
  - Error report if all retries fail
- **Validation**: Timeout handling

**Test Case 3.2.4: Empty clone directory**
- **Setup**: Clone succeeds but directory is empty
- **Expected**: 
  - Error detected
  - Error report created
  - Continues to next repo
- **Validation**: Empty directory detection

### 3.3 State Integration with Errors

**Test Case 3.3.1: Failed repos tracked in state**
- **Setup**: Scan with some failures
- **Expected**: 
  - Failed repos in state file
  - Error messages preserved
  - Retry counts tracked
- **Validation**: State tracks failures

**Test Case 3.3.2: Resume after failures**
- **Setup**: 
  - Initial run with failures
  - Second run with same state
- **Expected**: 
  - Failed repos retried (if retry_count < MAX_RETRIES)
  - Completed repos skipped
- **Validation**: Resume handles failures

**Test Case 3.3.3: Partial completion commit**
- **Setup**: Scan with some failures
- **Expected**: 
  - Partial results committed
  - Failed repos tracked for next run
- **Validation**: Partial commits work

---

## Integration Tests

### 4.1 End-to-End Single Org (Backward Compatibility)

**Test Case 4.1.1: Full single-org scan**
- **Setup**: 
  - Set `GITHUB_ORG=test-org`
  - Run get-repos, scan-repos, commit-results
- **Expected**: 
  - Works exactly as before
  - No breaking changes
- **Validation**: Backward compatibility maintained

### 4.2 End-to-End Multi-Org

**Test Case 4.2.1: Full multi-org scan**
- **Setup**: 
  - Set `GITHUB_ORGS=org1,org2`
  - Run complete workflow
- **Expected**: 
  - Both orgs scanned
  - Results organized by org
  - All results committed
- **Validation**: Multi-org workflow works

**Test Case 4.2.2: Multi-org with batching**
- **Setup**: 
  - Large org (500+ repos)
  - BATCH_SIZE=100
  - Run workflow
- **Expected**: 
  - Batches created
  - Parallel processing
  - All batches complete
- **Validation**: Batching works at scale

### 4.3 Error Recovery

**Test Case 4.3.1: Resume after workflow failure**
- **Setup**: 
  - Workflow fails mid-scan
  - Re-run workflow
- **Expected**: 
  - State file preserved
  - Completed repos skipped
  - Only pending/failed repos processed
- **Validation**: Resume capability

---

## Edge Cases and Boundary Conditions

### 5.1 Edge Cases

**Test Case 5.1.1: Single repo in org**
- **Setup**: Org with 1 repository
- **Expected**: Works normally
- **Validation**: Handles small orgs

**Test Case 5.1.2: Very large org (6k+ repos)**
- **Setup**: Org with 6000+ repositories
- **Expected**: 
  - Batches created (60+ batches with size 100)
  - Matrix strategy handles it
  - All batches processed
- **Validation**: Scales to large orgs

**Test Case 5.1.3: Special characters in org/repo names**
- **Setup**: Org or repo names with special characters
- **Expected**: 
  - Properly sanitized
  - No path traversal issues
- **Validation**: Security validation

**Test Case 5.1.4: Concurrent workflow runs**
- **Setup**: Two workflows run simultaneously
- **Expected**: 
  - Git push conflicts handled
  - Rebase logic works
  - No data loss
- **Validation**: Concurrent execution

### 5.2 Boundary Conditions

**Test Case 5.2.1: BATCH_SIZE=1**
- **Setup**: 10 repos, BATCH_SIZE=1
- **Expected**: 10 batches, each with 1 repo
- **Validation**: Minimum batch size

**Test Case 5.2.2: BATCH_SIZE larger than total repos**
- **Setup**: 5 repos, BATCH_SIZE=100
- **Expected**: 1 batch with 5 repos
- **Validation**: Handles edge case

**Test Case 5.2.3: MAX_RETRIES=0**
- **Setup**: MAX_RETRIES=0
- **Expected**: No retries, immediate failure
- **Validation**: Retry limit edge case

**Test Case 5.2.4: MAX_RETRIES very high**
- **Setup**: MAX_RETRIES=10
- **Expected**: Up to 10 retries
- **Validation**: High retry limit

---

## Performance Tests

### 6.1 Performance Benchmarks

**Test Case 6.1.1: Single org scan time**
- **Setup**: Org with 100 repos
- **Expected**: Completes within reasonable time
- **Validation**: Performance baseline

**Test Case 6.1.2: Multi-org scan time**
- **Setup**: 3 orgs, 100 repos each
- **Expected**: Sequential processing, total time reasonable
- **Validation**: Multi-org performance

**Test Case 6.1.3: Batched scan time**
- **Setup**: Large org, batched processing
- **Expected**: Parallel batches reduce total time
- **Validation**: Batching improves performance

---

## Security Tests

### 7.1 Security Validation

**Test Case 7.1.1: Path traversal prevention**
- **Setup**: Repo names with `../` or similar
- **Expected**: Properly sanitized, no path traversal
- **Validation**: Security_utils validation

**Test Case 7.1.2: Token sanitization**
- **Setup**: Errors containing tokens
- **Expected**: Tokens masked in logs/errors
- **Validation**: Token sanitization works

**Test Case 7.1.3: Org/repo name validation**
- **Setup**: Invalid org/repo names
- **Expected**: Validation errors, no processing
- **Validation**: Input validation

---

## Test Execution Checklist

### Local Testing (No GitHub API)
- [ ] Test 1.1.1: Single org format detection
- [ ] Test 1.2.1: Multi-org format detection
- [ ] Test 2.1.1: Batch creation (single-org)
- [ ] Test 2.1.2: Batch creation (multi-org)
- [ ] Test 2.2.1-2.2.6: State management CLI
- [ ] Test 3.1.1-3.1.4: Retry logic (mocked)
- [ ] Test 5.1.1: Edge cases (format detection)

### Integration Testing (With GitHub API)
- [ ] Test 1.1.1: Single org get-repos
- [ ] Test 1.2.1: Multi-org get-repos
- [ ] Test 1.4.1: Multi-org scan processing
- [ ] Test 2.3.1: Workflow execution
- [ ] Test 4.1.1: End-to-end single org
- [ ] Test 4.2.1: End-to-end multi-org
- [ ] Test 4.2.2: Multi-org with batching
- [ ] Test 4.3.1: Resume after failure

### Production Testing
- [ ] Test 5.1.2: Very large org (6k+ repos)
- [ ] Test 6.1.1-6.1.3: Performance benchmarks
- [ ] Test 5.1.4: Concurrent workflow runs

---

## Test Data Requirements

### Test Organizations
- `test-org-small`: 1-10 repos
- `test-org-medium`: 50-100 repos
- `test-org-large`: 500+ repos (if available)
- `test-org-empty`: 0 repos
- `test-org-invalid`: Non-existent org (for error testing)

### Test Repositories
- Public repos (for easy access)
- Private repos (for permission testing)
- Large repos (for timeout testing)
- Empty repos (for edge case testing)

---

## Success Criteria

### Phase 1 (Multi-Org Foundation)
- ✅ Single-org mode works (backward compatible)
- ✅ Multi-org mode works
- ✅ Format auto-detection works
- ✅ Sequential org processing works

### Phase 2 (Large Org Support)
- ✅ Batching works for single-org
- ✅ Batching works for multi-org
- ✅ State management works
- ✅ Workflow integration works

### Phase 3 (Error Handling)
- ✅ Retry logic works
- ✅ Error detection works
- ✅ State integration works
- ✅ Resume capability works

### Overall
- ✅ No breaking changes (backward compatible)
- ✅ All tests pass
- ✅ Performance acceptable
- ✅ Security validated
- ✅ Documentation updated

---

## Notes

- Local tests can be run without GitHub API access
- Integration tests require valid GitHub App token
- Performance tests should be run on representative data sizes
- Security tests are critical and must pass before production use
- All edge cases should be tested before deploying to production

