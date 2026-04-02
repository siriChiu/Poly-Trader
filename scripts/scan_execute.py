
import os, re

root_dir = r"C:\Users\Kazuha\repo\Poly-Trader"
pattern = re.compile(r'\.execute\((?!text)', re.MULTILINE)
for root, dirs, files in os.walk(root_dir):
    dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", ".venv", "node_modules"]]
    for f in files:
        if not f.endswith(".py"): continue
        p = os.path.join(root, f)
        try:
            c = open(p, encoding="utf-8").read()
            hits = [l.strip() for l in c.splitlines() if ".execute(" in l and "def " not in l and "#" not in l[:5]]
            if hits:
                print(f"--- {p}")
                for h in hits[:3]:
                    print(f"    {h}")
        except: pass
