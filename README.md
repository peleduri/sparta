# Sparta


This repository contains GitHub Actions workflows for scanning package vulnerabilities using Trivy across your GitHub organization.

> **Note**: This is a public repository. All workflows use dynamic references and require you to configure secrets in your repository settings. No hardcoded credentials or organization-specific values are included.

## Overview

This solution provides:

1. **Reusable Workflow** - A workflow that can be called from any repository in your GitHub org to scan for vulnerabilities on pull requests
2. **Daily Organization Scan** - A scheduled workflow that scans all repositories in your organization daily and stores results
3. **CVE Query Workflow** - A reusable workflow to query specific CVEs across all scanned repositories
4. **Aggregation Workflow** - A reusable workflow to aggregate and index scan results for reporting

## Components

### Overview

Sparta provides multiple workflows for different use cases:

1. **Reusable Workflow** - PR vulnerability checks
2. **Daily Organization Scan** - Single org daily scanning (backward compatible)
3. **Multi-Organization Scan** - Multi-org scanning with batching and state management (NEW)
4. **CVE Query Workflow** - Search for specific CVEs
5. **Aggregation Workflow** - Aggregate and index scan results

### 1. Reusable Workflow for PR Checks

**File**: `.github/workflows/sparta-package-vulnerability-scan.yml`

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
    uses: YOUR_ORG/sparta/.github/workflows/sparta-package-vulnerability-scan.yml@main
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

**File**: `.github/workflows/sparta-daily-org-scan.yml`

This workflow runs daily (at 2 AM UTC) and scans all repositories in your GitHub organization. Results are stored in the `vulnerability-reports/` directory structure.

#### Features

- Automatically discovers all repositories in your organization
- Scans each repository using Trivy
- Stores results in `vulnerability-reports/{org}/{repo}/{date}/trivy-report.json`
- Commits scan results back to the repository
- Handles errors gracefully (timeouts, access issues, etc.)
- **Backward compatible** - works with single organization

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

### 2.5. Multi-Organization Scan (NEW)

**File**: `.github/workflows/sparta-multi-org-scan.yml`

This workflow supports scanning multiple GitHub organizations in a single run, with advanced features for large organizations (6k+ repositories).

#### Features

- **Multi-organization support**: Scan multiple orgs in one workflow run
- **Batch processing**: Automatically splits large orgs into batches for parallel processing
- **State management**: Tracks scan progress with resume capability
- **Enhanced error handling**: Automatic retry with exponential backoff for transient failures
- **Scalable**: Handles organizations with 6k+ repositories via matrix strategy

#### Usage

**Manual Trigger with Multiple Organizations:**

```yaml
# Trigger from GitHub Actions UI or via workflow_dispatch
# Input: github-orgs: "org1,org2,org3"
# Optional: batch-size: "100" (default: 100 repos per batch)
```

**Scheduled Run:**

The workflow runs daily at 3 AM UTC (after single-org scan at 2 AM). Configure organizations via workflow inputs or environment variables.

#### Configuration

**Environment Variables:**

- `GITHUB_ORGS`: Comma-separated list of organizations (e.g., `org1,org2,org3`)
- `GITHUB_ORG`: Single organization (backward compatible, used if `GITHUB_ORGS` not set)
- `BATCH_SIZE`: Number of repositories per batch (default: 100)
- `MAX_RETRIES`: Maximum retry attempts for failed repos (default: 3)

**Example:**

```yaml
env:
  GITHUB_ORGS: "org1,org2,org3"
  BATCH_SIZE: "100"
  MAX_RETRIES: "3"
```

#### How It Works

1. **Get Repositories**: Fetches all repos from specified organizations
2. **Create Batches**: Splits repos into batches (configurable size, default 100)
3. **Parallel Scanning**: Uses GitHub Actions matrix strategy to scan batches in parallel
4. **State Tracking**: Maintains state files for progress tracking and resume capability
5. **Error Recovery**: Automatically retries transient failures (network, timeouts, rate limits)
6. **Commit Results**: Merges all batch results and commits to repository

#### Directory Structure

Multi-org scans create the same directory structure, organized by organization:

```
vulnerability-reports/
├── org1/
│   └── {repo}/
│       └── {date}/
│           └── trivy-report.json
├── org2/
│   └── {repo}/
│       └── {date}/
│           └── trivy-report.json
└── org3/
    └── {repo}/
        └── {date}/
            └── trivy-report.json
```

#### State Management

The workflow maintains state files (`scan-state-{org}-{date}.json`) that track:
- Completed repositories
- Failed repositories (with error messages and retry counts)
- Pending repositories
- Batch status

This enables:
- **Resume capability**: If a workflow fails, it can resume from where it left off
- **Retry logic**: Failed repos are automatically retried (up to MAX_RETRIES)
- **Progress tracking**: Monitor scan progress in real-time

#### Error Handling

- **Transient errors** (network, timeouts, rate limits): Automatically retried with exponential backoff
- **Permanent errors** (authentication, invalid repos): Logged and skipped
- **Partial completion**: Results are committed even if some repos fail
- **State persistence**: Failed repos are tracked for retry in subsequent runs

#### Large Organization Support

For organizations with 6k+ repositories:
- Automatically creates batches (e.g., 60+ batches for 6000 repos with batch size 100)
- Uses GitHub Actions matrix strategy for parallel processing
- Each batch runs independently, reducing total scan time
- State files track progress across all batches

#### Requirements

- Same as Daily Organization Scan (GitHub App with appropriate permissions)
- GitHub Actions with matrix strategy support (available on all plans)

### 3. CVE Query Workflow

**File**: `.github/workflows/sparta-query-cve.yml`

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
    uses: YOUR_ORG/sparta/.github/workflows/sparta-query-cve.yml@main
    with:
      cve-id: ${{ inputs.cve-id }}
      reports-dir: 'vulnerability-reports'
      output-format: 'table'  # or 'json'
```

Or call it directly from another workflow:

```yaml
jobs:
  query-cve:
    uses: YOUR_ORG/sparta/.github/workflows/sparta-query-cve.yml@main
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

**File**: `.github/workflows/sparta-aggregate-scans.yml`

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
    uses: YOUR_ORG/sparta/.github/workflows/sparta-aggregate-scans.yml@main
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

1. **Fork or Clone this repository** to your GitHub organization
   ```bash
   git clone https://github.com/peleduri/sparta.git
   # Or fork the repository to your organization
   ```

2. **Update workflow references** (if using from a fork):
   - Replace `YOUR_ORG` in the README examples with your actual GitHub organization name
   - If you forked the repo, workflows will automatically use your organization name via `${{ github.repository_owner }}`

3. **Configure secrets** (see Configuration section below)

4. **Ensure workflows are accessible** to other repositories in your organization (if using reusable workflows)

5. The workflows will automatically install required dependencies when running

### Configuration

#### GitHub App Setup (for Daily Organization Scan)

The daily organization scan requires a GitHub App for authentication. Set up the following secrets in your repository:

- `SPARTA_APP_ID`: Your GitHub App ID
- `SPARTA_APP_PRIVATE_KEY`: Your GitHub App private key

**Step-by-Step Setup:**

1. **Create GitHub App:**
   - Go to your organization settings → Developer settings → GitHub Apps
   - Click "New GitHub App" or edit existing app

2. **Configure Repository Permissions:**
   - ✅ **Contents**: Read (REQUIRED - allows cloning repositories)
   - ✅ **Metadata**: Read (REQUIRED - allows reading repository information)
   - ⚠️ **Pull requests**: Read (optional - only if scanning PRs)

3. **Configure Organization Permissions:**
   - ✅ **Members**: Read-only (REQUIRED - for accessing private repositories in the organization)

4. **Install the App:**
   - **CRITICAL**: Install on the **entire organization**, not individual repositories
   - Go to: Install App → Select your organization
   - Choose: **"All repositories"** (not "Only select repositories")
   - This ensures access to all repos including private ones

5. **Get App Credentials:**
   - Copy the **App ID** from the app settings
   - Generate and download a **Private Key** (you can only download it once)
   - Add both as secrets in your repository: Settings → Secrets and variables → Actions

**Important Notes:**
- ❌ **Administration permission is NOT required** for cloning repositories
- ✅ **Contents: Read** is the only repository permission needed for cloning
- ✅ **Members: Read-only** is required for accessing private organization repositories
- ✅ App must be installed on **"All repositories"** to access private repos

**Troubleshooting Permission Issues:**

If you see errors like `fatal: could not read Username for 'https://github.com'` when cloning private repos:

1. **Verify App Installation:**
   - Go to your organization → Settings → Installed GitHub Apps
   - Find your Sparta app and verify it shows "All repositories"
   - If it shows "Only select repositories", reinstall with "All repositories"

2. **Verify Permissions:**
   - Go to your GitHub App settings → Permissions & events
   - Verify **Contents: Read** is set
   - Verify **Members: Read-only** is set (for private repos)
   - Save changes if modified

3. **Check Token Generation:**
   - Verify the workflow step "Generate GitHub App token" succeeds
   - Check that `SPARTA_APP_ID` and `SPARTA_APP_PRIVATE_KEY` secrets are set correctly

4. **Verify Repository Access:**
   - The app must be installed on the organization level, not individual repos
   - Private repos require the app to have "All repositories" access

#### Docker Image

The workflows use a Docker image hosted on GitHub Container Registry (GHCR). The image is automatically built and pushed by the `sparta-build-docker.yml` workflow when you push changes to the repository.

**Image naming**: The image name automatically follows the pattern: `ghcr.io/{your-org}/sparta:latest`
- When run in `peleduri/sparta`, it will be: `ghcr.io/peleduri/sparta:latest`
- When run in your fork, it will be: `ghcr.io/{your-org}/sparta:latest`

**First-time setup**: 
1. Push your code to trigger the Docker build workflow
2. Wait for the build to complete (check the Actions tab)
3. The image will be available at `ghcr.io/{your-org}/sparta:latest`

**Using a custom image**: To use a different Docker registry, update the workflow files to reference your custom image location.

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

### Choosing Between Single-Org and Multi-Org Scans

**Use Single-Org Scan** (`.github/workflows/sparta-daily-org-scan.yml`) when:
- Scanning one organization
- You want simple, straightforward scanning
- You don't need batching or state management

**Use Multi-Org Scan** (`.github/workflows/sparta-multi-org-scan.yml`) when:
- Scanning multiple organizations
- Organization has 500+ repositories (benefits from batching)
- You need resume capability and state tracking
- You want enhanced error handling with retries

### Changing Scan Schedule

**Single-Org Scan**: Edit `.github/workflows/sparta-daily-org-scan.yml`:
```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Change to your preferred time
```

**Multi-Org Scan**: Edit `.github/workflows/sparta-multi-org-scan.yml`:
```yaml
on:
  schedule:
    - cron: '0 3 * * *'  # Change to your preferred time
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

### Multi-Org Scan Issues

**Workflow fails to start:**
- Verify `GITHUB_ORGS` or `GITHUB_ORG` is set correctly
- Check that organizations are comma-separated (no spaces or with spaces trimmed)
- Verify GitHub App has access to all specified organizations

**Batches not processing:**
- Check that `repo-batches.json` is created correctly
- Verify matrix strategy is working (check workflow logs)
- Ensure batch size is appropriate (not too large for GitHub Actions limits)

**State not persisting:**
- Verify state files are being created (`scan-state-{org}-{date}.json`)
- Check that state files are committed to repository
- Ensure resume logic is working correctly

**Retries not working:**
- Check `MAX_RETRIES` environment variable is set
- Verify errors are being detected as transient (network, timeout, rate limit)
- Review retry logs in workflow output

### CVE Query Returns No Results

- Verify scan results exist in `vulnerability-reports/`
- Check that the CVE ID format is correct (e.g., `CVE-2024-1234`)
- Ensure the reports directory path is correct
- Check workflow artifacts for detailed results
- Review workflow logs for any parsing errors

## Security

### Public Repository Safety

This repository is designed to be safely published as a public repository:

- ✅ **No hardcoded secrets**: All secrets are referenced via GitHub Secrets (`${{ secrets.* }}`)
- ✅ **Dynamic organization references**: All workflows use `${{ github.repository_owner }}` - automatically adapts to your organization
- ✅ **Dynamic Docker images**: Image names use `ghcr.io/${{ github.repository_owner }}/sparta:latest`
- ✅ **Environment-based configuration**: All scripts read from environment variables
- ✅ **No sensitive data**: Log files and temporary files are excluded via `.gitignore`

### Required Secrets

Before using the workflows, you must configure these secrets in your repository settings:

- `SPARTA_APP_ID`: GitHub App ID (for daily organization scan)
- `SPARTA_APP_PRIVATE_KEY`: GitHub App private key (for daily organization scan)

**Per-Organization Credentials (Optional)**:

For multi-organization scanning, you can optionally use different GitHub App credentials per organization:

- `SPARTA_APP_ID_<ORG_NAME>`: GitHub App ID for specific organization
- `SPARTA_APP_PRIVATE_KEY_<ORG_NAME>`: GitHub App private key for specific organization

**Org name normalization**: Organization names are normalized (uppercase, hyphens → underscores).
Example: For organization `my-org`, use secrets `SPARTA_APP_ID_MY_ORG` and `SPARTA_APP_PRIVATE_KEY_MY_ORG`.

If per-org credentials are not provided, the default `SPARTA_APP_ID` and `SPARTA_APP_PRIVATE_KEY` will be used for all organizations.

See [Multi-Organization Scanning Documentation](docs/MULTI_ORG_SCANNING.md#per-organization-github-app-credentials) for details.

**Important**: Never commit secrets or credentials to the repository. Always use GitHub Secrets.

### Reporting Security Issues

If you discover a security vulnerability, please report it responsibly. Do not open a public issue.

## Release Process

**Important**: Create a GitHub release for all major changes.

### When to Create a Release

Create a release when you:
- Add new features or workflows
- Make significant security improvements
- Update dependencies or base images
- Change workflow behavior or configuration
- Fix critical bugs

### How to Create a Release

**Automated (Recommended)**: Push a version tag to automatically create a release:
```bash
git tag v1.x.x
git push origin v1.x.x
```
The workflow will automatically:
- **Create GitHub release** - For the tagged commit
- **Generate release notes** - From commit messages since last tag
- **Make release available** - For use in workflows

**Important**: Only tag commits that have already been built and verified on the main branch. The release workflow assumes the tagged commit is already working and tested.

**Manual Options**:
1. **Via GitHub UI**: Go to https://github.com/security-pillar-ai-poc/sparta/releases/new
2. **Via GitHub CLI**:
   ```bash
   gh release create v1.x.x --title "Sparta v1.x.x - [Description]" --notes "[Release notes]"
   ```

### Release Versioning

- **Major (v1.0.0)**: Breaking changes, major new features
- **Minor (v1.1.0)**: New features, enhancements (backward compatible)
- **Patch (v1.0.1)**: Bug fixes, minor improvements

### Release Notes Template

Include:
- **Features**: New functionality added
- **Security**: Security improvements or fixes
- **Improvements**: Enhancements to existing features
- **Bug Fixes**: Issues resolved

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Add your license here]

## Recent Updates

### v1.3.0 - Multi-Organization Support

**New Features:**
- ✅ Multi-organization scanning support
- ✅ Batch processing for large organizations (6k+ repos)
- ✅ State management with resume capability
- ✅ Enhanced error handling with automatic retries
- ✅ Exponential backoff for transient failures
- ✅ Parallel batch processing via matrix strategy

**Backward Compatibility:**
- ✅ Single-org mode still works (GITHUB_ORG)
- ✅ All existing workflows continue to function
- ✅ No breaking changes

**See**: [GitHub Issue #4](https://github.com/peleduri/sparta/issues/4) for details

## References

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Trivy GitHub Action](https://github.com/marketplace/actions/aqua-security-trivy)
- [GitHub Actions Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [GitHub Actions Matrix Strategy](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)

