#!/usr/bin/env python
"""Check environment: Python, packages, venv"""
import sys, os, subprocess
print(f"Python: {sys.executable} {sys.version}")
print(f"CWD: {os.getcwd()}")
print(f"HOME: {os.path.expanduser('~')}")

for pkg in ['numpy', 'pandas', 'sqlite3', 'sklearn', 'scipy', 'xgboost']:
    try:
        mod = __import__(pkg)
        ver = getattr(mod, '__version__', 'ok')
        print(f"  {pkg}: {ver}")
    except ImportError:
        print(f"  {pkg}: NOT installed")

# Check for venv
for p in ['venv/bin/activate', '.venv/bin/activate']:
    if os.path.exists(p):
        print(f"  VENV found: {p}")

# Check requirements.txt
for p in ['requirements.txt', 'setup.py', 'pyproject.toml']:
    if os.path.exists(p):
        print(f"  CONFIG: {p}")

# Check DB
import os.path
home = os.path.expanduser('~')
print(f"HERMES_HOME would be: {home}/.hermes")
print(f"Poly-Trader dir exists: {os.path.exists('/home/kazuha/Poly-Trader')}")
print(f"Files in /home/kazuha/Poly-Trader:")
for f in sorted(os.listdir('/home/kazuha/Poly-Trader')):
    print(f"  {f}")
