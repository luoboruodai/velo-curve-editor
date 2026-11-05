#!/usr/bin/env node
'use strict';
const assert = require('assert');
const model = require('../VeloAE/js/curve-model.js');

let passed = 0;
function test(name, fn) {
  fn();
  passed += 1;
  process.stdout.write(`ok ${passed} - ${name}\n`);
}
function close(actual, expected, tolerance = 1e-9) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);
}

test('all presets keep finite samples and exact endpoints', () => {
  Object.keys(model.PRESETS).forEach((id) => {
    const samples = model.sample(model.presetState(id), 513);
    close(samples.values[0], 0);
    close(samples.values[512], 1);
    samples.values.forEach((value) => assert.ok(Number.isFinite(value), id));
  });
});

test('linear Bezier is the identity with unit derivative', () => {
  const samples = model.sample(model.presetState('linear'), 257);
  for (let i = 0; i < 257; i += 1) {
    close(samples.values[i], i / 256);
    close(samples.speeds[i], 1);
  }
});

test('smooth Bezier has zero endpoint speeds', () => {
  const samples = model.sample(model.presetState('smooth'), 257);
  close(samples.speeds[0], 0);
  close(samples.speeds[256], 0);
});

test('Bezier reversal reverses the sampled curve', () => {
  const original = model.sample(model.presetState('cubic_inout'), 257).values;
  const reversed = model.sample(model.reverse(model.presetState('cubic_inout')), 257).values;
  for (let i = 0; i < 257; i += 1) close(reversed[i], 1 - original[256 - i]);
});

test('direction reversal mirrors continuous Elastic and Bounce', () => {
  ['elastic', 'bounce'].forEach((mode) => {
    const out = model.sample(model.normalize({ mode, direction: 'out' }), 257).values;
    const inward = model.sample(model.normalize({ mode, direction: 'in' }), 257).values;
    for (let i = 0; i < 257; i += 1) close(inward[i], 1 - out[256 - i]);
  });
});

test('inout is symmetric for continuous models', () => {
  ['elastic', 'bounce'].forEach((mode) => {
    const values = model.sample(model.normalize({ mode, direction: 'inout' }), 257).values;
    for (let i = 0; i < 257; i += 1) close(values[i], 1 - values[256 - i]);
  });
});

test('native AE ease maps smooth handles to speed and influence', () => {
  const ease = model.nativeEase(model.presetState('smooth'), 100, 2);
  close(ease.out.speed, 0);
  close(ease.in.speed, 0);
  close(ease.out.influence, 42);
  close(ease.in.influence, 42);
});

test('native AE ease preserves signed scalar deltas', () => {
  const ease = model.nativeEase(model.presetState('fast'), -50, 2);
  close(ease.out.speed, -50);
  close(ease.in.speed, -0);
  close(ease.out.influence, 100 / 3);
});

test('AE handle normalization keeps native influence in range', () => {
  const state = model.normalize({ x1: -4, x2: 7, y1: 2.5, y2: -1.5 });
  close(state.x1, 0);
  close(state.x2, 1);
  close(state.y1, 2.5);
  close(state.y2, -1.5);
  const ease = model.nativeEase(state, 100, 1);
  assert.ok(ease.out.influence >= 0.1 && ease.out.influence <= 100);
  assert.ok(ease.in.influence >= 0.1 && ease.in.influence <= 100);
});

test('serialization returns a fresh normalized state', () => {
  const source = model.presetState('smooth');
  const output = model.serializable(source);
  output.x1 = 0.9;
  close(source.x1, 0.42);
  close(model.serializable(source).x1, 0.42);
});

test('non-Bezier models cannot masquerade as native AE ease', () => {
  assert.throws(() => model.nativeEase(model.presetState('elastic_out'), 100, 1), /Bezier/);
});

test('sample count is stable and speeds are derivative-consistent', () => {
  const state = model.presetState('sine_inout');
  const samples = model.sample(state, 1001);
  assert.strictEqual(samples.values.length, 1001);
  assert.strictEqual(samples.speeds.length, 1001);
  for (let i = 1; i < 1000; i += 1) {
    const numerical = (samples.values[i + 1] - samples.values[i - 1]) / 0.002;
    close(samples.speeds[i], numerical, 2e-5);
  }
});

process.stdout.write(`1..${passed}\n`);
