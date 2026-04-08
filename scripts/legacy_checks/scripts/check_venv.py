#!/usr/bin/env python3
"""Quick check: venv python + sqlalchemy import."""
import subprocess, sys, os

venv_python = '/home/kazuha/Poly-Trader/venv/bin/python'

if os.path.exists(venv_python):
    print(f"[OK] venv python exists: {venv_python}")
    r = subprocess.run([venv_python, '-c', 'import sqlalchemy; print(f"sqlalchemy {sqlalchemy.__version__} OK")'],
                       capture_output=True, text=True)
    print(f"  stdout: {r.stdout.strip()}")
    if r.returncode != 0:
        print(f"  stderr: {r.stderr.strip()}")
        print("  -> venv has partial packages but needs pip install -r requirements.txt")
else:
    print(f"[FAIL] venv python not found at {venv_python}")
    if os.path.isdir('/home/kazuha/Poly-Trader/venv'):
        print("  venv dir exists but python binary missing -> needs rebuild")

# Also check system site-packages
sys_packages = [
    '/home/kazuha/Poly-Trader/venv/lib/python3.11/site-packages',
    '/usr/lib/python3/dist-packages',
]
for d in sys_packages:
    if os.path.isdir(d):
        has_sql = os.path.isdir(os.path.join(d, 'sqlalchemy'))
        has_pd = os.path.isdir(os.path.join(d, 'pandas'))
        print(f"\n  {d}: sqlalchemy={'OK' if has_sql else 'MISSING'}, pandas={'OK' if has_pd else 'MISSING'}")
