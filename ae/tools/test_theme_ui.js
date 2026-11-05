#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createStyle() {
  const values = new Map();
  const writes = [];
  return {
    values,
    writes,
    getPropertyValue(name) { return values.get(name) || ''; },
    setProperty(name, value) {
      const text = String(value);
      values.set(name, text);
      writes.push([name, text]);
    }
  };
}

const rootStyle = createStyle();
const root = { style: rootStyle };
const context = { window: {}, document: { documentElement: root } };
const source = fs.readFileSync(path.join(__dirname, '../VeloAE/js/theme.js'), 'utf8');
vm.runInNewContext(source, context, { filename: 'theme.js' });

let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}

const app = { parent: root, style: createStyle() };
const modal = { parent: root, style: createStyle() };
app.style.values.set('--preset-box-size', '104px');
function inheritedToken(node, name) {
  let current = node;
  while (current) {
    const value = current.style.getPropertyValue(name);
    if (value) return value;
    current = current.parent;
  }
  return '';
}

check(typeof context.window.VeloTheme.apply === 'function', 'VeloTheme.apply is available');
const settings = { themeColor: '#f2b35d', themeBackground: '#242424', themeHandles: '#dcdcdc' };
context.window.VeloTheme.apply(settings);
const expected = {
  '--btn-active-bg': '#f2b35d',
  '--accent-soft': '#f2b35d80',
  '--btn-active-hover-bg': 'rgb(218,161,84)',
  '--curve-color': '#f2b35d',
  '--panel-bg': '#242424'
};
Object.entries(expected).forEach(([name, value]) => {
  check(rootStyle.getPropertyValue(name) === value, `root token ${name} follows the theme`);
});
check(rootStyle.writes.length === 5, 'the initial theme writes each shared token once');
check(inheritedToken(modal, '--btn-active-bg') === '#f2b35d', 'the sibling settings modal inherits the root accent');
check(inheritedToken(modal, '--panel-bg') === '#242424', 'the sibling settings modal inherits the shared canvas token');
check(app.style.getPropertyValue('--preset-box-size') === '104px' && app.style.writes.length === 0, 'theme application leaves app-scoped sizing untouched');

context.window.VeloTheme.apply(settings);
context.window.VeloTheme.apply(Object.assign({}, settings));
check(rootStyle.writes.length === 5, 'identical themes cause no duplicate writes');

context.window.VeloTheme.apply(Object.assign({}, settings, { themeColor: '#39c5cf' }));
check(rootStyle.writes.length === 9, 'an accent-only change leaves the unchanged background token unwritten');
check(inheritedToken(modal, '--btn-active-bg') === '#39c5cf', 'the modal observes subsequent accent changes');
check(rootStyle.getPropertyValue('--btn-active-hover-bg') === 'rgb(51,177,186)', 'hover is derived from the new accent');
check(rootStyle.getPropertyValue('--panel-bg') === '#242424', 'accent changes preserve the canvas background');

context.window.VeloTheme.apply(Object.assign({}, settings, { themeColor: '#39c5cf', themeBackground: '#181818' }));
check(rootStyle.writes.length === 10, 'a background-only change writes only the background token');
check(rootStyle.getPropertyValue('--panel-bg') === '#181818', 'the new canvas background reaches the common root');

console.log(`1..${checks}`);
