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


def validate_org_name(name: str) -> str:
    """
    Validate organization name format.
    
    GitHub org names: alphanumeric, hyphens, underscores, max 39 chars
    
    Args:
        name: Organization name to validate
        
    Returns:
        Sanitized organization name
        
    Raises:
        ValueError: If organization name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError("Organization name must be a non-empty string")
    # GitHub org names: alphanumeric, hyphens, underscores, max 39 chars
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-_]*[a-zA-Z0-9])?$', name):
        raise ValueError(f"Invalid organization name format: {name}")
    if len(name) > 39:
        raise ValueError(f"Organization name too long: {name}")
    return sanitize_string_input(name, max_length=39)


def validate_repo_name(name: str) -> str:
    """
    Validate repository name format (single repo name, no org prefix).
    
    GitHub repo names: alphanumeric, hyphens, underscores, dots, max 100 chars
    
    Args:
        name: Repository name to validate
        
    Returns:
        Sanitized repository name
        
    Raises:
        ValueError: If repository name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError("Repository name must be a non-empty string")
    # GitHub repo names: alphanumeric, hyphens, underscores, dots, max 100 chars
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$', name):
        raise ValueError(f"Invalid repository name format: {name}")
    if len(name) > 100:
        raise ValueError(f"Repository name too long: {name}")
    return sanitize_string_input(name, max_length=100)


def validate_repo_full_name(full_name: str) -> str:
    """
    Validate full repository name format (org/repo).
    
    Args:
        full_name: Full repository name in format 'org/repo'
        
    Returns:
        Sanitized full repository name
        
    Raises:
        ValueError: If full repository name is invalid
    """
    if not full_name or not isinstance(full_name, str):
        raise ValueError("Repository full name must be a non-empty string")
    # Full name format: org/repo
    if '/' not in full_name:
        raise ValueError(f"Full repository name must be in format 'org/repo': {full_name}")
    parts = full_name.split('/', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid full repository name format: {full_name}")
    org_part, repo_part = parts
    # Validate org part
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-_]*[a-zA-Z0-9])?$', org_part):
        raise ValueError(f"Invalid organization name in full name: {full_name}")
    # Validate repo part
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$', repo_part):
        raise ValueError(f"Invalid repository name in full name: {full_name}")
    if len(full_name) > 200:  # org (39) + / + repo (100) + buffer
        raise ValueError(f"Full repository name too long: {full_name}")
    return sanitize_string_input(full_name, max_length=200)


def sanitize_error_message(msg, tokens_to_sanitize: list) -> str:
    """
    Remove all tokens from error messages to prevent token exposure.
    
    Args:
        msg: Error message to sanitize
        tokens_to_sanitize: List of tokens to remove from the message
        
    Returns:
        Sanitized error message
    """
    if not msg or not isinstance(msg, str):
        return str(msg) if msg else ""
    sanitized = msg
    for token in tokens_to_sanitize:
        if token:
            sanitized = sanitized.replace(token, "***")
    return sanitized

