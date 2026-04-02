
import os, re
for root, dirs, files in os.walk(r"C:\Users\Kazuha\repo\Poly-Trader"):
    dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", ".venv", "node_modules"]]
    for f in files:
        if not f.endswith(".py"): continue
        p = os.path.join(root, f)
        try:
            c = open(p, encoding="utf-8").read()
            if "engine.execute" in c:
                count = c.count("engine.execute")
                print(f"{count}x engine.execute: {p}")
        except:
            pass
