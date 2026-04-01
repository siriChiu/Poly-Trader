import sys, io, subprocess, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPO = r"C:\Users\Kazuha\repo\poly-trader"
os.chdir(REPO)

# Delete accidentally created file
if os.path.exists("s1640.py"):
    os.remove("s1640.py")
    print("Deleted s1640.py")

# Commit
r = subprocess.run(
    ["git", "add", "-A"],
    capture_output=True, cwd=REPO
)
print("Staged")

r2 = subprocess.run(
    ["git", "commit", "-m", "fix: backtest normalization + 8-sense UI + 多感官 docs update"],
    capture_output=True,
    text=True,
    cwd=REPO,
    encoding="utf-8"
)
print(r2.stdout)
if r2.stderr:
    print(r2.stderr)

r3 = subprocess.run(["git", "log", "--oneline", "-3"], 
    capture_output=True, text=True, cwd=REPO, encoding="utf-8")
print("\nLatest commits:")
print(r3.stdout)
