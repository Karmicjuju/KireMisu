#!/usr/bin/env python3
"""
Generate secure keys and passwords for KireMisu authentication system.

This script helps administrators generate cryptographically secure keys
and passwords for their KireMisu installation.
"""

import secrets
import base64
import string
import sys
import os
from typing import Dict, Any


def generate_jwt_secret() -> str:
    """Generate a secure JWT secret key."""
    # Generate 64 random bytes and encode as base64
    random_bytes = secrets.token_bytes(64)
    return base64.b64encode(random_bytes).decode('utf-8')


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password."""
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Ensure at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    
    # Fill remaining length with random characters from all sets
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # Shuffle the password characters
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


def generate_vapid_keys() -> Dict[str, str]:
    """Generate VAPID keys for push notifications."""
    try:
        from py_vapid import Vapid
        
        vapid = Vapid()
        vapid.generate_keys()
        
        # Handle different versions of py_vapid
        try:
            public_key = vapid.public_key_bytes().hex()
            private_key = vapid.private_key_bytes().hex()
        except AttributeError:
            # Fallback for older versions
            public_key = vapid.public_key.hex() if hasattr(vapid, 'public_key') else "generated_key_placeholder"
            private_key = vapid.private_key.hex() if hasattr(vapid, 'private_key') else "generated_key_placeholder"
        
        return {
            "public_key": public_key,
            "private_key": private_key
        }
    except ImportError:
        return {
            "public_key": "# py_vapid not installed - run: uv add py-vapid",
            "private_key": "# py_vapid not installed - run: uv add py-vapid"
        }
    except Exception as e:
        return {
            "public_key": f"# VAPID key generation error: {e}",
            "private_key": f"# VAPID key generation error: {e}"
        }


def validate_existing_secret(secret: str) -> bool:
    """Validate if existing secret meets security requirements."""
    if len(secret) < 32:
        return False
    
    # Check if it's just a placeholder
    placeholders = [
        "your-secret-key-here",
        "change-in-production",
        "REPLACE_WITH_SECURE",
        "SECRET_KEY_GENERATED",
    ]
    
    for placeholder in placeholders:
        if placeholder.lower() in secret.lower():
            return False
    
    return True


def main():
    """Main function to generate and display secure keys."""
    print("🔐 KireMisu Security Key Generator")
    print("=" * 50)
    print()
    
    # Check if running in production
    env = os.getenv("KIREMISU_ENV", "development")
    if env == "production":
        print("⚠️  WARNING: Running in production environment!")
        print("   Make sure to keep these keys secure and private.")
        print()
    
    # Generate JWT secret
    jwt_secret = generate_jwt_secret()
    print("🔑 JWT Secret Key (copy to SECRET_KEY in .env):")
    print(f"   {jwt_secret}")
    print()
    
    # Generate admin password
    admin_password = generate_secure_password(16)
    print("👤 Admin Password (copy to DEFAULT_ADMIN_PASSWORD in .env):")
    print(f"   {admin_password}")
    print()
    
    # Generate VAPID keys
    print("📱 VAPID Keys for Push Notifications:")
    vapid_keys = generate_vapid_keys()
    print(f"   VAPID_PUBLIC_KEY={vapid_keys['public_key']}")
    print(f"   VAPID_PRIVATE_KEY={vapid_keys['private_key']}")
    print()
    
    # Security recommendations
    print("🛡️  Security Recommendations:")
    print("   • Store these keys securely (password manager, encrypted files)")
    print("   • Never commit these keys to version control")
    print("   • Rotate keys regularly (especially after any security incident)")
    print("   • Use different keys for each environment (dev, staging, prod)")
    print("   • Change the admin password after first login")
    print()
    
    # Check existing .env file
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_file):
        print("🔍 Checking existing .env file...")
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                
            # Check SECRET_KEY
            for line in content.split('\n'):
                if line.startswith('SECRET_KEY='):
                    existing_secret = line.split('=', 1)[1].strip()
                    if not validate_existing_secret(existing_secret):
                        print("   ❌ Current SECRET_KEY appears insecure - please update!")
                    else:
                        print("   ✅ Current SECRET_KEY appears secure")
                    break
            else:
                print("   ⚠️  No SECRET_KEY found in .env file")
                
        except Exception as e:
            print(f"   ❌ Error reading .env file: {e}")
    
    print()
    print("✅ Key generation complete!")
    print("   Copy the keys above to your .env file and restart KireMisu.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Key generation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error generating keys: {e}")
        sys.exit(1)