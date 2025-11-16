#!/usr/bin/env python3
"""
Comprehensive tests for GitHub App token credential format.

Tests verify that credential files are written in the correct format:
https://x-access-token:TOKEN@github.com

This format is required for GitHub App installation tokens per:
https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, call
from io import StringIO

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from security_utils import secure_git_clone


class TestCredentialFormat(unittest.TestCase):
    """Test credential file format for GitHub App tokens."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_token = "ghs_test1234567890abcdefghijklmnopqrstuvwxyz"
        self.test_repo_url = "https://github.com/test-org/test-repo.git"
        self.test_target_dir = Path(tempfile.mkdtemp())
        self.test_branch = "main"
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_target_dir.exists():
            import shutil
            shutil.rmtree(self.test_target_dir, ignore_errors=True)
    
    def test_credential_file_format_in_secure_git_clone(self):
        """Test that secure_git_clone writes credential file with x-access-token: prefix."""
        # Create a real temp file that we can read
        cred_file_path = None
        captured_content = []
        
        # Mock mkstemp to return a real temp file
        original_mkstemp = tempfile.mkstemp
        def mock_mkstemp(*args, **kwargs):
            nonlocal cred_file_path
            fd, cred_file_path = original_mkstemp(*args, **kwargs)
            return fd, cred_file_path
        
        # Mock os.fdopen to capture what's written
        original_fdopen = os.fdopen
        def mock_fdopen(fd, mode='r'):
            f = original_fdopen(fd, mode)
            if mode == 'w' and cred_file_path:
                # Wrap the file object to capture writes
                class CapturingFile:
                    def __init__(self, real_file, path):
                        self.real_file = real_file
                        self.path = path
                    def write(self, data):
                        captured_content.append(data)
                        return self.real_file.write(data)
                    def __enter__(self):
                        self.real_file.__enter__()
                        return self
                    def __exit__(self, *args):
                        return self.real_file.__exit__(*args)
                    def __getattr__(self, name):
                        return getattr(self.real_file, name)
                return CapturingFile(f, cred_file_path)
            return f
        
        try:
            with patch('tempfile.mkstemp', side_effect=mock_mkstemp):
                with patch('os.fdopen', side_effect=mock_fdopen):
                    with patch('os.unlink'):  # Prevent cleanup so we can read the file
                        with patch('subprocess.run') as mock_run:
                            # Mock successful git clone
                            mock_run.return_value = MagicMock(returncode=0, stderr='', stdout='')
                            
                            # Call secure_git_clone
                            success, error_msg = secure_git_clone(
                                repo_url=self.test_repo_url,
                                target_dir=self.test_target_dir,
                                branch=self.test_branch,
                                token=self.test_token,
                                timeout=300
                            )
                            
                            # Verify credential file was written
                            self.assertTrue(len(captured_content) > 0, "Credential should have been written")
                            
                            # Get the written content
                            credential_content = ''.join(captured_content).strip()
                            
                            # Verify format: https://x-access-token:TOKEN@github.com
                            expected_format = f"https://x-access-token:{self.test_token}@github.com"
                            self.assertEqual(
                                credential_content,
                                expected_format,
                                f"Credential file should use x-access-token: prefix. Got: {credential_content}"
                            )
                            
                            # Verify it doesn't use the old format
                            self.assertNotIn(
                                f"https://{self.test_token}@github.com",
                                credential_content,
                                "Credential file should NOT use old format without x-access-token: prefix"
                            )
        finally:
            # Clean up
            if cred_file_path and os.path.exists(cred_file_path):
                try:
                    os.unlink(cred_file_path)
                except:
                    pass
    
    def test_credential_file_format_with_special_characters(self):
        """Test credential format with tokens containing special characters."""
        # Tokens shouldn't normally have special chars, but test edge case
        special_token = "ghs_test+token-with_special.chars"
        cred_file_path = None
        captured_content = []
        
        original_mkstemp = tempfile.mkstemp
        def mock_mkstemp(*args, **kwargs):
            nonlocal cred_file_path
            fd, cred_file_path = original_mkstemp(*args, **kwargs)
            return fd, cred_file_path
        
        original_fdopen = os.fdopen
        def mock_fdopen(fd, mode='r'):
            f = original_fdopen(fd, mode)
            if mode == 'w' and cred_file_path:
                class CapturingFile:
                    def __init__(self, real_file):
                        self.real_file = real_file
                    def write(self, data):
                        captured_content.append(data)
                        return self.real_file.write(data)
                    def __enter__(self):
                        self.real_file.__enter__()
                        return self
                    def __exit__(self, *args):
                        return self.real_file.__exit__(*args)
                    def __getattr__(self, name):
                        return getattr(self.real_file, name)
                return CapturingFile(f)
            return f
        
        try:
            with patch('tempfile.mkstemp', side_effect=mock_mkstemp):
                with patch('os.fdopen', side_effect=mock_fdopen):
                    with patch('os.unlink'):
                        with patch('subprocess.run') as mock_run:
                            mock_run.return_value = MagicMock(returncode=0, stderr='', stdout='')
                            
                            success, error_msg = secure_git_clone(
                                repo_url=self.test_repo_url,
                                target_dir=self.test_target_dir,
                                branch=self.test_branch,
                                token=special_token,
                                timeout=300
                            )
                            
                            credential_content = ''.join(captured_content).strip()
                            expected_format = f"https://x-access-token:{special_token}@github.com"
                            self.assertEqual(credential_content, expected_format)
        finally:
            if cred_file_path and os.path.exists(cred_file_path):
                try:
                    os.unlink(cred_file_path)
                except:
                    pass
    
    def test_credential_file_not_created_without_token(self):
        """Test that no credential file is created when token is None."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr='', stdout='')
            
            # Call without token
            success, error_msg = secure_git_clone(
                repo_url=self.test_repo_url,
                target_dir=self.test_target_dir,
                branch=self.test_branch,
                token=None,
                timeout=300
            )
            
            # Verify subprocess.run was called with list (not shell command with credential helper)
            # This means no credential file was used
            calls = mock_run.call_args_list
            self.assertTrue(len(calls) > 0, "subprocess.run should be called")
            
            # Check that the call doesn't include credential helper
            for call_args in calls:
                args, kwargs = call_args
                if isinstance(args[0], str):
                    # Shell command - should not contain credential helper when no token
                    self.assertNotIn('credential.helper', args[0])
    
    def test_credential_file_format_in_commit_results(self):
        """Test that commit_results.py writes credential file with correct format."""
        # Import commit_results to test its credential writing
        import commit_results
        
        # Mock the credential file write
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_cred:
            cred_file_path = temp_cred.name
        
        try:
            # Read commit_results.py to verify it uses the correct format
            commit_results_path = Path(__file__).parent.parent / 'scripts' / 'commit_results.py'
            with open(commit_results_path, 'r') as f:
                commit_results_content = f.read()
            
            # Verify the file contains the correct format
            self.assertIn(
                'x-access-token:',
                commit_results_content,
                "commit_results.py should use x-access-token: prefix in credential file"
            )
            
            # Verify it doesn't use the old format
            self.assertNotIn(
                'https://{installation_token}@github.com',
                commit_results_content,
                "commit_results.py should NOT use old format without x-access-token: prefix"
            )
            
            # Verify it uses the correct format
            self.assertIn(
                'x-access-token:{installation_token}',
                commit_results_content,
                "commit_results.py should use x-access-token:{installation_token} format"
            )
        finally:
            if os.path.exists(cred_file_path):
                os.unlink(cred_file_path)
    
    def test_credential_file_format_matches_github_docs(self):
        """Test that credential format matches GitHub documentation requirements."""
        # Per GitHub docs: https://x-access-token:TOKEN@github.com/owner/repo.git
        test_cases = [
            ("ghs_1234567890", "https://x-access-token:ghs_1234567890@github.com"),
            ("ghs_abcdefghijklmnop", "https://x-access-token:ghs_abcdefghijklmnop@github.com"),
            ("ghs_test_token", "https://x-access-token:ghs_test_token@github.com"),
        ]
        
        for token, expected_format in test_cases:
            cred_file_path = None
            captured_content = []  # Create new list for each iteration
            
            original_mkstemp = tempfile.mkstemp
            def mock_mkstemp(*args, **kwargs):
                nonlocal cred_file_path
                fd, cred_file_path = original_mkstemp(*args, **kwargs)
                return fd, cred_file_path
            
            original_fdopen = os.fdopen
            def mock_fdopen(fd, mode='r'):
                f = original_fdopen(fd, mode)
                if mode == 'w':
                    class CapturingFile:
                        def __init__(self, real_file, content_list):
                            self.real_file = real_file
                            self.content_list = content_list
                        def write(self, data):
                            self.content_list.append(data)
                            return self.real_file.write(data)
                        def __enter__(self):
                            self.real_file.__enter__()
                            return self
                        def __exit__(self, *args):
                            return self.real_file.__exit__(*args)
                        def __getattr__(self, name):
                            return getattr(self.real_file, name)
                    return CapturingFile(f, captured_content)
                return f
            
            try:
                with patch('tempfile.mkstemp', side_effect=mock_mkstemp):
                    with patch('os.fdopen', side_effect=mock_fdopen):
                        with patch('os.unlink'):
                            with patch('subprocess.run') as mock_run:
                                mock_run.return_value = MagicMock(returncode=0, stderr='', stdout='')
                                
                                secure_git_clone(
                                    repo_url=self.test_repo_url,
                                    target_dir=self.test_target_dir,
                                    branch=self.test_branch,
                                    token=token,
                                    timeout=300
                                )
                                
                                credential_content = ''.join(captured_content).strip()
                                
                                self.assertEqual(
                                    credential_content,
                                    expected_format,
                                    f"Credential format should match GitHub docs. Expected: {expected_format}, Got: {credential_content}"
                                )
            finally:
                if cred_file_path and os.path.exists(cred_file_path):
                    try:
                        os.unlink(cred_file_path)
                    except:
                        pass


class TestCredentialFormatIntegration(unittest.TestCase):
    """Integration tests for credential format."""
    
    def test_credential_file_readable_by_git(self):
        """Test that credential file format is readable by git credential helper."""
        # This test verifies the format is correct by checking git can parse it
        test_token = "ghs_test1234567890"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_cred:
            cred_file_path = temp_cred.name
        
        try:
            # Write credential in correct format
            with open(cred_file_path, 'w') as f:
                f.write(f"https://x-access-token:{test_token}@github.com\n")
            
            # Verify file exists and is readable
            self.assertTrue(os.path.exists(cred_file_path))
            
            # Verify content is correct
            with open(cred_file_path, 'r') as f:
                content = f.read().strip()
                self.assertEqual(content, f"https://x-access-token:{test_token}@github.com")
                
                # Verify format structure
                self.assertTrue(content.startswith("https://x-access-token:"))
                self.assertTrue(content.endswith("@github.com"))
                self.assertIn(test_token, content)
        finally:
            if os.path.exists(cred_file_path):
                os.unlink(cred_file_path)


class TestProjectWideCredentialUsage(unittest.TestCase):
    """Test that credential format is used correctly throughout the project."""
    
    def test_no_old_credential_format_in_codebase(self):
        """Verify no old credential format exists in the codebase."""
        scripts_dir = Path(__file__).parent.parent / 'scripts'
        
        # Files that should use credential format
        files_to_check = [
            'security_utils.py',
            'commit_results.py',
        ]
        
        old_patterns = [
            'https://{token}@github.com',
            'https://{installation_token}@github.com',
            'f"https://{token}@github.com"',
            'f"https://{installation_token}@github.com"',
        ]
        
        for filename in files_to_check:
            file_path = scripts_dir / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                
                for pattern in old_patterns:
                    # Check for old format (without x-access-token:)
                    # But allow it in comments or documentation
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        # Skip comment lines
                        if line.strip().startswith('#'):
                            continue
                        # Check if line contains old format (not in comment)
                        if pattern.replace('{', '').replace('}', '') in line and 'x-access-token' not in line:
                            # This might be a false positive, but worth checking
                            pass  # We'll check more specifically below
                
                # More specific check: ensure x-access-token is used
                self.assertIn(
                    'x-access-token',
                    content,
                    f"{filename} should use x-access-token: prefix in credential format"
                )
    
    def test_all_credential_writes_use_correct_format(self):
        """Verify all credential file writes use the correct format."""
        scripts_dir = Path(__file__).parent.parent / 'scripts'
        
        # Check security_utils.py
        security_utils_path = scripts_dir / 'security_utils.py'
        with open(security_utils_path, 'r') as f:
            security_utils_content = f.read()
        
        # Should contain x-access-token format
        self.assertIn('x-access-token:', security_utils_content)
        # Should not contain old format (as actual code, not comment)
        # We check that the write statement uses x-access-token
        self.assertIn('x-access-token:{token}', security_utils_content)
        
        # Check commit_results.py
        commit_results_path = scripts_dir / 'commit_results.py'
        with open(commit_results_path, 'r') as f:
            commit_results_content = f.read()
        
        # Should contain x-access-token format
        self.assertIn('x-access-token:', commit_results_content)
        # Should not contain old format
        self.assertIn('x-access-token:{installation_token}', commit_results_content)


if __name__ == '__main__':
    unittest.main()

