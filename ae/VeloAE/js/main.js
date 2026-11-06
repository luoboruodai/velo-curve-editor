(function () {
  'use strict';

  const model = window.VeloModel;
  if (!model) throw new Error('Velo curve model is unavailable.');
  const i18n = window.VeloI18n;
  if (!i18n) throw new Error('Velo i18n is unavailable.');

  const $ = (id) => document.getElementById(id);
  const ui = {
    app: $('appContainer'), canvas: $('curveCanvas'), wrapper: $('canvasWrapper'),
    speedInfo: $('speedInfo'), direction: $('directionBtn'), settings: $('settingsBtn'),
    json: $('bezierJsonOutput'), copy: $('copyJsonBtn'),
    bezierPanel: $('bezierDataPanel'), elasticPanel: $('elasticParamsPanel'), bouncePanel: $('bounceParamsPanel'),
    amp: $('ampSlider'), freq: $('freqSlider'), cor: $('corSlider'), period: $('periodSlider'),
    paste: $('pasteBtn'), reset: $('resetBtn'), reverse: $('reverseBtn'), smoothAll: $('smoothAllBtn'), save: $('savePresetBtn'),
    inspect: $('inspectBtn'), read: $('readCurveBtn'), apply: $('applyBtn'), status: $('status'),
    presetPanel: $('presetPanel'), presetList: $('presetList'), resizer: $('panelResizer'),
    modal: $('settingsModal'), closeSettings: $('closeSettingsBtn'), location: $('presetLocation'), language: $('languageSelect'),
    compact: $('compactToggle'), speed: $('speedToggle'), autoInspect: $('autoApplyPreset'), defaults: $('resetDefaultsBtn'),
    motion: $('motionToggle'), presetSize: $('presetSize'), presetSizeValue: $('presetSizeValue'), restorePresets: $('restorePresetsBtn'),
    viewGroup: $('viewGroup'), contextMenu: $('presetContextMenu'), presetHide: $('presetHideBtn'), presetDelete: $('presetDeleteBtn'),
    anchorMenu: $('anchorContextMenu'), anchorSmooth: $('anchorSmoothBtn'), anchorPreserveDelete: $('anchorPreserveDeleteBtn'), anchorDelete: $('anchorDeleteBtn'), snapHint: $('tangentSnapHint'),
    easeCount: $('easeCopyCount'), easeCopy: $('easeCopyCopyBtn'), easePaste: $('easeCopyEaseBtn'), valuePaste: $('easeCopyValueBtn'),
    easePass: $('easeCopyPassBtn'), easeClear: $('easeCopyClearBtn'),
    ampValue: $('ampValue'), freqValue: $('freqValue'), corValue: $('corValue'), periodValue: $('periodValue'),
    preview: $('previewCanvas'), previewPlay: $('previewPlayBtn'), previewDuration: $('previewDuration'),
    doneSettings: $('doneSettingsBtn'), importPresets: $('importPresetsBtn'), exportPresets: $('exportPresetsBtn'), presetFile: $('presetFileInput'), exportPath: $('presetExportPath'),
    themeColor: $('themeColor'), themeBackground: $('themeBackground'), themeHandles: $('themeHandles'),
    gridX: $('gridX'), gridY: $('gridY'), precision: $('curvePrecision'), precisionValue: $('curvePrecisionValue'),
    speedStrength: $('speedStrength'), speedStrengthValue: $('speedStrengthValue'), fitCurve: $('fitCurveBtn'),
    colorModal: $('colorPickerModal'), colorClose: $('colorPickerClose'), colorField: $('colorField'), colorHue: $('colorHue'),
    colorHex: $('colorHex'), colorR: $('colorR'), colorG: $('colorG'), colorB: $('colorB'),
    colorPreview: $('colorPreview'), colorError: $('colorError'), colorCancel: $('colorPickerCancel'), colorApply: $('colorPickerApply'),
    multiModal: $('multiPointModal'), multiMessage: $('multiPointMessage'), multiClose: $('multiPointClose'),
    multiCancel: $('multiPointCancel'), multiSwitch: $('multiPointSwitch'),
    statusText: $('statusText'), healthDot: $('healthDot'),
    toast: $('statusToast'), toastDot: $('toastDot'), toastText: $('toastText'), toastClose: $('toastClose')
  };

  const DEFAULT_SETTINGS = {
    compact: false, location: 'right', language: 'zh-CN', showSpeed: true, autoInspect: true, presetSize: 80, reduceMotion: false,
    themeColor: '#4a90e2', themeBackground: '#222222', themeHandles: '#dcdcdc',
    gridX: 4, gridY: 4, precision: 300, speedStrength: 0.28
  };
  let state = model.normalize({});
  let settings = loadSettings();
  let settingsSaveTimer = null;
  let preview = { playing: true, time: 0, duration: 2, frame: 0, lastTime: null, lastDraw: 0, u: 0, lastPaintKey: null, resumeAfterMotion: false };
  let drag = null;
  let resizeDrag = null;
  let statusTimer = null;
  let currentStatus = { key: 'status.ready', params: {}, isError: false };
  let controlTextKey = '';
  let selectedPresetId = 'smooth';
  let editView = 'value';
  let contextPresetId = null;
  let contextAnchorIndex = null;
  let anchorWindowExtra = 0;
  let colorEditor = null;
  let multiPointOpen = false;
  let multiPointClosing = false;
  let multiPointCloseTimer = 0;
  let multiPointFocusReturn = null;
  let toastOpen = false;
  let toastClosing = false;
  let toastCloseTimer = 0;
  let toastRemaining = 4500;
  let toastStartedAt = 0;
  let easeBuffer = null;
  let preservePassthrough = false;
  let userPresets = loadUserPresets();
  let hiddenPresets = loadStoredArray('velo-ae-hidden-presets');
  let presetOrder = loadStoredArray('velo-ae-preset-order');
  let presetCanvases = new Map();
  let thumbnailSampleCache = new Map();
  let thumbnailFrame = 0;

  function loadSettings() {
    let stored = {};
    try { stored = JSON.parse(localStorage.getItem('velo-ae-settings-v2') || '{}'); } catch (error) { stored = {}; }
    const result = Object.assign({}, DEFAULT_SETTINGS, stored);
    result.location = ['right', 'left', 'top', 'bottom'].includes(result.location) ? result.location : 'right';
    result.language = i18n.normalizeLanguage(result.language);
    ['compact', 'showSpeed', 'autoInspect', 'reduceMotion'].forEach((key) => { result[key] = Boolean(result[key]); });
    result.presetSize = model.clamp(Number(result.presetSize) || 80, 40, 104);
    result.gridX = Math.round(model.clamp(Number(result.gridX) || 4, 1, 20));
    result.gridY = Math.round(model.clamp(Number(result.gridY) || 4, 1, 20));
    result.precision = Math.round(model.clamp(Number(result.precision) || 300, 50, 1000));
    result.speedStrength = model.clamp(Number(result.speedStrength) || 0.28, 0.05, 0.65);
    ['themeColor', 'themeBackground', 'themeHandles'].forEach((key) => {
      if (!/^#[0-9a-f]{6}$/i.test(result[key])) result[key] = DEFAULT_SETTINGS[key];
    });
    return result;
  }

  function flushSettings() {
    clearTimeout(settingsSaveTimer);
    settingsSaveTimer = null;
    try { localStorage.setItem('velo-ae-settings-v2', JSON.stringify(settings)); } catch (error) { /* storage is optional */ }
  }

  function saveSettings() {
    clearTimeout(settingsSaveTimer);
    settingsSaveTimer = setTimeout(flushSettings, 80);
  }

  function loadUserPresets() {
    try {
      const value = JSON.parse(localStorage.getItem('velo-ae-user-presets') || '[]');
      return Array.isArray(value) ? value.filter((entry) => entry && entry.state && entry.label).slice(0, 32) : [];
    } catch (error) {
      return [];
    }
  }

  function saveUserPresets() {
    try { localStorage.setItem('velo-ae-user-presets', JSON.stringify(userPresets)); } catch (error) { /* storage is optional */ }
  }

  function loadStoredArray(key) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || '[]');
      return Array.isArray(value) ? value.filter((entry) => typeof entry === 'string') : [];
    } catch (error) { return []; }
  }

  function storeArray(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (error) { /* storage is optional */ }
  }

  function statusHealth() {
    if (currentStatus.isError) return 'error';
    if (['status.inspecting', 'status.reading', 'status.applying'].includes(currentStatus.key)) return 'busy';
    if (['status.pointTooClose', 'status.pointLimit', 'status.multiPointUnavailable', 'status.browserPreview', 'status.browserNoWrite', 'status.inspectUnavailable', 'status.inspectUnavailableSkipped', 'status.readDeferred', 'status.readAdjusted', 'status.appliedMixed'].includes(currentStatus.key)) return 'warning';
    return 'ready';
  }

  function renderStatus() {
    const params = {};
    Object.keys(currentStatus.params).forEach((key) => {
      const value = currentStatus.params[key];
      params[key] = value && typeof value === 'object' && value.key ? i18n.t(value.key, value.params) : value;
    });
    const text = i18n.t(currentStatus.key, params);
    const health = statusHealth();
    const compactKey = currentStatus.key === 'status.ready'
      ? 'status.ready'
      : ({ warning: 'status.compactWarning', busy: 'status.compactBusy', error: 'status.compactError' }[health] || 'status.ready');
    const compactText = i18n.t(compactKey);
    if (ui.statusText.textContent !== compactText) ui.statusText.textContent = compactText;
    ui.status.title = text;
    ui.status.classList.toggle('error', currentStatus.isError);
    ui.healthDot.dataset.state = health;
    ui.status.dataset.state = health;
    if (ui.toastText.textContent !== text) ui.toastText.textContent = text;
    ui.toast.dataset.state = health;
    ui.toastDot.dataset.state = health;
    ui.toast.setAttribute('role', currentStatus.isError ? 'alert' : 'status');
  }

  function scheduleToastDismiss() {
    clearTimeout(statusTimer);
    toastStartedAt = Date.now();
    statusTimer = setTimeout(closeToast, toastRemaining);
  }

  function pauseToastDismiss() {
    if (!toastOpen || toastClosing || statusTimer === null) return;
    clearTimeout(statusTimer);
    statusTimer = null;
    toastRemaining = Math.max(0, toastRemaining - (Date.now() - toastStartedAt));
  }

  function resumeToastDismiss() {
    if (toastOpen && !toastClosing) scheduleToastDismiss();
  }

  function finishToastClose() {
    clearTimeout(toastCloseTimer);
    toastCloseTimer = 0;
    toastOpen = false;
    toastClosing = false;
    ui.toast.classList.remove('visible', 'closing');
    ui.toast.hidden = true;
    currentStatus = { key: 'status.ready', params: {}, isError: false };
    renderStatus();
  }

  function closeToast() {
    if (!toastOpen || toastClosing) return;
    clearTimeout(statusTimer);
    statusTimer = null;
    toastClosing = true;
    ui.toast.classList.remove('visible');
    if (multiPointReducedMotion()) {
      finishToastClose();
      return;
    }
    ui.toast.classList.add('closing');
    toastCloseTimer = setTimeout(finishToastClose, 160);
  }

  function showStatus(key, params, isError) {
    clearTimeout(statusTimer);
    statusTimer = null;
    currentStatus = { key, params: params || {}, isError: Boolean(isError) };
    if (key === 'status.ready') {
      if (toastOpen) closeToast();
      else renderStatus();
      return;
    }
    toastRemaining = 4500;
    toastOpen = true;
    toastClosing = false;
    clearTimeout(toastCloseTimer);
    toastCloseTimer = 0;
    renderStatus();
    const wasHidden = ui.toast.hidden;
    ui.toast.hidden = false;
    ui.toast.classList.remove('closing');
    if (!multiPointReducedMotion() && wasHidden) void ui.toast.offsetWidth;
    ui.toast.classList.add('visible');
    scheduleToastDismiss();
  }

  ui.toastClose.addEventListener('click', closeToast);
  ui.toast.addEventListener('pointerenter', pauseToastDismiss);
  ui.toast.addEventListener('pointerleave', resumeToastDismiss);
  ui.toast.addEventListener('focusin', pauseToastDismiss);
  ui.toast.addEventListener('focusout', resumeToastDismiss);

  function translatedError(key, params) {
    const error = new Error(key);
    error.translation = { key, params: params || {} };
    return error;
  }

  function showError(error, prefix) {
    const detail = error && error.translation ? error.translation : { key: 'status.raw', params: { text: error && error.message ? error.message : String(error) } };
    showStatus(prefix, { detail }, true);
  }

  function applyLanguage(language) {
    i18n.setLanguage(language);
    i18n.apply(document);
    renderStatus();
    updateEaseBuffer();
    updatePreviewButton();
  }

  function clamp01(value) { return model.clamp(value, 0, 1); }
  function stateText() { return JSON.stringify({ format: 'velo-ae-curve', version: state.segments ? 2 : 1, state: model.serializable(state) }); }
  function sameState(other) { return JSON.stringify(model.serializable(other)) === JSON.stringify(model.serializable(state)); }
  function setStyle(element, property, value) {
    if (element.style.getPropertyValue(property) !== value) element.style.setProperty(property, value);
  }
  function setValue(element, value) {
    const text = String(value);
    if (element.value !== text) element.value = text;
  }
  function setChecked(element, value) {
    if (element.checked !== value) element.checked = value;
  }
  function token(name) { return getComputedStyle(ui.app).getPropertyValue(name).trim(); }
  function mixColor(background, accent, amount) {
    function rgb(hex) { return [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16)); }
    const a = rgb(background), b = rgb(accent);
    return `rgb(${a.map((value, index) => Math.round(value + (b[index] - value) * amount)).join(',')})`;
  }

  function displayRange(data, required) {
    const finite = data.filter(Number.isFinite);
    let low = Math.min(...finite, ...required);
    let high = Math.max(...finite, ...required);
    if (high - low < 0.1) { low -= 0.1; high += 0.1; }
    const padding = (high - low) * 0.08;
    return [low - padding, high + padding];
  }

  function speedFitRange(data) {
    const finite = data.filter(Number.isFinite);
    const low = Math.min(0, ...finite);
    const high = Math.max(0, ...finite);
    const padding = Math.max(high - low, 0.4) * 0.28;
    return [low - padding, high + padding];
  }

  function speedPointerValue(speed, pointerY, metrics) {
    return Math.abs(pointerY - toY(0, metrics.speedRange, metrics)) <= 8 ? 0 : speed;
  }

  let metricsCache = null;
  let segmentsKeyCache = { reference: null, key: '' };
  let drawFrame = 0;
  let lastPointerMoveTime = -Infinity;
  let speedViewRange = null;
  let speedViewRangeStateKey = null;

  function curveStateKey() {
    const scalarKey = Object.keys(model.DEFAULTS).map((key) => state[key]).join('|');
    if (!state.segments) return scalarKey;
    if (segmentsKeyCache.reference !== state.segments) {
      segmentsKeyCache = { reference: state.segments, key: JSON.stringify(state.segments) };
    }
    return `${scalarKey}|${segmentsKeyCache.key}`;
  }

  function speedDragRange(data, drag) {
    return drag.speedRange.slice();
  }

  function speedEditorRange(speeds, stateKey) {
    if (drag && drag.speedRange) return speedDragRange(speeds, drag);
    if (!speedViewRange || speedViewRangeStateKey !== stateKey) {
      speedViewRange = speedFitRange(speeds);
      speedViewRangeStateKey = stateKey;
    }
    return speedViewRange;
  }

  function bezierValueData(state, values) {
    const data = values.slice();
    if (state.mode !== 'bezier') return data;
    if (state.segments) {
      state.segments.forEach((segment) => segment.forEach((point) => data.push(point[1])));
    } else {
      data.push(state.y1, state.y2);
    }
    return data;
  }

  function graphMetrics() {
    const rect = ui.canvas.getBoundingClientRect();
    const stateKey = curveStateKey();
    const viewKey = `${editView}|${speedViewRange ? speedViewRange.join(',') : 'fit'}|${drag && drag.speedRange ? drag.kind : ''}`;
    const cacheKey = `${stateKey}|${viewKey}`;
    if (metricsCache && metricsCache.stateKey === cacheKey &&
      metricsCache.rect.left === rect.left && metricsCache.rect.top === rect.top &&
      metricsCache.rect.width === rect.width && metricsCache.rect.height === rect.height) return metricsCache;
    let sampleCache = metricsCache && metricsCache.stateKey === cacheKey ? metricsCache : null;
    if (!sampleCache) {
      const samples = model.sample(state, state.precision);
      const speedView = state.mode === 'bezier' && editView === 'speed';
      sampleCache = {
        samples,
        valueRange: displayRange(bezierValueData(state, samples.values), [0, 1]),
        speedRange: speedView ? speedEditorRange(samples.speeds, stateKey) : displayRange(samples.speeds, [0])
      };
    }
    metricsCache = Object.assign({}, sampleCache, {
      stateKey: cacheKey,
      rect,
      left: 16,
      top: 16,
      width: Math.max(1, rect.width - 32),
      height: Math.max(1, rect.height - 32),
      speedBreakpoints: state.mode === 'bezier' ? model.bezierBreakpoints(state) : model.bounceBreakpoints(state, rect.width)
    });
    return metricsCache;
  }

  function syncCanvasSize() {
    const rect = ui.canvas.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (ui.canvas.width !== width || ui.canvas.height !== height) {
      ui.canvas.width = width;
      ui.canvas.height = height;
    }
    const ctx = ui.canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  }

  function drawLine(ctx, points, color, width) {
    if (!points.length) return;
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.moveTo(points[0][0], points[0][1]);
    points.slice(1).forEach((point) => ctx.lineTo(point[0], point[1]));
    ctx.stroke();
  }

  function gridYLines(metrics, gridY) {
    const bottom = metrics.top + metrics.height;
    const zeroY = Math.max(metrics.top, Math.min(bottom, toY(0, metrics.speedRange, metrics)));
    const count = Math.max(1, Math.round(gridY));
    const lowerCount = Math.max(2, Math.round(count * (bottom - zeroY) / metrics.height));
    const upperCount = Math.max(count > 3 ? 2 : 1, count - lowerCount);
    const lines = [];
    for (let i = 0; i <= upperCount; i += 1) lines.push(zeroY - (zeroY - metrics.top) * i / upperCount);
    for (let i = 1; i <= lowerCount; i += 1) lines.push(zeroY + (bottom - zeroY) * i / lowerCount);
    return lines;
  }

  function drawGrid(ctx, metrics) {
    const { left, top, width, height } = metrics;
    for (let i = 0; i <= settings.gridX; i += 1) {
      const x = left + width * i / settings.gridX;
      drawLine(ctx, [[x, top], [x, top + height]], '#303030', 1);
    }
    const speedView = state.mode === 'bezier' && editView === 'speed';
    if (speedView) {
      gridYLines(metrics, settings.gridY).forEach((y) => drawLine(ctx, [[left, y], [left + width, y]], '#303030', 1));
    } else {
      for (let i = 0; i <= settings.gridY; i += 1) {
        const y = top + height * i / settings.gridY;
        drawLine(ctx, [[left, y], [left + width, y]], '#303030', 1);
      }
    }
    ctx.strokeStyle = '#484848';
    ctx.lineWidth = 1;
    ctx.strokeRect(left, top, width, height);
    if (settings.showSpeed || (state.mode === 'bezier' && editView === 'speed')) {
      const y = toY(0, metrics.speedRange, metrics);
      const snapping = drag && drag.snapZero;
      drawLine(ctx, [[left, y], [left + width, y]], snapping ? token('--btn-active-bg') : '#3a454d', snapping ? 1.5 : 1);
    }
  }

  function toY(value, range, metrics) {
    return metrics.top + (1 - (value - range[0]) / (range[1] - range[0])) * metrics.height;
  }

  function drawSamples(ctx, samples, color, width, metrics, speed) {
    if (!samples.length) return;
    const range = speed ? metrics.speedRange : metrics.valueRange;
    const breakpoints = speed ? metrics.speedBreakpoints : null;
    let breakpointIndex = 0;
    let hasPoint = false;
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    for (let index = 0; index < samples.length; index += 1) {
      const u = index / (samples.length - 1);
      const x = metrics.left + u * metrics.width;
      let separated = !Number.isFinite(samples[index]);
      if (breakpoints && index > 0) {
        const previous = (index - 1) / (samples.length - 1);
        while (breakpointIndex < breakpoints.length && breakpoints[breakpointIndex] <= previous) breakpointIndex += 1;
        if (breakpointIndex < breakpoints.length && breakpoints[breakpointIndex] <= u) {
          separated = true;
          while (breakpointIndex < breakpoints.length && breakpoints[breakpointIndex] <= u) breakpointIndex += 1;
        }
      }
      if (!Number.isFinite(samples[index])) {
        hasPoint = false;
        continue;
      }
      const y = toY(samples[index], range, metrics);
      if (!hasPoint || separated) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      hasPoint = true;
    }
    ctx.stroke();
  }

  function drawAnchor(ctx, x, y) {
    ctx.fillStyle = settings.themeHandles;
    ctx.fillRect(x - 3, y - 3, 6, 6);
  }

  function drawHandle(ctx, x, y, square) {
    ctx.beginPath();
    if (square) ctx.rect(x - 4, y - 4, 8, 8);
    else ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = settings.themeBackground;
    ctx.fill();
    ctx.strokeStyle = settings.themeHandles;
    ctx.lineWidth = 1.4;
    ctx.stroke();
  }

  function bezierHandlePositions(metrics) {
    const speedView = editView === 'speed';
    const range = speedView ? metrics.speedRange : metrics.valueRange;
    const values = speedView ? metrics.samples.speeds : metrics.samples.values;
    const startValue = Number.isNaN(values[0]) ? 0 : model.clamp(values[0], range[0], range[1]);
    const endValue = Number.isNaN(values[values.length - 1]) ? 0 : model.clamp(values[values.length - 1], range[0], range[1]);
    const startY = toY(startValue, range, metrics);
    const endY = toY(endValue, range, metrics);
    const firstY = speedView ? startY : toY(state.y1, range, metrics);
    const secondY = speedView ? endY : toY(state.y2, range, metrics);
    return {
      start: [metrics.left, startY],
      end: [metrics.left + metrics.width, endY],
      first: [metrics.left + state.x1 * metrics.width, firstY],
      second: [metrics.left + state.x2 * metrics.width, secondY]
    };
  }

  function multiBezierPositions(metrics) {
    const segments = state.segments;
    const speedView = editView === 'speed';
    return segments.map((segment, index) => {
      const previous = index > 0 ? segments[index - 1] : null;
      const point = index === 0 ? segment[0] : previous[3];
      const speed = model.valueAndSpeed(state, point[0])[1];
      const range = speedView ? metrics.speedRange : metrics.valueRange;
      const value = speedView ? speed : point[1];
      const anchor = {
        index,
        point: [metrics.left + point[0] * metrics.width, toY(model.clamp(value, range[0], range[1]), range, metrics)]
      };
      if (previous) {
        const handle = previous[2];
        const handleSpeed = speedView ? model.segmentSpeedAt(previous, 1) : null;
        anchor.incoming = [metrics.left + handle[0] * metrics.width, toY(speedView ? model.clamp(handleSpeed, range[0], range[1]) : handle[1], range, metrics)];
      }
      const handle = segment[1];
      const handleSpeed = speedView ? model.segmentSpeedAt(segment, 0) : null;
      anchor.outgoing = [metrics.left + handle[0] * metrics.width, toY(speedView ? model.clamp(handleSpeed, range[0], range[1]) : handle[1], range, metrics)];
      return anchor;
    }).concat({
      index: segments.length,
      point: (() => {
        const point = segments[segments.length - 1][3];
        if (!speedView) return [metrics.left + metrics.width, toY(point[1], metrics.valueRange, metrics)];
        const speed = model.valueAndSpeed(state, 1)[1];
        return [metrics.left + metrics.width, toY(model.clamp(speed, metrics.speedRange[0], metrics.speedRange[1]), metrics.speedRange, metrics)];
      })(),
      incoming: (() => {
        const last = segments[segments.length - 1], handle = last[2];
        if (!speedView) return [metrics.left + handle[0] * metrics.width, toY(handle[1], metrics.valueRange, metrics)];
        const speed = model.segmentSpeedAt(last, 1);
        return [metrics.left + handle[0] * metrics.width, toY(model.clamp(speed, metrics.speedRange[0], metrics.speedRange[1]), metrics.speedRange, metrics)];
      })()
    }).filter((anchor) => !model.isShapeAnchor(state, anchor.index));
  }

  function drawHandles(ctx, metrics) {
    if (state.mode === 'bezier' && state.segments) {
      const anchors = multiBezierPositions(metrics);
      const snappingIndex = drag && drag.snapTangent ? drag.segmentIndex + (drag.pointIndex === 2 ? 1 : 0) : -1;
      if (anchors.length) {
        anchors.forEach((anchor) => {
          const highlighted = anchor.index === snappingIndex;
          const color = highlighted ? token('--btn-active-bg') : '#777777';
          const width = highlighted ? 1.7 : 1;
          if (anchor.incoming) drawLine(ctx, [anchor.point, anchor.incoming], color, width);
          if (anchor.outgoing) drawLine(ctx, [anchor.point, anchor.outgoing], color, width);
        });
      }
      anchors.forEach((anchor) => {
        drawAnchor(ctx, anchor.point[0], anchor.point[1]);
        if (anchor.index === snappingIndex) {
          ctx.beginPath();
          ctx.arc(anchor.point[0], anchor.point[1], 9, 0, Math.PI * 2);
          ctx.strokeStyle = token('--btn-active-bg');
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }
      });
      if (anchors.length) {
        anchors.forEach((anchor) => {
          if (anchor.incoming) drawHandle(ctx, anchor.incoming[0], anchor.incoming[1], false);
          if (anchor.outgoing) drawHandle(ctx, anchor.outgoing[0], anchor.outgoing[1], false);
        });
      }
      return;
    }
    const points = state.mode === 'bezier' ? bezierHandlePositions(metrics) : null;
    const start = points ? points.start : [metrics.left, toY(metrics.samples.values[0], metrics.valueRange, metrics)];
    const end = points ? points.end : [metrics.left + metrics.width, toY(metrics.samples.values[metrics.samples.values.length - 1], metrics.valueRange, metrics)];
    drawAnchor(ctx, start[0], start[1]);
    drawAnchor(ctx, end[0], end[1]);
    if (points) {
      drawLine(ctx, [points.start, points.first], '#777777', 1);
      drawLine(ctx, [points.end, points.second], '#777777', 1);
      drawHandle(ctx, points.first[0], points.first[1], false);
      drawHandle(ctx, points.second[0], points.second[1], false);
    } else if (state.mode === 'elastic') {
      const gain = state.elastic_gain;
      const control = [metrics.left + (0.5 / state.frequency) * metrics.width, toY(state.direction === 'in' ? gain : 1 - gain, metrics.valueRange, metrics)];
      const decay = [metrics.left + metrics.width, toY((state.decay - 1) / 19, metrics.valueRange, metrics)];
      drawLine(ctx, [[control[0], metrics.top + metrics.height], control], '#555555', 1);
      drawLine(ctx, [[decay[0], metrics.top + metrics.height], decay], '#555555', 1);
      drawHandle(ctx, control[0], control[1], true);
      drawHandle(ctx, decay[0], decay[1], true);
    } else {
      const c = state.restitution;
      const x = state.bounce_period * (c + 1) * 0.5;
      const point = [metrics.left + x * metrics.width, toY(1 - c * c, metrics.valueRange, metrics)];
      drawLine(ctx, [[point[0], metrics.top + metrics.height], point], '#555555', 1);
      drawHandle(ctx, point[0], point[1], false);
    }
  }

  function draw() {
    if (drawFrame) cancelAnimationFrame(drawFrame);
    drawFrame = 0;
    const ctx = syncCanvasSize();
    const metrics = graphMetrics();
    ctx.clearRect(0, 0, metrics.rect.width, metrics.rect.height);
    ctx.fillStyle = settings.themeBackground;
    ctx.fillRect(0, 0, metrics.rect.width, metrics.rect.height);
    drawGrid(ctx, metrics);
    const speedView = state.mode === 'bezier' && editView === 'speed';
    if (speedView) {
      drawSamples(ctx, metrics.samples.values, mixColor(settings.themeBackground, settings.themeColor, 0.2), 1.1, metrics, false);
      drawSamples(ctx, metrics.samples.speeds, settings.themeColor, 1.8, metrics, true);
    } else {
      if (settings.showSpeed) drawSamples(ctx, metrics.samples.speeds, mixColor(settings.themeBackground, settings.themeColor, settings.speedStrength), 1.2, metrics, true);
      drawSamples(ctx, metrics.samples.values, settings.themeColor, 1.7, metrics, false);
    }
    drawHandles(ctx, metrics);
    drawPlayhead();
  }

  function requestDraw() {
    if (!drawFrame) drawFrame = requestAnimationFrame(draw);
  }

  function sampleSeries(values, u) {
    const position = model.clamp(u, 0, 1) * (values.length - 1);
    const index = Math.floor(position);
    const fraction = position - index;
    return values[index] + (values[Math.min(values.length - 1, index + 1)] - values[index]) * fraction;
  }

  function previewPoint() {
    const metrics = graphMetrics();
    const speedView = state.mode === 'bezier' && editView === 'speed';
    const series = speedView ? metrics.samples.speeds : metrics.samples.values;
    const range = speedView ? metrics.speedRange : metrics.valueRange;
    const value = sampleSeries(series, preview.u);
    return {
      x: metrics.left + preview.u * metrics.width,
      y: toY(value, range, metrics),
      rect: metrics.rect
    };
  }

  function drawPlayhead() {
    const rect = ui.preview.getBoundingClientRect();
    const point = previewPoint();
    const visible = Number.isFinite(point.x) && Number.isFinite(point.y) && point.x >= 0 && point.x <= rect.width && point.y >= 0 && point.y <= rect.height;
    const key = visible
      ? [point.x, point.y, rect.width, rect.height, settings.themeColor, settings.themeHandles, window.devicePixelRatio || 1].join('|')
      : 'outside';
    if (preview.lastPaintKey === key) return;
    preview.lastPaintKey = key;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (ui.preview.width !== width || ui.preview.height !== height) {
      ui.preview.width = width;
      ui.preview.height = height;
    }
    const ctx = ui.preview.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    if (!visible) return;
    ctx.beginPath();
    ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = settings.themeHandles;
    ctx.fill();
    ctx.strokeStyle = settings.themeColor;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(point.x - 8, point.y);
    ctx.lineTo(point.x + 8, point.y);
    ctx.moveTo(point.x, point.y - 8);
    ctx.lineTo(point.x, point.y + 8);
    ctx.strokeStyle = 'rgba(220,220,220,.55)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  function updatePreviewButton() {
    ui.previewPlay.innerHTML = preview.playing
      ? '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z"/></svg>'
      : '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5 13 8l-9 5.5z"/></svg>';
    const label = i18n.t(preview.playing ? 'preview.pause' : 'preview.play');
    if (ui.previewPlay.title !== label) ui.previewPlay.title = label;
    if (ui.previewPlay.getAttribute('aria-label') !== label) ui.previewPlay.setAttribute('aria-label', label);
  }

  function startPreview() {
    preview.playing = true;
    preview.lastTime = null;
    updatePreviewButton();
    if (!preview.frame && !document.hidden) preview.frame = requestAnimationFrame(previewTick);
  }

  function pausePreview() {
    preview.playing = false;
    if (preview.frame) cancelAnimationFrame(preview.frame);
    preview.frame = 0;
    preview.lastTime = null;
    updatePreviewButton();
    drawPlayhead();
  }

  function previewTick(now) {
    preview.frame = 0;
    if (!preview.playing || document.hidden) { preview.lastTime = null; return; }
    const dt = preview.lastTime === null ? 0 : Math.min(0.1, Math.max(0, (now - preview.lastTime) / 1000));
    preview.lastTime = now;
    preview.time += dt;
    if (now - preview.lastDraw >= 33) {
      preview.u = model.clamp((preview.time % (preview.duration + 0.8) - 0.08) / preview.duration, 0, 1);
      preview.lastDraw = now;
      drawPlayhead();
    }
    if (preview.playing) preview.frame = requestAnimationFrame(previewTick);
  }

  function updateControlText() {
    const nextKey = [i18n.getLanguage(), settings.compact, state.direction].join('|');
    if (nextKey === controlTextKey) return;
    controlTextKey = nextKey;
    document.querySelectorAll('.mode-btn').forEach((button) => {
      const label = i18n.t(`mode.${button.dataset.mode}${settings.compact ? 'Compact' : ''}`);
      if (button.textContent !== label) button.textContent = label;
    });
    document.querySelectorAll('.view-btn').forEach((button) => {
      const label = i18n.t(`view.${button.dataset.view}`);
      if (button.textContent !== label) button.textContent = label;
    });
    const direction = i18n.t(`direction.${state.direction}`);
    if (ui.direction.textContent !== direction) ui.direction.textContent = direction;
  }

  function updateAnchorLayout() {
    const multi = state.mode === 'bezier' && Boolean(state.segments);
    if (!multi || editView !== 'value') closeAnchorMenu();
    const count = multi ? model.visibleAnchorCount(state) : 2;
    const extra = multi ? Math.min(180, Math.max(0, count - 4) * 36) : 0;
    setStyle(ui.app, '--anchor-extra-height', `${extra}px`);
    ui.app.classList.toggle('anchor-expanded', extra > 0);
    document.body.classList.toggle('anchor-expanded', extra > 0);
    ui.smoothAll.disabled = !multi || editView !== 'value' || count < 3;
    ui.snapHint.hidden = !(drag && drag.snapTangent);
    if (extra !== anchorWindowExtra) {
      const delta = extra - anchorWindowExtra;
      anchorWindowExtra = extra;
      if (window.__adobe_cep__ && window.CSInterface) {
        const maximum = Math.max(420, window.screen.availHeight - 60);
        const target = Math.round(Math.min(maximum, Math.max(420, window.innerHeight + delta)));
        if (target !== window.innerHeight) {
          try { new window.CSInterface().resizeContent(window.outerWidth, target); } catch (error) { /* docked panels use internal scrolling */ }
        }
      }
    }
  }

  function updateControls() {
    state = model.normalize(state);
    state.precision = settings.precision;
    updateAnchorLayout();
    updateControlText();
    document.querySelectorAll('.mode-btn').forEach((button) => {
      button.classList.toggle('active', button.dataset.mode === state.mode);
    });
    document.querySelectorAll('.view-btn').forEach((button) => button.classList.toggle('active', button.dataset.view === editView));
    ui.viewGroup.hidden = state.mode !== 'bezier';
    ui.direction.hidden = state.mode === 'bezier';
    ui.bezierPanel.hidden = state.mode !== 'bezier';
    ui.elasticPanel.hidden = state.mode !== 'elastic';
    ui.bouncePanel.hidden = state.mode !== 'bounce';
    setValue(ui.amp, Math.round(state.elastic_gain * 100));
    setValue(ui.freq, Math.round(state.frequency * 100));
    setValue(ui.cor, Math.round(state.restitution * 100));
    setValue(ui.period, Math.round(state.bounce_period * 100));
    setValue(ui.ampValue, state.elastic_gain.toFixed(2));
    setValue(ui.freqValue, state.frequency.toFixed(2));
    setValue(ui.corValue, state.restitution.toFixed(2));
    setValue(ui.periodValue, state.bounce_period.toFixed(2));
    const jsonText = stateText();
    if (ui.json.value !== jsonText) ui.json.value = jsonText;
    ui.speedInfo.hidden = true;
    ui.app.classList.toggle('compact-mode', settings.compact);
    ui.app.classList.toggle('preset-right', settings.location === 'right');
    ui.app.classList.toggle('preset-left', settings.location === 'left');
    ui.app.classList.toggle('preset-top', settings.location === 'top');
    ui.app.classList.toggle('preset-bottom', settings.location === 'bottom');
    ui.app.classList.toggle('reduce-motion', settings.reduceMotion);
    ui.multiModal.classList.toggle('reduce-motion', settings.reduceMotion);
    ui.toast.classList.toggle('reduce-motion', settings.reduceMotion);
    setStyle(ui.app, '--preset-box-size', `${settings.presetSize}px`);
    window.VeloTheme.apply(settings);
    const presetBasis = `${['right', 'left'].includes(settings.location)
      ? Math.max(112, settings.presetSize * 2 + 30) : Math.max(112, settings.presetSize + 24)}px`;
    if (ui.presetPanel.style.flexBasis !== presetBasis) ui.presetPanel.style.flexBasis = presetBasis;
    setValue(ui.location, settings.location);
    setValue(ui.language, settings.language);
    setChecked(ui.compact, settings.compact);
    setChecked(ui.speed, settings.showSpeed);
    setChecked(ui.autoInspect, settings.autoInspect);
    setChecked(ui.motion, settings.reduceMotion);
    setValue(ui.presetSize, settings.presetSize);
    setValue(ui.presetSizeValue, settings.presetSize);
    setValue(ui.themeColor, settings.themeColor);
    setValue(ui.themeBackground, settings.themeBackground);
    setValue(ui.themeHandles, settings.themeHandles);
    setValue(ui.gridX, settings.gridX);
    setValue(ui.gridY, settings.gridY);
    setValue(ui.precision, settings.precision);
    setValue(ui.precisionValue, settings.precision);
    setValue(ui.speedStrength, Math.round(settings.speedStrength * 100));
    setValue(ui.speedStrengthValue, `${Math.round(settings.speedStrength * 100)}%`);
    settleMultiPointMotion();
    requestDraw();
  }

  function updatePresetSelection() {
    document.querySelectorAll('.preset-item').forEach((item) => {
      item.classList.toggle('selected', item.dataset.id === selectedPresetId);
    });
  }

  function clearPresetSelection() {
    if (selectedPresetId === null) return;
    selectedPresetId = null;
    updatePresetSelection();
  }

  function thumbnailSamples(presetState) {
    const key = JSON.stringify(model.serializable(presetState));
    if (!thumbnailSampleCache.has(key)) thumbnailSampleCache.set(key, model.sample(presetState, 65).values);
    return thumbnailSampleCache.get(key);
  }

  function renderThumbnail(canvas, presetState) {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const rect = canvas.getBoundingClientRect();
    if (rect.width < 12 || rect.height < 12) return;
    const width = Math.max(1, Math.round(rect.width * dpr));
    const height = Math.max(1, Math.round(rect.height * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    const values = thumbnailSamples(presetState);
    const range = displayRange(values, [0, 1]);
    const points = values.map((value, index) => [6 + index / 64 * (rect.width - 12), 6 + (1 - (value - range[0]) / (range[1] - range[0])) * (rect.height - 26)]);
    drawLine(ctx, points, settings.themeColor, 1.4);
    [points[0], points[points.length - 1]].forEach((point) => {
      ctx.beginPath();
      ctx.arc(point[0], point[1], 2, 0, Math.PI * 2);
      ctx.fillStyle = settings.themeColor;
      ctx.fill();
    });
  }

  function refreshPresetThumbnails() {
    if (settings.compact) return;
    presetCanvases.forEach((presetState, canvas) => renderThumbnail(canvas, presetState));
  }

  function schedulePresetThumbnails() {
    if (thumbnailFrame) return;
    thumbnailFrame = requestAnimationFrame(() => {
      thumbnailFrame = 0;
      refreshPresetThumbnails();
    });
  }

  function reorderPreset(source, target, entries) {
    if (!source || source === target || !entries.some((entry) => entry.id === source) || !entries.some((entry) => entry.id === target)) return;
    presetOrder = entries.map((item) => item.id).filter((id) => id !== source);
    presetOrder.splice(presetOrder.indexOf(target), 0, source);
    storeArray('velo-ae-preset-order', presetOrder);
    renderPresetList();
  }

  let presetPointerDrag = null;
  let suppressPresetClick = false;

  function startPresetPointerDrag(event, entry, button, entries) {
    if (presetPointerDrag || event.button !== 0 || event.isPrimary === false) return;
    const pointerId = event.pointerId;
    let active = false;
    let targetId = null;
    presetPointerDrag = { pointerId, button };
    try { button.setPointerCapture(pointerId); } catch (error) { /* pointerup on the card remains available */ }

    function clearTargets() {
      ui.presetList.querySelectorAll('.drop-target').forEach((item) => item.classList.remove('drop-target'));
    }
    function finish(cancelled, pointEvent) {
      if (!presetPointerDrag || presetPointerDrag.pointerId !== pointerId) return;
      const target = pointEvent && document.elementFromPoint(pointEvent.clientX, pointEvent.clientY);
      const targetButton = target && target.closest('.preset-item');
      if (targetButton && ui.presetList.contains(targetButton)) targetId = targetButton.dataset.id;
      if (active && pointEvent) pointEvent.preventDefault();
      presetPointerDrag = null;
      button.classList.remove('dragging');
      clearTargets();
      try { if (button.hasPointerCapture(pointerId)) button.releasePointerCapture(pointerId); } catch (error) { /* capture is optional */ }
      if (!active) return;
      suppressPresetClick = true;
      setTimeout(() => { suppressPresetClick = false; }, 0);
      if (!cancelled) reorderPreset(entry.id, targetId, entries);
    }
    button.addEventListener('pointermove', (moveEvent) => {
      if (!presetPointerDrag || presetPointerDrag.pointerId !== pointerId) return;
      if (!active && Math.hypot(moveEvent.clientX - event.clientX, moveEvent.clientY - event.clientY) < 6) return;
      active = true;
      moveEvent.preventDefault();
      button.classList.add('dragging');
      const target = document.elementFromPoint(moveEvent.clientX, moveEvent.clientY);
      const targetButton = target && target.closest('.preset-item');
      targetId = targetButton && ui.presetList.contains(targetButton) ? targetButton.dataset.id : null;
      clearTargets();
      if (targetButton && targetId !== entry.id) targetButton.classList.add('drop-target');
    });
    button.addEventListener('pointerup', (upEvent) => finish(false, upEvent));
    button.addEventListener('pointercancel', () => finish(true));
    button.addEventListener('lostpointercapture', () => finish(true));
  }

  function renderPresetList() {
    if (thumbnailFrame) cancelAnimationFrame(thumbnailFrame);
    thumbnailFrame = 0;
    presetCanvases = new Map();
    const fragment = document.createDocumentFragment();
    const entries = Object.entries(model.PRESETS).filter(([, preset]) => preset.mode === state.mode).map(([id, preset]) => ({ id, label: i18n.presetLabel(id, preset.label), state: model.presetState(id) }));
    userPresets.filter((preset) => model.normalize(preset.state).mode === state.mode).forEach((preset) => entries.push({ id: preset.id, label: preset.label, state: preset.state }));
    entries.sort((a, b) => {
      const ai = presetOrder.indexOf(a.id), bi = presetOrder.indexOf(b.id);
      return (ai < 0 ? 10000 : ai) - (bi < 0 ? 10000 : bi);
    });
    entries.filter((entry) => entry.state.mode === state.mode && !hiddenPresets.includes(entry.id)).forEach((entry) => {
      const button = document.createElement('button');
      button.className = 'preset-item';
      button.type = 'button';
      button.title = entry.label;
      button.draggable = !window.CSInterface;
      button.dataset.id = entry.id;
      const canvas = document.createElement('canvas');
      const label = document.createElement('span');
      label.className = 'preset-label';
      label.textContent = entry.label;
      button.append(canvas, label);
      fragment.appendChild(button);
      presetCanvases.set(canvas, entry.state);
      button.addEventListener('click', (event) => {
        if (suppressPresetClick) {
          event.preventDefault();
          suppressPresetClick = false;
          return;
        }
        applyPreset(entry.id);
      });
      button.addEventListener('contextmenu', (event) => {
        event.preventDefault();
        contextPresetId = entry.id;
        ui.presetHide.hidden = !model.PRESETS[entry.id];
        ui.presetDelete.hidden = Boolean(model.PRESETS[entry.id]);
        ui.contextMenu.style.left = `${Math.min(event.clientX, window.innerWidth - 150)}px`;
        ui.contextMenu.style.top = `${Math.min(event.clientY, window.innerHeight - 90)}px`;
        ui.contextMenu.hidden = false;
      });
      if (window.CSInterface) button.addEventListener('pointerdown', (event) => startPresetPointerDrag(event, entry, button, entries));
      button.addEventListener('dragstart', (event) => {
        button.classList.add('dragging');
        event.dataTransfer.setData('text/x-velo-preset', entry.id);
      });
      button.addEventListener('dragend', () => button.classList.remove('dragging'));
      button.addEventListener('dragover', (event) => event.preventDefault());
      button.addEventListener('drop', (event) => {
        event.preventDefault();
        reorderPreset(event.dataTransfer.getData('text/x-velo-preset'), entry.id, entries);
      });
    });
    ui.presetList.replaceChildren(fragment);
    refreshPresetThumbnails();
    updatePresetSelection();
  }

  function applyPreset(id) {
    const builtin = model.PRESETS[id];
    if (builtin) state = model.presetState(id);
    else {
      const custom = userPresets.find((preset) => preset.id === id);
      if (!custom) return;
      state = model.normalize(custom.state);
    }
    selectedPresetId = id;
    updatePresetSelection();
    updateControls();
    const label = builtin ? { key: `preset.${id}` } : userPresets.find((preset) => preset.id === id).label;
    showStatus('status.preset', { label });
  }

  function hostCall(script) {
    return new Promise((resolve, reject) => {
      if (!window.CSInterface) { resolve(null); return; }
      const cs = new window.CSInterface();
      cs.evalScript(script, (result) => {
        if (result === undefined || result === null || result === '') { reject(translatedError('error.emptyHostResult')); return; }
        try { resolve(JSON.parse(result)); } catch (error) { reject(translatedError('error.invalidHostResponse', { detail: String(result).slice(0, 240) })); }
      });
    });
  }

  async function inspectHost() {
    try {
      const result = await hostCall('VeloAE.inspect()');
      if (!result) { showStatus('status.browserPreview'); return null; }
      if (!result.ok) throw result.error ? new Error(result.error) : translatedError('error.inspectFailed');
      const skipped = (result.skipped || []).length;
      const key = result.canApply
        ? (skipped ? 'status.inspectReadySkipped' : 'status.inspectReady')
        : (skipped ? 'status.inspectUnavailableSkipped' : 'status.inspectUnavailable');
      showStatus(key, { propertyCount: result.propertyCount, segmentCount: result.segmentCount, skipped }, !result.canApply);
      return result;
    } catch (error) {
      showError(error, 'error.inspect');
      return null;
    }
  }

  async function readHostCurve() {
    showStatus('status.reading');
    try {
      const result = await hostCall('VeloAE.readCurve()');
      if (!result) { showStatus('status.browserPreview'); return; }
      if (!result.ok) throw result.error ? new Error(result.error) : translatedError('error.invalidCurveJson');
      if (!result.curve || !model.validSegments(result.curve.segments)) throw translatedError('error.invalidCurveJson');
      state = model.normalize({ mode: 'bezier', segments: result.curve.segments });
      editView = 'value';
      speedViewRange = null;
      clearPresetSelection();
      updateControls();
      const params = { name: result.curve.name, keys: result.curve.keyTimes.length, deferred: result.deferredCount };
      const key = result.curve.adjusted ? 'status.readAdjusted' : (result.deferredCount ? 'status.readDeferred' : 'status.read');
      showStatus(key, params);
    } catch (error) {
      showError(error, 'error.read');
    }
  }

  async function applyHost() {
    try {
      if (settings.autoInspect) {
        const inspection = await inspectHost();
        if (inspection && !inspection.canApply) return;
      }
      const payload = { mode: state.mode, samples: model.sample(state, state.segments ? 1025 : 257).values };
      if (state.mode === 'bezier' && state.segments) {
        payload.segments = model.serializable(state).segments;
        payload.hiddenAnchors = state.hiddenAnchors || [];
      } else if (state.mode === 'bezier') {
        payload.points = [state.x1, state.y1, state.x2, state.y2];
      }
      const result = await hostCall(`VeloAE.apply(${JSON.stringify(payload)})`);
      if (!result) { showStatus('status.browserNoWrite'); return; }
      if (!result.ok) throw result.error ? new Error(result.error) : translatedError('error.applyFailed');
      if (result.shapePreservedSegments) {
        showStatus('status.appliedMixed', result);
      } else if (result.nativeSegments) {
        showStatus('status.appliedNative', result);
      } else {
        showStatus('status.applied', { segmentCount: result.segmentCount, createdKeys: result.createdKeys });
      }
    } catch (error) {
      showError(error, 'error.apply');
    }
  }

  function updateEaseBuffer() {
    const count = easeBuffer ? easeBuffer.groups.reduce((sum, group) => sum + group.keys.length, 0) : 0;
    const text = easeBuffer ? i18n.t('ease.count', { count, properties: easeBuffer.groups.length }) : i18n.t('ease.emptyCount');
    if (ui.easeCount.textContent !== text) ui.easeCount.textContent = text;
    ui.easePaste.disabled = !easeBuffer;
    ui.valuePaste.disabled = !easeBuffer;
    ui.easeClear.disabled = !easeBuffer;
    ui.easePass.setAttribute('aria-pressed', String(preservePassthrough));
  }

  async function copyEaseKeyframes() {
    try {
      const result = await hostCall('VeloAE.easeCopyCopy()');
      if (!result) { showStatus('status.browserPreview', {}, true); return; }
      if (!result.ok) throw result.error ? new Error(result.error) : translatedError('error.copyKeysFailed');
      easeBuffer = { format: 'velo-ae-easecopy', version: 1, groups: result.groups };
      updateEaseBuffer();
      showStatus('status.easeCopied', { count: result.keyCount });
    } catch (error) { showError(error, 'error.easeCopy'); }
  }

  async function pasteEaseKeyframes(kind) {
    if (!easeBuffer) { showStatus('status.easeEmpty', {}, true); return; }
    try {
      const payload = { kind, preserve: preservePassthrough, groups: easeBuffer.groups };
      const result = await hostCall(`VeloAE.easeCopyPaste(${JSON.stringify(payload)})`);
      if (!result) { showStatus('status.browserNoWrite', {}, true); return; }
      if (!result.ok) throw result.error ? new Error(result.error) : translatedError('error.pasteKeysFailed');
      showStatus(kind === 'ease' ? 'status.easePastedEase' : 'status.easePastedValue', { count: result.changed });
    } catch (error) { showError(error, 'error.easePaste'); }
  }

  function copyText(text) {
    const fallback = () => {
      const area = document.createElement('textarea');
      area.value = text;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      const copied = document.execCommand('copy');
      area.remove();
      return copied ? Promise.resolve() : Promise.reject(translatedError('error.copyFailed'));
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try { return navigator.clipboard.writeText(text).catch(fallback); } catch (error) { return fallback(); }
    }
    return fallback();
  }

  function readText() {
    const fallback = () => Promise.resolve(window.prompt(i18n.t('prompt.pasteJson'), ''));
    if (navigator.clipboard && navigator.clipboard.readText) {
      try { return navigator.clipboard.readText().catch(fallback); } catch (error) { return fallback(); }
    }
    return fallback();
  }

  function findHandle(x, y) {
    const metrics = graphMetrics();
    const candidates = [];
    if (state.mode === 'bezier' && state.segments) {
      multiBezierPositions(metrics).forEach((anchor) => {
        if (anchor.incoming) candidates.push({ kind: 'multiHandle', segmentIndex: anchor.index - 1, pointIndex: 2, x: anchor.incoming[0], y: anchor.incoming[1] });
        if (anchor.outgoing) candidates.push({ kind: 'multiHandle', segmentIndex: anchor.index, pointIndex: 1, x: anchor.outgoing[0], y: anchor.outgoing[1] });
        if (anchor.index > 0 && anchor.index < state.segments.length) candidates.push({ kind: 'multiAnchor', anchorIndex: anchor.index, x: anchor.point[0], y: anchor.point[1] });
      });
    } else if (state.mode === 'bezier') {
      const points = bezierHandlePositions(metrics);
      candidates.push({ kind: 'bezier1', x: points.first[0], y: points.first[1] });
      candidates.push({ kind: 'bezier2', x: points.second[0], y: points.second[1] });
    } else if (state.mode === 'elastic') {
      candidates.push({ kind: 'elastic_control', x: metrics.left + (0.5 / state.frequency) * metrics.width, y: toY(state.direction === 'in' ? state.elastic_gain : 1 - state.elastic_gain, metrics.valueRange, metrics) });
      candidates.push({ kind: 'elastic_decay', x: metrics.left + metrics.width, y: toY((state.decay - 1) / 19, metrics.valueRange, metrics) });
    } else {
      const c = state.restitution;
      candidates.push({ kind: 'bounce_control', x: metrics.left + state.bounce_period * (c + 1) * 0.5 * metrics.width, y: toY(1 - c * c, metrics.valueRange, metrics) });
    }
    let nearest = null;
    let distance = Infinity;
    candidates.forEach((candidate) => {
      const current = Math.hypot(x - candidate.x, y - candidate.y);
      if (current < distance) { nearest = candidate; distance = current; }
    });
    return distance <= 24 ? nearest : null;
  }

  function updateFromPointer(event) {
    if (event.type === 'mousemove' && performance.now() - lastPointerMoveTime < 400) return;
    if (event.type === 'pointermove') lastPointerMoveTime = performance.now();
    const pointerId = event.pointerId === undefined ? 1 : event.pointerId;
    if (!drag || pointerId !== drag.pointerId || event.isPrimary === false) return;
    const metrics = graphMetrics();
    const x = clamp01((event.clientX - metrics.rect.left - metrics.left) / metrics.width);
    const speedView = state.mode === 'bezier' && editView === 'speed';
    const range = speedView ? metrics.speedRange : metrics.valueRange;
    const pointerY = event.clientY - metrics.rect.top;
    const rawY = range[0] + (1 - (pointerY - metrics.top) / metrics.height) * (range[1] - range[0]);
    const y = speedView ? speedPointerValue(rawY, pointerY, metrics) : rawY;
    if (speedView) drag.snapZero = Math.abs(pointerY - toY(0, metrics.speedRange, metrics)) <= 8;
    drag.snapTangent = false;
    if (drag.kind === 'multiHandle') {
      const segment = state.segments[drag.segmentIndex], pointIndex = drag.pointIndex;
      const gap = Math.min(0.001, (segment[3][0] - segment[0][0]) * 0.01);
      const minimumX = pointIndex === 1 ? segment[0][0] + gap : segment[0][0];
      const maximumX = pointIndex === 2 ? segment[3][0] - gap : segment[3][0];
      const handleX = model.clamp(x, minimumX, maximumX);
      let handleY = y;
      if (speedView) {
        const anchor = pointIndex === 1 ? segment[0] : segment[3];
        handleY = anchor[1] + (pointIndex === 1 ? 1 : -1) * y * (handleX - anchor[0]) / 3;
      }
      const snapRange = speedView ? metrics.valueRange : range;
      const snap = model.snapHandleToTangent(state, drag.segmentIndex, pointIndex, handleX, model.clamp(handleY, -8, 8), metrics.width, metrics.height / (snapRange[1] - snapRange[0]));
      segment[pointIndex] = [model.clamp(snap.point[0], minimumX, maximumX), snap.point[1]];
      drag.snapTangent = snap.snapped;
      if (snap.snapped) {
        const anchorIndex = drag.segmentIndex + (drag.pointIndex === 2 ? 1 : 0);
        const anchor = multiBezierPositions(metrics).find((item) => item.index === anchorIndex);
        if (anchor) {
          ui.snapHint.style.left = `${model.clamp(anchor.point[0] + 12, 8, Math.max(8, metrics.rect.width - 104))}px`;
          ui.snapHint.style.top = `${model.clamp(anchor.point[1] - 30, 8, Math.max(8, metrics.rect.height - 30))}px`;
        }
      }
    } else if (drag.kind === 'multiAnchor') {
      const index = drag.anchorIndex;
      const previous = state.segments[index - 1], following = state.segments[index];
      const old = previous[3];
      const nextX = model.clamp(x, previous[0][0] + 0.001, following[3][0] - 0.001);
      const nextY = model.clamp(y, -8, 8);
      const dx = nextX - old[0], dy = nextY - old[1];
      previous[3] = [nextX, nextY];
      following[0] = [nextX, nextY];
      previous[2] = [model.clamp(previous[2][0] + dx, previous[0][0], nextX), model.clamp(previous[2][1] + dy, -8, 8)];
      following[1] = [model.clamp(following[1][0] + dx, nextX, following[3][0]), model.clamp(following[1][1] + dy, -8, 8)];
    } else if (drag.kind === 'bezier1' || drag.kind === 'bezier2') {
      const suffix = drag.kind === 'bezier1' ? '1' : '2';
      state['x' + suffix] = x;
      if (speedView && suffix === '1') state.y1 = model.clamp(y * x, -8, 8);
      else if (speedView) state.y2 = model.clamp(1 - y * (1 - x), -8, 8);
      else state['y' + suffix] = model.clamp(y, -8, 8);
    } else if (drag.kind === 'elastic_control') {
      state.frequency = 0.5 / Math.max(0.001, x);
      state.elastic_gain = state.direction === 'in' ? clamp01(y) : 1 - clamp01(y);
    } else if (drag.kind === 'elastic_decay') {
      state.decay = state.direction === 'in' ? 19 * (1 - clamp01(y)) + 1 : 19 * clamp01(y) + 1;
    } else {
      const restitution = Math.sqrt(1 - clamp01(y));
      state.restitution = model.clamp(restitution, 0, Math.sqrt(0.999));
      state.bounce_period = 2 * x / (state.restitution + 1);
    }
    clearPresetSelection();
    updateControls();
  }

  function startDrag(event) {
    if (drag || event.isPrimary === false || (event.button !== undefined && event.button !== 0)) return;
    const rect = ui.canvas.getBoundingClientRect();
    const handle = findHandle(event.clientX - rect.left, event.clientY - rect.top);
    if (!handle) return;
    event.preventDefault();
    drag = Object.assign({}, handle, { before: stateText(), pointerId: event.pointerId === undefined ? 1 : event.pointerId });
    if (state.mode === 'bezier' && editView === 'speed') {
      drag.speedRange = graphMetrics().speedRange.slice();
    }
    try { ui.canvas.setPointerCapture(drag.pointerId); } catch (error) { /* document-level move/up remains available */ }
    updateFromPointer(event);
  }

  const systemMotionPreference = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;

  function multiPointReducedMotion() {
    return settings.reduceMotion || Boolean(systemMotionPreference && systemMotionPreference.matches);
  }

  function finishMultiPointClose() {
    clearTimeout(multiPointCloseTimer);
    multiPointCloseTimer = 0;
    multiPointOpen = false;
    multiPointClosing = false;
    ui.multiModal.classList.remove('opening', 'visible', 'closing');
    ui.multiModal.hidden = true;
    const previous = multiPointFocusReturn;
    multiPointFocusReturn = null;
    const target = previous && previous.isConnected && previous !== document.body ? previous : document.querySelector('.mode-btn.active');
    if (target && target.isConnected) {
      try { target.focus({ preventScroll: true }); } catch (error) { target.focus(); }
    }
  }

  function settleMultiPointMotion() {
    if (multiPointClosing && multiPointReducedMotion()) finishMultiPointClose();
    if (toastClosing && multiPointReducedMotion()) finishToastClose();
  }

  if (systemMotionPreference) {
    if (systemMotionPreference.addEventListener) systemMotionPreference.addEventListener('change', settleMultiPointMotion);
    else if (systemMotionPreference.addListener) systemMotionPreference.addListener(settleMultiPointMotion);
  }

  function openMultiPointDialog() {
    if (multiPointOpen && !multiPointClosing) return;
    clearTimeout(multiPointCloseTimer);
    multiPointCloseTimer = 0;
    closeAnchorMenu();
    ui.contextMenu.hidden = true;
    if (!multiPointOpen) multiPointFocusReturn = document.activeElement;
    multiPointOpen = true;
    multiPointClosing = false;
    ui.multiMessage.textContent = i18n.t('dialog.multiPointMode');
    const wasHidden = ui.multiModal.hidden;
    ui.multiModal.hidden = false;
    ui.multiModal.classList.remove('closing');
    ui.multiModal.classList.add('opening');
    if (!multiPointReducedMotion() && wasHidden) void ui.multiModal.offsetWidth;
    ui.multiModal.classList.add('visible');
    ui.multiModal.classList.remove('opening');
    ui.multiSwitch.focus();
    showStatus('status.multiPointUnavailable');
  }

  function closeMultiPointDialog() {
    if (!multiPointOpen || multiPointClosing) return;
    multiPointClosing = true;
    clearTimeout(multiPointCloseTimer);
    ui.multiModal.classList.remove('opening', 'visible');
    if (multiPointReducedMotion()) {
      finishMultiPointClose();
      return;
    }
    ui.multiModal.classList.add('closing');
    multiPointCloseTimer = setTimeout(finishMultiPointClose, 160);
  }

  function switchToMultiPointValue() {
    if (!multiPointOpen || multiPointClosing) return;
    state.mode = 'bezier';
    editView = 'value';
    closeMultiPointDialog();
    clearPresetSelection();
    updateControls();
    renderPresetList();
    showStatus('status.multiPointReady');
  }

  ui.multiClose.addEventListener('click', closeMultiPointDialog);
  ui.multiCancel.addEventListener('click', closeMultiPointDialog);
  ui.multiSwitch.addEventListener('click', switchToMultiPointValue);
  ui.multiModal.addEventListener('click', (event) => { if (event.target === ui.multiModal) closeMultiPointDialog(); });

  function addPoint(event) {
    if (drag) return;
    if (state.mode !== 'bezier') {
      openMultiPointDialog();
      return;
    }
    const rect = ui.canvas.getBoundingClientRect();
    const x = event.clientX - rect.left, y = event.clientY - rect.top;
    if (findHandle(x, y)) return;
    const metrics = graphMetrics();
    const u = (x - metrics.left) / metrics.width;
    if (u <= 0 || u >= 1) return;
    event.preventDefault();
    const before = state.segments ? state.segments.length : 1;
    const next = model.splitAt(state, u);
    if ((next.segments ? next.segments.length : 1) === before) {
      if (before >= model.MAX_SEGMENTS) showStatus('status.pointLimit', { count: model.MAX_SEGMENTS + 1 }, true);
      else showStatus('status.pointTooClose');
      return;
    }
    state = next;
    clearPresetSelection();
    updateControls();
    showStatus('status.pointAdded', { count: model.visibleAnchorCount(state) });
  }

  function closeAnchorMenu() {
    ui.anchorMenu.hidden = true;
    contextAnchorIndex = null;
  }

  function applyAnchorAction(action) {
    if (contextAnchorIndex === null) return;
    const index = contextAnchorIndex;
    if (action === 'smooth') state = model.smoothAnchor(state, index);
    else state = model.removeAnchor(state, index, action === 'preserve');
    closeAnchorMenu();
    clearPresetSelection();
    updateControls();
    if (action === 'smooth') showStatus('status.pointSmoothed');
    else if (action === 'preserve') showStatus('status.pointPreserved', { count: model.visibleAnchorCount(state) });
    else showStatus('status.pointDeleted');
  }

  function deletePoint(event) {
    if (state.mode !== 'bezier' || !state.segments || editView !== 'value') return;
    const rect = ui.canvas.getBoundingClientRect();
    const x = event.clientX - rect.left, y = event.clientY - rect.top;
    const metrics = graphMetrics();
    const anchors = multiBezierPositions(metrics);
    let nearest = null, distance = Infinity;
    anchors.slice(1, -1).forEach((anchor) => {
      const current = Math.hypot(x - anchor.point[0], y - anchor.point[1]);
      if (current < distance) { nearest = anchor; distance = current; }
    });
    if (!nearest || distance > 14) { closeAnchorMenu(); return; }
    event.preventDefault();
    event.stopPropagation();
    if (event.shiftKey) {
      state = model.removeAnchor(state, nearest.index, true);
      closeAnchorMenu();
      clearPresetSelection();
      updateControls();
      showStatus('status.pointPreserved', { count: model.visibleAnchorCount(state) });
      return;
    }
    contextAnchorIndex = nearest.index;
    ui.anchorMenu.style.left = `${model.clamp(event.clientX, 8, Math.max(8, window.innerWidth - 188))}px`;
    ui.anchorMenu.style.top = `${model.clamp(event.clientY, 8, Math.max(8, window.innerHeight - 132))}px`;
    ui.anchorMenu.hidden = false;
  }

  ui.canvas.addEventListener('pointerdown', startDrag);
  ui.canvas.addEventListener('mousedown', startDrag);
  ui.canvas.addEventListener('dblclick', addPoint);
  ui.canvas.addEventListener('contextmenu', deletePoint);
  document.addEventListener('pointermove', updateFromPointer);
  document.addEventListener('mousemove', updateFromPointer);
  function finishDrag(cancel) {
    if (!drag) return;
    const before = drag.before;
    const pointerId = drag.pointerId;
    const initialSpeedRange = drag.speedRange;
    const tangentSnapped = Boolean(drag.snapTangent);
    const finalSpeedRange = initialSpeedRange && !cancel ? graphMetrics().speedRange.slice() : null;
    if (initialSpeedRange) speedViewRange = cancel ? initialSpeedRange.slice() : finalSpeedRange;
    drag = null;
    ui.snapHint.hidden = true;
    try { if (ui.canvas.hasPointerCapture(pointerId)) ui.canvas.releasePointerCapture(pointerId); } catch (error) { /* capture is optional */ }
    if (cancel) {
      const parsed = JSON.parse(before);
      state = model.normalize(parsed.state);
      updateControls();
      showStatus('status.dragCancelled');
    } else if (initialSpeedRange) {
      requestDraw();
    }
    if (!cancel && tangentSnapped) showStatus('status.tangentSnapped');
    if (initialSpeedRange) speedViewRangeStateKey = curveStateKey();
  }
  document.addEventListener('pointerup', () => finishDrag(false));
  document.addEventListener('pointercancel', () => finishDrag(true));
  document.addEventListener('mouseup', () => finishDrag(false));
  ui.canvas.addEventListener('lostpointercapture', () => finishDrag(false));
  function changeSettings(patch) {
    const next = Object.assign({}, patch);
    if (next.language !== undefined) next.language = i18n.normalizeLanguage(next.language);
    const languageChanged = next.language !== undefined && next.language !== settings.language;
    const refreshThumbnails = ['themeColor', 'presetSize', 'location'].some((key) => next[key] !== undefined && next[key] !== settings[key]);
    settings = Object.assign({}, settings, next);
    if (languageChanged) applyLanguage(settings.language);
    saveSettings();
    updateControls();
    if (languageChanged) renderPresetList();
    if (refreshThumbnails) schedulePresetThumbnails();
  }

  function setSettingsPage(page) {
    document.querySelectorAll('.settings-tab').forEach((button) => button.classList.toggle('active', button.dataset.settingsPage === page));
    document.querySelectorAll('.settings-page').forEach((section) => { section.hidden = section.dataset.page !== page; });
  }

  function orderedPresetIds(order, userEntries) {
    const result = [];
    const seen = new Set();
    const available = new Set(Object.keys(model.PRESETS));
    userEntries.forEach((entry) => available.add(entry.id));
    function add(id) {
      if (typeof id !== 'string' || seen.has(id) || !available.has(id)) return;
      seen.add(id);
      result.push(id);
    }
    (Array.isArray(order) ? order : []).forEach(add);
    Object.keys(model.PRESETS).forEach(add);
    userEntries.forEach((entry) => add(entry.id));
    return result;
  }

  function presetExportData(userEntries, hiddenIds, order) {
    const presets = Object.entries(model.PRESETS).map(([id, preset]) => ({
      id, label: preset.label, state: model.serializable(model.presetState(id))
    }));
    userEntries.forEach((entry) => presets.push({ id: entry.id, label: entry.label, state: entry.state }));
    const hiddenPresets = [];
    (Array.isArray(hiddenIds) ? hiddenIds : []).forEach((id) => {
      if (model.PRESETS[id] && !hiddenPresets.includes(id)) hiddenPresets.push(id);
    });
    return { format: 'velo-presets', version: 2, presets, hiddenPresets, presetOrder: orderedPresetIds(order, userEntries) };
  }

  function allocateImportedId(usedIds, index) {
    const base = `preset_user_${Date.now()}_${index}`;
    let id = base;
    let suffix = 1;
    while (usedIds.has(id)) {
      id = `${base}_${suffix}`;
      suffix += 1;
    }
    return id;
  }

  function parsePresetImport(data, existing, idFactory) {
    const complete = Boolean(data && !Array.isArray(data) && typeof data === 'object' && data.format === 'velo-presets' && data.version === 2);
    if (!complete && data && !Array.isArray(data) && typeof data === 'object' && data.version !== undefined && data.version !== 1) {
      throw translatedError('error.invalidPresetFile');
    }
    const entries = Array.isArray(data) ? data : data && typeof data === 'object' ? data.presets : null;
    if (!Array.isArray(entries)) throw translatedError('error.invalidPresetFile');
    if (complete && (!Array.isArray(data.hiddenPresets) || !Array.isArray(data.presetOrder))) throw translatedError('error.invalidPresetFile');

    const builtinIds = new Set(Object.keys(model.PRESETS));
    const fileIds = new Set();
    const foundBuiltins = new Set();
    const usedIds = new Set(existing.map((entry) => entry.id));
    builtinIds.forEach((id) => usedIds.add(id));
    const idMap = new Map();
    const imported = [];
    const makeId = idFactory || allocateImportedId;
    const numericFields = ['x1', 'y1', 'x2', 'y2', 'elastic_gain', 'frequency', 'decay', 'restitution', 'bounce_period', 'precision'];

    entries.forEach((entry, index) => {
      if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw translatedError('error.presetMissing', { index: index + 1 });
      const curve = complete ? entry.state : entry.state || entry.curve;
      const label = complete ? entry.label : entry.label || entry.name;
      if (!curve || typeof curve !== 'object' || Array.isArray(curve) || typeof label !== 'string' || !label.trim()) {
        throw translatedError('error.presetMissing', { index: index + 1 });
      }
      if (complete) {
        if (typeof entry.id !== 'string' || !entry.id || fileIds.has(entry.id)) throw translatedError('error.invalidPresetFile');
        if (!builtinIds.has(entry.id) && !/^preset_user_[A-Za-z0-9_-]+$/.test(entry.id)) throw translatedError('error.invalidPresetFile');
        if (curve.mode !== undefined && !['bezier', 'elastic', 'bounce'].includes(curve.mode)) throw translatedError('error.invalidPresetFile');
        if (curve.direction !== undefined && !['in', 'out', 'inout'].includes(curve.direction)) throw translatedError('error.invalidPresetFile');
        numericFields.forEach((key) => {
          if (curve[key] !== undefined && (typeof curve[key] !== 'number' || !isFinite(curve[key]))) throw translatedError('error.invalidPresetFile');
        });
        if (curve.segments !== undefined && !model.validSegments(curve.segments)) throw translatedError('error.invalidPresetFile');
        fileIds.add(entry.id);
      }
      const serialized = model.serializable(curve);
      if (complete && builtinIds.has(entry.id)) {
        foundBuiltins.add(entry.id);
        idMap.set(entry.id, entry.id);
        return;
      }
      let id = complete && !usedIds.has(entry.id) ? entry.id : makeId(usedIds, index);
      usedIds.add(id);
      imported.push({ id, label: label.slice(0, 80), state: serialized });
      if (complete) idMap.set(entry.id, id);
    });

    const userPresets = existing.concat(imported);
    if (userPresets.length > 32) throw translatedError('error.invalidPresetFile');
    if (!complete) return { userPresets, importedCount: imported.length, configuration: false };
    if (foundBuiltins.size !== builtinIds.size || Array.from(builtinIds).some((id) => !foundBuiltins.has(id))) throw translatedError('error.invalidPresetFile');

    const hiddenPresets = [];
    data.hiddenPresets.forEach((id) => {
      if (typeof id !== 'string' || !builtinIds.has(id)) throw translatedError('error.invalidPresetFile');
      if (!hiddenPresets.includes(id)) hiddenPresets.push(id);
    });
    const mappedOrder = data.presetOrder.map((id) => {
      if (typeof id !== 'string' || !idMap.has(id)) throw translatedError('error.invalidPresetFile');
      return idMap.get(id);
    });
    return {
      userPresets,
      hiddenPresets,
      presetOrder: orderedPresetIds(mappedOrder, userPresets),
      importedCount: imported.length,
      configuration: true
    };
  }

  async function exportPresets() {
    const data = presetExportData(userPresets, hiddenPresets, presetOrder);
    const payload = JSON.stringify(data, null, 2);
    ui.exportPresets.disabled = true;
    try {
      const result = await hostCall(`VeloAE.exportPresetFile(${JSON.stringify(payload)})`);
      if (result) {
        if (!result.ok) throw result.error ? new Error(result.error) : translatedError('error.exportFailed');
        if (result.cancelled) {
          showStatus('status.exportCancelled');
          return;
        }
        ui.exportPath.hidden = false;
        ui.exportPath.textContent = i18n.t('status.exportedAt', { path: result.path });
        ui.exportPath.title = result.path;
        showStatus('status.exportedAt', { path: result.path });
        return;
      }
      const url = URL.createObjectURL(new Blob([payload], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'Velo_Presets.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      showStatus('status.exported', { count: data.presets.length });
    } catch (error) {
      showError(error, 'error.export');
    } finally {
      ui.exportPresets.disabled = false;
    }
  }

  async function importPresets(file) {
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const next = parsePresetImport(data, userPresets);
      userPresets = next.userPresets;
      if (next.configuration) {
        hiddenPresets = next.hiddenPresets;
        presetOrder = next.presetOrder;
      }
      saveUserPresets();
      if (next.configuration) {
        storeArray('velo-ae-hidden-presets', hiddenPresets);
        storeArray('velo-ae-preset-order', presetOrder);
      }
      renderPresetList();
      showStatus('status.imported', { count: next.importedCount });
    } catch (error) {
      showError(error, 'error.import');
    } finally {
      ui.presetFile.value = '';
    }
  }

  function colorRgbToHex(rgb) {
    return `#${rgb.map((value) => Math.round(model.clamp(value, 0, 255)).toString(16).padStart(2, '0')).join('')}`;
  }

  function colorHexToRgb(value) {
    const match = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(value).trim());
    if (!match) return null;
    let text = match[1];
    if (text.length === 3) text = text.split('').map((character) => character + character).join('');
    return [0, 2, 4].map((offset) => parseInt(text.slice(offset, offset + 2), 16));
  }

  function colorRgbToHsv(rgb) {
    const values = rgb.map((value) => value / 255);
    const maximum = Math.max(...values), minimum = Math.min(...values), delta = maximum - minimum;
    let hue = 0;
    if (delta) {
      const [r, g, b] = values;
      if (maximum === r) hue = (g - b) / delta % 6;
      else if (maximum === g) hue = (b - r) / delta + 2;
      else hue = (r - g) / delta + 4;
      hue /= 6;
      if (hue < 0) hue += 1;
    }
    return { h: hue, s: maximum ? delta / maximum : 0, v: maximum };
  }

  function colorHsvToRgb(hsv) {
    const h = (hsv.h % 1) * 6, s = hsv.s, v = hsv.v;
    const index = Math.floor(h), fraction = h - index;
    const p = v * (1 - s), q = v * (1 - fraction * s), t = v * (1 - (1 - fraction) * s);
    const choices = [[v, t, p], [q, v, p], [p, v, t], [p, q, v], [t, p, v], [v, p, q]];
    return choices[index % 6].map((value) => Math.round(value * 255));
  }

  function drawColorField() {
    if (!colorEditor) return;
    const canvas = ui.colorField, ctx = canvas.getContext('2d');
    const hsv = colorEditor.hsv;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = `hsl(${hsv.h * 360},100%,50%)`;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const white = ctx.createLinearGradient(0, 0, canvas.width, 0);
    white.addColorStop(0, '#ffffff');
    white.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = white;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const black = ctx.createLinearGradient(0, 0, 0, canvas.height);
    black.addColorStop(0, 'rgba(0,0,0,0)');
    black.addColorStop(1, '#000000');
    ctx.fillStyle = black;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const x = hsv.s * canvas.width, y = (1 - hsv.v) * canvas.height;
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, Math.PI * 2);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, 7.5, 0, Math.PI * 2);
    ctx.strokeStyle = '#222222';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  function updateColorDraft(skipHexInput) {
    if (!colorEditor) return;
    const rgb = colorHsvToRgb(colorEditor.hsv);
    colorEditor.hex = colorRgbToHex(rgb);
    setValue(ui.colorHue, Math.round(colorEditor.hsv.h * 360));
    setValue(ui.colorR, rgb[0]);
    setValue(ui.colorG, rgb[1]);
    setValue(ui.colorB, rgb[2]);
    if (!skipHexInput) setValue(ui.colorHex, colorEditor.hex);
    ui.colorPreview.style.background = colorEditor.hex;
    ui.colorError.hidden = true;
    ui.colorApply.disabled = false;
    drawColorField();
    settings[colorEditor.target] = colorEditor.hex;
    updateControls();
    schedulePresetThumbnails();
  }

  function setColorDraft(value, skipHexInput) {
    if (!colorEditor) return false;
    const rgb = colorHexToRgb(value);
    if (!rgb) {
      ui.colorError.hidden = false;
      ui.colorApply.disabled = true;
      return false;
    }
    colorEditor.hsv = colorRgbToHsv(rgb);
    updateColorDraft(skipHexInput);
    return true;
  }

  function openColorPicker(target) {
    closeAnchorMenu();
    ui.contextMenu.hidden = true;
    colorEditor = { target, original: settings[target], hex: settings[target], hsv: colorRgbToHsv(colorHexToRgb(settings[target])), fieldDragging: false };
    ui.colorModal.hidden = false;
    ui.colorModal.classList.add('visible');
    updateColorDraft(false);
    setTimeout(() => { if (colorEditor) { ui.colorHex.focus(); ui.colorHex.select(); } }, 0);
  }

  function closeColorPicker(apply) {
    if (!colorEditor) return;
    const target = colorEditor.target, original = colorEditor.original, value = colorEditor.hex;
    const shouldApply = apply && !ui.colorApply.disabled;
    ui.colorModal.classList.remove('visible');
    ui.colorModal.hidden = true;
    colorEditor = null;
    if (shouldApply) {
      settings[target] = value;
      changeSettings({ [target]: value });
      showStatus('status.colorApplied', { value });
    } else {
      settings[target] = original;
      updateControls();
      schedulePresetThumbnails();
      showStatus('status.colorCancelled');
    }
    ui[target].focus();
  }

  function updateColorField(event) {
    if (!colorEditor) return;
    const rect = ui.colorField.getBoundingClientRect();
    colorEditor.hsv.s = clamp01((event.clientX - rect.left) / rect.width);
    colorEditor.hsv.v = 1 - clamp01((event.clientY - rect.top) / rect.height);
    updateColorDraft(false);
  }

  [ui.themeColor, ui.themeBackground, ui.themeHandles].forEach((input) => {
    input.addEventListener('click', (event) => {
      event.preventDefault();
      openColorPicker(input.id);
    });
  });
  ui.colorHue.addEventListener('input', () => {
    if (!colorEditor) return;
    colorEditor.hsv.h = model.clamp(Number(ui.colorHue.value) / 360, 0, 1);
    updateColorDraft(false);
  });
  ui.colorHex.addEventListener('input', () => setColorDraft(ui.colorHex.value, true));
  [ui.colorR, ui.colorG, ui.colorB].forEach((input) => {
    input.addEventListener('input', () => {
      if (!colorEditor) return;
      const rgb = [ui.colorR, ui.colorG, ui.colorB].map((field) => Number(field.value));
      if (rgb.every((value) => Number.isFinite(value))) setColorDraft(colorRgbToHex(rgb), false);
    });
  });
  document.querySelectorAll('.color-swatches button').forEach((button) => {
    button.addEventListener('click', () => setColorDraft(button.dataset.color, false));
  });
  ui.colorField.addEventListener('pointerdown', (event) => {
    if (!colorEditor) return;
    event.preventDefault();
    colorEditor.fieldDragging = true;
    try { ui.colorField.setPointerCapture(event.pointerId); } catch (error) { /* capture is optional */ }
    updateColorField(event);
  });
  ui.colorField.addEventListener('pointermove', (event) => {
    if (colorEditor && colorEditor.fieldDragging) updateColorField(event);
  });
  ui.colorField.addEventListener('pointerup', () => { if (colorEditor) colorEditor.fieldDragging = false; });
  ui.colorField.addEventListener('pointercancel', () => { if (colorEditor) colorEditor.fieldDragging = false; });
  ui.colorClose.addEventListener('click', () => closeColorPicker(false));
  ui.colorCancel.addEventListener('click', () => closeColorPicker(false));
  ui.colorApply.addEventListener('click', () => closeColorPicker(true));
  ui.colorModal.addEventListener('click', (event) => { if (event.target === ui.colorModal) closeColorPicker(false); });

  function openSettings() {
    closeAnchorMenu();
    ui.contextMenu.hidden = true;
    ui.modal.hidden = false;
    ui.modal.classList.add('visible');
  }
  function closeSettings() {
    flushSettings();
    ui.modal.classList.remove('visible');
    ui.modal.hidden = true;
  }
  document.addEventListener('keydown', (event) => {
    if (colorEditor && event.key === 'Tab') {
      const items = Array.from(ui.colorModal.querySelectorAll('button, input')).filter((item) => !item.disabled && item.type !== 'hidden');
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || !ui.colorModal.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
      return;
    }
    if (event.key === 'Escape' && colorEditor) {
      event.preventDefault();
      closeColorPicker(false);
      return;
    }
    if (multiPointOpen && event.key === 'Tab') {
      if (event.shiftKey && document.activeElement === ui.multiCancel) {
        event.preventDefault();
        ui.multiSwitch.focus();
      } else if (!event.shiftKey && document.activeElement === ui.multiSwitch) {
        event.preventDefault();
        ui.multiCancel.focus();
      }
      return;
    }
    if (event.key === 'Escape' && multiPointOpen) {
      event.preventDefault();
      closeMultiPointDialog();
      return;
    }
    if (event.key === 'Escape' && toastOpen && !toastClosing) {
      event.preventDefault();
      closeToast();
      return;
    }
    if (event.key !== 'Escape') return;
    if (drag) { event.preventDefault(); finishDrag(true); }
    else if (!ui.anchorMenu.hidden) { event.preventDefault(); closeAnchorMenu(); }
    else if (!ui.contextMenu.hidden) { event.preventDefault(); ui.contextMenu.hidden = true; }
    else if (ui.modal.classList.contains('visible')) closeSettings();
  });

  document.querySelectorAll('.mode-btn').forEach((button) => {
    button.addEventListener('click', () => {
      state.mode = button.dataset.mode;
      clearPresetSelection();
      updateControls();
      renderPresetList();
      showStatus('status.mode', { mode: i18n.t(`mode.${state.mode}`) });
    });
  });
  document.querySelectorAll('.view-btn').forEach((button) => {
    button.addEventListener('click', () => { editView = button.dataset.view; updateControls(); });
  });
  ui.direction.addEventListener('click', () => {
    const directions = ['out', 'in', 'inout'];
    state.direction = directions[(directions.indexOf(state.direction) + 1) % directions.length];
    clearPresetSelection();
    updateControls();
  });
  ui.settings.addEventListener('click', openSettings);
  ui.closeSettings.addEventListener('click', closeSettings);
  ui.modal.addEventListener('click', (event) => { if (event.target === ui.modal) closeSettings(); });
  document.querySelectorAll('.settings-tab').forEach((button) => button.addEventListener('click', () => setSettingsPage(button.dataset.settingsPage)));
  ui.language.addEventListener('change', () => changeSettings({ language: ui.language.value }));
  ui.location.addEventListener('change', () => changeSettings({ location: ui.location.value }));
  ui.compact.addEventListener('change', () => changeSettings({ compact: ui.compact.checked }));
  ui.speed.addEventListener('change', () => changeSettings({ showSpeed: ui.speed.checked }));
  ui.motion.addEventListener('change', () => {
    if (ui.motion.checked) {
      preview.resumeAfterMotion = preview.playing;
      pausePreview();
    } else if (preview.resumeAfterMotion) {
      preview.resumeAfterMotion = false;
      startPreview();
    }
    changeSettings({ reduceMotion: ui.motion.checked });
  });
  ui.presetSize.addEventListener('input', () => changeSettings({ presetSize: Number(ui.presetSize.value) }));
  ui.autoInspect.addEventListener('change', () => changeSettings({ autoInspect: ui.autoInspect.checked }));
  ui.themeColor.addEventListener('input', () => changeSettings({ themeColor: ui.themeColor.value }));
  ui.themeBackground.addEventListener('input', () => changeSettings({ themeBackground: ui.themeBackground.value }));
  ui.themeHandles.addEventListener('input', () => changeSettings({ themeHandles: ui.themeHandles.value }));
  document.querySelectorAll('.theme-choice').forEach((button) => button.addEventListener('click', () => changeSettings({ themeColor: button.dataset.color })));
  ui.gridX.addEventListener('input', () => changeSettings({ gridX: Math.round(model.clamp(Number(ui.gridX.value) || 4, 1, 20)) }));
  ui.gridY.addEventListener('input', () => changeSettings({ gridY: Math.round(model.clamp(Number(ui.gridY.value) || 4, 1, 20)) }));
  ui.precision.addEventListener('input', () => changeSettings({ precision: Math.round(Number(ui.precision.value)) }));
  ui.speedStrength.addEventListener('input', () => changeSettings({ speedStrength: Number(ui.speedStrength.value) / 100 }));
  ui.fitCurve.addEventListener('click', () => { speedViewRange = null; draw(); showStatus('status.fitted'); });
  ui.doneSettings.addEventListener('click', closeSettings);
  ui.importPresets.addEventListener('click', () => ui.presetFile.click());
  ui.presetFile.addEventListener('change', () => { if (ui.presetFile.files[0]) importPresets(ui.presetFile.files[0]); });
  ui.exportPresets.addEventListener('click', exportPresets);
  ui.restorePresets.addEventListener('click', () => { hiddenPresets = []; storeArray('velo-ae-hidden-presets', hiddenPresets); renderPresetList(); showStatus('status.hiddenRestored'); });
  ui.defaults.addEventListener('click', () => {
    settings = Object.assign({}, DEFAULT_SETTINGS);
    saveSettings();
    state = model.normalize({});
    selectedPresetId = 'smooth';
    editView = 'value';
    preview.time = 0;
    preview.u = 0;
    preview.duration = 2;
    ui.previewDuration.value = '2.0';
    pausePreview();
    startPreview();
    applyLanguage(settings.language);
    updateControls();
    renderPresetList();
    closeSettings();
    showStatus('status.defaultsRestored');
  });
  ui.presetHide.addEventListener('click', () => {
    if (contextPresetId && model.PRESETS[contextPresetId] && !hiddenPresets.includes(contextPresetId)) hiddenPresets.push(contextPresetId);
    storeArray('velo-ae-hidden-presets', hiddenPresets);
    ui.contextMenu.hidden = true;
    renderPresetList();
  });
  ui.presetDelete.addEventListener('click', () => {
    userPresets = userPresets.filter((preset) => preset.id !== contextPresetId);
    if (selectedPresetId === contextPresetId) selectedPresetId = null;
    saveUserPresets();
    ui.contextMenu.hidden = true;
    renderPresetList();
  });
  document.addEventListener('click', (event) => {
    if (!ui.contextMenu.contains(event.target)) ui.contextMenu.hidden = true;
    if (!ui.anchorMenu.contains(event.target)) closeAnchorMenu();
  });

  ui.amp.addEventListener('input', () => { state.elastic_gain = Number(ui.amp.value) / 100; clearPresetSelection(); updateControls(); });
  ui.freq.addEventListener('input', () => { state.frequency = Number(ui.freq.value) / 100; clearPresetSelection(); updateControls(); });
  ui.cor.addEventListener('input', () => { state.restitution = Number(ui.cor.value) / 100; clearPresetSelection(); updateControls(); });
  ui.period.addEventListener('input', () => { state.bounce_period = Number(ui.period.value) / 100; clearPresetSelection(); updateControls(); });

  ui.copy.addEventListener('click', async () => {
    try { await copyText(stateText()); showStatus('status.jsonCopied'); } catch (error) { showError(error, 'error.copy'); }
  });
  ui.paste.addEventListener('click', async () => {
    try {
      const text = await readText();
      const payload = JSON.parse(text);
      if (!payload || payload.format !== 'velo-ae-curve' || ![1, 2].includes(payload.version) || !payload.state) throw translatedError('error.invalidCurveJson');
      if (payload.state.segments && (payload.version !== 2 || !model.validSegments(payload.state.segments))) throw translatedError('error.invalidCurveJson');
      state = model.normalize(payload.state);
      clearPresetSelection();
      updateControls();
      showStatus('status.curvePasted');
    } catch (error) {
      showError(error, 'error.paste');
    }
  });
  ui.reset.addEventListener('click', () => {
    const mode = state.mode;
    state = model.normalize({ mode });
    selectedPresetId = ({ bezier: 'smooth', elastic: 'elastic_out', bounce: 'bounce_out' })[mode];
    updateControls();
    renderPresetList();
    showStatus('status.reset');
  });
  ui.reverse.addEventListener('click', () => {
    state = model.reverse(state);
    closeAnchorMenu();
    clearPresetSelection();
    updateControls();
    showStatus('status.reversed');
  });
  ui.smoothAll.addEventListener('click', () => {
    const result = model.smoothAllAnchors(state);
    state = result.state;
    closeAnchorMenu();
    clearPresetSelection();
    updateControls();
    showStatus('status.allSmoothed', { removed: result.removed, stops: result.stops });
  });
  ui.anchorSmooth.addEventListener('click', () => applyAnchorAction('smooth'));
  ui.anchorPreserveDelete.addEventListener('click', () => applyAnchorAction('preserve'));
  ui.anchorDelete.addEventListener('click', () => applyAnchorAction('delete'));
  ui.save.addEventListener('click', () => {
    const id = `preset_user_${Date.now()}`;
    const label = `User ${String(userPresets.length + 1).padStart(2, '0')}`;
    userPresets.push({ id, label, state: model.serializable(state) });
    if (userPresets.length > 32) userPresets = userPresets.slice(-32);
    selectedPresetId = id;
    saveUserPresets();
    renderPresetList();
    showStatus('status.saved', { label });
  });
  ui.easeCopy.addEventListener('click', copyEaseKeyframes);
  ui.easePaste.addEventListener('click', () => pasteEaseKeyframes('ease'));
  ui.valuePaste.addEventListener('click', () => pasteEaseKeyframes('value'));
  ui.easePass.addEventListener('click', () => { preservePassthrough = !preservePassthrough; updateEaseBuffer(); showStatus(preservePassthrough ? 'status.easePreserve' : 'status.easeOverwrite'); });
  ui.easeClear.addEventListener('click', () => { easeBuffer = null; updateEaseBuffer(); showStatus('status.easeCleared'); });
  ui.previewPlay.addEventListener('click', () => {
    preview.resumeAfterMotion = false;
    if (preview.playing) pausePreview();
    else startPreview();
  });
  ui.previewDuration.addEventListener('change', () => {
    const value = Number(ui.previewDuration.value);
    preview.duration = model.clamp(Number.isFinite(value) ? value : 2, 0.1, 60);
    ui.previewDuration.value = preview.duration.toFixed(1);
    preview.u = model.clamp((preview.time % (preview.duration + 0.8) - 0.08) / preview.duration, 0, 1);
    drawPlayhead();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      flushSettings();
      if (preview.frame) cancelAnimationFrame(preview.frame);
      preview.frame = 0;
      preview.lastTime = null;
    } else {
      schedulePresetThumbnails();
      if (preview.playing && !preview.frame) {
        preview.lastTime = null;
        preview.frame = requestAnimationFrame(previewTick);
      }
    }
  });
  ui.read.addEventListener('click', readHostCurve);
  ui.inspect.addEventListener('click', inspectHost);
  ui.apply.addEventListener('click', applyHost);

  ui.resizer.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    resizeDrag = { x: event.clientX, y: event.clientY, width: ui.presetPanel.getBoundingClientRect().width, height: ui.presetPanel.getBoundingClientRect().height };
    ui.resizer.setPointerCapture(event.pointerId);
  });
  ui.resizer.addEventListener('pointermove', (event) => {
    if (!resizeDrag) return;
    if (['right', 'left'].includes(settings.location)) {
      const delta = settings.location === 'right' ? resizeDrag.x - event.clientX : event.clientX - resizeDrag.x;
      const next = resizeDrag.width + delta;
      ui.presetPanel.style.flexBasis = `${model.clamp(next, 140, 360)}px`;
    } else {
      const delta = settings.location === 'top' ? event.clientY - resizeDrag.y : resizeDrag.y - event.clientY;
      const next = resizeDrag.height + delta;
      ui.presetPanel.style.flexBasis = `${model.clamp(next, 110, 320)}px`;
    }
    requestDraw();
    schedulePresetThumbnails();
  });
  ui.resizer.addEventListener('pointerup', () => { resizeDrag = null; draw(); schedulePresetThumbnails(); });
  ui.resizer.addEventListener('pointercancel', () => { resizeDrag = null; schedulePresetThumbnails(); });

  if (window.ResizeObserver) new ResizeObserver(requestDraw).observe(ui.wrapper);
  window.addEventListener('resize', () => { requestDraw(); schedulePresetThumbnails(); });
  window.addEventListener('pagehide', flushSettings);
  window.addEventListener('error', (event) => showError(event.error || event.message, 'error.runtime'));

  applyLanguage(settings.language);
  updateControls();
  renderPresetList();
  if (!settings.reduceMotion) startPreview();
}());
