#!/usr/bin/env python3
"""Teste rápido só do SMTP para debug."""
import smtplib
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path('.env'))
except ImportError:
    print("dotenv not available")

# Get credentials
username = os.getenv('MA_SMTP_USERNAME', '').strip()
password = os.getenv('MA_SMTP_PASSWORD', '').strip(' "\'')  # Remove quotes/spaces
host = os.getenv('MA_SMTP_HOST', 'smtp.gmail.com')
port = int(os.getenv('MA_SMTP_PORT', '587'))

print(f"Testing SMTP connection...")
print(f"Host: {host}:{port}")
print(f"Username: {username}")
print(f"Password: {'*' * len(password)} ({len(password)} chars)")

try:
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        print("✅ SMTP connection successful!")

except Exception as e:
    print(f"❌ SMTP failed: {e}")
    if "Username and Password not accepted" in str(e):
        print("💡 Try:")
        print("1. Generate new App Password at https://myaccount.google.com")
        print("2. Remove quotes from password in .env")
        print("3. Check if 2FA is enabled")