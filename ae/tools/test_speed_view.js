'use strict';

const fs = require('node:fs');
const assert = require('node:assert/strict');
const model = require('../VeloAE/js/curve-model.js');

const source = fs.readFileSync(require('node:path').join(__dirname, '../VeloAE/js/main.js'), 'utf8');
function declaration(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert(start >= 0, `${name} exists`);
  const end = source.indexOf('\n  function ', start + 2);
  assert(end > start, `${name} has a complete declaration`);
  return source.slice(start, end);
}
const { displayRange, speedDragRange, speedFitRange, speedPointerValue, gridYLines, toY, drawLine, drawGrid, bezierValueData, drawSamples } = new Function('settings', 'state', 'editView', 'drag', 'token', `${declaration('displayRange')}\n${declaration('speedDragRange')}\n${declaration('speedFitRange')}\n${declaration('speedPointerValue')}\n${declaration('gridYLines')}\n${declaration('toY')}\n${declaration('drawLine')}\n${declaration('drawGrid')}\n${declaration('bezierValueData')}\n${declaration('drawSamples')}\nreturn { displayRange, speedDragRange, speedFitRange, speedPointerValue, gridYLines, toY, drawLine, drawGrid, bezierValueData, drawSamples };`)(
  { gridX: 4, gridY: 4, showSpeed: false }, { mode: 'bezier' }, 'speed', { snapZero: true }, () => '#4a90e2'
);
let checks = 0;
function check(condition, message) {
  assert(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}
function ratio(speed, range) {
  return (speed - range[0]) / (range[1] - range[0]);
}
function stableCase(state, initial, message) {
  const range = speedDragRange(model.sample(state, 300).speeds, { speedRange: initial });
  check(range.every(Number.isFinite) && range.every((value, index) => value === initial[index]) && Math.abs(ratio(0, range) - ratio(0, initial)) < 1e-12, message);
  return range;
}
const initial = displayRange(model.sample(model.normalize({}), 300).speeds, [0]);
stableCase(model.normalize({ y1: -1 }), initial, 'negative start speed does not move the other endpoint');
stableCase(model.normalize({ y1: 1.5 }), initial, 'positive start speed does not move the other endpoint');
stableCase(model.normalize({ y2: -1 }), initial, 'negative end speed does not move the other endpoint');
stableCase(model.normalize({ y2: 2 }), initial, 'positive end speed does not move the other endpoint');
stableCase(model.normalize({ y1: 0.05 }), initial, 'in-range edits keep the viewport fixed');
stableCase(model.normalize({ y1: -1, y2: 2 }), initial, 'both handles can change without rescaling either endpoint');
const fitted = displayRange(model.sample(model.normalize({ y1: -1 }), 300).speeds, [0]);
check(fitted[0] < initial[0] && Math.abs(ratio(0, fitted) - ratio(0, initial)) > 0.01, 'explicit fit can reframe an extreme curve when requested');
const fittedSpeed = speedFitRange([0, 2]);
check(Math.abs(fittedSpeed[0] + 0.56) < 1e-12 && Math.abs(fittedSpeed[1] - 2.56) < 1e-12, 'speed fit adds substantial headroom above and below the curve');
const negativeSpeed = speedFitRange([-3, -1]);
check(Math.abs(negativeSpeed[0] - (-3.84)) < 1e-12 && Math.abs(negativeSpeed[1] - 0.84) < 1e-12, 'negative curves retain both their range and room around zero');
const defaultSpeed = speedFitRange(model.sample(model.normalize({}), 300).speeds);
check(ratio(0, defaultSpeed) > 0.15 && ratio(0, defaultSpeed) < 0.25, 'zero baseline leaves useful adjustment space below it');
const pointerMetrics = { top: 16, height: 400, speedRange: [-1, 3] };
const zeroY = toY(0, pointerMetrics.speedRange, pointerMetrics);
check(speedPointerValue(0.25, zeroY + 8, pointerMetrics) === 0 && speedPointerValue(0.25, zeroY + 8.25, pointerMetrics) === 0.25, 'positive speed snaps within eight screen pixels and releases beyond them');
check(speedPointerValue(-0.25, zeroY - 8, pointerMetrics) === 0 && speedPointerValue(-0.25, zeroY - 8.25, pointerMetrics) === -0.25, 'negative speed can snap to zero without clamping negative values');
check(declaration('speedEditorRange').includes('speedFitRange(speeds)'), 'dedicated speed view uses the expanded fit range');
const strokes = [];
const ctx = {
  beginPath() {}, moveTo() {}, lineTo() {}, strokeRect() {},
  stroke() { strokes.push({ color: this.strokeStyle, width: this.lineWidth }); }
};
drawGrid(ctx, { left: 16, top: 16, width: 320, height: 400, speedRange: [-1, 3] });
check(strokes.some(line => line.color === '#4a90e2' && line.width === 1.5), 'zero line remains visible and highlights during snapping');
const gridMetrics = { top: 16, height: 416.6, speedRange: [-0.6, 2.7] };
const fiveRows = gridYLines(gridMetrics, 5);
const eightRows = gridYLines(gridMetrics, 8);
const gridZero = toY(0, gridMetrics.speedRange, gridMetrics);
check(fiveRows.length === 6 && fiveRows.filter(y => y > gridZero).length === 2, 'five-row speed grid preserves two cells below zero');
check(eightRows.length === 9 && eightRows.filter(y => y > gridZero).length === 2 && Math.abs(eightRows[1] - eightRows[0]) < Math.abs(fiveRows[1] - fiveRows[0]), 'increasing grid density shrinks cells without crowding the zero baseline');
const threeRows = gridYLines(gridMetrics, 3);
check(threeRows.length === 4 && threeRows.filter(y => y > gridZero).length === 2, 'three-row setting keeps three rows with two below zero');
const twoRows = gridYLines(gridMetrics, 2);
check(twoRows.length === 4 && twoRows.filter(y => y > gridZero).length === 2 && twoRows.length < fiveRows.length, 'lower grid density enlarges cells while retaining the lower editing region');
const singleRow = gridYLines(gridMetrics, 1);
check(singleRow.length === 4 && singleRow[0] === gridZero && singleRow.includes(gridMetrics.top) && singleRow.at(-1) === gridMetrics.top + gridMetrics.height, 'minimum grid density remains bounded and includes both canvas edges');
const balancedRows = gridYLines({ top: 16, height: 400, speedRange: [-1, 1] }, 6);
check(balancedRows.length === 7 && balancedRows.filter(y => y > 216).length === 3, 'grid subdivisions adapt to the available space on each side of zero');
const controlState = { mode: 'bezier', segments: [
  [[0, 0], [0.1, 4], [0.2, -3], [0.5, 0.5]],
  [[0.5, 0.5], [0.6, 0.5], [0.9, 1], [1, 1]]
] };
const controlData = bezierValueData(controlState, [0, 0.5, 1]);
const controlRange = displayRange(controlData, [0, 1]);
check(controlData.includes(4) && controlData.includes(-3) && controlRange[0] < -3 && controlRange[1] > 4, 'value viewport includes both extreme control handles instead of hiding one side');
const path = [];
const pathCtx = {
  beginPath() {}, stroke() {},
  moveTo(x, y) { path.push(['M', x, y]); },
  lineTo(x, y) { path.push(['L', x, y]); }
};
drawSamples(pathCtx, [0, Infinity, 1, NaN, 2], '#4a90e2', 1, { left: 16, top: 16, width: 320, height: 400, speedRange: [-1, 3], speedBreakpoints: [] }, true);
check(path.every(([, x, y]) => Number.isFinite(x) && Number.isFinite(y)), 'non-finite speeds never reach Canvas coordinates');
check(path.filter(([command]) => command === 'M').length === 3, 'non-finite speed samples start new subpaths instead of drawing artifacts');
path.length = 0;
drawSamples(pathCtx, [0, 1, 2, 3, 4], '#4a90e2', 1, { left: 16, top: 16, width: 320, height: 400, speedRange: [-1, 5], speedBreakpoints: [0.5] }, true);
check(path.length === 5 && path.some(([command, x]) => command === 'M' && x === 176), 'real speed breakpoints start a new subpath without dropping finite samples');
console.log(`1..${checks}`);
