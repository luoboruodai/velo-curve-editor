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
const { colorRgbToHex, colorHexToRgb, colorRgbToHsv, colorHsvToRgb } = new Function('model', `${declaration('colorRgbToHex')}\n${declaration('colorHexToRgb')}\n${declaration('colorRgbToHsv')}\n${declaration('colorHsvToRgb')}\nreturn { colorRgbToHex, colorHexToRgb, colorRgbToHsv, colorHsvToRgb };`)(model);
let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}
function sameRgb(a, b) {
  return a.every((value, index) => value === b[index]);
}

check(sameRgb(colorHexToRgb('#4a90e2'), [74, 144, 226]), 'six-digit hex parses the current theme');
check(sameRgb(colorHexToRgb('abc'), [170, 187, 204]), 'three-digit shorthand works without a hash');
check(colorHexToRgb('#12xz00') === null && colorHexToRgb('#12345') === null, 'invalid color text is rejected');
check(colorRgbToHex([74, 144, 226]) === '#4a90e2', 'RGB serializes to the current theme hex');
for (const rgb of [[0, 0, 0], [255, 255, 255], [74, 144, 226], [242, 179, 93], [99, 33, 177]]) {
  check(sameRgb(colorHsvToRgb(colorRgbToHsv(rgb)), rgb), `HSV roundtrip preserves ${rgb.join(',')}`);
}
check(colorRgbToHsv([255, 0, 0]).h === 0, 'red has zero hue');
check(Math.abs(colorRgbToHsv([0, 255, 0]).h - 1 / 3) < 1e-12, 'green has one-third hue');
check(Math.abs(colorRgbToHsv([0, 0, 255]).h - 2 / 3) < 1e-12, 'blue has two-thirds hue');
check(sameRgb(colorHsvToRgb({ h: 1, s: 1, v: 1 }), colorHsvToRgb({ h: 0, s: 1, v: 1 })), 'hue wraps cleanly at the top of the slider');
check(source.includes('openColorPicker(input.id)'), 'all three theme inputs open the custom picker');
check(source.includes('event.preventDefault();\n      openColorPicker(input.id);'), 'native color activation is prevented before opening the custom picker');
check(source.includes('function closeColorPicker(apply)') && source.includes('settings[target] = original'), 'cancel restores the original color');
check(source.includes('changeSettings({ [target]: value })'), 'apply persists only the selected color setting');
check(source.includes("event.key === 'Escape' && colorEditor"), 'Escape closes the active color picker before the settings dialog');
check(source.includes("event.key === 'Tab'") && source.includes('ui.colorModal.contains(document.activeElement)'), 'focus remains inside the color picker dialog');
check(source.includes('ui.colorApply.disabled = true') && source.includes('ui.colorError.hidden = false'), 'invalid drafts disable Apply and show an error');
console.log(`1..${checks}`);
