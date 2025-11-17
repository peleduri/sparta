# Multi-Organization Scanning Support

This document describes Sparta's multi-organization scanning capabilities, including support for large organizations with thousands of repositories.

## Overview

Sparta supports scanning multiple GitHub organizations in a single workflow run, with automatic batching for large organizations (>500 repositories) and state tracking for resume capability.

## Features

### Multi-Organization Support

- Scan multiple organizations in a single workflow run
- Sequential processing of organizations to avoid resource contention
- Automatic detection of large organizations requiring batching
- Backward compatible with single-organization workflows

### Large Organization Support

- Automatic batching for organizations with >500 repositories
- Configurable batch size (default: 100 repositories per batch)
- Parallel batch processing using GitHub Actions matrix strategy
- Up to 256 concurrent batch jobs

### State Management and Resume

- State files track scan progress per organization
- Resume capability: skip already-scanned repositories
- Automatic retry of failed repositories (max 3 retries with exponential backoff)
- State files committed to repository for cross-run persistence

### Error Handling

- Per-repository error tracking with timestamps
- Retry logic for transient failures (network, timeouts, rate limits)
- Separate error reports per organization
- Partial completion handling with incremental commits

## Configuration

### Environment Variables

- `GITHUB_ORGS`: Comma-separated list of organization names (e.g., `org1,org2,org3`)
- `GITHUB_ORG`: Single organization name (backward compatible)
- `BATCH_SIZE`: Number of repositories per batch (default: 100)
- `MAX_RETRIES`: Maximum retry attempts for failed repos (default: 3)

### Workflow Inputs

The `sparta-multi-org-scan.yml` workflow accepts:

- `github-orgs`: Comma-separated list of GitHub organizations to scan (required)
- `batch-size`: Number of repositories per batch (optional, default: 100)

## Usage

### Manual Workflow Trigger

1. Go to the Actions tab in your repository
2. Select "Sparta - Multi-Organization Vulnerability Scan"
3. Click "Run workflow"
4. Enter comma-separated organization names (e.g., `org1,org2,org3`)
5. Optionally adjust batch size
6. Click "Run workflow"

### Scheduled Runs

The workflow runs daily at 3 AM UTC (after the single-org scan at 2 AM UTC).

### Programmatic Usage

```yaml
- uses: ./.github/workflows/sparta-multi-org-scan.yml
  with:
    github-orgs: "org1,org2,org3"
    batch-size: "100"
```

## Workflow Architecture

### Job Flow

1. **get-repos**: Fetches repositories from all specified organizations
2. **Auto-detect batching**: Determines if any organization has >500 repos
3. **batch-repos** (conditional): Splits large organizations into batches
4. **scan-batches** (conditional): Scans repositories in parallel batches
5. **commit-results**: Commits scan results and state files

### State File Structure

State files are named `scan-state-{org}-{date}.json` and contain:

```json
{
  "org": "org-name",
  "scan_date": "20250116",
  "batch_size": 100,
  "total_repos": 6000,
  "completed_repos": ["repo1", "repo2"],
  "failed_repos": [
    {
      "repo": "repo3",
      "error": "Git clone failed: ...",
      "retry_count": 1,
      "timestamp": "2025-01-16T10:30:00Z"
    }
  ],
  "pending_repos": ["repo4", "repo5"],
  "batches": {
    "batch-1": {
      "status": "completed",
      "repos": ["repo1", "repo2"],
      "completed_at": "2025-01-16T10:30:00Z"
    }
  },
  "last_updated": "2025-01-16T10:30:00Z"
}
```

## Result Structure

Scan results are organized by organization:

```
vulnerability-reports/
  {org1}/
    {repo1}/
      {YYYYMMDD}/
        trivy-report.json
    {repo2}/
      {YYYYMMDD}/
        trivy-report.json
  {org2}/
    {repo1}/
      {YYYYMMDD}/
        trivy-report.json
```

## Resume Capability

If a scan is interrupted or fails:

1. State files are committed to the repository
2. On the next run, the workflow loads existing state files
3. Already-completed repositories are skipped
4. Failed repositories are retried (up to MAX_RETRIES)
5. Only pending repositories are scanned

## Batching Strategy

### When Batching is Enabled

- Organizations with >500 repositories automatically use batching
- Repositories are split into batches of configurable size (default: 100)
- Each batch runs in a separate GitHub Actions job
- Batches run in parallel (up to 256 concurrent jobs)

### Batch Processing

- Each batch job processes a subset of repositories independently
- State is tracked per batch
- Results are merged at the end
- Failed batches can be retried individually

## Error Handling

### Transient Errors

The following errors trigger automatic retry:
- Network timeouts
- Connection failures
- Rate limit errors
- Temporary service unavailability

### Retry Logic

- Maximum retries: 3 (configurable via `MAX_RETRIES`)
- Exponential backoff: 2^retry_count seconds (max 60 seconds)
- Retry count tracked in state file

### Error Reports

Failed repositories generate error reports:

```json
{
  "error": "Git clone failed: ...",
  "repository": "org/repo",
  "timestamp": "2025-01-16T10:30:00Z",
  "clone_url": "https://github.com/org/repo.git",
  "retry_count": 2
}
```

## Best Practices

1. **Start Small**: Test with small organizations first before scanning large ones
2. **Monitor State Files**: Check state files to track progress and identify issues
3. **Adjust Batch Size**: For very large orgs (>6k repos), consider smaller batch sizes (50-75)
4. **Schedule Appropriately**: Large scans may take hours; schedule during off-peak times
5. **Review Error Reports**: Check error reports to identify systematic issues

## Troubleshooting

### Workflow Fails to Start

- Verify GitHub App has access to all specified organizations
- Check that `GITHUB_ORGS` contains valid organization names
- Ensure GitHub App has required permissions (Contents: Read, Metadata: Read)

### Batching Not Working

- Verify organizations have >500 repositories
- Check that `repo-batches.json` is generated
- Review workflow logs for batching detection step

### State Files Not Persisting

- Ensure state files are committed to repository
- Check that `commit-results` job completes successfully
- Verify Git permissions for workflow

### Repositories Not Resuming

- Verify state files exist in repository
- Check state file format and structure
- Ensure scan_date matches current date format (YYYYMMDD)

## Limitations

- Maximum 256 concurrent batch jobs (GitHub Actions limit)
- 6-hour job timeout per batch
- State files must be committed for resume capability
- Large organizations may require multiple workflow runs

## Migration from Single-Org

To migrate from single-organization to multi-organization scanning:

1. Update workflow trigger to use `sparta-multi-org-scan.yml`
2. Set `GITHUB_ORGS` environment variable with comma-separated orgs
3. Existing single-org workflow (`sparta-daily-org-scan.yml`) remains available for backward compatibility
4. No changes needed to scan scripts (auto-detection handles both formats)

## Related Documentation

- [README.md](../README.md): General Sparta documentation
- [GITHUB_APP_PERMISSIONS_FIX.md](../GITHUB_APP_PERMISSIONS_FIX.md): GitHub App setup guide

