#!/usr/bin/env python3
"""Check Python environment and run heartbeat."""
import subprocess, sys, os

os.chdir("/home/kazuha/Poly-Trader")

# Check python versions
for py in ["/usr/bin/python3", "/usr/bin/python3.12"]:
    if os.path.exists(py):
        result = subprocess.run([py, "--version"], capture_output=True, text=True)
        print(f"{py}: {result.stdout.strip()}")

# Check imports
try:
    import pandas, numpy, sklearn, ccxt, sqlalchemy
    print("All imports OK")
except ImportError as e:
    print(f"Import failed: {e}")

# Check python path
print(f"sys.executable: {sys.executable}")
print(f"sys.version: {sys.version}")
