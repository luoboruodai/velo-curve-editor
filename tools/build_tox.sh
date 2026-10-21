#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
from pathlib import Path

root = Path.cwd()
source = root / 'src' / 'curve_editor.tox.dir' / 'CurveEditor'
mappings = {
    'curve_logic.py': ('curve_logic.text', 'curve_logic.text'),
    'ui_style.py': ('ui_style.text', 'curve_logic.text'),
    'curve_model.py': ('curve_model.text', 'curve_logic.text'),
    'bezier_handles.py': ('bezier_handles.text', 'curve_logic.text'),
    'keyframe_export.py': ('keyframe_export.text', 'curve_logic.text'),
    'graph_engine.py': ('graph_engine.text', 'curve_logic.text'),
    'plugin_dialogs.py': ('plugin_dialogs.text', 'curve_logic.text'),
    'preset_layout.py': ('preset_layout.text', 'curve_logic.text'),
    'easecopy.py': ('easecopy.text', 'curve_logic.text'),
    'speed_shape_callbacks.py': ('speed_shape_callbacks.text', 'curve_shape_callbacks.text'),
    'user_presets.json': ('user_presets.text', 'README_CN.text'),
    'state_store.json': ('state_store.text', 'README_CN.text'),
    'drag_events.py': ('drag_events.text', 'drag_events.text'),
    'esc_events_callbacks.py': ('esc_events_callbacks.text', 'drag_events.text'),
    'README_CN.py': ('README_CN.text', 'README_CN.text'),
}
for input_name, (output_name, template_name) in mappings.items():
    payload = (root / 'src' / 'python' / input_name).read_bytes()
    if len(payload) > 65535:
        raise ValueError(f'{input_name} exceeds the TD .text payload limit')
    output = source / output_name
    template = output if output.exists() else source / template_name
    header = template.read_bytes()[:27]
    if len(header) != 27:
        raise ValueError(f'invalid TD text header: {template}')
    header = header[:0x19] + len(payload).to_bytes(2, 'big') + header[0x1b:]
    output.write_bytes(header + payload)
    check = output.read_bytes()
    assert int.from_bytes(check[0x19:0x1b], 'big') == len(payload)
    assert check[27:] == payload
    print(f'synced {input_name} -> {output_name} ({len(payload)} bytes)')
PY

if [ "${1:-}" = "--sync-only" ]; then
    exit 0
fi

mkdir -p dist private/verification
if [ -f src/curve_editor.tox ]; then
    mv -f src/curve_editor.tox private/verification/previous_build.tox
fi

set +e
(
    cd src
    "/Applications/TouchDesigner.app/Contents/MacOS/toecollapse" curve_editor.tox
)
status=$?
set -e
if [ ! -f src/curve_editor.tox ]; then
    echo "toecollapse did not create src/curve_editor.tox (exit $status)" >&2
    exit 1
fi

cp src/curve_editor.tox dist/Velo.tox
"/Applications/TouchDesigner.app/Contents/MacOS/toeexpand" -b dist/Velo.tox || true
shasum -a 256 dist/Velo.tox
