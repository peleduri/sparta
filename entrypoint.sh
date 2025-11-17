#!/bin/bash
set -e

# Main entrypoint script for Sparta Docker container
# Handles different commands: get-repos, scan-repos, commit-results, query-cve, aggregate-scans

COMMAND="${1:-help}"

case "$COMMAND" in
    get-repos)
        python3 /app/scripts/get_repos.py
        ;;
    scan-repos)
        python3 /app/scripts/scan_repos.py
        ;;
    commit-results)
        python3 /app/scripts/commit_results.py
        ;;
    query-cve)
        # Handle CVE ID as argument or environment variable
        if [ -n "$2" ]; then
            python3 /app/scripts/query-cve.py "$2"
        else
            python3 /app/scripts/query-cve.py
        fi
        ;;
    aggregate-scans)
        python3 /app/scripts/aggregate-scans.py
        ;;
    batch-repos)
        python3 /app/scripts/batch_repos.py
        ;;
    scan-state)
        python3 /app/scripts/scan_state.py "${@:2}"
        ;;
    orchestrate-scan)
        python3 /app/scripts/orchestrate_scan.py "${@:2}"
        ;;
    help|--help|-h)
        echo "Sparta - Vulnerability Scanning Tool"
        echo ""
        echo "Usage: docker run <image> <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  get-repos          Get all organization repositories"
        echo "  scan-repos         Scan all repositories for vulnerabilities"
        echo "  commit-results     Commit scan results to repository"
        echo "  query-cve [CVE]    Query for specific CVE across all scans"
        echo "  aggregate-scans    Aggregate and index scan results"
        echo "  batch-repos        Split repositories into batches for parallel processing"
        echo "  scan-state [cmd]   Manage scan state (init, completed, failed, summary)"
        echo "  orchestrate-scan   Run complete scan orchestration (single or multi-org)"
        echo "  help              Show this help message"
        echo ""
        echo "Environment variables:"
        echo "  GITHUB_ORG         GitHub organization name (single org)"
        echo "  GITHUB_ORGS        GitHub organization names (comma-separated, multi-org)"
        echo "  GITHUB_APP_TOKEN   GitHub App installation token"
        echo "  BATCH_SIZE         Batch size for parallel processing (default: 100)"
        echo "  MAX_RETRIES        Maximum retry attempts for failed repos (default: 3)"
        echo "  GITHUB_REPOSITORY  Current repository (org/repo)"
        echo "  GITHUB_WORKSPACE   Workspace directory (for Trivy cache)"
        echo "  REPORTS_DIR        Directory for vulnerability reports (default: vulnerability-reports)"
        echo "  OUTPUT_DIR         Output directory for aggregated results (default: aggregated)"
        echo "  CVE_ID             CVE identifier for query-cve command"
        echo "  OUTPUT_FORMAT      Output format for query-cve (table or json, default: table)"
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run 'help' for usage information"
        exit 1
        ;;
esac

