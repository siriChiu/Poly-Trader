import sys, io, subprocess, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REPO = r"C:\Users\Kazuha\repo\poly-trader"
os.chdir(REPO)

# Clean up temp files
temp_files = [
    "fix_backtest_win.py", "fix_backtest_v2.py", "check_db_state.py",
    "diagnose2.py", "diagnose_all.py", "recompute_all.py", 
    "find_wugan.py", "update_all_refs.py", "final_fix.py",
    "t1.py", "t2.py", "fix_emoji.py", "fixed_sensechart.py", "fixed_radar.py",
]
for f in temp_files:
    fp = os.path.join(REPO, f)
    if os.path.exists(fp):
        os.remove(fp)
        print(f"Deleted: {f}")

# Commit
result = subprocess.run(
    "git add -A && git diff --cached --stat",
    shell=True, capture_output=True, text=True, cwd=REPO
)
print("Files to commit:")
print(result.stdout)

result2 = subprocess.run(
    "git commit -m \"fix: web backtest + 8-sense API + RadarChart + 感官->多感官 docs\n\n- Backtest scoring: normalize features -1~1 to 0~1 before threshold comparison\n- Backtest threshold: 0.55 → 0.50, added exit_thresh 0.45\n- SensesChart: 5→8 features (pulse, aura, mind)\n- RadarChart: pentagon→polygon, dynamic 8-sense SENSE_KEYS/SENSE_INFO\n- /api/features: now returns 8 features\n- Senses.tsx: SENSE_COLORS 8 senses, dynamic avg\n- All docs: 感官->多感官 (AI_AGENT_ROLE.md, PRD.md, ROADMAP.md, architecture.md, README.md, ISSUES.md, 23 source files)\"",
    shell=True, capture_output=True, text=True, cwd=REPO
)
print("Commit result:")
print(result2.stdout)
if result2.stderr:
    print(result2.stderr)

print("\n=== DONE ===")
