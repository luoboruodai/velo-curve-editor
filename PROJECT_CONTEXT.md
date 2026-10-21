# Velo project context

Last updated: **2026-10-21 · v1.1.0**

This is the compact, public handoff for future agents and maintainers. It preserves product intent, architecture, verified decisions and failure boundaries without private chat logs, local paths, credentials or real user data.

## 1. Start here

Velo is a native TouchDesigner curve editor for motion designers. Its original goal is to edit a value curve while seeing its synchronized speed in the same canvas, reducing view switching and guesswork. It remains a native COMP rather than a web UI embedded in TD.

Current capabilities:

- Bezier, Elastic and Bounce models; multi-keyframe value editing and synchronized speed display.
- Flexible Bezier handles constrained by the real monotonic-time invariant rather than a legacy coordinate box.
- Built-in and user presets, EaseCopy, adaptive accent themes and native settings.
- Live CHOP output plus opt-in native Animation COMP keyframe export.

Read next only as needed:

| Task | Entry points |
|---|---|
| Curve / output behavior | `src/python/curve_logic.py`, `src/python/curve_model.py` |
| Bezier handle issue | `src/python/bezier_handles.py`, `tools/test_velocity_editor.py` |
| Settings / native UI | `src/python/plugin_dialogs.py`, `tools/generate_ui.py` |
| Preset geometry | `src/python/preset_layout.py`, `tools/test_preset_library.py` |
| EaseCopy | `src/python/easecopy.py`, `tools/test_easecopy.py` |
| Animation export | `src/python/keyframe_export.py`, `tools/test_keyframe_export.py` |
| Build / packaging | `tools/build_tox.sh`, `tools/ui_manifest.txt`, `src/curve_editor.tox.toc` |
| Evidence / platform claims | `docs/VERIFICATION.md` |

## 2. Non-negotiable contracts

- Native TD nodes only; no WebRender, HTML browser, external frontend runtime or TD global-theme modification.
- First output remains one `fade` CHOP channel with 257 samples and endpoints `0 → 1`.
- Display, editing, EaseCopy, reversal, export and CHOP lookup use the same sampling model.
- Existing custom parameters and parent-parameter synchronization remain compatible.
- Real user presets and projects are never test fixtures or public release content.
- macOS / TouchDesigner 2025.31550 is the verified environment. Windows receives the same native TOX but is not runtime-verified here.

## 3. Architecture and data flow

1. **State**: `curve_logic.py` normalizes component state and coordinates actions, caches and synchronization. Internal JSON DATs hold state and presets without adding fragile host parameters.
2. **Mathematics**: `curve_model.py` evaluates Bezier / Elastic / Bounce curves. `bezier_handles.py` protects finite coordinates and monotonic time.
3. **Display**: `graph_engine.py` generates native Script SOP geometry for grid, value, speed, handles, anchors and playhead. Geometry and Render TOPs feed the native panel.
4. **Native UI**: `plugin_dialogs.py` owns settings layout and dispatch. `preset_layout.py` owns stable card geometry. `generate_ui.py` manages native node files and manifest entries.
5. **EaseCopy**: `easecopy.py` handles single-key or range copy, integer-multiple paste, ease/value separation, passthrough preservation and buffer clearing.
6. **Output**: `curve_values` produces the live `fade` channel; `out1` preserves the downstream contract.
7. **Optional authoring**: `keyframe_export.py` converts `out1` to an Animation COMP and writes explicit linear keys.

### Keyframe export details

**Settings → Graph → 写入关键帧** is an explicit action, not a background replacement for live output.

- `convertToKeyframes(tolerance=0.001)` creates the native animation structure.
- `setKeyframe(..., channel='fade', function='linear()')` writes the sampled values.
- The verified `keys` table has **258 data keys at frames 0–257**, including both endpoints; this is distinct from the live output's 257 samples.
- `velo_animation[_NN]` is allocated among the current component's direct children to avoid overwriting an existing animation node.
- Native evidence covers the real settings action, Animation COMP, `fade` channel and editable `keys` table. Manual dragging inside Animation Editor is a separate, unclaimed test.

## 4. Design intent and interaction decisions

- **Direct manipulation first**: dragging a value curve immediately updates its speed background; the auxiliary layer must not steal input.
- **One mathematical truth**: speed and value are not separate approximations. Speed has its own vertical scale and zero baseline.
- **Dense but quiet**: neutral surfaces, compact native controls, readable captions and limited accent color support a professional tool rather than a marketing page.
- **Stable layout**: preset columns do not collapse based on the number of items on the last page. EaseCopy uses a status row and a separate action row below primary actions.
- **Role-based themes**: accent color affects curves, thumbnails, selection and functional icons. Neutral surfaces, danger states, true swatches and default white handles / knobs retain their own semantics.
- **Settings structure**: switches need visible on/off tracks and white knobs; section captions are transparent and separated from the first content row.
- **Material honesty**: translucent fills and thin borders provide a glass-like layer, not a claim of real-time background blur.
- **Host workflow over AE imitation**: the live CHOP output does not need an AE-style Apply button. Native keyframe export is an explicit additional workflow.

## 5. Verified troubleshooting record

### Foundation and build

| Symptom / risk | Verified cause | Resolution / reusable decision |
|---|---|---|
| Binary TOX was impractical to edit as text | TD's expanded format has its own headers and file contract | Use `toeexpand` / `toecollapse`; preserve the 27-byte `.text` header and big-endian payload length, then verify by re-expansion and diff |
| Non-ASCII source path failed in tooling | The TD expansion path could not open some Chinese filenames | Build through an ASCII-named copy and compare hashes |
| Second generation could omit nodes | Managed TOC / manifest registration was not idempotent | Re-register managed files on every generation; run generation and build twice, then compare expanded identity |
| A DAT approached 65,535 bytes | Curve, UI and math code accumulated in one payload | Split by stable responsibility and update generator, build mapping, TOC and host module references together |
| `loadTox` module lookup failed | The real component could be a child of the loaded wrapper | Inspect the actual loaded subtree before resolving the component and DAT modules |
| Canvas freedom conflicted with parameter behavior | Parameter min / max / normalized ranges still clamped values | Use the real Par API and over-range readback, not `.cparm` text guesses |
| Value direction flip left interactions reversed | Render and input used different coordinate conventions | Migrate value, speed, thumbnails, hit tests and drag mapping together |
| Multi-row preset clicks hit the wrong card | Render TOP bottom-origin and COMP top-origin Y coordinates were mixed | Apply one explicit per-cell Y conversion to thumbnails, borders, labels and hit tests; test a second-row card |

### U020–U029 visual and interaction refinement

| Stage | Problem | Final resolution |
|---|---|---|
| U020 | Preset deletion left stale rendering and ambiguous action layers | Recompute page / layout, invalidate catalogue and selection rendering in order, and separate background, text and hit layers |
| U021 | The last remaining preset stretched after deletion | Keep stable column counts and integer row-width allocation; compare the surviving card's actual rectangle before and after deletion |
| U021–U022 | EaseCopy competed with primary actions | Keep it in a lower advanced-tool region with a title / buffer-count row and a separate action row |
| U022 | Computed 4 px gaps rendered as 3 px | TD panel parameters rounded fractional widths; use integer allocation and inspect actual rectangles |
| U023 | Bezier handles were unnecessarily restricted | Use the cubic X-derivative minimum for monotonic time, allow finite Y / crossing, and fall back along the drag path to the nearest valid X |
| U023 | Released out-of-view handles became unreachable | Fit includes anchors and handles; releasing outside expands rather than shrinks the viewport |
| U024 | Theme changes left stale blue elements | Unify color roles, include theme in cache keys and update popover / hover targets from the same source |
| U024–U025 | White controls were incorrectly tinted | Keep default handles, anchors and knobs on an independent white role; custom handle colors still take precedence |
| U025–U026 | Off switches and sliders disappeared into the surface | Give off tracks a dark fill and border, on tracks the accent role and knobs a stable contrasting white |
| U026–U027 | Section captions looked like duplicate tabs | Use transparent in-section captions with independent spacing before the first content row; fix structure before color |
| U028 | Public release risked private material and platform overclaim | Use a separate public clone, explicit file staging, source / archive scans and downloaded-artifact hash verification |
| U029 | Project knowledge was dispersed across iterations | Preserve symptom → root cause → fix → evidence → reusable principle; do not turn project-specific colors or sizes into generic rules |

### U030–U031 actual TD control and authoring

| Stage | Question | Evidence and boundary |
|---|---|---|
| U030 | Does the live CHOP output really control TD? | A physical `constant1 → level1` chain used an expression reading `CurveEditor/out1`; 36 samples and rendered alpha frames confirmed nonlinear parameter evaluation and visible control. This did not prove keyframe authoring |
| U031 | Can Velo create native animation keys? | The real settings action created an Animation COMP and editable `keys` table with 258 linear keys and one `fade` channel. Unique naming and unchanged user presets were checked. Animation Editor dragging was not separately tested |

## 6. Verification model

Use separate evidence layers:

1. **Offline**: mathematics, state, layout, EaseCopy, export calls and failure paths.
2. **Build**: Python payloads synchronize into native DATs; repeated builds have identical hashes and expanded-source identity.
3. **Native host**: the actual TOX loads in TouchDesigner and the affected action executes.
4. **Physical interaction / render**: real pointer, keyboard, parameter evaluation or rendered pixels when required by the change.

Current public release baseline: **69 offline regressions**, deterministic repeated builds and native macOS checks. Do not convert a successful build into a claim of native interaction, or a native `keys` table inspection into a claim of manual Animation Editor dragging.

## 7. Change and release checklist

1. Read the current request and preserve existing user work; do not rerun completed releases merely because a chat was resumed.
2. Make the smallest coherent source / generator / manifest change.
3. Run affected offline tests and actual TOX host checks.
4. Update `VERSION`, bilingual README files, changelog, verification and this context when behavior or evidence changes.
5. Stage only public source, documents, synthetic media and native artifacts. Scan file contents and archive members for private paths, test hooks and credentials.
6. Freeze the tested commit and artifacts, create the tag / release, then download the actual attachments and compare SHA-256 and archive membership.
7. Record unresolved platform and interaction boundaries explicitly.

## 8. Deliberately not generalized

The current gray values, component dimensions, button captions, QA names, hashes and local evidence paths are project-specific. They are not reusable design laws. Likewise, native keyframe creation does not imply every Animation Editor interaction has been tested, and a Windows package does not imply Windows runtime verification.
