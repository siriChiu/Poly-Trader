#!/usr/bin/env python3
"""Fix venv by installing sqlalchemy if missing, or use system packages."""
import subprocess
import sys

# Check if the venv python works and has sqlalchemy
venv_python = '/home/kazuha/Poly-Trader/venv/bin/python'

try:
    r = subprocess.run([venv_python, '-c', 'import sqlalchemy; print("OK")'],
                       capture_output=True, text=True, timeout=10)
    if r.stdout.strip() == 'OK':
        print("venv already has sqlalchemy, all good")
        sys.exit(0)
    else:
        print(f"venv sqlalchemy check failed: {r.stderr}")
except Exception as e:
    print(f"venv python error: {e}")

# Try pip install
print("Attempting pip install...")
pip = '/home/kazuha/Poly-Trader/venv/bin/pip'
import os
if os.path.exists(pip):
    r = subprocess.run([pip, 'install', 'sqlalchemy', 'pandas', 'numpy'], 
                       capture_output=True, text=True, timeout=300)
    print(f"pip stdout: {r.stdout[-500:]}")
    print(f"pip stderr: {r.stderr[-500:]}")
    print(f"pip returncode: {r.returncode}")
else:
    print(f"pip not found at {pip}")
    # Try to bootstrap pip
    subprocess.run([venv_python, '-m', 'ensurepip', '--upgrade', '--default-pip'],
                   capture_output=True, text=True)
    pip2 = '/home/kazuha/Poly-Trader/venv/bin/pip'
    if os.path.exists(pip2):
        r = subprocess.run([pip2, 'install', 'sqlalchemy', 'pandas', 'numpy'], 
                           capture_output=True, text=True, timeout=300)
        print(f"pip stdout: {r.stdout[-500:]}")
        print(f"pip stderr: {r.stderr[-500:]}")
        print(f"pip returncode: {r.returncode}")
