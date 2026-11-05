#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const i18n = require('../VeloAE/js/i18n.js');
const model = require('../VeloAE/js/curve-model.js');

const html = fs.readFileSync(path.join(__dirname, '../VeloAE/index.html'), 'utf8');
const main = fs.readFileSync(path.join(__dirname, '../VeloAE/js/main.js'), 'utf8');
const i18nSource = fs.readFileSync(path.join(__dirname, '../VeloAE/js/i18n.js'), 'utf8');
let checks = 0;
function check(condition, message) {
  assert.ok(condition, message);
  checks += 1;
  console.log(`ok ${checks} - ${message}`);
}

check(JSON.stringify(i18n.LANGUAGES) === JSON.stringify(['zh-CN', 'en', 'ja', 'ko']), 'exact four language values are exposed');
check(i18n.DEFAULT_LANGUAGE === 'zh-CN', 'Chinese is the default language');
const keys = Object.keys(i18n.dictionaries['zh-CN']).sort();
check(keys.length > 130, 'the centralized dictionary covers the full panel');
i18n.LANGUAGES.forEach((language) => {
  check(JSON.stringify(Object.keys(i18n.dictionaries[language]).sort()) === JSON.stringify(keys), `${language} has the complete translation key set`);
  check(keys.every((key) => typeof i18n.dictionaries[language][key] === 'string' && i18n.dictionaries[language][key].length > 0), `${language} has no empty translations`);
});
Object.keys(model.PRESETS).forEach((id) => {
  check(keys.includes(`preset.${id}`), `built-in preset has a centralized label: ${id}`);
});

const representative = {
  'zh-CN': {
    'ease.pasteEase': '粘贴缓动',
    'ease.pass': '直通',
    'param.restitution': '恢复系数',
    'settings.language': '语言'
  },
  en: {
    'ease.pasteEase': 'Ease',
    'ease.pass': 'Pass',
    'param.restitution': 'Restitution',
    'settings.language': 'Language'
  },
  ja: {
    'ease.pasteEase': 'イーズ',
    'ease.pass': 'スルー',
    'param.restitution': '復元係数',
    'settings.language': '言語'
  },
  ko: {
    'ease.pasteEase': '이즈',
    'ease.pass': '스루',
    'param.restitution': '반발 계수',
    'settings.language': '언어',
    'settings.export': 'Export'
  }
};
Object.entries(representative).forEach(([language, entries]) => {
  i18n.setLanguage(language);
  Object.entries(entries).forEach(([key, expected]) => {
    check(i18n.t(key) === expected, `${language} translates ${key} accurately`);
  });
  check(i18n.t('mode.bezier') === 'Bezier' && i18n.t('mode.elastic') === 'Elastic' && i18n.t('mode.bounce') === 'Bounce', `${language} preserves technical mode names`);
});
check(i18n.dictionaries.ko['ease.passTitle'].includes(String.fromCharCode(45236, 48512)), 'Korean Pass Through help refers to interior keyframes');

['en', 'ja', 'ko'].forEach((language) => {
  i18n.setLanguage(language);
  check(i18n.t('settings.interface') === 'UI', `${language} uses the compact UI tab label`);
});
i18n.setLanguage('en');
check(i18n.t('view.value') === 'Val' && i18n.t('view.speed') === 'Spd', 'English view labels fit the compact segmented control');
check(i18n.t('view.valueTitle') === 'Edit value curve', 'compact view labels keep full title text');
[['ja', '速', '速度カーブを編集'], ['ko', '속', '속도 커브 편집']].forEach(([language, label, title]) => {
  i18n.setLanguage(language);
  check(i18n.t('view.speed') === label && i18n.t('view.speedTitle') === title, `${language} uses a one-glyph speed label with the full title`);
});
[['en', 'Inspect'], ['ja', '検査'], ['ko', '검사']].forEach(([language, expected]) => {
  i18n.setLanguage(language);
  check(i18n.t('action.inspect') === expected, `${language} uses a short inspect action`);
});
[['en', 'Import', 'Export'], ['ja', '読込', '書出'], ['ko', '가져오기', 'Export']].forEach(([language, importLabel, exportLabel]) => {
  i18n.setLanguage(language);
  check(i18n.t('settings.import') === importLabel && i18n.t('settings.export') === exportLabel, `${language} uses concise import and export actions`);
});
i18n.setLanguage('ja');
check(i18n.t('settings.interfaceTitle') === 'インターフェース設定', 'Japanese full settings heading is preserved');
check(i18n.t('settings.presetManagement') === 'プリセット管理', 'Japanese full preset heading is preserved');

check(i18n.t('ease.count', { count: 3, properties: 2 }, 'en') === 'Keyframes 3 · Properties 2', 'dynamic count interpolation uses supplied values');
check(i18n.t('error.presetMissing', { index: 4 }, 'ja') === 'プリセット 4 に名前またはカーブがありません。', 'error interpolation preserves the preset index');
check(i18n.t('status.exported', { count: 5 }, 'zh-CN') === '已导出 5 个曲线预设', 'Chinese status interpolation remains intact');
check(i18n.t('settings.open', {}, 'unknown') === '设置', 'an unknown requested language falls back to Chinese');
check(i18n.setLanguage('fr') === 'zh-CN' && i18n.getLanguage() === 'zh-CN', 'setLanguage normalizes unsupported values');
check(i18n.t('missing.translation.key') === 'missing.translation.key', 'an unknown key remains visible for diagnosis');
check(i18n.t('status.saved', { label: 'Keep 原文' }, 'en') === 'Saved Keep 原文', 'interpolation does not alter user text');
check(i18n.t('status.saved', {}, 'en') === 'Saved {label}', 'missing interpolation values remain explicit');

i18n.LANGUAGES.forEach((language) => {
  i18n.setLanguage(language);
  check(i18n.presetLabel('preset_user_custom', 'My プリセット 원문') === 'My プリセット 원문', `${language} preserves custom preset names verbatim`);
});
i18n.setLanguage('en');
check(i18n.presetLabel('smooth', '平滑') === 'Smooth', 'built-in preset labels use the active language');
i18n.setLanguage('ja');
check(i18n.presetLabel('linear', '线性') === 'リニア', 'built-in labels can differ from model storage labels');
check(model.PRESETS.smooth.label === '平滑' && model.PRESETS.linear.label === '线性', 'display translation does not mutate model preset data');

const htmlKeys = [];
html.replace(/data-i18n(?:-title|-aria-label)?="([^"]+)"/g, (match, key) => {
  htmlKeys.push(key);
  return match;
});
check(htmlKeys.length >= 70, 'static text, titles, and aria labels use translation markers');
htmlKeys.forEach((key) => check(keys.includes(key), `HTML translation key exists: ${key}`));
const mainKeys = [];
main.replace(/'((?:status|error|ease|mode|view|direction|param|preset|settings|action|curve|canvas|preview|speed|group|location|theme|prompt|anchor|color|dialog)\.[A-Za-z0-9_]+)'/g, (match, key) => {
  mainKeys.push(key);
  return match;
});
mainKeys.forEach((key) => check(keys.includes(key), `main.js translation key exists: ${key}`));

function fakeElement(attributes, textContent) {
  const values = Object.assign({}, attributes);
  return {
    textContent: textContent || '',
    getAttribute(name) { return Object.prototype.hasOwnProperty.call(values, name) ? values[name] : null; },
    setAttribute(name, value) { values[name] = String(value); }
  };
}
const app = fakeElement({ 'data-language': 'zh-CN' });
const textNode = fakeElement({ 'data-i18n': 'settings.open' }, '设置');
const titleNode = fakeElement({ 'data-i18n-title': 'ease.pasteEaseTitle', title: '只粘贴缓动，保留数值' });
const ariaNode = fakeElement({ 'data-i18n-aria-label': 'canvas.aria', 'aria-label': '值曲线和背景速度曲线' });
const documentRef = {
  documentElement: { lang: 'zh-CN' },
  getElementById(id) { return id === 'appContainer' ? app : null; },
  querySelectorAll() { return [textNode, titleNode, ariaNode]; }
};
i18n.apply(documentRef, 'ja');
check(documentRef.documentElement.lang === 'ja' && app.getAttribute('data-language') === 'ja', 'language apply updates root lang and app data-language');
check(textNode.textContent === '設定', 'language apply updates static text');
check(titleNode.getAttribute('title') === 'イーズのみを貼り付け、値を保持', 'language apply updates title text');
check(ariaNode.getAttribute('aria-label') === '値カーブと背景の速度カーブ', 'language apply updates aria text');
i18n.apply(documentRef, 'en');
check(documentRef.documentElement.lang === 'en' && app.getAttribute('data-language') === 'en' && textNode.textContent === 'Settings', 'subsequent language changes update the same nodes');
check(!/MutationObserver|setInterval/.test(i18nSource + main), 'translation uses no observer or polling');

function declaration(name) {
  const start = main.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, `${name} exists`);
  const end = main.indexOf('\n  function ', start + 2);
  assert.ok(end > start, `${name} has a complete declaration`);
  return main.slice(start, end);
}
const defaultsSource = main.match(/  const DEFAULT_SETTINGS = \{[\s\S]*?\n  \};/)[0];
function settingsLoader(raw) {
  const localStorage = { getItem(key) { return key === 'velo-ae-settings-v2' ? raw : null; } };
  return new Function('model', 'localStorage', 'i18n', `${defaultsSource}\n${declaration('loadSettings')}\nreturn loadSettings();`)(model, localStorage, i18n);
}
const legacy = settingsLoader(JSON.stringify({ compact: true, location: 'left', themeColor: '#123456', futurePreference: 'keep' }));
check(legacy.language === 'zh-CN', 'legacy settings without language default to Chinese');
check(legacy.compact === true && legacy.location === 'left' && legacy.themeColor === '#123456', 'legacy preferences remain unchanged');
check(legacy.futurePreference === 'keep', 'unknown future settings survive the merge');
i18n.LANGUAGES.forEach((language) => {
  const loaded = settingsLoader(JSON.stringify({ language, compact: true }));
  check(loaded.language === language && loaded.compact === true, `valid stored language is preserved: ${language}`);
});
['fr', '', null, 42].forEach((language) => {
  check(settingsLoader(JSON.stringify({ language })).language === 'zh-CN', `invalid stored language falls back: ${String(language)}`);
});
const malformed = settingsLoader('{not-json');
check(malformed.language === 'zh-CN' && malformed.location === 'right', 'malformed settings retain all defaults including language');
check(/settings = Object\.assign\(\{\}, settings, next\);/.test(main), 'setting changes merge with existing preferences');
check(/settings = Object\.assign\(\{\}, DEFAULT_SETTINGS\);/.test(main), 'restore defaults uses the shared default object');
check(/language: 'zh-CN'/.test(defaultsSource), 'restore defaults returns to Chinese');

const controls = declaration('updateControls');
const controlText = declaration('updateControlText');
check(!controls.includes('i18n.apply'), 'drag-time control updates do not retranslate the document');
check(controlText.includes('nextKey === controlTextKey') && controlText.includes('settings.compact') && controlText.includes('state.direction'), 'dynamic labels are cached by language and relevant control state');
check(declaration('applyLanguage').includes('renderStatus();') && declaration('applyLanguage').includes('updateEaseBuffer();'), 'language changes refresh current status and EaseCopy counts');
check(/label: i18n\.presetLabel\(id, preset\.label\)/.test(main) && /label: preset\.label, state: preset\.state/.test(main), 'only built-in preset labels are translated');
check(!/stateText[\s\S]*i18n/.test(declaration('stateText')), 'curve JSON serialization has no translation path');

function integrationElement(tagName) {
  const attributes = {};
  const listeners = {};
  const classes = new Set();
  const styleValues = new Map();
  const context2d = new Proxy({}, {
    get(target, key) {
      if (!(key in target)) target[key] = () => {};
      return target[key];
    },
    set(target, key, value) { target[key] = value; return true; }
  });
  return {
    tagName,
    children: [],
    dataset: {},
    value: '',
    checked: false,
    disabled: false,
    hidden: false,
    textContent: '',
    innerHTML: '',
    title: '',
    className: '',
    style: {
      getPropertyValue(name) { return styleValues.get(name) || ''; },
      setProperty(name, value) { styleValues.set(name, String(value)); }
    },
    classList: {
      toggle(name, force) { if (force) classes.add(name); else classes.delete(name); },
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); }
    },
    addEventListener(type, listener) { (listeners[type] || (listeners[type] = [])).push(listener); },
    dispatch(type) { (listeners[type] || []).forEach((listener) => listener({ target: this })); },
    listenerCount(type) { return (listeners[type] || []).length; },
    getAttribute(name) { return Object.prototype.hasOwnProperty.call(attributes, name) ? attributes[name] : null; },
    setAttribute(name, value) { attributes[name] = String(value); },
    append(...nodes) { this.children.push(...nodes); },
    appendChild(node) { this.children.push(node); return node; },
    replaceChildren(fragment) { this.children = fragment.children.slice(); },
    remove() {},
    select() {},
    click() {},
    getBoundingClientRect() { return { left: 0, top: 0, width: 80, height: 80 }; },
    getContext() { return context2d; }
  };
}

const elements = {};
html.replace(/id="([^"]+)"/g, (match, id) => {
  elements[id] = integrationElement();
  return match;
});
const modeButtons = ['bezier', 'elastic', 'bounce'].map((mode) => {
  const button = integrationElement('button');
  button.dataset.mode = mode;
  return button;
});
const viewButtons = ['value', 'speed'].map((view) => {
  const button = integrationElement('button');
  button.dataset.view = view;
  return button;
});
const settingsTabs = ['interface', 'presets', 'theme', 'graph'].map((page) => {
  const button = integrationElement('button');
  button.dataset.settingsPage = page;
  return button;
});
const settingsPages = ['interface', 'presets', 'theme', 'graph'].map((page) => {
  const section = integrationElement('section');
  section.dataset.page = page;
  return section;
});
const themeChoices = ['#4a90e2', '#39c5cf', '#f2b35d'].map((color) => {
  const button = integrationElement('button');
  button.dataset.color = color;
  return button;
});
elements.settingsTitle.setAttribute('data-i18n', 'settings.open');
elements.easeCopyEaseBtn.setAttribute('data-i18n', 'ease.pasteEase');
elements.easeCopyPassBtn.setAttribute('data-i18n', 'ease.pass');
elements.appContainer.setAttribute('data-language', 'zh-CN');
const documentElement = { lang: 'zh-CN' };
const integrationDocument = {
  documentElement,
  hidden: false,
  body: integrationElement('body'),
  getElementById(id) { return elements[id] || null; },
  querySelectorAll(selector) {
    if (selector === '.mode-btn') return modeButtons;
    if (selector === '.view-btn') return viewButtons;
    if (selector === '.settings-tab') return settingsTabs;
    if (selector === '.settings-page') return settingsPages;
    if (selector === '.theme-choice') return themeChoices;
    if (selector === '.preset-item') return elements.presetList.children;
    return Object.values(elements).filter((element) => ['data-i18n', 'data-i18n-title', 'data-i18n-aria-label'].some((name) => element.getAttribute(name)));
  },
  createDocumentFragment() { return integrationElement('fragment'); },
  createElement(tagName) { return integrationElement(tagName); },
  addEventListener() {},
  execCommand() { return true; }
};
const customState = model.serializable(model.normalize({}));
const storage = {
  'velo-ae-settings-v2': JSON.stringify({ language: 'en', compact: true, themeColor: '#123456' }),
  'velo-ae-user-presets': JSON.stringify([{ id: 'preset_user_keep', label: 'Keep 原文', state: customState }])
};
const localStorageRef = {
  getItem(key) { return Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : null; },
  setItem(key, value) { storage[key] = String(value); }
};
const timers = new Map();
let timerId = 0;
let animationId = 0;
const themeSnapshots = [];
const windowRef = {
  VeloModel: model,
  VeloI18n: i18n,
  VeloTheme: { apply(settings) { themeSnapshots.push(Object.assign({}, settings)); } },
  devicePixelRatio: 1,
  innerWidth: 800,
  innerHeight: 700,
  addEventListener() {}
};
require('node:vm').runInNewContext(main, {
  window: windowRef,
  document: integrationDocument,
  localStorage: localStorageRef,
  navigator: {},
  performance: { now() { return 0; } },
  requestAnimationFrame() { animationId += 1; return animationId; },
  cancelAnimationFrame() {},
  setTimeout(callback) { timerId += 1; timers.set(timerId, callback); return timerId; },
  clearTimeout(id) { timers.delete(id); },
  getComputedStyle() { return { getPropertyValue() { return ''; } }; }
}, { filename: 'main.js' });

function presetText(id) {
  const button = elements.presetList.children.find((entry) => entry.dataset.id === id);
  return button ? button.children[1].textContent : null;
}
function flushTimers() {
  const callbacks = Array.from(timers.values());
  timers.clear();
  callbacks.forEach((callback) => callback());
}
const initialJson = elements.bezierJsonOutput.value;
check(documentElement.lang === 'en' && elements.appContainer.getAttribute('data-language') === 'en', 'main initializes from the stored language');
check(elements.languageSelect.value === 'en' && elements.settingsTitle.textContent === 'Settings', 'main synchronizes the language control and static text');
check(presetText('smooth') === 'Smooth' && presetText('preset_user_keep') === 'Keep 原文', 'main renders translated built-ins and untouched user presets');
const scenarios = [
  { language: 'ja', title: '設定', ready: '準備完了', pasteEase: 'イーズ', smooth: 'スムーズ' },
  { language: 'ko', title: '설정', ready: '준비 완료', pasteEase: '이즈', smooth: '부드러움' },
  { language: 'zh-CN', title: '设置', ready: '就绪', pasteEase: '粘贴缓动', smooth: '平滑' },
  { language: 'en', title: 'Settings', ready: 'Ready', pasteEase: 'Ease', smooth: 'Smooth' }
];
scenarios.forEach((scenario) => {
  elements.languageSelect.value = scenario.language;
  elements.languageSelect.dispatch('change');
  flushTimers();
  check(documentElement.lang === scenario.language && elements.appContainer.getAttribute('data-language') === scenario.language, `change event updates root language: ${scenario.language}`);
  check(elements.settingsTitle.textContent === scenario.title && elements.statusText.textContent === scenario.ready, `change event updates static and dynamic text: ${scenario.language}`);
  check(elements.easeCopyEaseBtn.textContent === scenario.pasteEase, `change event updates EaseCopy: ${scenario.language}`);
  check(presetText('smooth') === scenario.smooth && presetText('preset_user_keep') === 'Keep 原文', `change event refreshes only built-in names: ${scenario.language}`);
  check(elements.bezierJsonOutput.value === initialJson, `change event preserves curve JSON: ${scenario.language}`);
  const saved = JSON.parse(storage['velo-ae-settings-v2']);
  check(saved.language === scenario.language && saved.compact === true && saved.themeColor === '#123456', `change event merges persisted preferences: ${scenario.language}`);
});
check(elements.languageSelect.listenerCount('change') === 1, 'repeated language changes do not add listeners');
check(themeSnapshots.every((settings) => settings.themeColor === '#123456'), 'language changes never fall back to a default theme');

elements.presetList.children.find((entry) => entry.dataset.id === 'smooth').dispatch('click');
check(elements.statusText.textContent === 'Ready' && elements.toastText.textContent === 'Preset · Smooth', 'selecting Smooth keeps the header compact while the toast carries the full localized preset');
elements.languageSelect.value = 'zh-CN';
elements.languageSelect.dispatch('change');
check(elements.toastText.textContent === '预设 · 平滑', 'an unexpired built-in preset status is retranslated in the toast on language change');
elements.presetList.children.find((entry) => entry.dataset.id === 'preset_user_keep').dispatch('click');
check(elements.toastText.textContent === '预设 · Keep 原文', 'selecting a user preset keeps its original name in the toast');
elements.languageSelect.value = 'en';
elements.languageSelect.dispatch('change');
check(elements.toastText.textContent === 'Preset · Keep 原文', 'an unexpired user preset status never translates the custom name in the toast');
check(elements.languageSelect.listenerCount('change') === 1, 'preset status regressions add no duplicate language listeners');

console.log(`1..${checks}`);
