#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const model = require('../VeloAE/js/curve-model.js');

const mainPath = path.join(__dirname, '../VeloAE/js/main.js');
const modelPath = path.join(__dirname, '../VeloAE/js/curve-model.js');
const mainSource = fs.readFileSync(mainPath, 'utf8');
let passed = 0;

function test(name, fn) {
  fn();
  passed += 1;
  console.log(`ok ${passed} - ${name}`);
}
function close(actual, expected, tolerance = 1e-9) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);
}
function closeArray(actual, expected, tolerance = 1e-9) {
  assert.strictEqual(actual.length, expected.length);
  actual.forEach((value, index) => close(value, expected[index], tolerance));
}
function declaration(name) {
  const start = mainSource.indexOf(`  function ${name}(`);
  assert(start >= 0, `${name} exists`);
  const end = mainSource.indexOf('\n  function ', start + 2);
  assert(end > start, `${name} has a complete declaration`);
  return mainSource.slice(start, end);
}
function publicSamples(state, count) {
  const normalized = model.normalize(state);
  const result = { values: [], speeds: [] };
  for (let index = 0; index < count; index += 1) {
    const pair = model.valueAndSpeed(normalized, index / (count - 1));
    result.values.push(pair[0]);
    result.speeds.push(pair[1]);
  }
  result.values[0] = 0;
  result.values[count - 1] = 1;
  return result;
}
function mockContext() {
  return {
    operations: [],
    strokes: 0,
    beginPath() {},
    moveTo(x, y) { this.operations.push({ type: 'moveTo', x, y }); },
    lineTo(x, y) { this.operations.push({ type: 'lineTo', x, y }); },
    stroke() { this.strokes += 1; }
  };
}

const drawSamples = new Function(`${declaration('toY')}\n${declaration('drawSamples')}\nreturn drawSamples;`)();

test('Bounce Out preserves the continuous value and physical velocity jump', () => {
  const state = model.normalize({ mode: 'bounce', direction: 'out', restitution: 0.56, bounce_period: 0.4 });
  const left = model.valueAndSpeed(state, 0.2 - 1e-7);
  const at = model.valueAndSpeed(state, 0.2);
  const right = model.valueAndSpeed(state, 0.2 + 1e-7);
  close(left[0], 1, 2e-6);
  close(at[0], 1, 1e-12);
  close(right[0], 1, 2e-6);
  close(left[1], 10, 2e-5);
  close(at[1], -5.6, 1e-12);
  close(right[1], -5.6, 2e-5);
  close(right[1] / left[1], -0.56, 2e-5);
});

test('breakpoints use impact recurrence and sorted direction mappings', () => {
  const basis = { mode: 'bounce', restitution: 0.56, bounce_period: 0.4, precision: 300 };
  const out = model.bounceBreakpoints(Object.assign({}, basis, { direction: 'out' }), 800);
  const expectedImpacts = [0.2, 0.2 + 0.4 * 0.56, 0.2 + 0.4 * 0.56 + 0.4 * 0.56 * 0.56];
  closeArray(out.slice(0, 3), expectedImpacts);
  const inward = model.bounceBreakpoints(Object.assign({}, basis, { direction: 'in' }), 800);
  closeArray(inward, out.map((event) => 1 - event).reverse());
  const inout = model.bounceBreakpoints(Object.assign({}, basis, { direction: 'inout' }), 800);
  const expectedInOut = out.flatMap((event) => [(1 - event) * 0.5, (1 + event) * 0.5]).sort((a, b) => a - b);
  closeArray(inout, expectedInOut);
  assert.ok(inward.includes(0.8));
  assert.ok(inout.includes(0.4) && inout.includes(0.6));
  [
    { direction: 'in', event: 0.8, value: 0, left: -5.6, right: 10 },
    { direction: 'inout', event: 0.4, value: 0, left: -5.6, right: 10 },
    { direction: 'inout', event: 0.6, value: 1, left: 10, right: -5.6 }
  ].forEach((entry) => {
    const state = Object.assign({}, basis, { direction: entry.direction });
    const left = model.valueAndSpeed(state, entry.event - 1e-7);
    const right = model.valueAndSpeed(state, entry.event + 1e-7);
    close(left[0], entry.value, 2e-6);
    close(right[0], entry.value, 2e-6);
    close(left[1], entry.left, 2e-5);
    close(right[1], entry.right, 2e-5);
  });
});

test('zero restitution and period boundaries produce only interior events', () => {
  const zero = model.normalize({ mode: 'bounce', direction: 'out', restitution: 0, bounce_period: 0.4 });
  closeArray(model.bounceBreakpoints(zero, 800), [0.2]);
  closeArray(model.bounceBreakpoints(Object.assign({}, zero, { direction: 'in' }), 800), [0.8]);
  closeArray(model.bounceBreakpoints(Object.assign({}, zero, { direction: 'inout' }), 800), [0.4, 0.6]);
  close(model.valueAndSpeed(zero, 0.2)[0], 1);
  close(model.valueAndSpeed(zero, 0.2)[1], 0);
  close(model.valueAndSpeed(zero, 0.2 - 1e-7)[1], 10, 2e-5);
  assert.deepStrictEqual(model.bounceBreakpoints({ mode: 'bounce', restitution: 0, bounce_period: 2 }, 800), []);
  closeArray(model.bounceBreakpoints({ mode: 'bounce', restitution: 0, bounce_period: 0.0001 }, 800), [0.00005]);
});

test('zero restitution direction events drive production Canvas topology', () => {
  const expectedMoves = { out: [0, 1], in: [0, 4], inout: [0, 2, 3] };
  ['out', 'in', 'inout'].forEach((direction) => {
    const state = model.normalize({ mode: 'bounce', direction, restitution: 0, bounce_period: 0.4 });
    const samples = model.sample(state, 6);
    const breaks = model.bounceBreakpoints(state, 800);
    const metrics = {
      left: 0, top: 0, width: 100, height: 100,
      speedRange: [-20, 20], valueRange: [-0.2, 1.2], speedBreakpoints: breaks
    };
    const speedContext = mockContext();
    const valueContext = mockContext();
    drawSamples(speedContext, samples.speeds, '#555555', 1.2, metrics, true);
    drawSamples(valueContext, samples.values, '#ffffff', 1.7, metrics, false);
    const expectedTypes = samples.speeds.map((value, index) => expectedMoves[direction].includes(index) ? 'moveTo' : 'lineTo');
    assert.deepStrictEqual(speedContext.operations.map((point) => point.type), expectedTypes);
    valueContext.operations.forEach((point, index) => assert.strictEqual(point.type, index === 0 ? 'moveTo' : 'lineTo'));
    if (direction !== 'out') assert.strictEqual(speedContext.operations[1].type, 'lineTo');
    speedContext.operations.forEach((point, index) => {
      if (point.type !== 'lineTo') return;
      const previous = (index - 1) / 5;
      const current = index / 5;
      assert.ok(!breaks.some((event) => previous < event && event <= current));
    });
  });
});

test('representative parameters stay finite with ordered interior breakpoints', () => {
  const cases = [
    { restitution: 0, bounce_period: 0.0001 },
    { restitution: 0.56, bounce_period: 0.4 },
    { restitution: 0.68, bounce_period: 0.37 },
    { restitution: 0.95, bounce_period: 1.8 },
    { restitution: Math.sqrt(0.999), bounce_period: 2 }
  ];
  cases.forEach((parameters) => {
    ['out', 'in', 'inout'].forEach((direction) => {
      const state = Object.assign({ mode: 'bounce', direction, precision: 300 }, parameters);
      const samples = model.sample(state, 301);
      assert.strictEqual(samples.values[0], 0);
      assert.strictEqual(samples.values[300], 1);
      assert.ok(samples.values.every(Number.isFinite));
      assert.ok(samples.speeds.every(Number.isFinite));
      const breaks = model.bounceBreakpoints(state, 800);
      assert.ok(breaks.every((event, index) => event > 0 && event < 1 && (index === 0 || event > breaks[index - 1])));
      assert.ok(model.bounceBreakpoints(state, NaN).every(Number.isFinite));
    });
  });
});

test('mock Canvas breaks every speed crossing but never the value series', () => {
  ['out', 'in', 'inout'].forEach((direction) => {
    const state = model.normalize({ mode: 'bounce', direction, restitution: 0.56, bounce_period: 0.4, precision: 300 });
    const samples = model.sample(state, 300);
    const breaks = model.bounceBreakpoints(state, 800);
    const metrics = {
      left: 16, top: 16, width: 768, height: 400,
      speedRange: [-20, 20], valueRange: [-0.2, 1.2], speedBreakpoints: breaks
    };
    const speedContext = mockContext();
    const valueContext = mockContext();
    drawSamples(speedContext, samples.speeds, '#555555', 1.2, metrics, true);
    drawSamples(valueContext, samples.values, '#ffffff', 1.7, metrics, false);
    assert.strictEqual(speedContext.operations.length, 300);
    assert.strictEqual(valueContext.operations.length, 300);
    assert.strictEqual(speedContext.strokes, 1);
    assert.strictEqual(valueContext.strokes, 1);
    speedContext.operations.concat(valueContext.operations).forEach((point) => {
      assert.ok(Number.isFinite(point.x) && Number.isFinite(point.y));
    });
    speedContext.operations.forEach((point, index) => {
      if (index === 0) assert.strictEqual(point.type, 'moveTo');
      if (point.type !== 'lineTo') return;
      const previous = (index - 1) / 299;
      const current = index / 299;
      assert.ok(!breaks.some((event) => previous < event && event <= current), `${direction} crossed an impact at sample ${index}`);
    });
    valueContext.operations.forEach((point, index) => {
      assert.strictEqual(point.type, index === 0 ? 'moveTo' : 'lineTo');
    });
    if (direction === 'out') {
      assert.strictEqual(speedContext.operations[59].type, 'lineTo');
      assert.strictEqual(speedContext.operations[60].type, 'moveTo');
      assert.strictEqual(valueContext.operations[60].type, 'lineTo');
    }
  });
});

test('exact sample boundaries and non-Bounce modes retain correct topology', () => {
  const metrics = { left: 0, top: 0, width: 100, height: 100, speedRange: [0, 1], valueRange: [0, 1], speedBreakpoints: [0.3, 0.4, 0.5] };
  const speedContext = mockContext();
  drawSamples(speedContext, [0, 0.25, 1, 0.75, 1], '#555555', 1, metrics, true);
  assert.deepStrictEqual(speedContext.operations.map((point) => point.type), ['moveTo', 'lineTo', 'moveTo', 'lineTo', 'lineTo']);
  const valueContext = mockContext();
  drawSamples(valueContext, [0, 0.25, 1, 0.75, 1], '#ffffff', 1, metrics, false);
  assert.deepStrictEqual(valueContext.operations.map((point) => point.type), ['moveTo', 'lineTo', 'lineTo', 'lineTo', 'lineTo']);
  ['bezier', 'elastic'].forEach((mode) => {
    assert.deepStrictEqual(model.bounceBreakpoints({ mode, direction: 'inout' }, 800), []);
    const context = mockContext();
    drawSamples(context, [0, 0.5, 1], '#555555', 1, Object.assign({}, metrics, { speedBreakpoints: [] }), true);
    assert.deepStrictEqual(context.operations.map((point) => point.type), ['moveTo', 'lineTo', 'lineTo']);
  });
});

test('sample JSON exactly matches the public valueAndSpeed contract', () => {
  ['bezier', 'elastic', 'bounce'].forEach((mode) => {
    ['out', 'in', 'inout'].forEach((direction) => {
      const state = { mode, direction, restitution: 0.56, bounce_period: 0.4, frequency: 3.25, decay: 7.5, elastic_gain: 0.72 };
      [50, 300].forEach((count) => {
        assert.strictEqual(JSON.stringify(model.sample(state, count)), JSON.stringify(publicSamples(state, count)));
      });
    });
  });
});

test('sample normalizes once per call instead of once per sample', () => {
  const source = fs.readFileSync(modelPath, 'utf8');
  const marker = 'function normalize(input) {';
  assert.ok(source.includes(marker));
  const context = { module: { exports: {} }, exports: {} };
  vm.runInNewContext(`var normalizeCalls = 0;\n${source.replace(marker, `${marker} normalizeCalls += 1;`)}`, context, { filename: modelPath });
  const counted = context.module.exports;
  const state = { mode: 'bounce', direction: 'inout', restitution: 0.56, bounce_period: 0.4 };
  [50, 300, 1000, 2000].forEach((count) => {
    context.normalizeCalls = 0;
    const actual = counted.sample(state, count);
    assert.strictEqual(context.normalizeCalls, 1);
    assert.strictEqual(JSON.stringify(actual), JSON.stringify(model.sample(state, count)));
  });
  context.normalizeCalls = 0;
  counted.valueAndSpeed(state, 0.2);
  assert.strictEqual(context.normalizeCalls, 1);
});

test('metrics cache reuses samples across geometry changes while updating event mapping', () => {
  const counts = { samples: 0, breakpoints: 0 };
  const countingModel = Object.assign({}, model, {
    sample(state, count) { counts.samples += 1; return model.sample(state, count); },
    bounceBreakpoints(state, width) { counts.breakpoints += 1; return model.bounceBreakpoints(state, width); }
  });
  let rect = { left: 10, top: 20, width: 800, height: 500 };
  const ui = { canvas: { getBoundingClientRect() { return Object.assign({}, rect); } } };
  const source = [
    'let drag = null;',
    "let editView = 'value';",
    declaration('displayRange'), declaration('curveStateKey'), declaration('speedFitRange'), declaration('speedDragRange'),
    'let metricsCache = null; let speedViewRange = null; let speedViewRangeStateKey = null;',
    declaration('speedEditorRange'), declaration('bezierValueData'), declaration('graphMetrics'),
    'return { graphMetrics, setState(next) { state = next; } };'
  ].join('\n');
  let state = model.normalize({ mode: 'bounce', direction: 'out', restitution: 0.56, bounce_period: 0.4, precision: 300 });
  const cache = new Function('model', 'ui', 'state', source)(countingModel, ui, state);
  const first = cache.graphMetrics();
  assert.strictEqual(cache.graphMetrics(), first);
  assert.deepStrictEqual(counts, { samples: 1, breakpoints: 1 });
  state = model.normalize(Object.assign({}, state, { direction: 'in' }));
  cache.setState(state);
  const inward = cache.graphMetrics();
  assert.notStrictEqual(inward, first);
  closeArray(inward.speedBreakpoints, first.speedBreakpoints.map((event) => 1 - event).reverse());
  assert.deepStrictEqual(counts, { samples: 2, breakpoints: 2 });
  state = model.normalize(Object.assign({}, state, { restitution: 0.6 }));
  cache.setState(state);
  cache.graphMetrics();
  state = model.normalize(Object.assign({}, state, { bounce_period: 0.45 }));
  cache.setState(state);
  cache.graphMetrics();
  assert.deepStrictEqual(counts, { samples: 4, breakpoints: 4 });
  const samplesBeforeResize = cache.graphMetrics().samples;
  rect = Object.assign({}, rect, { width: 400 });
  const resized = cache.graphMetrics();
  assert.strictEqual(resized.samples, samplesBeforeResize);
  assert.strictEqual(resized.rect.width, 400);
  rect = Object.assign({}, rect, { height: 460 });
  const relaidOut = cache.graphMetrics();
  assert.strictEqual(relaidOut.samples, samplesBeforeResize);
  assert.strictEqual(relaidOut.rect.height, 460);
  assert.deepStrictEqual(counts, { samples: 4, breakpoints: 6 });
  state = model.normalize(Object.assign({}, state, { precision: 400 }));
  cache.setState(state);
  cache.graphMetrics();
  assert.deepStrictEqual(counts, { samples: 5, breakpoints: 7 });
  const cached = cache.graphMetrics();
  assert.strictEqual(cache.graphMetrics(), cached);
  assert.deepStrictEqual(counts, { samples: 5, breakpoints: 7 });
});

console.log(`1..${passed}`);
