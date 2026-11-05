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
function maximumDifference(a, b) {
  return Math.max(...a.map((value, index) => Math.abs(value - b[index])));
}
function anchor(state, index) {
  return state.segments[index - 1][3];
}

const base = model.splitAt(model.presetState('sine_inout'), 0.6);
const triple = model.splitAt(base, 0.3);
const broken = model.serializable(triple);
broken.segments[0][2] = [0.24, 0.12];
const before = model.sample(broken, 1001);
const preserved = model.removeAnchor(broken, 1, true);
const after = model.sample(preserved, 1001);
check(model.visibleAnchorCount(broken) === 4 && model.visibleAnchorCount(preserved) === 3, 'shape-preserving deletion removes one visible keyframe');
check(preserved.segments.length === broken.segments.length && model.isShapeAnchor(preserved, 1), 'shape-preserving deletion retains the cubic geometry as an internal shape knot');
check(maximumDifference(before.values, after.values) === 0, 'shape-preserving deletion has exactly zero sampled value difference');
check(maximumDifference(before.speeds, after.speeds) === 0, 'shape-preserving deletion has exactly zero sampled speed difference');
check(!model.sampleTimes(preserved, 257).includes(0.3) && model.sampleTimes(preserved, 257).includes(0.6), 'Apply sample times omit the deleted keyframe but retain other explicit anchors');
const preservedRoundtrip = model.serializable(preserved);
check(preservedRoundtrip.hiddenAnchors.length === 1 && Math.abs(preservedRoundtrip.hiddenAnchors[0] - 0.3) < 1e-12, 'shape knots survive JSON serialization');
check(model.isShapeAnchor(model.reverse(preserved), 2), 'reversal mirrors shape-knot identity');
const ordinary = model.removeAnchor(broken, 1, false);
check(ordinary.segments.length === 2 && !ordinary.hiddenAnchors, 'ordinary deletion still reconnects and reduces cubic segments');
check(maximumDifference(before.values, model.sample(ordinary, 1001).values) > 1e-4, 'ordinary deletion is allowed to change the curve shape');

const smoothed = model.smoothAnchor(broken, 1);
check(!model.bezierBreakpoints(smoothed).includes(0.3), 'single-anchor smoothing removes the speed discontinuity');
check(anchor(smoothed, 1).every((value, index) => value === anchor(broken, 1)[index]), 'single-anchor smoothing does not move the keyframe');
check(model.validSegments(smoothed.segments), 'single-anchor smoothing produces valid cubic segments');

const snappedInput = model.serializable(broken);
const snap = model.snapHandleToTangent(snappedInput, 1, 1, snappedInput.segments[1][1][0], snappedInput.segments[1][1][1] + 0.001, 800, 800);
check(snap.snapped, 'a handle within eight screen pixels of tangent continuity snaps');
snappedInput.segments[1][1] = snap.point;
check(!model.bezierBreakpoints(snappedInput).includes(0.3), 'the snapped handle produces a continuous tangent');
const farSnap = model.snapHandleToTangent(broken, 1, 1, 0.9, 4, 800, 800);
check(!farSnap.snapped, 'a handle far from the tangent ray remains free');

const redundant = model.smoothAllAnchors(triple);
check(redundant.removed > 0 && model.visibleAnchorCount(redundant.state) < model.visibleAnchorCount(triple), 'global smoothing simplifies redundant visible keyframes');
check(model.validSegments(redundant.state.segments), 'global smoothing preserves valid geometry');
check(model.sample(redundant.state, 1001).values.every(Number.isFinite), 'global smoothing keeps every sample finite');

const negative = model.normalize({ mode: 'bezier', segments: [
  [[0, 0], [0.05, 0.3], [0.12, 0.7], [0.2, 0.8]],
  [[0.2, 0.8], [0.28, 0.9], [0.32, 0.7], [0.4, 0.6]],
  [[0.4, 0.6], [0.48, 0.5], [0.52, 0.5], [0.6, 0.4]],
  [[0.6, 0.4], [0.68, 0.3], [0.72, 0.6], [0.8, 0.7]],
  [[0.8, 0.7], [0.86, 0.8], [0.94, 0.9], [1, 1]]
] });
const adapted = model.smoothAllAnchors(negative).state;
check(model.valueAndSpeed(adapted, 0.4)[1] < 0, 'global smoothing preserves a continuously negative-speed region');
check(Math.abs(model.valueAndSpeed(adapted, 0.6)[1]) < 1e-9, 'global smoothing uses zero speed at an intentional extremum');
check(anchor(adapted, 2).every((value, index) => value === anchor(negative, 2)[index]), 'adaptive smoothing preserves negative-region keyframe values');
check(anchor(adapted, 3).every((value, index) => value === anchor(negative, 3)[index]), 'adaptive smoothing preserves extremum keyframe values');

const plateau = model.normalize({ mode: 'bezier', segments: [
  [[0, 0], [0.1, 0.2], [0.2, 0.4], [0.3, 0.5]],
  [[0.3, 0.5], [0.4, 0.5], [0.5, 0.5], [0.6, 0.5]],
  [[0.6, 0.5], [0.7, 0.6], [0.9, 0.9], [1, 1]]
] });
const plateauResult = model.smoothAllAnchors(plateau);
check(plateauResult.stops >= 2, 'global smoothing explicitly detects plateau boundaries');
check(Math.abs(model.valueAndSpeed(plateauResult.state, 0.3)[1]) < 1e-9 && Math.abs(model.valueAndSpeed(plateauResult.state, 0.6)[1]) < 1e-9, 'plateau boundaries retain intentional zero speed');
check(model.bezierBreakpoints(plateauResult.state).length === 0, 'adaptive smoothing joins all interior tangents continuously');

console.log(`1..${checks}`);
