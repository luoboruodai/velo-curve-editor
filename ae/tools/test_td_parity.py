#!/usr/bin/env python3
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src' / 'python'))
import curve_logic

CLI = ROOT / 'ae' / 'tools' / 'model_cli.js'
states = [curve_logic.preset_state(name) for name in curve_logic.PRESETS]
states.extend([
    curve_logic.normalized_state({'mode': 'elastic', 'direction': direction, 'frequency': 3.25, 'decay': 7.5, 'elastic_gain': 0.72})
    for direction in ('in', 'out', 'inout')
])
states.extend([
    curve_logic.normalized_state({'mode': 'bounce', 'direction': direction, 'restitution': 0.68, 'bounce_period': 0.37})
    for direction in ('in', 'out', 'inout')
])

for index, state in enumerate(states, 1):
    payload = {'state': {key: state.get(key) for key in (
        'model', 'mode', 'direction', 'x1', 'y1', 'x2', 'y2', 'elastic_gain',
        'frequency', 'decay', 'restitution', 'bounce_period', 'precision')}, 'count': 257}
    result = json.loads(subprocess.check_output(['node', str(CLI),], input=json.dumps(payload).encode()))
    expected, _ = curve_logic.sample_curve(state, 257)
    actual = result['samples']['values']
    for sample_index, (left, right) in enumerate(zip(expected, actual)):
        if not math.isclose(left, right, rel_tol=0, abs_tol=2e-9):
            raise AssertionError((index, state['mode'], state['direction'], sample_index, left, right))
    print(f"ok {index} - TD parity {state['mode']} {state['direction']}")

print(f'1..{len(states)}')
