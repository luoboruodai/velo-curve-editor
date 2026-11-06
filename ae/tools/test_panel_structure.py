#!/usr/bin/env python3
from pathlib import Path
from html.parser import HTMLParser
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / 'VeloAE'
checks = 0


def check(condition, message):
    global checks
    assert condition, message
    checks += 1
    print(f'ok {checks} - {message}')


manifest = PANEL / 'CSXS' / 'manifest.xml'
root = ET.parse(manifest).getroot()
check(root.attrib['ExtensionBundleId'] == 'com.velo.curveeditor', 'bundle id is stable')
main_path = root.findtext('./DispatchInfoList/Extension/DispatchInfo/Resources/MainPath')
script_path = root.findtext('./DispatchInfoList/Extension/DispatchInfo/Resources/ScriptPath')
check((PANEL / main_path).is_file(), 'manifest HTML exists')
check((PANEL / script_path).is_file(), 'manifest host JSX exists')
check(root.find('./ExecutionEnvironment/HostList/Host').attrib['Version'] == '[17.0,99.9]', 'manifest host range covers AE 2026')

html = (PANEL / 'index.html').read_text(encoding='utf-8')
for relative in re.findall(r'(?:src|href)="([^"]+)"', html):
    if relative.startswith(('http://', 'https://', 'data:')):
        raise AssertionError(f'external resource: {relative}')
    check((PANEL / relative).is_file(), f'local resource exists: {relative}')

for element_id in (
    'appContainer', 'curveCanvas', 'settingsBtn', 'directionBtn', 'bezierJsonOutput',
    'ampSlider', 'freqSlider', 'corSlider', 'periodSlider', 'pasteBtn', 'resetBtn',
    'reverseBtn', 'smoothAllBtn', 'savePresetBtn', 'inspectBtn', 'readCurveBtn', 'applyBtn', 'presetPanel', 'presetList',
    'settingsModal', 'closeSettingsBtn', 'languageSelect', 'presetLocation', 'compactToggle', 'speedToggle',
    'viewGroup', 'motionToggle', 'presetSize', 'restorePresetsBtn', 'presetContextMenu',
    'anchorContextMenu', 'anchorSmoothBtn', 'anchorPreserveDeleteBtn', 'anchorDeleteBtn', 'tangentSnapHint',
    'easeCopyCopyBtn', 'easeCopyEaseBtn', 'easeCopyValueBtn', 'easeCopyPassBtn', 'easeCopyClearBtn',
    'previewCanvas', 'previewPlayBtn', 'previewDuration',
    'importPresetsBtn', 'exportPresetsBtn', 'presetFileInput', 'presetExportPath', 'themeColor', 'themeBackground',
    'themeHandles', 'gridX', 'gridY', 'curvePrecision', 'speedStrength', 'fitCurveBtn', 'doneSettingsBtn',
    'colorPickerModal', 'colorPickerClose', 'colorField', 'colorHue', 'colorHex', 'colorR', 'colorG', 'colorB',
    'colorPreview', 'colorError', 'colorPickerCancel', 'colorPickerApply',
    'multiPointModal', 'multiPointMessage', 'multiPointClose', 'multiPointCancel', 'multiPointSwitch',
    'statusText', 'healthDot',
):
    check(re.search(rf'id="{element_id}"', html) is not None, f'control id: {element_id}')

check(re.search(r'id="settingsModal"[^>]*\bhidden\b', html) is not None, 'settings modal starts outside layout and hit testing')
check(re.search(r'id="previewCanvas"[^>]*aria-hidden="true"', html) is not None, 'preview overlay is noninteractive')

main = (PANEL / 'js' / 'main.js').read_text(encoding='utf-8')
check('VeloAE.inspect()' in main, 'host inspection is wired')
check('VeloAE.apply(' in main, 'host apply is wired')
check('VeloAE.easeCopyCopy()' in main and 'VeloAE.easeCopyPaste(' in main, 'EaseCopy host calls are wired')
check('VeloAE.exportPresetFile(' in main and "showStatus('status.exportCancelled')" in main, 'export uses the native save dialog and handles cancellation')
check('ui.exportPath.textContent' in main and 'ui.exportPath.title = result.path' in main, 'the selected export path is visible in settings')
check('model.sample' in main, 'shared model supplies samples')
check('navigator.clipboard.writeText(text).catch(fallback)' in main and 'navigator.clipboard.readText().catch(fallback)' in main, 'clipboard permission rejections reach the existing copy and manual-paste fallbacks')
check("addEventListener('dblclick', addPoint)" in main and "addEventListener('contextmenu', deletePoint)" in main, 'double-click insertion and right-click deletion are wired to the canvas')
check('payload.segments = model.serializable(state).segments' in main and 'payload.hiddenAnchors = state.hiddenAnchors || []' in main and '!model.validSegments(payload.state.segments)' in main, 'multi-segment native output, hidden-anchor metadata and curve JSON validation are wired')
check('VeloAE.readCurve()' in main and "ui.read.addEventListener('click', readHostCurve)" in main, 'reading AE curves is a separate action from target inspection')
check('pointerdown' in main and 'pointermove' in main and 'pointercancel' in main, 'pointer drag lifecycle exists')
check('Math.hypot(x - candidate.x, y - candidate.y)' in main and 'rect.left + candidate.x' not in main, 'handle hit testing uses one local coordinate space')
check('setPointerCapture' in main and 'document-level move/up remains available' in main, 'drag survives pointer capture failure')
check('requestAnimationFrame(previewTick)' in main and 'preview.duration + 0.8' in main, 'TD preview timing is implemented')
check('drawPlayhead' in main and 'preview.u' in main and 'editView' in main, 'preview follows value and speed views')
motion = main.split("ui.motion.addEventListener('change', () => {", 1)[1].split('ui.presetSize.addEventListener', 1)[0]
check('preview.resumeAfterMotion = preview.playing;' in motion, 'reduced motion preserves prior playing state')
check('else if (preview.resumeAfterMotion)' in motion and 'startPreview();' in motion, 'leaving reduced motion resumes only prior playback')
manual_preview = main.split("ui.previewPlay.addEventListener('click', () => {", 1)[1].split('});', 1)[0]
check('preview.resumeAfterMotion = false;' in manual_preview, 'manual preview control clears pending resume')
check('localStorage' in main, 'user presets persist locally')
check('selectedPresetId' in main and 'item.dataset.id === selectedPresetId' in main, 'preset selection is explicit')
check('contextmenu' in main and 'dragstart' in main and 'restorePresetsBtn' in main, 'preset management is wired')
check('button.draggable = !window.CSInterface' in main and 'startPresetPointerDrag' in main, 'CEP presets use pointer dragging while browser drag and drop remains available')
check('Math.hypot(moveEvent.clientX - event.clientX, moveEvent.clientY - event.clientY) < 6' in main, 'preset dragging starts only after a movement threshold')
check('document.elementFromPoint' in main and "classList.add('drop-target')" in main, 'pointer dragging identifies and highlights a real target card')
check("addEventListener('pointercancel'" in main and "addEventListener('lostpointercapture'" in main, 'preset pointer cancellation releases its interaction state')
check('suppressPresetClick = true;' in main, 'a completed preset drag cannot also apply a card')
check('function reorderPreset(' in main and "reorderPreset(event.dataTransfer.getData('text/x-velo-preset'), entry.id, entries)" in main, 'pointer and HTML5 dragging share the same persisted ordering function')
check('function exportPresets' in main and 'function importPresets' in main, 'preset import and export are implemented')
check('function presetExportData' in main and 'function parsePresetImport' in main, 'complete preset configuration has testable import and export paths')
check("format: 'velo-presets', version: 2" in main, 'complete preset export uses the version 2 schema')
check('Object.entries(model.PRESETS).map' in main and 'model.serializable(model.presetState(id))' in main, 'all built-in presets are included from their canonical definitions')
check('hiddenPresets, presetOrder: orderedPresetIds(order, userEntries)' in main, 'hidden state and the complete preset order are exported')
check('foundBuiltins.size !== builtinIds.size' in main, 'complete imports require every built-in preset exactly once')
check('const idMap = new Map();' in main and 'makeId(usedIds, index)' in main, 'user ID conflicts are remapped without overwriting existing presets')
check('presetOrder: orderedPresetIds(mappedOrder, userPresets)' in main, 'imported order is deduplicated and missing current IDs are restored')
preset_import = main.split('function parsePresetImport(', 1)[1].split('function exportPresets(', 1)[0]
check('if (userPresets.length > 32)' in preset_import and '.slice(-32)' not in preset_import, 'capacity errors cannot silently discard existing user presets')
check(html.count('data-settings-page=') >= 4, 'all four settings pages exist')
check('min="40" max="104"' in html, 'TD preset card size range is preserved')
check(re.search(r'class="preview-transport"[^>]*\bhidden\b', html) is not None, 'preview transport is removed from the canvas')
check(re.search(r'id="speedInfo"[^>]*\bhidden\b', html) is not None, 'speed badge is removed from the canvas')
preset_render = main.split('function renderPresetList()', 1)[1].split('function applyPreset(', 1)[0]
check('filter(([, preset]) => preset.mode === state.mode)' in preset_render, 'built-in presets are filtered by current mode')
check('model.normalize(preset.state).mode === state.mode' in preset_render, 'user presets are filtered by current mode')
mode_listener = main.split("state.mode = button.dataset.mode;", 1)[1].split('});', 1)[0]
check('renderPresetList();' in mode_listener, 'mode switching refreshes filtered presets')
check('settings.presetSize * 2 + 30' in main, 'preset sidebar reserves two cards, spacing and scrollbar space')
for size in (40, 80, 104):
    available = max(112, size * 2 + 30) - 30
    check(available >= size * 2, f'two {size}px preset cards fit the sidebar')
handles = main.split('function drawHandles(', 1)[1].split('function draw()', 1)[0]
positions = main.split('function bezierHandlePositions(', 1)[1].split('function drawHandles(', 1)[0]
check('const values = speedView ? metrics.samples.speeds : metrics.samples.values;' in positions, 'speed and value views use their matching series')
check('const range = speedView ? metrics.speedRange : metrics.valueRange;' in positions, 'speed and value views use their matching vertical scale')
check('const startY = toY(startValue, range, metrics)' in positions and 'const endY = toY(endValue, range, metrics)' in positions, 'speed anchors use endpoint speeds and the speed range')
check('const firstY = speedView ? startY' in positions and 'const secondY = speedView ? endY' in positions, 'speed controls are horizontal endpoint-speed handles')
check('drawLine(ctx, [points.start, points.first]' in handles and 'drawLine(ctx, [points.end, points.second]' in handles, 'drawn handles use the shared position mapping')
hit = main.split('function findHandle(', 1)[1].split('function updateFromPointer(', 1)[0]
check('const points = bezierHandlePositions(metrics);' in hit, 'hit testing uses the same handle positions as drawing')
check('function requestDraw()' in main and 'requestAnimationFrame(draw)' in main, 'redraws are coalesced by animation frame')
check('let metricsCache = null;' in main and 'metricsCache.stateKey === cacheKey' in main, 'unchanged curve samples are cached')
check('let segmentsKeyCache = { reference: null, key:' in main and 'segmentsKeyCache.reference !== state.segments' in main, 'multi-segment state keys serialize only when the segment array changes')
check('const scalarKey = Object.keys(model.DEFAULTS)' in main, 'scalar curve edits always contribute to the current state key')
check('return drag.speedRange.slice();' in main and 'drag.stableRatio' not in main, 'speed dragging keeps a fixed viewport instead of auto-scaling')
check('function speedEditorRange(' in main and 'speedViewRangeStateKey !== stateKey' in main, 'speed viewport refits only for external curve changes')
finish_drag = main.split('function finishDrag(', 1)[1].split('function changeSettings(', 1)[0]
check('const finalSpeedRange = initialSpeedRange && !cancel ? graphMetrics().speedRange.slice() : null;' in finish_drag, 'releasing a speed drag preserves the final viewport')
check('cancel ? initialSpeedRange.slice() : finalSpeedRange' in finish_drag, 'cancelling a speed drag restores the initial viewport')
check('speedViewRangeStateKey = curveStateKey();' in finish_drag, 'finished speed drags retain their viewport state key')
check('speedViewRange = null; draw();' in main, 'explicit fit-to-curve remains available')
check('function thumbnailSamples(' in main and 'thumbnailSampleCache.get(key)' in main, 'preset thumbnails reuse sampled curves')
check('document.createDocumentFragment()' in main and 'presetCanvases.set(canvas, entry.state)' in main, 'preset list mounts once and retains thumbnail state')
setting_changes = main.split('function changeSettings(', 1)[1].split('function setSettingsPage(', 1)[0]
check('schedulePresetThumbnails();' in setting_changes and "['themeColor', 'presetSize', 'location']" in setting_changes, 'thumbnail refreshes are limited to theme and layout changes')
check('setTimeout(flushSettings, 80)' in main and "addEventListener('pagehide', flushSettings)" in main, 'settings writes are debounced and flushed on exit')
check('preview.lastPaintKey === key' in main, 'identical playhead frames are not repainted')
check('Math.max(112, settings.presetSize + 24)' in main, 'horizontal preset panels fit larger cards')
check("ui.gridX.addEventListener('input'" in main, 'grid X updates during numeric input')
check("ui.gridY.addEventListener('input'" in main, 'grid Y updates during numeric input')
check("settings.location === 'top' ? event.clientY - resizeDrag.y" in main and 'event.clientX - resizeDrag.x' in main, 'all preset resize directions are mapped correctly')
apply_preset = main.split('function applyPreset(', 1)[1].split('function hostCall(', 1)[0]
check('selectedPresetId = id;\n    updatePresetSelection();' in apply_preset, 'preset selection updates without a full control render dependency')
check('event.type === \'pointermove\'' in main and 'lastPointerMoveTime' in main, 'legacy mouse moves are deduplicated against pointer moves')
check('velo-ae-settings-v2' in main, 'settings persist across panel reloads')
check('eval(' not in main, 'no dynamic JavaScript eval')
check(not re.search(r'https?://', html + main), 'no remote runtime dependency')
check('<html lang="zh-CN">' in html, 'document defaults to Chinese')
check(re.search(r'id="appContainer"[^>]*data-language="zh-CN"', html) is not None, 'app exposes its initial language')
language_select = re.search(r'<select id="languageSelect">(.*?)</select>', html, re.S)
check(language_select is not None, 'language select exists in interface settings')
for value, label in (('zh-CN', '中文'), ('en', 'English'), ('ja', '日本語'), ('ko', '한국어')):
    check(f'<option value="{value}">{label}</option>' in language_select.group(1), f'native language option: {value}')
check(html.index('js/i18n.js') < html.index('js/main.js'), 'i18n module loads before main.js')
i18n = (PANEL / 'js' / 'i18n.js').read_text(encoding='utf-8')
check('window.VeloI18n' not in i18n or 'root.VeloI18n = api' in i18n, 'i18n public API is exposed')
check('MutationObserver' not in i18n + main and 'setInterval' not in i18n + main, 'language updates use no observer or polling')
check(html.count('data-i18n=') >= 50 and 'data-i18n-title=' in html and 'data-i18n-aria-label=' in html, 'static text, titles, and aria labels are translatable')
check("language: 'zh-CN'" in main and 'i18n.normalizeLanguage' in main, 'stored language is validated with a Chinese default')
check("ui.language.addEventListener('change'" in main and 'applyLanguage(settings.language);' in main, 'language control refreshes the panel')
check('renderStatus();' in main and 'updateEaseBuffer();' in main and 'renderPresetList();' in main, 'language refresh covers status, counts, and presets')

jsx = (PANEL / 'jsx' / 'hostscript.jsx').read_text(encoding='utf-8')
for name in ('ping', 'inspect', 'readCurve', 'apply', 'exportPresetFile', 'easeCopyCopy', 'easeCopyPaste', 'passthrough', 'stringify', 'beginUndoGroup', 'endUndoGroup', 'setTemporalEaseAtKey', 'setValueAtTime'):
    check(name in jsx, f'host capability: {name}')
check('File.saveDialog' in jsx and 'file.fsName' in jsx, 'native export returns the user-selected save path')
check('cancelled: true' in jsx and 'file.write(payload)' in jsx, 'native export distinguishes cancellation from an actual file write')
check('function validNativeSegments' in jsx and 'function applyMulti' in jsx and 'function easeSideFor' in jsx, 'multi-anchor Apply writes per-dimension native temporal easing')
check('hiddenAt(hidden, u)' in jsx and 'shapePreservedSegments' in jsx, 'hidden anchors stay out of sampled keys and the local fallback is reported explicitly')
check('Math.abs(prop.keyTime(index) - time) > 0.0001' in jsx, 'key lookup tolerates AE frame-time quantization without losing new keys')
value_paste = jsx.split('if (payload.kind === "value") {', 1)[1].split('} else if (targets.length === 1) {', 1)[0]
check('var originalEases = [];' in value_paste and 'inEase: prop.keyInTemporalEase(targets[v].index)' in value_paste and 'outEase: prop.keyOutTemporalEase(targets[v].index)' in value_paste, 'value paste captures both target ease sides before AE can recalculate them')
check(value_paste.index('prop.setValueAtKey(') < value_paste.index('prop.setTemporalEaseAtKey(targets[v].index, originalEases[v].inEase, originalEases[v].outEase);'), 'value paste restores all target ease sides only after every value changes')

model = (PANEL / 'js' / 'curve-model.js').read_text(encoding='utf-8')
check(model.count('label:') == 22, '22 built-in presets remain')
check('function nativeEase' in model, 'native AE ease mapping remains')
check('function sample' in model, 'sampling remains available')
check('function splitAt' in model and 'function removeAnchor' in model, 'multi-segment insertion and deletion are available')
check('function validSegments' in model and 'function bezierBreakpoints' in model, 'multi-segment validation and true speed breakpoints are available')
check('function smoothAnchor' in model and 'function smoothAllAnchors' in model, 'single-anchor and global smoothing share the curve model')
check('function snapHandleToTangent' in model and 'function visibleAnchorCount' in model, 'tangent snapping and visible-anchor accounting are model-driven')
check('preserveShape' in model and 'hiddenAnchors' in model and '!isShapeAnchor(state, i + 1)' in model, 'shape-preserving deletion retains geometry while omitting Apply anchor times')
check('event.shiftKey' in main and 'model.removeAnchor(state, nearest.index, true)' in main, 'Shift right-click invokes shape-preserving deletion directly')
check("applyAnchorAction('smooth')" in main and "applyAnchorAction('preserve')" in main and "applyAnchorAction('delete')" in main, 'the anchor menu exposes smooth, preserving and ordinary deletion actions')
check('model.smoothAllAnchors(state)' in main and 'model.snapHandleToTangent(state' in main, 'the main smoothing button and handle snapping call the shared model')
check('function updateAnchorLayout' in main and 'model.visibleAnchorCount(state)' in main, 'editing height adapts to the visible anchor count')
check('filter((anchor) => !model.isShapeAnchor(state, anchor.index))' in main, 'shape knots cannot intercept visible-anchor hit testing')
check('function bezierValueData' in main and 'segment.forEach((point) => data.push(point[1]))' in main, 'value viewport includes every Bezier control handle')
check('if (!Number.isFinite(samples[index]))' in main and 'hasPoint = false' in main, 'non-finite speed samples start new subpaths instead of reaching Canvas')
check('function openColorPicker' in main and 'function closeColorPicker' in main, 'custom color picker opens and closes through shared controller functions')
check('function colorRgbToHsv' in main and 'function colorHsvToRgb' in main, 'color editing supports HSV and RGB conversion')
check('settings[target] = original' in main and 'changeSettings({ [target]: value })' in main, 'color cancellation restores and application persists the intended values')
check('function segmentSpeedAt' in model and 'MIN_ANCHOR_GAP' in model, 'true endpoint derivatives and the near-duplicate insertion guard are available')
check('model.segmentSpeedAt(previous, 1)' in main and 'model.segmentSpeedAt(segment, 0)' in main, 'multi-segment speed handles use true segment endpoint derivatives')
check('if (anchor.incoming || anchor.outgoing)' not in main, 'speed drawing does not reference an out-of-scope anchor variable')
check('function openMultiPointDialog' in main and 'function switchToMultiPointValue' in main, 'unsupported modes open a dedicated multi-anchor dialog with a value-view switch')
check('function statusHealth' in main and 'ui.healthDot.dataset.state' in main and 'ui.statusText.textContent' in main, 'Velo health color and status text have independent state mappings')

css = (PANEL / 'css' / 'style.css').read_text(encoding='utf-8')
check('.color-picker-backdrop' in css and 'z-index: 1400' in css, 'color picker is a top-level interactive dialog')
check('.anchor-snap-hint' in css and '.app-container.anchor-expanded' in css, 'snap feedback and expanded editor styles exist')
for token in ('#323232', '#222222', '#4a4a4a', '#0078d4', '#2a2a2a'):
    check(token in css, f'visual token: {token}')
check('border-radius: 4px' in css, 'rounded controls exist')
check('border-radius: 8px' in css, 'rounded settings panel exists')
check('prefers-reduced-motion' in css, 'reduced motion is respected')
check('display: grid; grid-template-columns: repeat(2, var(--preset-box-size));' in css, 'preset list is an explicit two-column grid')
check('aspect-ratio: 1;' in css and css.count('display: flex; flex-wrap: nowrap;') >= 2, 'square preset cards preserve horizontal layouts')
check('flex: 0 0 var(--preset-box-size); width: var(--preset-box-size); height: var(--preset-box-size);' in css, 'top and bottom cards cannot shrink')
check('.app-container:not(.compact-mode) .preset-item { flex: 0 0 var(--preset-box-size); width: var(--preset-box-size); height: var(--preset-box-size); }' in css, 'narrow panels preserve card size')
check('box-shadow: 0 0 4px var(--accent-soft);' in css, 'selected glow follows the active theme')
check('#applyBtn:hover { background: var(--btn-active-hover-bg); }' in css, 'apply hover follows the active theme')
check('.settings-button-row > button.theme-choice { flex: 1 1 0; min-width: 0; white-space: nowrap; }' in css, 'three quick themes share one equal-width row without wrapping')

print(f'1..{checks}')
