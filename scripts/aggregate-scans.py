#!/usr/bin/env python3
"""
Aggregate and index Trivy scan results for faster querying.

This script processes all stored scan results and creates:
- Summary statistics
- CVE index for faster lookups
- Repository vulnerability summary

Usage:
    python3 aggregate-scans.py
    python3 aggregate-scans.py --reports-dir vulnerability-reports --output-dir aggregated
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Set


def load_scan_reports(reports_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all scan reports from the reports directory.
    
    Args:
        reports_dir: Directory containing vulnerability reports
        
    Returns:
        List of report data with metadata
    """
    reports = []
    
    if not reports_dir.exists():
        print(f"Error: Reports directory '{reports_dir}' does not exist", file=sys.stderr)
        return reports
    
    for report_file in reports_dir.rglob('trivy-report.json'):
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            
            # Extract metadata from path
            parts = report_file.parts
            if len(parts) >= 4:
                org = parts[-4] if len(parts) >= 4 else 'unknown'
                repo = parts[-3] if len(parts) >= 3 else 'unknown'
                scan_date = parts[-2] if len(parts) >= 2 else 'unknown'
            else:
                org = 'unknown'
                repo = 'unknown'
                scan_date = 'unknown'
            
            reports.append({
                'file': str(report_file),
                'org': org,
                'repo': repo,
                'scan_date': scan_date,
                'data': report_data
            })
        
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse {report_file}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Warning: Error processing {report_file}: {e}", file=sys.stderr)
            continue
    
    return reports


def aggregate_statistics(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate statistics from all scan reports.
    
    Args:
        reports: List of report data
        
    Returns:
        Aggregated statistics
    """
    stats = {
        'total_scans': 0,
        'total_repositories': set(),
        'total_orgs': set(),
        'scan_dates': set(),
        'cve_index': defaultdict(list),  # CVE -> list of occurrences
        'repo_vulnerabilities': defaultdict(lambda: {
            'total': 0,
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'cves': set()
        }),
        'severity_distribution': defaultdict(int),
        'package_vulnerabilities': defaultdict(lambda: {
            'cves': set(),
            'repos': set()
        })
    }
    
    for report in reports:
        if 'error' in report['data']:
            continue
        
        stats['total_scans'] += 1
        stats['total_repositories'].add(f"{report['org']}/{report['repo']}")
        stats['total_orgs'].add(report['org'])
        stats['scan_dates'].add(report['scan_date'])
        
        repo_key = f"{report['org']}/{report['repo']}"
        
        # Process vulnerabilities
        if 'Results' in report['data']:
            for result in report['data'].get('Results', []):
                if 'Vulnerabilities' in result:
                    for vuln in result['Vulnerabilities']:
                        cve_id = vuln.get('VulnerabilityID', '')
                        severity = vuln.get('Severity', 'UNKNOWN').upper()
                        pkg_name = vuln.get('PkgName', 'unknown')
                        
                        if cve_id:
                            # Add to CVE index
                            stats['cve_index'][cve_id].append({
                                'repository': repo_key,
                                'org': report['org'],
                                'repo': report['repo'],
                                'scan_date': report['scan_date'],
                                'severity': severity,
                                'package': pkg_name,
                                'package_version': vuln.get('InstalledVersion', ''),
                                'fixed_version': vuln.get('FixedVersion', ''),
                            })
                            
                            # Update repository stats
                            stats['repo_vulnerabilities'][repo_key]['total'] += 1
                            stats['repo_vulnerabilities'][repo_key]['cves'].add(cve_id)
                            if severity == 'CRITICAL':
                                stats['repo_vulnerabilities'][repo_key]['critical'] += 1
                            elif severity == 'HIGH':
                                stats['repo_vulnerabilities'][repo_key]['high'] += 1
                            elif severity == 'MEDIUM':
                                stats['repo_vulnerabilities'][repo_key]['medium'] += 1
                            elif severity == 'LOW':
                                stats['repo_vulnerabilities'][repo_key]['low'] += 1
                            
                            # Update severity distribution
                            stats['severity_distribution'][severity] += 1
                            
                            # Update package stats
                            stats['package_vulnerabilities'][pkg_name]['cves'].add(cve_id)
                            stats['package_vulnerabilities'][pkg_name]['repos'].add(repo_key)
    
    # Convert sets to lists for JSON serialization
    stats['total_repositories'] = sorted(list(stats['total_repositories']))
    stats['total_orgs'] = sorted(list(stats['total_orgs']))
    stats['scan_dates'] = sorted(list(stats['scan_dates']))
    
    # Convert CVE index sets
    for repo_key in stats['repo_vulnerabilities']:
        stats['repo_vulnerabilities'][repo_key]['cves'] = sorted(list(stats['repo_vulnerabilities'][repo_key]['cves']))
    
    for pkg_name in stats['package_vulnerabilities']:
        stats['package_vulnerabilities'][pkg_name]['cves'] = sorted(list(stats['package_vulnerabilities'][pkg_name]['cves']))
        stats['package_vulnerabilities'][pkg_name]['repos'] = sorted(list(stats['package_vulnerabilities'][pkg_name]['repos']))
    
    return stats


def generate_summary_report(stats: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary report.
    
    Args:
        stats: Aggregated statistics
        
    Returns:
        Formatted summary report
    """
    lines = []
    lines.append("=" * 80)
    lines.append("Vulnerability Scan Aggregation Summary")
    lines.append("=" * 80)
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("\nOverall Statistics:")
    lines.append(f"  Total Scans: {stats['total_scans']}")
    lines.append(f"  Total Repositories: {len(stats['total_repositories'])}")
    lines.append(f"  Total Organizations: {len(stats['total_orgs'])}")
    lines.append(f"  Scan Date Range: {min(stats['scan_dates'])} to {max(stats['scan_dates'])}")
    lines.append(f"  Unique CVEs Found: {len(stats['cve_index'])}")
    
    lines.append("\nSeverity Distribution:")
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']:
        count = stats['severity_distribution'].get(severity, 0)
        if count > 0:
            lines.append(f"  {severity}: {count}")
    
    # Top repositories by vulnerability count
    lines.append("\nTop 10 Repositories by Vulnerability Count:")
    sorted_repos = sorted(
        stats['repo_vulnerabilities'].items(),
        key=lambda x: x[1]['total'],
        reverse=True
    )[:10]
    
    for repo, repo_stats in sorted_repos:
        lines.append(f"  {repo}: {repo_stats['total']} vulnerabilities "
                    f"(C: {repo_stats['critical']}, H: {repo_stats['high']}, "
                    f"M: {repo_stats['medium']}, L: {repo_stats['low']})")
    
    # Most common CVEs
    lines.append("\nTop 10 Most Common CVEs:")
    sorted_cves = sorted(
        stats['cve_index'].items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:10]
    
    for cve_id, occurrences in sorted_cves:
        lines.append(f"  {cve_id}: Found in {len(occurrences)} repository scan(s)")
    
    lines.append("\n" + "=" * 80)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Aggregate and index Trivy scan results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 aggregate-scans.py
  python3 aggregate-scans.py --reports-dir ./vulnerability-reports --output-dir ./aggregated
        """
    )
    
    parser.add_argument(
        '--reports-dir',
        type=Path,
        default=Path('vulnerability-reports'),
        help='Directory containing vulnerability reports (default: vulnerability-reports)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('aggregated'),
        help='Output directory for aggregated data (default: aggregated)'
    )
    
    args = parser.parse_args()
    
    print("Loading scan reports...")
    reports = load_scan_reports(args.reports_dir)
    
    if not reports:
        print("No reports found.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loaded {len(reports)} scan reports")
    print("Aggregating statistics...")
    
    stats = aggregate_statistics(reports)
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save aggregated data
    stats_file = args.output_dir / 'statistics.json'
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Saved statistics to {stats_file}")
    
    # Save CVE index
    cve_index_file = args.output_dir / 'cve-index.json'
    with open(cve_index_file, 'w') as f:
        json.dump(dict(stats['cve_index']), f, indent=2)
    print(f"Saved CVE index to {cve_index_file}")
    
    # Save repository summary
    repo_summary_file = args.output_dir / 'repository-summary.json'
    with open(repo_summary_file, 'w') as f:
        json.dump(dict(stats['repo_vulnerabilities']), f, indent=2)
    print(f"Saved repository summary to {repo_summary_file}")
    
    # Generate and save summary report
    summary_report = generate_summary_report(stats)
    summary_file = args.output_dir / 'summary.txt'
    with open(summary_file, 'w') as f:
        f.write(summary_report)
    print(f"Saved summary report to {summary_file}")
    
    # Print summary to console
    print("\n" + summary_report)
    
    print(f"\nAggregation complete. Output saved to {args.output_dir}/")


if __name__ == '__main__':
    main()

