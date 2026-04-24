import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('analyze_bb_breakout.py', encoding='utf-8') as f:
    content = f.read()

old = "{'Gi\u1edd':<16} {'S\u1ed1 TH':>8} {'Prec':>8} {'TP%':>8} {'SL%':>8} {'EV':>8}\")\n        lines.append(f\"  {'-'*60}\")"
new = "{'Gi\u1edd':<16} {'S\u1ed1 TH':>8} {'Prec':>8} {'TP%':>8} {'SL%':>8} {'EV':>8} {'WidthAvg':>10}\")\n        lines.append(f\"  {'-'*72}\")"

if old in content:
    content = content.replace(old, new)
    with open('analyze_bb_breakout.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK - header patched")
else:
    print("NOT FOUND - searching...")
    for i, line in enumerate(content.split('\n'), 1):
        if "EV':>8}" in line:
            print(f"  Line {i}: {repr(line)}")
