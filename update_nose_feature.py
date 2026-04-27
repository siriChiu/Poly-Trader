import sys

def update_nose_feature(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if line.strip() == '# 3. Nose: rsi14_norm — RSI(14) 正規化至 [0,1]':
            start_idx = i
        if line.strip() == '# 4. Tongue: vol_ratio_24_144 — 24期/144期波動率比（breakout 強度）':
            end_idx = i
            break

    if start_idx is not None and end_idx is not None:
        new_nose = [
            '    # 3. Nose: rsi7_norm — RSI(7) 正規化至 [0,1]\n',
            '    #    試圖提高靈敏度和有效性\n',
            '    if len(close) >= 8:\n',
            '        delta = close.diff()\n',
            '        gain = delta.clip(lower=0).rolling(7).mean()\n',
            '        loss = (-delta.clip(upper=0)).rolling(7).mean()\n',
            '        last_loss = float(loss.iloc[-1]) if not loss.empty else 1e-9\n',
            '        last_gain = float(gain.iloc[-1]) if not gain.empty else 0.0\n',
            '        if last_loss > 0:\n',
            '            rsi = 100 - 100 / (1 + last_gain / last_loss)\n',
            '        else:\n',
            '            rsi = 100.0\n',
            '        features["feat_nose_sigmoid"] = float(rsi) / 100.0\n',
            '    else:\n',
            '        features["feat_nose_sigmoid"] = 0.5\n'
        ]
        lines[start_idx:end_idx] = new_nose
        with open(filepath, 'w') as f:
            f.writelines(lines)
        print('Nose feature updated to RSI(7)')
        return True
    else:
        print('Could not find the nose section markers')
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python update_nose_feature.py <path_to_preprocessor.py>')
        sys.exit(1)
    success = update_nose_feature(sys.argv[1])
    sys.exit(0 if success else 1)