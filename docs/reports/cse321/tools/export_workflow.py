#!/usr/bin/env python3
"""Export this report's Mermaid sequence subset as a source-derived SVG.

This is an independent layout, not Mermaid's renderer. Unsupported syntax fails
rather than silently dropping content. PNG conversion uses render_diagrams.mjs.
"""
from pathlib import Path
import hashlib
import html
import re
import textwrap

D = Path(__file__).resolve().parents[1] / 'diagrams'
source = (D / 'grade-workflow.mmd').read_text()
participants = []
events = []
for raw in source.splitlines():
    line = raw.strip()
    if not line or line == 'sequenceDiagram':
        continue
    match = re.fullmatch(r'participant (\w+) as (.+)', line)
    if match:
        participants.append(match.groups())
        continue
    match = re.fullmatch(r'(\w+)(-->>|->>)(\w+): (.+)', line)
    if match:
        events.append(('message', *match.groups()))
        continue
    match = re.fullmatch(r'Note over ([\w,]+): (.+)', line)
    if match:
        events.append(('note', *match.groups()))
        continue
    match = re.fullmatch(r'(alt|else) (.+)', line)
    if match:
        events.append(match.groups())
        continue
    if line == 'end':
        events.append(('end',))
        continue
    raise ValueError(f'Unsupported sequence syntax: {line}')
assert len(participants) == 5
width = 1200
xs = {name: 120 + i * 240 for i, (name, _) in enumerate(participants)}
def esc(value):
    return html.escape(value, quote=True)

def text(x, y, lines, size=16, anchor='middle', color='#17324d'):
    return ''.join(f'<text x="{x}" y="{y+i*21}" text-anchor="{anchor}" '
                   f'font-family="Helvetica,Arial,sans-serif" font-size="{size}" '
                   f'fill="{color}">{esc(line)}</text>' for i, line in enumerate(lines))

rows = []
y = 135
stack = []
frames = []
for event in events:
    kind = event[0]
    if kind == 'message':
        _, sender, arrow, recipient, label = event
        x1, x2 = xs[sender], xs[recipient]
        wrap = max(24, int(abs(x2-x1)/8)-3) if x1 != x2 else 35
        lines = textwrap.wrap(label, width=wrap)
        h = len(lines)*21 + 32
        cy = y + h - 13
        if x1 == x2:
            rows.append(text(x1+20, y+17, lines, anchor='start'))
            path = f'M {x1} {cy-8} h 145 v 18 h -145'
        else:
            rows.append(text((x1+x2)/2, y+17, lines))
            path = f'M {x1} {cy} H {x2}'
        dashed = ' stroke-dasharray="7 5"' if arrow == '-->>' else ''
        rows.append(f'<path d="{path}" fill="none" stroke="#17324d" stroke-width="1.6"{dashed} marker-end="url(#arrow)"/>')
        y += h
    elif kind == 'note':
        _, names, label = event
        targets = [xs[name] for name in names.split(',')]
        mid = sum(targets)/len(targets)
        left = max(55, min(mid-210, width-475))
        lines = textwrap.wrap(label, width=49)
        h = 20 + 21*len(lines)
        rows.append(f'<rect x="{left}" y="{y}" width="420" height="{h}" rx="4" fill="#fff3cd" stroke="#bd9c43"/>')
        rows.append(text(left+210, y+22, lines, size=15))
        y += h+16
    elif kind == 'alt':
        depth = len(stack)
        stack.append((y, depth))
        rows.append(text(35+depth*15, y+19, ['alt: '+event[1]], size=15, anchor='start'))
        y += 38
    elif kind == 'else':
        assert stack
        depth = stack[-1][1]
        rows.append(f'<path d="M {25+depth*15} {y} H {width-25-depth*15}" stroke="#64748b" stroke-dasharray="6 4"/>')
        rows.append(text(35+depth*15, y+22, ['else: '+event[1]], size=15, anchor='start'))
        y += 40
    elif kind == 'end':
        start, depth = stack.pop()
        frames.append(f'<rect x="{25+depth*15}" y="{start}" width="{width-50-depth*30}" height="{y-start+8}" fill="none" stroke="#64748b" stroke-width="1.3"/>')
        y += 23
assert not stack
height = y+50
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
       '<title id="title">Gnosis grade save and subsequent result inspection</title>',
       '<desc id="desc">Source-derived layout preserving every participant, message, note and alternative in grade-workflow.mmd. Not a direct Mermaid render.</desc>',
       f'<!-- Source SHA256: {hashlib.sha256(source.encode()).hexdigest()} -->',
       '<rect width="100%" height="100%" fill="white"/>',
       '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#17324d"/></marker></defs>',
       text(width/2, 28, ['Gnosis v0.1: grade save and result inspection'], size=21)]
for name, label in participants:
    x = xs[name]
    svg.append(f'<rect x="{x-105}" y="50" width="210" height="62" rx="5" fill="#eef3f8" stroke="#17324d"/>')
    svg.append(text(x, 76, textwrap.wrap(label, width=22)))
    svg.append(f'<path d="M {x} 112 V {height-24}" stroke="#94a3b8" stroke-dasharray="5 5"/>')
svg += frames + rows + ['</svg>']
(D/'grade-workflow.svg').write_text('\n'.join(svg)+'\n')
print(f'Exported {len(participants)} participants and {len(events)} events; {width} x {height}.')
