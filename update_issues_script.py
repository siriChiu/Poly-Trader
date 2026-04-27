with open('ISSUES.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the index of the line that starts with '## Open Issues'
try:
    open_issues_index = next(i for i, line in enumerate(lines) if line.strip() == '## Open Issues')
except StopIteration:
    print('Could not find ## Open Issues')
    exit(1)

new_lines = [
    '',
    '### P0. Eye 感官 IC=0.0490 (<0.05) 無效',
    '- 真相：Eye 特徵 feat_eye_dist 的 IC 為 0.0490，低於 0.05 有效性閾值',
    '- 下一步：替換 feat_eye_dist 特徵，研究替代眼部特徵（例如：price_return_24h / volatility_72h 的其他變體，或使用不同的窗口大小）',
    '- 驗證：通過腳本 calculate_ic.py 檢查新特徵的 IC 是否 > 0.05',
    '',
    '### P0. Nose 感官 IC=0.0198 (<0.05) 無效',
    '- 真相：Nose 特徵 feat_nose_sigmoid 的 IC 為 0.0198，低於 0.05 有效性閾值',
    '- 下一步：替換 feat_nose_sigmoid 特徵，我們已將其改為 RSI(7) 以提高靈敏度',
    '- 驗證：通過腳本 calculate_ic.py 檢查新特徵的 IC 是否 > 0.05',
    '',
    '### P0. Tongue 感官 IC=-0.0288 (<0.05) 無效',
    '- 真相：Tongue 特徵 feat_tongue_pct 的 IC 為 -0.0288，低於 0.05 有效性閾值',
    '- 下一步：替換 feat_tongue_pct 特徵，研究替代舌部特徵（例如：價格突破指標、成交量異常指標）',
    '- 驗證：通過腳本 calculate_ic.py 檢查新特徵的 IC 是否 > 0.05',
    ''
]

# Insert the new lines after the open_issues_index line.
# We want to put them right after the '## Open Issues' line, so we insert at open_issues_index+1.
lines[open_issues_index+1:open_issues_index+1] = new_lines

with open('ISSUES.md', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('ISSUES.md updated with P0 issues for Eye, Nose, Tongue')