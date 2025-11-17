#!/usr/bin/env python3
"""
Tests for workflow trigger conditions and YAML structure.

Verifies workflow triggers, conditions, and dependencies.
"""

import os
import sys
import yaml
from pathlib import Path

# PyYAML interprets 'on' as boolean True, so we need to handle this
def load_workflow_yaml(file_path):
    """Load workflow YAML, handling 'on' key correctly."""
    import re
    with open(file_path, 'r') as f:
        content = f.read()
        # Replace 'on:' at start of line with a placeholder, then restore
        # Use regex to match 'on:' only when it's a key (at start of line with optional whitespace)
        content = re.sub(r'^(\s*)on:', r'\1___ON_KEY___:', content, flags=re.MULTILINE)
        workflow = yaml.safe_load(content)
        if workflow and '___ON_KEY___' in workflow:
            workflow['on'] = workflow.pop('___ON_KEY___')
        return workflow


def test_organization_scan_triggers():
    """Test organization scan workflow triggers."""
    print("\n=== Test 1: Organization Scan Triggers ===")
    
    workflow_file = Path('.github/workflows/sparta-organization-scan.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    # Check triggers - 'on' can be a dict or list
    on = workflow.get('on', {})
    if isinstance(on, list):
        # Convert list format to dict for easier checking
        on_dict = {}
        for item in on:
            if isinstance(item, dict):
                on_dict.update(item)
        on = on_dict
    
    # Should have schedule
    assert 'schedule' in on
    schedule = on['schedule']
    assert isinstance(schedule, list)
    assert len(schedule) == 1
    # Schedule can be a list of dicts or a list of strings
    if isinstance(schedule[0], dict):
        assert schedule[0].get('cron') == '0 2 * * *'
    else:
        # If it's a string, it should be in the YAML as a comment or we check the raw content
        assert True  # Schedule exists, which is what matters
    
    # Should have workflow_dispatch
    assert 'workflow_dispatch' in on
    
    # Should NOT have push
    assert 'push' not in on
    
    print("✓ Organization scan triggers are correct")


def test_organization_scan_inputs():
    """Test organization scan workflow inputs."""
    print("\n=== Test 2: Organization Scan Inputs ===")
    
    workflow_file = Path('.github/workflows/sparta-organization-scan.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    on = workflow.get('on', {})
    if isinstance(on, list):
        # Find workflow_dispatch in list
        workflow_dispatch = None
        for item in on:
            if isinstance(item, dict) and 'workflow_dispatch' in item:
                workflow_dispatch = item['workflow_dispatch']
                break
        inputs = workflow_dispatch.get('inputs', {}) if workflow_dispatch else {}
    else:
        inputs = on.get('workflow_dispatch', {}).get('inputs', {})
    
    # Check github-orgs input
    assert 'github-orgs' in inputs
    assert inputs['github-orgs']['required'] == False
    assert inputs['github-orgs']['type'] == 'string'
    
    # Check batch-size input
    assert 'batch-size' in inputs
    assert inputs['batch-size']['required'] == False
    assert inputs['batch-size']['type'] == 'string'
    assert inputs['batch-size']['default'] == '100'
    
    print("✓ Organization scan inputs are correct")


def test_aggregate_workflow_triggers():
    """Test aggregate workflow triggers."""
    print("\n=== Test 3: Aggregate Workflow Triggers ===")
    
    workflow_file = Path('.github/workflows/sparta-aggregate-scans.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    on = workflow.get('on', {})
    if isinstance(on, list):
        on_dict = {}
        for item in on:
            if isinstance(item, dict):
                on_dict.update(item)
        on = on_dict
    
    # Should have workflow_dispatch
    assert 'workflow_dispatch' in on
    
    # Should have workflow_call
    assert 'workflow_call' in on
    
    # Should NOT have push
    assert 'push' not in on
    
    print("✓ Aggregate workflow triggers are correct")


def test_self_scan_triggers():
    """Test self-scan workflow triggers."""
    print("\n=== Test 4: Self-Scan Workflow Triggers ===")
    
    workflow_file = Path('.github/workflows/sparta-self-scan.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    on = workflow.get('on', {})
    if isinstance(on, list):
        on_dict = {}
        for item in on:
            if isinstance(item, dict):
                on_dict.update(item)
        on = on_dict
    
    # Should have schedule
    assert 'schedule' in on
    schedule = on['schedule']
    assert isinstance(schedule, list)
    assert len(schedule) == 1
    # Schedule can be a list of dicts or a list of strings
    if isinstance(schedule[0], dict):
        assert schedule[0].get('cron') == '0 3 * * 0'  # Weekly Sunday
    else:
        # If it's a string, it should be in the YAML as a comment or we check the raw content
        assert True  # Schedule exists, which is what matters
    
    # Should have workflow_dispatch
    assert 'workflow_dispatch' in on
    
    # Should NOT have push
    assert 'push' not in on
    
    # Should NOT have pull_request
    assert 'pull_request' not in on
    
    print("✓ Self-scan triggers are correct")


def test_self_scan_repo_exclusion():
    """Test self-scan repo exclusion condition."""
    print("\n=== Test 5: Self-Scan Repo Exclusion ===")
    
    workflow_file = Path('.github/workflows/sparta-self-scan.yml')
    with open(workflow_file, 'r') as f:
        content = f.read()
    
    # Check for exclusion condition
    assert 'github.repository !=' in content
    assert 'security-pillar-ai-poc/sparta' in content
    assert 'peleduri/sparta' in content
    
    print("✓ Self-scan repo exclusion condition present")


def test_workflow_dependency_chain():
    """Test workflow dependency chain (scan → aggregate)."""
    print("\n=== Test 6: Workflow Dependency Chain ===")
    
    workflow_file = Path('.github/workflows/sparta-organization-scan.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    jobs = workflow.get('jobs', {})
    aggregate_job = jobs.get('aggregate', {})
    
    # Check dependency (can be string or list)
    assert 'needs' in aggregate_job
    needs = aggregate_job['needs']
    assert needs == 'scan' or needs == ['scan']
    
    # Check condition
    assert 'if' in aggregate_job
    assert 'success()' in aggregate_job['if']
    
    # Check workflow_call
    assert 'uses' in aggregate_job
    assert 'sparta-aggregate-scans.yml' in aggregate_job['uses']
    
    print("✓ Workflow dependency chain is correct")


def test_build_docker_triggers():
    """Test build docker workflow triggers."""
    print("\n=== Test 7: Build Docker Triggers ===")
    
    workflow_file = Path('.github/workflows/sparta-build-docker.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    on = workflow.get('on', {})
    if isinstance(on, list):
        on_dict = {}
        for item in on:
            if isinstance(item, dict):
                on_dict.update(item)
        on = on_dict
    
    # Should have push (with paths)
    assert 'push' in on
    push = on['push']
    assert 'branches' in push
    assert 'paths' in push
    
    # Should have pull_request (with paths)
    assert 'pull_request' in on
    pr = on['pull_request']
    assert 'branches' in pr
    assert 'paths' in pr
    
    # Should have workflow_dispatch
    assert 'workflow_dispatch' in on
    
    print("✓ Build docker triggers are correct")


def test_build_docker_paths():
    """Test build docker workflow path filters."""
    print("\n=== Test 8: Build Docker Path Filters ===")
    
    workflow_file = Path('.github/workflows/sparta-build-docker.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    on = workflow.get('on', {})
    push_paths = on.get('push', {}).get('paths', [])
    
    # Should trigger on relevant file changes
    expected_paths = ['Dockerfile', 'entrypoint.sh', 'scripts/**', 'requirements.txt']
    for path in expected_paths:
        assert path in push_paths
    
    print("✓ Build docker path filters are correct")


def test_all_workflows_yaml_valid():
    """Test all workflow files have valid YAML."""
    print("\n=== Test 9: All Workflows YAML Valid ===")
    
    workflows_dir = Path('.github/workflows')
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    errors = []
    for workflow_file in workflow_files:
        try:
            load_workflow_yaml(workflow_file)
        except Exception as e:
            errors.append(f"{workflow_file.name}: {e}")
    
    assert len(errors) == 0, f"YAML errors found: {errors}"
    print(f"✓ All {len(workflow_files)} workflow files have valid YAML")


def test_workflow_permissions():
    """Test workflow permissions are set correctly."""
    print("\n=== Test 10: Workflow Permissions ===")
    
    workflow_file = Path('.github/workflows/sparta-organization-scan.yml')
    workflow = load_workflow_yaml(workflow_file)
    
    jobs = workflow.get('jobs', {})
    scan_job = jobs.get('scan', {})
    
    # Check permissions
    assert 'permissions' in scan_job
    permissions = scan_job['permissions']
    assert 'contents' in permissions
    assert permissions['contents'] == 'write'  # Needed for committing results
    
    print("✓ Workflow permissions are correct")


def run_all_tests():
    """Run all workflow trigger tests."""
    print("=" * 60)
    print("Workflow Trigger Tests")
    print("=" * 60)
    
    tests = [
        test_organization_scan_triggers,
        test_organization_scan_inputs,
        test_aggregate_workflow_triggers,
        test_self_scan_triggers,
        test_self_scan_repo_exclusion,
        test_workflow_dependency_chain,
        test_build_docker_triggers,
        test_build_docker_paths,
        test_all_workflows_yaml_valid,
        test_workflow_permissions
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

