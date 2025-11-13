# Sparta

This repository contains GitHub Actions workflows for scanning package vulnerabilities using Trivy across your GitHub organization.

## Overview

This solution provides:

1. **Reusable Workflow** - A workflow that can be called from any repository in your GitHub org to scan for vulnerabilities on pull requests
2. **Daily Organization Scan** - A scheduled workflow that scans all repositories in your organization daily and stores results
3. **CVE Query Workflow** - A reusable workflow to query specific CVEs across all scanned repositories
4. **Aggregation Workflow** - A reusable workflow to aggregate and index scan results for reporting

## Components

### 1. Reusable Workflow for PR Checks

**File**: `.github/workflows/package-vulnerability-scan.yml`

This is a reusable workflow that can be called from any repository in your organization to scan for vulnerabilities. It will fail the check if HIGH or CRITICAL vulnerabilities are found.

#### Usage in Your Repositories

To use this workflow in any repository, create a workflow file (e.g., `.github/workflows/security-scan.yml`) with the following content:

```yaml
name: Security Scan

on:
  pull_request:
    branches:
      - main
      - master
      - develop

jobs:
  vulnerability-scan:
    name: Run Vulnerability Scan
    uses: security-pillar-ai-poc/sparta/.github/workflows/package-vulnerability-scan.yml@main
    # Optional: Override default inputs
    # with:
    #   scan-ref: '.'
    #   severity: 'CRITICAL,HIGH'
    #   exit-code: '1'
```


#### Workflow Inputs

- `scan-ref` (optional): Path to scan (default: `.`)
- `severity` (optional): Severity levels to check (default: `CRITICAL,HIGH`)
- `exit-code` (optional): Exit code when vulnerabilities found (default: `1`)

#### Configuration

The workflow uses the following Trivy configuration:
- **Scan Type**: Filesystem (`fs`)
- **Format**: JSON
- **Vulnerability Types**: OS and library vulnerabilities
- **Severity**: CRITICAL and HIGH (configurable)
- **Timeout**: 120 minutes
- **Trivy Version**: v0.65.0
- **Cache**: Enabled (uses dynamic cache directory per repository)

### 2. Daily Organization Scan

**File**: `.github/workflows/daily-org-scan.yml`

This workflow runs daily (at 2 AM UTC) and scans all repositories in your GitHub organization. Results are stored in the `vulnerability-reports/` directory structure.

#### Features

- Automatically discovers all repositories in your organization
- Scans each repository using Trivy
- Stores results in `vulnerability-reports/{org}/{repo}/{date}/trivy-report.json`
- Commits scan results back to the repository
- Handles errors gracefully (timeouts, access issues, etc.)

#### Manual Trigger

You can also trigger this workflow manually from the GitHub Actions UI using the `workflow_dispatch` event.

#### Requirements

- The workflow requires `GITHUB_TOKEN` with organization read permissions
- The repository must have write access to commit scan results

#### Directory Structure

Scan results are stored in the following structure:

```
vulnerability-reports/
└── {org}/
    └── {repo}/
        └── {date}/
            └── trivy-report.json
```

### 3. CVE Query Workflow

**File**: `.github/workflows/query-cve.yml`

A reusable GitHub Actions workflow to search for specific CVEs across all stored scan results.

#### Usage

To query for a CVE, create a workflow file (e.g., `.github/workflows/query-cve-workflow.yml`) with the following content:

```yaml
name: Query CVE

on:
  workflow_dispatch:
    inputs:
      cve-id:
        description: 'CVE identifier to search for'
        required: true
        type: string

jobs:
  query:
    name: Query CVE
    uses: security-pillar-ai-poc/sparta/.github/workflows/query-cve.yml@main
    with:
      cve-id: ${{ inputs.cve-id }}
      reports-dir: 'vulnerability-reports'
      output-format: 'table'  # or 'json'
```

Or call it directly from another workflow:

```yaml
jobs:
  query-cve:
    uses: security-pillar-ai-poc/sparta/.github/workflows/query-cve.yml@main
    with:
      cve-id: 'CVE-2024-1234'
      output-format: 'table'
```

#### Workflow Inputs

- `cve-id` (required): CVE identifier to search for (e.g., `CVE-2024-1234`)
- `reports-dir` (optional): Directory containing vulnerability reports (default: `vulnerability-reports`)
- `output-format` (optional): Output format - `table` or `json` (default: `table`)

#### Workflow Outputs

- `found`: Whether CVE was found in any repository (`true` or `false`)
- `count`: Number of occurrences found

#### Output

The workflow provides:
- List of repositories containing the CVE
- Severity level
- Package name and version
- Fixed version (if available)
- Scan date
- Additional vulnerability details
- Results saved as workflow artifacts (both text and JSON formats)
- Summary displayed in workflow run summary

#### Example Output

The workflow will display results in the GitHub Actions summary and save them as artifacts:

```
## Found 3 occurrence(s) of CVE-2024-1234

| Repository | Severity | Package | Version | Scan Date |
|------------|----------|---------|---------|-----------|
| myorg/repo1 | HIGH | package-name | 1.2.3 | 20240115 |
| myorg/repo2 | CRITICAL | another-package | 2.0.0 | 20240115 |
| myorg/repo3 | HIGH | some-package | 0.9.1 | 20240115 |
```

### 4. Aggregation Workflow

**File**: `.github/workflows/aggregate-scans.yml`

A reusable GitHub Actions workflow to aggregate and index all scan results for faster querying and reporting.

#### Usage

To aggregate scan results, create a workflow file (e.g., `.github/workflows/aggregate-workflow.yml`) with the following content:

```yaml
name: Aggregate Scans

on:
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * *'  # Run daily after scans complete

jobs:
  aggregate:
    name: Aggregate Scan Results
    uses: security-pillar-ai-poc/sparta/.github/workflows/aggregate-scans.yml@main
    with:
      reports-dir: 'vulnerability-reports'
      output-dir: 'aggregated'
```

#### Workflow Inputs

- `reports-dir` (optional): Directory containing vulnerability reports (default: `vulnerability-reports`)
- `output-dir` (optional): Output directory for aggregated data (default: `aggregated`)

#### Output

The workflow generates and uploads as artifacts:
- `statistics.json` - Overall statistics and metrics
- `cve-index.json` - Index of all CVEs and their occurrences
- `repository-summary.json` - Summary of vulnerabilities per repository
- `summary.txt` - Human-readable summary report

#### Summary Report Includes

- Total scans and repositories
- Severity distribution
- Top repositories by vulnerability count
- Most common CVEs
- Package vulnerability statistics

## Setup

### Prerequisites

1. GitHub Actions enabled in your organization
2. Appropriate permissions for the workflows
3. Python 3.11+ (only needed for the daily scan workflow which uses Python internally)

### Installation

1. Clone or fork this repository
2. Ensure the workflows are accessible to other repositories in your organization
3. The workflows will automatically install required dependencies when running

## Workflow Permissions

### Reusable Workflow

The reusable workflow requires:
- `contents: read` - To checkout code
- `security-events: write` - To upload security findings (optional)

### Daily Scan Workflow

The daily scan workflow requires:
- `contents: read` - To checkout code and read repository list
- `contents: write` - To commit scan results (if committing back)
- Organization read access via `GITHUB_TOKEN`

### CVE Query Workflow

The CVE query workflow requires:
- `contents: read` - To read scan results from the repository

### Aggregation Workflow

The aggregation workflow requires:
- `contents: read` - To read scan results from the repository

## Customization

### Changing Scan Schedule

Edit `.github/workflows/daily-org-scan.yml` and modify the cron schedule:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Change to your preferred time
```

### Adjusting Severity Levels

In the reusable workflow, you can override the severity levels:

```yaml
with:
  severity: 'CRITICAL,HIGH,MEDIUM'  # Include MEDIUM severity
```

### Retention Policy

By default, all scan results are kept. To implement retention, you can:

1. Modify the daily scan workflow to delete old reports
2. Use GitHub Actions artifacts with retention policies
3. Implement cleanup in the aggregation script

## Troubleshooting

### Workflow Fails on PR

- Check that the repository has access to the reusable workflow
- Verify the workflow file path is correct
- Check Trivy scan logs for specific errors

### Daily Scan Not Running

- Verify the workflow is enabled in the repository
- Check GitHub Actions permissions for the organization
- Review workflow logs for authentication or permission errors

### CVE Query Returns No Results

- Verify scan results exist in `vulnerability-reports/`
- Check that the CVE ID format is correct (e.g., `CVE-2024-1234`)
- Ensure the reports directory path is correct
- Check workflow artifacts for detailed results
- Review workflow logs for any parsing errors

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Add your license here]

## References

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Trivy GitHub Action](https://github.com/marketplace/actions/aqua-security-trivy)
- [GitHub Actions Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)

