#!/usr/bin/env python3
"""
Query script to search for specific CVEs across all stored Trivy scan results.

Usage:
    python3 query-cve.py CVE-2024-1234
    python3 query-cve.py CVE-2024-1234 --format json
    python3 query-cve.py CVE-2024-1234 --reports-dir vulnerability-reports
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Import security utilities
try:
    from security_utils import validate_cve_id, sanitize_path
except ImportError:
    # Fallback if running from different directory
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from security_utils import validate_cve_id, sanitize_path


def find_cve_in_reports(cve_id: str, reports_dir: Path) -> List[Dict[str, Any]]:
    """
    Search for a CVE across all Trivy scan reports.
    
    Args:
        cve_id: CVE identifier (e.g., 'CVE-2024-1234')
        reports_dir: Directory containing vulnerability reports
        
    Returns:
        List of findings containing the CVE
    """
    findings = []
    
    if not reports_dir.exists():
        print(f"Error: Reports directory '{reports_dir}' does not exist", file=sys.stderr)
        return findings
    
    # Walk through all report files
    for report_file in reports_dir.rglob('trivy-report.json'):
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            
            # Extract repository info from path
            # Path format: vulnerability-reports/{org}/{repo}/{date}/trivy-report.json
            parts = report_file.parts
            if len(parts) >= 4:
                org = parts[-4] if len(parts) >= 4 else 'unknown'
                repo = parts[-3] if len(parts) >= 3 else 'unknown'
                scan_date = parts[-2] if len(parts) >= 2 else 'unknown'
            else:
                org = 'unknown'
                repo = 'unknown'
                scan_date = 'unknown'
            
            # Check if report has error
            if 'error' in report_data:
                continue
            
            # Search for CVE in results
            if 'Results' in report_data:
                for result in report_data.get('Results', []):
                    if 'Vulnerabilities' in result:
                        for vuln in result['Vulnerabilities']:
                            if vuln.get('VulnerabilityID') == cve_id:
                                finding = {
                                    'cve': cve_id,
                                    'repository': f"{org}/{repo}",
                                    'org': org,
                                    'repo': repo,
                                    'scan_date': scan_date,
                                    'severity': vuln.get('Severity', 'UNKNOWN'),
                                    'package': vuln.get('PkgName', 'unknown'),
                                    'package_version': vuln.get('InstalledVersion', 'unknown'),
                                    'title': vuln.get('Title', ''),
                                    'description': vuln.get('Description', ''),
                                    'fixed_version': vuln.get('FixedVersion', ''),
                                    'published_date': vuln.get('PublishedDate', ''),
                                    'last_modified_date': vuln.get('LastModifiedDate', ''),
                                }
                                findings.append(finding)
        
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse {report_file}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Warning: Error processing {report_file}: {e}", file=sys.stderr)
            continue
    
    return findings


def format_output(findings: List[Dict[str, Any]], output_format: str = 'table') -> str:
    """
    Format findings for output.
    
    Args:
        findings: List of findings
        output_format: 'table' or 'json'
        
    Returns:
        Formatted string
    """
    if output_format == 'json':
        return json.dumps(findings, indent=2)
    
    # Table format
    if not findings:
        return f"No findings for CVE in scanned repositories."
    
    lines = []
    lines.append(f"\nFound {len(findings)} occurrence(s) of CVE across repositories:\n")
    lines.append("=" * 100)
    lines.append(f"{'Repository':<40} {'Severity':<10} {'Package':<30} {'Version':<15} {'Scan Date':<12}")
    lines.append("=" * 100)
    
    for finding in findings:
        repo = finding['repository']
        severity = finding['severity']
        pkg = finding['package'][:28] + '..' if len(finding['package']) > 30 else finding['package']
        version = finding['package_version'][:13] + '..' if len(finding['package_version']) > 15 else finding['package_version']
        scan_date = finding['scan_date']
        
        lines.append(f"{repo:<40} {severity:<10} {pkg:<30} {version:<15} {scan_date:<12}")
    
    lines.append("=" * 100)
    lines.append("\nDetailed information:")
    lines.append("-" * 100)
    
    for i, finding in enumerate(findings, 1):
        lines.append(f"\n{i}. Repository: {finding['repository']}")
        lines.append(f"   CVE: {finding['cve']}")
        lines.append(f"   Severity: {finding['severity']}")
        lines.append(f"   Package: {finding['package']} (version: {finding['package_version']})")
        if finding.get('fixed_version'):
            lines.append(f"   Fixed Version: {finding['fixed_version']}")
        if finding.get('title'):
            lines.append(f"   Title: {finding['title']}")
        if finding.get('published_date'):
            lines.append(f"   Published: {finding['published_date']}")
        lines.append(f"   Scan Date: {finding['scan_date']}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Query CVEs across all stored Trivy scan results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 query-cve.py CVE-2024-1234
  python3 query-cve.py CVE-2024-1234 --format json
  python3 query-cve.py CVE-2024-1234 --reports-dir ./vulnerability-reports
        """
    )
    
    parser.add_argument(
        'cve_id',
        help='CVE identifier (e.g., CVE-2024-1234)'
    )
    
    parser.add_argument(
        '--reports-dir',
        type=Path,
        default=Path('vulnerability-reports'),
        help='Directory containing vulnerability reports (default: vulnerability-reports)'
    )
    
    parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    
    args = parser.parse_args()
    
    # Validate CVE format
    cve_id_upper = args.cve_id.upper()
    if not validate_cve_id(cve_id_upper):
        print(f"Error: Invalid CVE ID format: '{args.cve_id}'. Expected format: CVE-YYYY-NNNN+", file=sys.stderr)
        sys.exit(1)
    
    # Sanitize and validate reports directory path
    try:
        base_dir = Path.cwd()
        sanitized_reports_dir = sanitize_path(str(args.reports_dir), base_dir)
    except ValueError as e:
        print(f"Error: Invalid reports directory path: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Search for CVE
    findings = find_cve_in_reports(cve_id_upper, sanitized_reports_dir)
    
    # Format and print output
    output = format_output(findings, args.format)
    print(output)
    
    # Exit with appropriate code
    sys.exit(0 if findings else 1)


if __name__ == '__main__':
    main()

