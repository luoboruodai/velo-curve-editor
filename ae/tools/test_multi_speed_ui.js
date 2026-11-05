#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const model = require('../VeloAE/js/curve-model.js');
const source = fs.readFileSync(require('node:path').join(__dirname, '../VeloAE/js/main.js'), 'utf8');
function declaration(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert(start >= 0, `${name} exists`);
  const end = source.indexOf('\n  function ', start + 2);
  assert(end > start, `${name} has a complete declaration`);
  return source.slice(start, end);
}
let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}
function difference(a, b) {
  return Math.max(...a.map((value, index) => Math.abs(value - b[index])));
}

const base = model.splitAt(model.splitAt(model.presetState('sine_inout'), 0.6), 0.3);
const preserved = model.removeAnchor(base, 1, true);
const before = model.sample(preserved, 1001);
const hiddenX = base.segments[0][3][0];
const near = model.splitAt(preserved, hiddenX + 0.001);
check(near.segments.length === preserved.segments.length && near.hiddenAnchors.length === 1, 'near-duplicate insertion leaves the preserved segments unchanged');
check(difference(before.values, model.sample(near, 1001).values) === 0 && difference(before.speeds, model.sample(near, 1001).speeds) === 0, 'near-duplicate insertion keeps value and speed samples exactly identical');
const allowed = model.splitAt(preserved, hiddenX + 0.003);
check(allowed.segments.length === preserved.segments.length + 1 && allowed.hiddenAnchors.length === 1, 'a sufficiently separated insertion keeps the original shape-knot identity');
check(difference(before.values, model.sample(allowed, 1001).values) < 1e-6 && difference(before.speeds, model.sample(allowed, 1001).speeds) < 1e-5, 'allowed insertion preserves the curve within the measured tolerance');

const firstSegment = base.segments[0];
const expectedStart = (() => {
  const dx = 3 * (firstSegment[1][0] - firstSegment[0][0]), dy = 3 * (firstSegment[1][1] - firstSegment[0][1]);
  return dy / dx;
})();
check(model.segmentSpeedAt(firstSegment, 0) === expectedStart, 'segment start speed uses the true right derivative');
const expectedEnd = (() => {
  const dx = 3 * (firstSegment[3][0] - firstSegment[2][0]), dy = 3 * (firstSegment[3][1] - firstSegment[2][1]);
  return dy / dx;
})();
check(model.segmentSpeedAt(firstSegment, 1) === expectedEnd, 'segment end speed uses the true left derivative');

const { toY, multiBezierPositions } = new Function('model', 'state', 'editView', `${declaration('toY')}\n${declaration('multiBezierPositions')}\nreturn { toY, multiBezierPositions };`)(model, base, 'speed');
const metrics = { left: 16, top: 16, width: 320, height: 400, valueRange: [0, 1], speedRange: [-2, 2] };
const anchors = multiBezierPositions(metrics);
check(anchors[1].incoming && anchors[1].outgoing, 'interior anchors expose both speed handles');
check(anchors[0].outgoing && anchors[anchors.length - 1].incoming, 'endpoints expose their corresponding speed handles');
const expectedOutgoingY = toY(model.clamp(model.segmentSpeedAt(base.segments[1], 0), -2, 2), [-2, 2], metrics);
check(anchors[1].outgoing[1] === expectedOutgoingY, 'speed handle Y maps the segment start derivative instead of the value control Y');
const expectedIncomingY = toY(model.clamp(model.segmentSpeedAt(base.segments[0], 1), -2, 2), [-2, 2], metrics);
check(anchors[1].incoming[1] === expectedIncomingY, 'speed handle Y maps the segment end derivative instead of the value control Y');
const findHandleBody = source.slice(source.indexOf('  function findHandle('), source.indexOf('  function updateFromPointer('));
check(!findHandleBody.includes("if (editView !== 'value') return null"), 'speed view handles participate in hit testing');
check(source.includes('handleY = anchor[1] + (pointIndex === 1 ? 1 : -1) * y * (handleX - anchor[0]) / 3'), 'speed dragging maps derivative speed back to the value handle');
check(source.includes('minimumX = pointIndex === 1 ? segment[0][0] + gap') && source.includes('maximumX = pointIndex === 2 ? segment[3][0] - gap'), 'multi-handle dragging keeps a positive time-direction margin');

const { statusHealth } = new Function('currentStatus', `${declaration('statusHealth')}\nreturn { statusHealth };`)({ key: 'status.ready', isError: false });
check(statusHealth() === 'ready', 'ready status uses the green breathing dot');
const { statusHealth: warningHealth } = new Function('currentStatus', `${declaration('statusHealth')}\nreturn { statusHealth };`)({ key: 'status.pointTooClose', isError: false });
check(warningHealth() === 'warning', 'near-duplicate and unsupported-mode warnings use the yellow dot');
const { statusHealth: busyHealth } = new Function('currentStatus', `${declaration('statusHealth')}\nreturn { statusHealth };`)({ key: 'status.applying', isError: false });
check(busyHealth() === 'busy', 'host activity uses the yellow busy dot');
const { statusHealth: errorHealth } = new Function('currentStatus', `${declaration('statusHealth')}\nreturn { statusHealth };`)({ key: 'status.invalidCurveJson', isError: true });
check(errorHealth() === 'error', 'errors use the red dot');
check(source.includes('function openMultiPointDialog') && source.includes('function switchToMultiPointValue'), 'unsupported modes open a dedicated multi-anchor dialog with a switch action');
check(source.includes('ui.statusText.textContent') && source.includes('ui.healthDot.dataset.state'), 'status text and health color update independently');
const css = fs.readFileSync(require('node:path').join(__dirname, '../VeloAE/css/style.css'), 'utf8');
check(css.includes('@keyframes health-breathe') && css.includes('.reduce-motion .health-dot { animation: none; }'), 'breathing is CSS-driven and disabled by the project reduced-motion setting');
check(css.includes('@media (prefers-reduced-motion: reduce) { .health-dot { animation: none; } }'), 'system reduced-motion also disables breathing');
console.log(`1..${checks}`);
