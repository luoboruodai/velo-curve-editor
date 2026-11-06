#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}
function close(actual, expected, tolerance = 1e-8) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);
}
function ease(speed, influence) { return { speed, influence }; }
let hostContext = null;
function clone(value) {
  const text = JSON.stringify(value);
  return hostContext ? vm.runInContext(`(${text})`, hostContext) : JSON.parse(text);
}
class KeyframeEase {
  constructor(speed, influence) { this.speed = speed; this.influence = influence; }
}
const KeyframeInterpolationType = { LINEAR: 1, BEZIER: 2, HOLD: 3 };
class Property {
  constructor(name, times, values, easeDimensions = 0) {
    this.name = name;
    this.times = times.slice();
    this.values = clone(values);
    this.isSpatial = name === 'Position';
    this.easeDimensions = easeDimensions || this.dimensions;
    this.selectedKeys = times.map((_, index) => index + 1);
    this.inEase = times.map(() => this.easeSide());
    this.outEase = times.map(() => this.easeSide());
    this.inType = times.map(() => KeyframeInterpolationType.BEZIER);
    this.outType = times.map(() => KeyframeInterpolationType.BEZIER);
  }
  get numKeys() { return this.times.length; }
  get dimensions() { return typeof this.values[0] === 'number' ? 1 : this.values[0].length; }
  easeSide() { return Array.from({ length: this.easeDimensions }, () => ease(0, 100 / 3)); }
  index(index) { return index - 1; }
  keyTime(index) { return this.times[this.index(index)]; }
  keyValue(index) { return clone(this.values[this.index(index)]); }
  nearestKeyIndex(time) {
    let best = 0;
    for (let i = 1; i < this.times.length; i += 1) if (Math.abs(this.times[i] - time) < Math.abs(this.times[best] - time)) best = i;
    return best + 1;
  }
  setEase(index, incoming, outgoing) {
    if (incoming) this.inEase[this.index(index)] = clone(incoming);
    if (outgoing) this.outEase[this.index(index)] = clone(outgoing);
  }
  keyInTemporalEase(index) { return this.inEase[this.index(index)].map(item => new KeyframeEase(item.speed, item.influence)); }
  keyOutTemporalEase(index) { return this.outEase[this.index(index)].map(item => new KeyframeEase(item.speed, item.influence)); }
  setTemporalEaseAtKey(index, incoming, outgoing) { this.setEase(index, incoming, outgoing); }
  keyInInterpolationType(index) { return this.inType[this.index(index)]; }
  keyOutInterpolationType(index) { return this.outType[this.index(index)]; }
  setInterpolationTypeAtKey(index, incoming, outgoing) {
    this.inType[this.index(index)] = incoming;
    this.outType[this.index(index)] = outgoing;
  }
  setSelectedAtKey(index, selected) {
    const set = new Set(this.selectedKeys);
    if (selected) set.add(index); else set.delete(index);
    this.selectedKeys = [...set].sort((a, b) => a - b);
  }
  setValueAtTime(time, value) {
    let index = this.nearestKeyIndex(time);
    if (Math.abs(this.keyTime(index) - time) <= 0.0001) this.values[this.index(index)] = clone(value);
    else {
      const at = this.times.findIndex(item => item > time);
      const insertAt = at < 0 ? this.times.length : at;
      this.times.splice(insertAt, 0, time);
      this.values.splice(insertAt, 0, clone(value));
      this.inEase.splice(insertAt, 0, this.easeSide());
      this.outEase.splice(insertAt, 0, this.easeSide());
      this.inType.splice(insertAt, 0, KeyframeInterpolationType.BEZIER);
      this.outType.splice(insertAt, 0, KeyframeInterpolationType.BEZIER);
      index = insertAt + 1;
    }
    this.selectedKeys = this.times.map((_, i) => i + 1);
    return index;
  }
  removeKey(index) {
    const at = this.index(index);
    for (const key of ['times', 'values', 'inEase', 'outEase', 'inType', 'outType']) this[key].splice(at, 1);
    this.selectedKeys = this.times.map((_, i) => i + 1);
  }
}
class CompItem {
  constructor(properties) { this.selectedProperties = properties; this.frameDuration = 1 / 24; this.name = 'Synthetic native curve test'; }
}
function hostWith(properties) {
  const comp = new CompItem(properties);
  const app = { project: { activeItem: comp }, undoGroups: 0, endGroups: 0,
    beginUndoGroup() { this.undoGroups += 1; }, endUndoGroup() { this.endGroups += 1; } };
  const source = fs.readFileSync(path.join(__dirname, '../VeloAE/jsx/hostscript.jsx'), 'utf8');
  const context = vm.createContext({ app, Property, CompItem, KeyframeEase, KeyframeInterpolationType });
  hostContext = context;
  for (const property of properties) property.values = clone(property.values);
  const host = vm.runInNewContext(`${source}\nVeloAE;`, context);
  host.evaluate = script => vm.runInContext(script, context);
  return { host, app, comp };
}
function call(host, method, payload) {
  const script = payload === undefined ? `VeloAE.${method}()` : `VeloAE.${method}(${JSON.stringify(payload)})`;
  const result = JSON.parse(host.evaluate(script));
  check(JSON.stringify(result).indexOf('Infinity') === -1 && JSON.stringify(result).indexOf('NaN') === -1, `${method} returns finite JSON`);
  return result;
}
function apply(host, segments, samples, hiddenAnchors = []) {
  return call(host, 'apply', { mode: 'bezier', segments, hiddenAnchors, samples: samples || Array.from({ length: 257 }, (_, i) => i / 256) });
}
const twoSegments = [
  [[0, 0], [0.2, -0.2], [0.3, 0.4], [0.5, 0.3]],
  [[0.5, 0.3], [0.65, 0.1], [0.8, 1.2], [1, 1]]
];

{
  const property = new Property('Opacity', [0, 1, 3], [10, 30, 50]);
  property.setEase(1, null, [ease(2, 25)]);
  property.setEase(2, [ease(4, 20)], [ease(-3, 30)]);
  property.setEase(3, [ease(6, 40)], null);
  const { host, app } = hostWith([property]);
  const inspection = call(host, 'inspect');
  check(inspection.propertyCount === 1 && inspection.segmentCount === 2 && !inspection.curve, 'Inspect reports the selection without importing or replacing the editor curve');
  const result = call(host, 'readCurve');
  check(result.ok && result.curve.segments.length === 2 && result.curve.dimensions === 1, 'Read imports two adjacent native scalar segments');
  check(JSON.stringify(result.curve.keyTimes) === '[0,1,3]' && JSON.stringify(result.curve.values) === '[10,30,50]', 'Read returns the actual selected key times and values');
  close(result.curve.segments[0][1][0], 0.25 / 3);
  close(result.curve.segments[0][1][1], 0.0125);
  close(result.curve.segments[0][2][0], 0.8 / 3);
  close(result.curve.segments[0][2][1], 0.48);
  close(result.curve.segments[1][1][1], 0.455);
  close(result.curve.segments[1][2][1], 0.88);
  check(result.deferredCount === 0 && app.undoGroups === 0, 'Reading a curve never opens an UndoGroup');
  const target = new Property('Opacity', [0, 2], [10, 50]);
  const targetHost = hostWith([target]).host;
  const written = apply(targetHost, result.curve.segments);
  check(written.ok, `Apply accepts imported native segments: ${JSON.stringify(written)}`);
  check(target.times.length === 3 && Math.abs(target.times[1] - 2 / 3) < 1e-8, `Two native model segments create exactly one interior key at the normalized time of the new selection: ${JSON.stringify(target.times)}`);
  close(target.values[1], 30);
  const roundTrip = call(targetHost, 'readCurve');
  close(roundTrip.curve.segments[0][1][1], result.curve.segments[0][1][1]);
  close(roundTrip.curve.segments[1][1][1], result.curve.segments[1][1][1]);
  close(roundTrip.curve.segments[1][2][1], result.curve.segments[1][2][1]);
}
{
  const property = new Property('Position', [0, 2], [[0, 10, 100], [100, 110, 200]], 3);
  const { host, app } = hostWith([property]);
  const result = apply(host, twoSegments);
  check(result.ok && result.nativeSegments === 2 && result.bakedSegments === 0, `Multi-anchor Apply uses native segments for equal-length arrays: ${JSON.stringify(result)}`);
  check(property.times.length === 3 && property.times[1] === 1, 'Position receives one native interior key rather than hundreds of samples');
  property.values[1].forEach((value, dimension) => close(value, [30, 40, 130][dimension]));
  check(property.outEase[0].length === 3 && property.inEase[1].length === 3 && property.outEase[1].length === 3, 'Every native ease side retains the property dimension');
  close(property.outEase[0][0].speed, -50);
  close(property.outEase[0][1].speed, -50);
  close(property.outEase[0][2].speed, -50);
  const roundTrip = call(host, 'readCurve');
  check(roundTrip.ok && roundTrip.curve.segments.length === 2 && roundTrip.curve.dimensions === 3, 'Native Position curves can be read back after writing');
  close(roundTrip.curve.segments[0][1][1], -0.2);
  close(roundTrip.curve.segments[1][1][1], 0.1);
  check(app.undoGroups === 1 && app.endGroups === 1, 'The whole multi-anchor property uses exactly one UndoGroup');
}
{
  const property = new Property('Position', [0, 1], [[20, 30], [20, 30]]);
  property.setEase(1, null, [ease(0, 25), ease(0, 25)]);
  property.setEase(2, [ease(0, 50), ease(0, 50)], null);
  const { host } = hostWith([property]);
  const result = call(host, 'readCurve');
  check(result.ok && result.curve.segments[0][1][1] === 0 && result.curve.segments[0][2][1] === 1, 'Flat values fall back to finite flat handles rather than Infinity');
}
{
  const property = new Property('Position', [0, 1], [[0, 0], [100, 200]]);
  property.setEase(1, null, [ease(2, 25), ease(6, 25)]);
  property.setEase(2, [ease(2, 25), ease(6, 25)], null);
  const { host } = hostWith([property]);
  const result = call(host, 'readCurve');
  check(!result.ok && /维度/.test(result.error), `Inconsistent dimensional curves are rejected rather than silently collapsed into one curve: ${JSON.stringify(result)}`);
}
{
  const first = new Property('Opacity', [0, 1, 2, 3], [0, 20, 40, 100]);
  const second = new Property('Position', [0, 3], [[0, 0], [100, 200]]);
  const { host, app } = hostWith([first, second]);
  const result = apply(host, twoSegments);
  check(result.ok && first.times.length === 3 && second.times.length === 3, 'Multiple properties preserve the same visible anchor count in one Apply');
  check(app.undoGroups === 1 && app.endGroups === 1, 'Multiple properties are covered by one undo operation');
  const reduced = new Property('Opacity', [0, 1, 2, 3], [0, 20, 40, 100]);
  const reducedHost = hostWith([reduced]).host;
  const single = apply(reducedHost, [[[0, 0], [0.3, 0.3], [0.7, 0.7], [1, 1]]], undefined, []);
  check(single.ok && reduced.times.length === 2 && reduced.times[1] === 3, 'Replacing a selected span removes redundant selected interior keys');
  check(single.removedKeys === 2 && single.createdKeys === 0, 'Apply reports removed redundant keys separately from newly created keys');
}
{
  const property = new Property('Opacity', [0, 1], [0, 100]);
  const { host } = hostWith([property]);
  const segments = [
    [[0, 0], [0.1, 0], [0.15, 0.4], [0.25, 0.5]],
    [[0.25, 0.5], [0.35, 0.6], [0.4, 0.3], [0.5, 0.3]],
    [[0.5, 0.3], [0.65, 0.1], [0.8, 1.2], [1, 1]]
  ];
  const result = apply(host, segments, undefined, [0.25]);
  check(result.ok && result.nativeSegments === 1 && result.shapePreservedSegments === 1, 'Only a span containing shape-preserving hidden anchors uses the explicit sampling fallback');
  check(!property.times.some(time => Math.abs(time - 0.25) < 0.0001), 'The hidden shape anchor is not recreated as a visible AE keyframe');
  check(property.times.some(time => Math.abs(time - 0.5) < 0.0001) && property.times[property.times.length - 1] === 1, 'Visible boundaries remain native keys in the mixed fallback');
  check(result.createdKeys < 257, 'Local shape-preserving sampling does not bake the entire curve into hundreds of keys');
}
{
  const property = new Property('Opacity', [0, 1, 3], [0, 50, 100]);
  property.selectedKeys = [1, 3];
  const { host, app } = hostWith([property]);
  const result = apply(host, twoSegments);
  check(!result.ok && app.undoGroups === 0 && property.times.length === 3, 'Non-contiguous selected keys are rejected before any mutation');
  const invalid = apply(host, [[[0, 0], [0.9, 0], [0.2, 1], [1, 1]]]);
  check(!invalid.ok && app.undoGroups === 0, 'Invalid native handles cannot open an UndoGroup');
}
{
  const property = new Property('Opacity', [0, 1], [0, 100]);
  property.outType[0] = KeyframeInterpolationType.LINEAR;
  property.inType[1] = KeyframeInterpolationType.LINEAR;
  const { host } = hostWith([property]);
  const result = call(host, 'readCurve');
  check(result.ok && result.curve.segments[0][1][0] === 1 / 3 && result.curve.segments[0][2][0] === 2 / 3, 'Linear AE segments import as linear geometry instead of unused temporal ease values');
  property.outType[0] = KeyframeInterpolationType.HOLD;
  const held = call(host, 'readCurve');
  check(!held.ok, 'Hold interpolation is reported instead of being misrepresented as a Bezier curve');
}
{
  const property = new Property('Position', [0, 2], [[0, 10, 0], [100, 110, 0]], 1);
  const { host } = hostWith([property]);
  const positive = [
    [[0, 0], [0.1, 0.1], [0.3, 0.4], [0.5, 0.5]],
    [[0.5, 0.5], [0.6, 0.6], [0.8, 0.8], [1, 1]]
  ];
  const result = apply(host, positive);
  check(result.ok && property.outEase[0].length === 1 && property.inEase[1].length === 1, 'Linked Position keeps one shared ease object rather than forcing one per value component');
  check(result.nativeSegments === 2 && result.bakedSegments === 0, 'Positive linked-spatial segments remain native');
  close(property.values[1][0], 50);
  close(property.values[1][1], 60);
  close(property.values[1][2], 0);
  close(property.outEase[0][0].speed, 50);
  const read = call(host, 'readCurve');
  check(read.ok && read.curve.dimensions === 3 && read.curve.segments.length === 2, 'Shared ease objects are readable across all linked value dimensions');
  close(read.curve.segments[0][1][1], 0.1);
  close(read.curve.segments[1][2][1], 0.8);
  const negativeProperty = new Property('Position', [0, 2], [[0, 10, 0], [100, 110, 0]], 1);
  const negativeHost = hostWith([negativeProperty]).host;
  const negative = apply(negativeHost, twoSegments);
  check(negative.ok && negative.bakedSegments === 2 && negative.methods[0].spatialSegments === 2, 'Shared spatial negative speeds use a disclosed local sampling fallback');
  check(negativeProperty.times.length > 3 && negativeProperty.times.length < 257, 'Spatial fallback is bounded and keeps explicit visible anchors instead of baking the full curve');
}
const hostSource = fs.readFileSync(path.join(__dirname, '../VeloAE/jsx/hostscript.jsx'), 'utf8');
check(!/[{,]\s*native\s*:/.test(hostSource), 'ExtendScript reserved native is never used as an unquoted object key');
console.log(`1..${checks}`);
