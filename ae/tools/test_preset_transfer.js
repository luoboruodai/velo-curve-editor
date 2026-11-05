#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const model = require('../VeloAE/js/curve-model.js');

const source = fs.readFileSync(path.join(__dirname, '../VeloAE/js/main.js'), 'utf8');
function declaration(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, `${name} exists`);
  const end = source.indexOf('\n  function ', start + 2);
  assert.ok(end > start, `${name} has a complete declaration`);
  return source.slice(start, end);
}
function translatedError(key, params) {
  const error = new Error(key);
  error.translation = { key, params: params || {} };
  return error;
}
const transfer = new Function('model', 'translatedError', `
  ${declaration('orderedPresetIds')}
  ${declaration('presetExportData')}
  ${declaration('allocateImportedId')}
  ${declaration('parsePresetImport')}
  return { orderedPresetIds, presetExportData, parsePresetImport };
`)(model, translatedError);

let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}
function ids(used, index) {
  return `preset_user_${index}`;
}
function user(id, label = id) {
  return { id, label, state: model.serializable({ x1: 0.2, y1: 0.3, x2: 0.7, y2: 0.9 }) };
}
function rejects(data, existing, key = 'error.invalidPresetFile') {
  const before = JSON.stringify(existing);
  assert.throws(() => transfer.parsePresetImport(data, existing, ids), error => error.translation && error.translation.key === key);
  check(JSON.stringify(existing) === before, `rejected input leaves existing presets untouched: ${key}`);
}

const originalUser = user('preset_user_original', '原始 Name 프리셋');
const exported = transfer.presetExportData([originalUser], ['slow', 'slow'], ['quad_out', 'slow', 'quad_out', 'preset_user_original']);
check(exported.format === 'velo-presets' && exported.version === 2, 'export uses the complete version 2 envelope');
check(exported.presets.length === 23, 'export contains all 22 built-ins and one user preset');
check(Object.keys(model.PRESETS).every(id => exported.presets.some(entry => entry.id === id)), 'every built-in stable ID is present');
check(exported.presets.filter(entry => entry.id === 'slow').length === 1, 'built-ins are not duplicated as user presets');
check(exported.presets.find(entry => entry.id === 'linear').label === model.PRESETS.linear.label, 'built-in labels retain their original model text');
check(exported.presets.at(-1).label === originalUser.label && exported.presets.at(-1).state === originalUser.state, 'user names and state objects are exported verbatim');
check(exported.presets.filter(entry => model.PRESETS[entry.id]).every(entry => JSON.stringify(entry.state) === JSON.stringify(model.serializable(model.presetState(entry.id)))), 'built-in states come from canonical preset definitions');
check(JSON.stringify(exported.hiddenPresets) === JSON.stringify(['slow']), 'hidden built-ins are retained and deduplicated');
check(exported.presetOrder[0] === 'quad_out' && exported.presetOrder[1] === 'slow', 'custom order leads the exported order');
check(exported.presetOrder.filter(id => id === 'quad_out').length === 1, 'export order is deduplicated');
check(exported.presetOrder.length === 23 && exported.presetOrder.includes('elastic_out') && exported.presetOrder.includes('bounce_inout'), 'export order includes omitted built-ins and all current IDs');
check(exported.presetOrder.indexOf('preset_user_original') < exported.presetOrder.indexOf('linear'), 'a user preset keeps its explicit position instead of being forced last');

const roundTrip = transfer.parsePresetImport(JSON.parse(JSON.stringify(exported)), [], ids);
check(roundTrip.configuration === true && roundTrip.importedCount === 1, 'version 2 import restores configuration and counts only new user presets');
check(roundTrip.userPresets.length === 1 && roundTrip.userPresets[0].id === originalUser.id, 'round trip preserves a nonconflicting user ID');
check(roundTrip.userPresets[0].label === originalUser.label, 'round trip preserves Unicode user labels');
check(JSON.stringify(roundTrip.hiddenPresets) === JSON.stringify(exported.hiddenPresets), 'round trip restores hidden built-ins');
check(JSON.stringify(roundTrip.presetOrder) === JSON.stringify(exported.presetOrder), 'round trip restores the full order without omissions');

const existing = [user('preset_user_original', 'Keep existing'), user('preset_user_keep', 'Keep second')];
const existingBefore = JSON.stringify(existing);
const conflict = transfer.parsePresetImport(JSON.parse(JSON.stringify(exported)), existing, ids);
check(conflict.userPresets.length === 3 && conflict.userPresets[0].label === 'Keep existing' && conflict.userPresets[1].label === 'Keep second', 'an importing backup never overwrites existing user presets');
check(conflict.userPresets[2].id === 'preset_user_22' && conflict.userPresets[2].label === originalUser.label, 'a conflicting user ID is deterministically remapped');
check(conflict.presetOrder.includes('preset_user_original') && conflict.presetOrder.includes('preset_user_22'), 'order retains both the existing and remapped IDs');
check(JSON.stringify(existing) === existingBefore, 'the import parser does not mutate existing user data');

const legacyState = model.serializable({ mode: 'elastic', direction: 'inout', frequency: 3 });
const legacy = transfer.parsePresetImport([
  { name: 'TD 原始', curve: legacyState },
  { label: 'AE original', state: legacyState }
], existing, ids);
check(legacy.configuration === false && legacy.importedCount === 2, 'legacy arrays continue to import without replacing configuration');
check(legacy.userPresets.length === 4 && legacy.userPresets[2].id === 'preset_user_0' && legacy.userPresets[3].id === 'preset_user_1', 'legacy imports receive fresh IDs');
check(legacy.userPresets[2].label === 'TD 原始' && legacy.userPresets[3].label === 'AE original', 'legacy name/curve and label/state forms are both accepted');
check(legacy.hiddenPresets === undefined && legacy.presetOrder === undefined, 'legacy import does not replace hidden state or order');
const legacyObject = transfer.parsePresetImport({ format: 'velo-presets', version: 1, presets: [{ label: 'v1', state: legacyState }] }, [], ids);
check(legacyObject.configuration === false && legacyObject.userPresets.length === 1, 'the version 1 object envelope remains compatible');

rejects(null, existing);
rejects({ format: 'velo-presets', version: 3, presets: [] }, existing);
rejects({ format: 'velo-presets', version: 2, presets: exported.presets }, existing);
const missingBuiltin = JSON.parse(JSON.stringify(exported));
missingBuiltin.presets = missingBuiltin.presets.filter(entry => entry.id !== 'linear');
rejects(missingBuiltin, existing);
const duplicateBuiltin = JSON.parse(JSON.stringify(exported));
duplicateBuiltin.presets.push(duplicateBuiltin.presets[0]);
rejects(duplicateBuiltin, existing);
const invalidHidden = JSON.parse(JSON.stringify(exported));
invalidHidden.hiddenPresets = ['preset_user_original'];
rejects(invalidHidden, existing);
const invalidOrder = JSON.parse(JSON.stringify(exported));
invalidOrder.presetOrder = ['missing_id'];
rejects(invalidOrder, existing);
const invalidId = JSON.parse(JSON.stringify(exported));
invalidId.presets.at(-1).id = '__proto__';
invalidId.presetOrder = invalidId.presetOrder.map(id => id === 'preset_user_original' ? '__proto__' : id);
rejects(invalidId, existing);
const invalidState = JSON.parse(JSON.stringify(exported));
invalidState.presets.at(-1).state.x1 = 'not-a-number';
rejects(invalidState, existing);
const missingState = JSON.parse(JSON.stringify(exported));
delete missingState.presets.at(-1).state;
rejects(missingState, existing, 'error.presetMissing');
rejects([{ label: 'Over capacity', state: legacyState }], Array.from({ length: 32 }, (_, index) => user(`preset_user_${index}`)));

const incompleteOrder = JSON.parse(JSON.stringify(exported));
incompleteOrder.presetOrder = ['quad_out', 'preset_user_original', 'quad_out'];
const completed = transfer.parsePresetImport(incompleteOrder, [], ids);
check(completed.presetOrder.length === 23 && completed.presetOrder[0] === 'quad_out' && completed.presetOrder[1] === 'preset_user_original', 'import deduplicates order and appends omitted current IDs');
const duplicateHidden = JSON.parse(JSON.stringify(exported));
duplicateHidden.hiddenPresets = ['slow', 'slow', 'linear'];
const hiddenResult = transfer.parsePresetImport(duplicateHidden, [], ids);
check(JSON.stringify(hiddenResult.hiddenPresets) === JSON.stringify(['slow', 'linear']), 'valid duplicate hidden IDs are deduplicated');

const multiState = model.splitAt(model.presetState('sine_inout'), 0.5);
const multiUser = { id: 'preset_user_multi', label: 'Multi 原文', state: multiState };
const multiExport = transfer.presetExportData([multiUser], [], []);
const multiResult = transfer.parsePresetImport(JSON.parse(JSON.stringify(multiExport)), [], ids);
check(multiResult.userPresets[0].state.segments.length === 2 && model.validSegments(multiResult.userPresets[0].state.segments), 'multi-segment user presets survive the complete configuration round trip');
const invalidSegments = JSON.parse(JSON.stringify(multiExport));
invalidSegments.presets.at(-1).state.segments = [];
rejects(invalidSegments, existing);

console.log(`1..${checks}`);
