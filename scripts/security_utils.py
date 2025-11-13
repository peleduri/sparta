#!/usr/bin/env python3
"""
Security utility functions for Sparta project.

Provides:
- CVE ID validation
- Path sanitization to prevent directory traversal
- Secure git clone helper
"""

import re
import subprocess
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple


def validate_cve_id(cve_id: str) -> bool:
    """
    Validate CVE ID format.
    
    Valid format: CVE-YYYY-NNNN+ (e.g., CVE-2024-1234, CVE-2024-12345)
    
    Args:
        cve_id: CVE identifier to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not cve_id or not isinstance(cve_id, str):
        return False
    
    # CVE format: CVE-YYYY-NNNN+ where YYYY is year and NNNN+ is at least 4 digits
    pattern = r'^CVE-\d{4}-\d{4,}$'
    return bool(re.match(pattern, cve_id.upper()))


def sanitize_path(user_path: str, base_dir: Path) -> Path:
    """
    Sanitize user-provided path to prevent directory traversal attacks.
    
    Resolves the path and ensures it's within the base directory.
    
    Args:
        user_path: User-provided path (can be relative or contain ..)
        base_dir: Base directory that the path must be within
        
    Returns:
        Sanitized Path object
        
    Raises:
        ValueError: If path traversal is detected or path is invalid
    """
    if not user_path or not isinstance(user_path, str):
        raise ValueError("Path must be a non-empty string")
    
    # Convert to Path and resolve to absolute path
    base_dir = Path(base_dir).resolve()
    user_path = Path(user_path)
    
    # If relative, join with base_dir; if absolute, use as-is
    if user_path.is_absolute():
        resolved = user_path.resolve()
    else:
        resolved = (base_dir / user_path).resolve()
    
    # Check if resolved path is within base directory
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Path traversal detected: {user_path} resolves outside base directory")
    
    return resolved


def secure_git_clone(
    repo_url: str,
    target_dir: Path,
    branch: str = "main",
    token: Optional[str] = None,
    timeout: int = 300
) -> Tuple[bool, str]:
    """
    Securely clone a git repository without exposing token in URL or logs.
    
    Uses git credential helper to avoid embedding token in URL.
    
    Args:
        repo_url: Repository URL (without token, e.g., https://github.com/org/repo.git)
        target_dir: Directory to clone into
        branch: Branch to checkout (default: main)
        token: GitHub token for authentication (optional)
        timeout: Timeout in seconds (default: 300)
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    target_dir = Path(target_dir)
    
    try:
        # Create temporary credential file if token is provided
        cred_file = None
        if token:
            # Create temporary credential file
            cred_fd, cred_file = tempfile.mkstemp(text=True)
            try:
                # Write credential in format: https://token@github.com
                with os.fdopen(cred_fd, 'w') as f:
                    f.write(f"https://{token}@github.com\n")
                
                # Configure git to use credential file
                subprocess.run(
                    ['git', 'config', '--global', 'credential.helper', f'store --file={cred_file}'],
                    check=True,
                    capture_output=True,
                    timeout=10
                )
            except Exception:
                if cred_file and os.path.exists(cred_file):
                    os.unlink(cred_file)
                raise
        
        # Clone repository
        result = subprocess.run(
            ['git', 'clone', '--depth', '1', '--branch', branch, repo_url, str(target_dir)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Clean up credential file
        if cred_file and os.path.exists(cred_file):
            try:
                os.unlink(cred_file)
            except Exception:
                pass
        
        # Reset credential helper
        if token:
            try:
                subprocess.run(
                    ['git', 'config', '--global', '--unset', 'credential.helper'],
                    capture_output=True,
                    timeout=10
                )
            except Exception:
                pass
        
        if result.returncode == 0:
            return (True, "")
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            # Sanitize error message to remove any potential token exposure
            error_msg = error_msg.replace(token, "***") if token else error_msg
            return (False, error_msg)
            
    except subprocess.TimeoutExpired:
        return (False, f"Git clone timeout after {timeout} seconds")
    except Exception as e:
        error_msg = str(e)
        # Sanitize error message
        if token:
            error_msg = error_msg.replace(token, "***")
        return (False, error_msg)


def sanitize_string_input(input_str: str, max_length: int = 1000, allowed_chars: Optional[str] = None) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        allowed_chars: Optional regex pattern of allowed characters
        
    Returns:
        Sanitized string
        
    Raises:
        ValueError: If input is invalid
    """
    if not isinstance(input_str, str):
        raise ValueError("Input must be a string")
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\n\r\t')
    
    # Check length
    if len(sanitized) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length}")
    
    # Check allowed characters if pattern provided
    if allowed_chars:
        if not re.match(allowed_chars, sanitized):
            raise ValueError(f"Input contains invalid characters")
    
    return sanitized

