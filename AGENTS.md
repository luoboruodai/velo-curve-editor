# Velo maintainer guide

Start with `PROJECT_CONTEXT.md`, then read only the modules needed for the current task. `VERSION`, `CHANGELOG.md` and `docs/VERIFICATION.md` describe the public release; do not infer current behavior from old screenshots or release notes alone.

## Product boundaries

- Keep Velo native to TouchDesigner. Do not introduce WebRender, HTML, an external frontend runtime or changes to the TD global theme.
- Preserve the first CHOP output contract unless the user explicitly changes it: one `fade` channel, 257 samples, endpoints `0 → 1`.
- Preserve existing parameter and parent-sync behavior. Keep real user presets and projects out of public fixtures, screenshots, commits and release archives.
- `Velo.tox` and `Velo_Demo.tox` are identical component payloads, not separate feature tiers.

## Source map

- `src/python/curve_logic.py`: shared state, sampling, actions, cache and output orchestration.
- `src/python/curve_model.py`: Bezier / Elastic / Bounce mathematics.
- `src/python/bezier_handles.py`: finite-coordinate, monotonic-safe handle editing.
- `src/python/graph_engine.py`: native plot geometry and rendering inputs.
- `src/python/plugin_dialogs.py`: settings layout and action dispatch.
- `src/python/preset_layout.py`: stable preset-grid geometry.
- `src/python/easecopy.py`: copy / paste semantics.
- `src/python/keyframe_export.py`: opt-in native Animation COMP export.
- `tools/generate_ui.py`: managed native-node generation and manifest registration.
- `tools/build_tox.sh`: Python-to-DAT synchronization and TOX build.

## Change rules

1. Keep one mathematical source for display, editing, copy, export and CHOP output.
2. When adding or splitting a DAT, update the source generator, build mapping, TOC / manifest and host references together. A TD `.text` payload must remain below 65,535 bytes.
3. Invalidate in this order when applicable: data → layout → dependent geometry → rendering. Do not hide stale dependencies with permanent forced redraws.
4. Keep theme colors role-based. Neutral surfaces, danger colors, true color swatches and default white handles / knobs are not accent-tinted indiscriminately.
5. Keyframe export is opt-in. It must use unique direct-child names and must not overwrite existing animation nodes or user presets.
6. Do not claim Animation Editor dragging, Windows runtime support or other host behavior without direct evidence.

## Verification

Run the offline suite after relevant changes:

```bash
for test in tools/test_*.py; do python3 "$test"; done
```

Build on a machine with the expected TouchDesigner tools:

```bash
bash tools/build_tox.sh
```

For native changes, also load the actual TOX in TouchDesigner and test the affected workflow with isolated data. Record offline, native-host and physical-input evidence separately. Repeated builds must be compared by hash and expanded-source identity.

## Publishing and handoff

- Use explicit public-file staging; never publish private projects, verification logs, credentials, local absolute paths or real user presets.
- Package the same native TOX for macOS and Windows, but state only the platforms actually tested.
- After a meaningful architecture, workflow or verification change, update `PROJECT_CONTEXT.md` and the affected public docs in the same commit.
