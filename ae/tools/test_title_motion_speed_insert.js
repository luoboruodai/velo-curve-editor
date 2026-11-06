#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const model = require('../VeloAE/js/curve-model.js');
const source = fs.readFileSync(path.join(__dirname, '../VeloAE/js/main.js'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, '../VeloAE/index.html'), 'utf8');
const css = fs.readFileSync(path.join(__dirname, '../VeloAE/css/style.css'), 'utf8');
const manifest = fs.readFileSync(path.join(__dirname, '../VeloAE/CSXS/manifest.xml'), 'utf8');
const translations = fs.readFileSync(path.join(__dirname, '../VeloAE/js/i18n.js'), 'utf8');
let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}
function declaration(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert(start >= 0, `${name} exists`);
  const end = source.indexOf('\n  function ', start + 2);
  assert(end > start, `${name} has a complete declaration`);
  return source.slice(start, end);
}
function difference(a, b) {
  return Math.max(...a.map((value, index) => Math.abs(value - b[index])));
}
function insertionHarness(initial) {
  let dialogs = 0;
  const args = [
    model, initial, null,
    { canvas: { getBoundingClientRect: () => ({ left: 0, top: 0 }) } },
    () => null,
    () => ({ rect: { left: 0, top: 0 }, left: 0, width: 100 }),
    () => {}, () => {}, () => {}, () => { dialogs += 1; }
  ];
  const harness = new Function('model', 'state', 'drag', 'ui', 'findHandle', 'graphMetrics', 'clearPresetSelection', 'updateControls', 'showStatus', 'openMultiPointDialog', `${declaration('addPoint')}\nreturn { addPoint, getState: () => state };`)(...args);
  return { harness, dialogs: () => dialogs };
}

const addPointBody = declaration('addPoint');
check(addPointBody.includes("if (state.mode !== 'bezier')") && !addPointBody.includes("editView !== 'value'"), 'Bezier speed view uses the same insertion path as the value view');
const insertion = insertionHarness(model.presetState('sine_inout'));
const before = model.sample(insertion.harness.getState(), 1001);
insertion.harness.addPoint({ clientX: 50, clientY: 20, preventDefault() {} });
const after = insertion.harness.getState();
check(after.segments.length === 2 && insertion.dialogs() === 0, 'double-click in the speed view inserts a real segment without opening the dialog');
const afterSamples = model.sample(after, 1001);
check(difference(before.values, afterSamples.values) < 1e-8, 'speed insertion preserves all value samples');
check(difference(before.speeds, afterSamples.speeds) < 1e-7, 'speed insertion preserves all derivative samples');
const unsupported = insertionHarness(model.presetState('bounce_out'));
const unsupportedBefore = unsupported.harness.getState();
unsupported.harness.addPoint({ clientX: 50, clientY: 20, preventDefault() {} });
check(unsupported.dialogs() === 1, 'Elastic and Bounce retain the dedicated multi-anchor dialog');
check(unsupported.harness.getState() === unsupportedBefore, 'unsupported-mode dialog leaves the curve unchanged');

const headerStart = html.indexOf('<header class="header">');
const modeStart = html.indexOf('<div class="mode-group"');
const statusStart = html.indexOf('id="status"');
check(headerStart >= 0 && statusStart > headerStart && statusStart < modeStart, 'the status badge is immediately before the Bezier mode group');
const actionsStart = html.indexOf('<div class="actions">');
check(actionsStart > 0 && !html.slice(actionsStart).includes('id="status"'), 'the old bottom status is removed instead of duplicated');
check(!source.includes('setWindowTitle') && !source.includes('renderWindowTitle'), 'status changes never rewrite the macOS window title');
check(manifest.includes('<Menu>Velo</Menu>') && !manifest.includes('🟢'), 'the native AE tab is plain Velo without the green icon');
check((manifest.match(/1\.2\.1/g) || []).length === 2, 'both manifest versions are 1.2.1');
check(html.includes('id="healthDot"') && html.includes('id="statusText"'), 'breathing health and readable status remain available');
check(declaration('renderStatus').includes('ui.status.title = text') && declaration('renderStatus').includes('ui.status.dataset.state = health'), 'the badge preserves full tooltip text and its state mapping');
check(declaration('renderStatus').includes('status.compactWarning') && declaration('renderStatus').includes('status.compactError'), 'the header uses short state labels instead of expanding for full messages');
check(css.includes('.header-status { flex: 0 0 auto;') && css.includes('margin-right: 4px'), 'the header uses content-based compact spacing next to Bezier');
check(css.includes('.mode-group { flex: 1 1 160px; gap: 3px; }'), 'narrow layouts keep the status and Bezier mode group on the same row');
check(html.includes('id="statusToast"') && html.includes('id="toastClose"'), 'a dedicated notification toast and close action exist');
check(css.includes('.status-toast.visible') && css.includes('translateX(0)') && css.includes('translateX(calc(100% + 16px))'), 'toast enters and exits from the right edge');
check(source.includes('pointerenter') && source.includes('pointerleave') && source.includes('focusin') && source.includes('focusout'), 'hover and focus pause and resume notification dismissal');
check(declaration('finishToastClose').includes('ui.toast.hidden = true') && declaration('finishToastClose').includes("currentStatus = { key: 'status.ready'"), 'toast completion hides the notification and restores the ready state');
check(source.includes('setTimeout(finishToastClose, 160)') && source.includes('if (toastClosing && multiPointReducedMotion()) finishToastClose();'), 'toast exit has a bounded interval and immediately settles under reduced motion');

check(source.includes('let multiPointClosing = false;') && source.includes('let multiPointFocusReturn = null;'), 'dialog tracks its closing phase and focus-return target');
check(source.includes('setTimeout(finishMultiPointClose, 160)'), 'dialog hides only after its exit animation interval');
check(declaration('finishMultiPointClose').includes('ui.multiModal.hidden = true;') && declaration('finishMultiPointClose').includes('target.focus'), 'dialog completion hides the backdrop and restores focus');
check(source.includes('function multiPointReducedMotion()') && source.includes('systemMotionPreference.matches'), 'project and system reduced-motion preferences share the dialog lifecycle');
check(source.includes("ui.multiModal.classList.toggle('reduce-motion', settings.reduceMotion)"), 'the top-level dialog inherits the project reduced-motion class even though it is outside appContainer');
check(source.includes("systemMotionPreference.addEventListener('change', settleMultiPointMotion)"), 'system reduced-motion changes settle an active closing transition');
check(source.includes('if (multiPointOpen && !multiPointClosing) return;'), 'repeated dialog opens do not duplicate listeners or reset the current entry');
check(source.includes('if (!multiPointOpen || multiPointClosing) return;'), 'closing ignores repeated cancellation and switching actions');
check(css.includes('.multi-point-backdrop.visible .multi-point-panel') && css.includes('translateY(8px) scale(.97)'), 'dialog entry combines opacity, translation, and scale');
check(css.includes('.multi-point-backdrop.closing .multi-point-panel') && css.includes('translateY(6px) scale(.98)'), 'dialog exit has a distinct reverse motion');
check(css.includes('.multi-point-backdrop.opening, .multi-point-backdrop.closing { visibility: visible; pointer-events: auto; }'), 'opening and closing backdrops block background pointer input from the first frame');
check(css.includes('.multi-point-backdrop.closing { opacity: 0; transition-duration: .15s; }'), 'dialog exit timing matches its completion lifecycle');
check(!source.includes('dialog.multiPointSpeed') && !translations.includes('dialog.multiPointSpeed') && !translations.includes('status.addPointValueOnly'), 'obsolete speed-view restriction text is removed');
console.log(`1..${checks}`);
