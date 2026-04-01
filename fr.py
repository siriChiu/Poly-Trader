import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
REPO = r"C:\Users\Kazuha\repo\poly-trader"
skip = {'.git', 'node_modules', '.venv', '__pycache__', 'dist'}

repl = {
    '多感官量化交易': '多感官量化交易',
    '多感官量化': '多感官量化',
    '多感官數據': '多感官數據',
    '多感官': '多感官',
    '多感官收集': '多感官收集',
    '多感官模組': '多感官模組',
    '多感官特徵': '多感官特徵',
    '多感官有效性': '多感官有效性',
    '多感官量化': '多感官量化',
    '多感官整合': '多感官整合',
    '多感官分析': '多感官分析',
    '感官之': '感官之',
    '感官': '感官',
}
changes = 0
files = 0
for root, dirs, fnames in os.walk(REPO):
    dirs[:] = [d for d in dirs if d not in skip]
    for f in fnames:
        ext = os.path.splitext(f)[1].lower()
        if ext not in ('.py', '.md', '.json', '.yaml', '.yml', '.toml', '.ts', '.tsx', '.html', '.css'):
            continue
        fp = os.path.join(root, f)
        try:
            with open(fp, 'r', encoding='utf-8', errors='replace') as fh:
                c = fh.read()
            orig = c
            for old, new in repl.items():
                if old in c:
                    c = c.replace(old, new)
            if c != orig:
                with open(fp, 'w', encoding='utf-8') as fh:
                    fh.write(c)
                rel = os.path.relpath(fp, REPO)
                cnt = sum(orig.count(old) for old in repl)
                print(f"  {rel}: {cnt} changes")
                files += 1
                changes += cnt
        except:
            pass
print(f"\nDone: {files} files, {changes} replacements")
