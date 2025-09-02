#!/usr/bin/env python3
"""
Security verification script for KireMisu backend.
This script checks that the security vulnerabilities have been properly addressed.
"""
import os
import re
import sys
from pathlib import Path


def check_file_content(file_path: str, patterns: dict) -> dict:
    """Check if file contains any of the security issues."""
    results = {}
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            for issue, pattern in patterns.items():
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    results[issue] = True
                else:
                    results[issue] = False
    except FileNotFoundError:
        results = {issue: "FILE_NOT_FOUND" for issue in patterns.keys()}
    return results


def main():
    """Run security checks on the codebase."""
    print("🔒 KireMisu Security Verification")
    print("=" * 40)
    
    # Security patterns to check for (these should NOT be found)
    security_issues = {
        "app/core/config.py": {
            "hardcoded_secret": r'SECRET_KEY.*=.*["\']development-secret-key',
            "default_password": r'POSTGRES_PASSWORD.*=.*["\']development["\']',
        },
        "app/api/v1/endpoints/auth.py": {
            "fake_users_db": r'fake_users_db\s*=\s*{[^}]*admin[^}]*}',
            "hardcoded_admin": r'["\']admin123["\']',
        },
        "app/main.py": {
            "wildcard_cors_methods": r'allow_methods.*=.*\[\s*["\*"]\s*\]',
            "wildcard_cors_headers": r'allow_headers.*=.*\[\s*["\*"]\s*\]',
        }
    }
    
    # Security features that SHOULD be present
    security_features = {
        "app/core/config.py": {
            "secret_key_required": r'SECRET_KEY:\s*str\s*#.*Required',
            "password_validation": r'if not postgres_user or not postgres_password',
        },
        "app/main.py": {
            "security_middleware": r'class SecurityHeadersMiddleware',
            "security_headers": r'X-Content-Type-Options.*nosniff',
            "specific_cors_methods": r'allow_methods.*=.*\[.*GET.*POST.*PUT.*DELETE.*OPTIONS.*\]',
        }
    }
    
    all_passed = True
    
    print("🚫 Checking for security issues (should be ABSENT):")
    for file_path, patterns in security_issues.items():
        print(f"\n📁 {file_path}")
        results = check_file_content(file_path, patterns)
        for issue, found in results.items():
            if found == "FILE_NOT_FOUND":
                print(f"  ⚠️  File not found: {issue}")
                all_passed = False
            elif found:
                print(f"  ❌ SECURITY ISSUE: {issue} found")
                all_passed = False
            else:
                print(f"  ✅ {issue} - not found (good)")
    
    print("\n" + "=" * 40)
    print("✅ Checking for security features (should be PRESENT):")
    for file_path, patterns in security_features.items():
        print(f"\n📁 {file_path}")
        results = check_file_content(file_path, patterns)
        for feature, found in results.items():
            if found == "FILE_NOT_FOUND":
                print(f"  ⚠️  File not found: {feature}")
                all_passed = False
            elif found:
                print(f"  ✅ {feature} - implemented")
            else:
                print(f"  ❌ MISSING: {feature}")
                all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All security checks passed!")
        return 0
    else:
        print("⚠️  Some security issues were found. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())