#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const model = require('../VeloAE/js/curve-model.js');
let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}
function close(actual, expected, tolerance = 1e-9) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);
}
function maximumDifference(a, b) {
  return Math.max(...a.map((value, index) => Math.abs(value - b[index])));
}

const original = model.presetState('sine_inout');
const originalSamples = model.sample(original, 1001);
const split = model.splitAt(original, 0.5);
check(split.segments.length === 2 && model.validSegments(split.segments), 'double-click splitting produces two valid cubic segments');
const splitSamples = model.sample(split, 1001);
check(maximumDifference(originalSamples.values, splitSamples.values) < 1e-10, 'splitting preserves the sampled value curve');
check(maximumDifference(originalSamples.speeds, splitSamples.speeds) < 1e-7, 'splitting preserves the derivative including the new anchor');
check(model.bezierBreakpoints(split).length === 0, 'a newly split smooth anchor does not create a false speed discontinuity');
check(splitSamples.values.every(Number.isFinite), 'multi-segment samples remain finite');
close(splitSamples.values[0], 0);
close(splitSamples.values[1000], 1);

const triple = model.splitAt(split, 0.25);
const tripleSamples = model.sample(triple, 1001);
check(triple.segments.length === 3 && model.validSegments(triple.segments), 'a second insertion creates three independently addressable segments');
check(maximumDifference(originalSamples.values, tripleSamples.values) < 1e-10, 'repeated splitting still preserves the original curve');
const times = model.sampleTimes(triple, 257);
check(times.includes(0.25) && times.includes(0.5), 'host sample times include exact interior anchor positions');
check(times.length === 257 && times.every((time, index) => index === 0 || time > times[index - 1]), 'anchors already on the uniform grid are not duplicated');
close(model.valueAndSpeed(triple, 0.25)[0], originalSamples.values[250]);
close(model.valueAndSpeed(triple, 0.5)[0], originalSamples.values[500]);

const serialized = model.serializable(triple);
check(model.validSegments(serialized.segments), 'serialization preserves multi-segment data');
serialized.segments[0][1][0] = 0.99;
check(triple.segments[0][1][0] !== 0.99, 'serialized points do not share mutable references with the editor state');
const reversed = model.reverse(triple);
const reversedSamples = model.sample(reversed, 1001);
check(model.validSegments(reversed.segments), 'reversal retains valid multi-segment geometry');
check(maximumDifference(reversedSamples.values, originalSamples.values.slice().reverse().map(value => 1 - value)) < 1e-10, 'multi-segment reversal mirrors the sampled curve');

const removed = model.removeAnchor(triple, 1);
check(removed.segments.length === 2 && model.validSegments(removed.segments), 'removing an interior anchor reconnects its neighbors');
const single = model.removeAnchor(removed, 1);
check(!single.segments && model.validSegments(model.splitAt(single, 0.5).segments), 'removing the final interior anchor returns to the legacy single-cubic representation');
check(typeof model.nativeEase(single, 100, 1).out.speed === 'number', 'returning to one segment restores native AE ease compatibility');
assert.throws(() => model.nativeEase(triple, 100, 1), /single Bezier/);
checks += 1;
console.log(`ok ${checks} - multi-segment state cannot masquerade as native single-segment ease`);

const discontinuous = model.serializable(triple);
discontinuous.segments[1][2][1] += 0.4;
check(model.bezierBreakpoints(discontinuous).includes(0.5), 'an explicitly broken tangent creates a real speed breakpoint');

let limited = model.presetState('smooth');
for (let index = 0; index < 24; index += 1) limited = model.splitAt(limited, (index + 1) / 25);
check(limited.segments.length <= model.MAX_SEGMENTS, 'point insertion remains bounded by the segment limit');
check(!model.validSegments([]), 'empty segment arrays are rejected');
check(!model.validSegments([[[0, 0], [0.2, 0], [0.8, 1], [1, 1]], [[0.5, 0.5], [0.6, 0.6], [0.8, 0.8], [1, 1]]]), 'disconnected segment anchors are rejected');
const invalidNumber = model.serializable(split);
invalidNumber.segments[0][1][0] = NaN;
check(!model.validSegments(invalidNumber.segments), 'non-finite point coordinates are rejected');
const elastic = model.splitAt(model.presetState('elastic_out'), 0.5);
check(!elastic.segments && elastic.mode === 'elastic', 'non-Bezier models are unchanged by point insertion');

const finiteDifferenceState = model.splitAt(model.presetState('cubic_inout'), 0.5);
let maximumDerivativeError = 0;
for (const u of [0.1, 0.3, 0.49, 0.51, 0.7, 0.9]) {
  const step = 1e-6;
  const numerical = (model.valueAndSpeed(finiteDifferenceState, u + step)[0] - model.valueAndSpeed(finiteDifferenceState, u - step)[0]) / (2 * step);
  maximumDerivativeError = Math.max(maximumDerivativeError, Math.abs(numerical - model.valueAndSpeed(finiteDifferenceState, u)[1]));
}
check(maximumDerivativeError < 2e-5, 'analytic multi-segment speeds agree with finite differences away from anchors');
console.log(`1..${checks}`);
