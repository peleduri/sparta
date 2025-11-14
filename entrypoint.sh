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
        echo "  help              Show this help message"
        echo ""
        echo "Environment variables:"
        echo "  GITHUB_ORG         GitHub organization name"
        echo "  GITHUB_APP_TOKEN   GitHub App installation token"
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

