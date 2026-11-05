(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.VeloModel = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var MODEL = 'continuous-v3';
  var TAU = Math.PI * 2;
  var DEFAULTS = {
    model: MODEL,
    mode: 'bezier',
    direction: 'out',
    x1: 0.42,
    y1: 0,
    x2: 0.58,
    y2: 1,
    elastic_gain: 0.5,
    frequency: 2,
    decay: 5,
    restitution: 0.5,
    bounce_period: 0.5,
    precision: 300
  };

  var PRESETS = {
    linear: { label: '线性', mode: 'bezier', points: [0, 0, 1, 1] },
    fast: { label: '快速', mode: 'bezier', points: [1 / 3, 2 / 3, 2 / 3, 1] },
    slow: { label: '缓慢', mode: 'bezier', points: [0.65, 0, 0.9, 0.3] },
    smooth: { label: '平滑', mode: 'bezier', points: [0.42, 0, 0.58, 1] },
    sine_in: { label: 'Sine In', mode: 'bezier', points: [0.47, 0, 0.745, 0.715] },
    sine_out: { label: 'Sine Out', mode: 'bezier', points: [0.39, 0.575, 0.565, 1] },
    sine_inout: { label: 'Sine I/O', mode: 'bezier', points: [0.445, 0.05, 0.55, 0.95] },
    quad_in: { label: 'Quad In', mode: 'bezier', points: [0.55, 0.085, 0.68, 0.53] },
    quad_out: { label: 'Quad Out', mode: 'bezier', points: [0.25, 0.46, 0.45, 0.94] },
    quad_inout: { label: 'Quad I/O', mode: 'bezier', points: [0.455, 0.03, 0.515, 0.955] },
    cubic_in: { label: 'Cubic In', mode: 'bezier', points: [0.55, 0.055, 0.675, 0.19] },
    cubic_out: { label: 'Cubic Out', mode: 'bezier', points: [0.215, 0.61, 0.355, 1] },
    cubic_inout: { label: 'Cubic I/O', mode: 'bezier', points: [0.645, 0.045, 0.645, 1] },
    quart_in: { label: 'Quart In', mode: 'bezier', points: [0.895, 0.03, 0.895, 0.22] },
    quart_out: { label: 'Quart Out', mode: 'bezier', points: [0.165, 0.84, 0.44, 1] },
    quart_inout: { label: 'Quart I/O', mode: 'bezier', points: [0.77, 0, 0.77, 1] },
    elastic_in: { label: 'Elastic In', mode: 'elastic', direction: 'in' },
    elastic_out: { label: 'Elastic Out', mode: 'elastic', direction: 'out' },
    elastic_inout: { label: 'Elastic I/O', mode: 'elastic', direction: 'inout' },
    bounce_in: { label: 'Bounce In', mode: 'bounce', direction: 'in' },
    bounce_out: { label: 'Bounce Out', mode: 'bounce', direction: 'out' },
    bounce_inout: { label: 'Bounce I/O', mode: 'bounce', direction: 'inout' }
  };

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, Number(value)));
  }

  function finite(value, fallback) {
    var number = Number(value);
    return isFinite(number) ? number : fallback;
  }

  function copy(object) {
    var result = {};
    Object.keys(object || {}).forEach(function (key) { result[key] = object[key]; });
    return result;
  }

  var MAX_SEGMENTS = 16;
  var MIN_ANCHOR_GAP = 0.002;
  function normalizedPoint(value, fallback) {
    if (!(value instanceof Array) || value.length < 2) return fallback.slice();
    return [finite(value[0], fallback[0]), finite(value[1], fallback[1])];
  }

  function normalizeSegments(input) {
    var source = input.slice(0, MAX_SEGMENTS);
    var count = source.length;
    if (!count) return null;
    var raw = source.map(function (segment, index) {
      segment = segment instanceof Array ? segment : [];
      var start = index / count, end = (index + 1) / count;
      return [
        normalizedPoint(segment[0], [start, 0]),
        normalizedPoint(segment[1], [start + 1 / (3 * count), 0]),
        normalizedPoint(segment[2], [start + 2 / (3 * count), 1]),
        normalizedPoint(segment[3], [end, 1])
      ];
    });
    var anchorX = raw.slice(0, -1).map(function (segment, index) {
      return clamp(segment[3][0], 0, 1);
    }).sort(function (a, b) { return a - b; });
    var anchors = [[0, 0]];
    for (var i = 0; i < count - 1; i += 1) {
      var minimum = anchors[i][0] + 0.001;
      var maximum = 1 - (count - i - 1) * 0.001;
      anchors.push([clamp(anchorX[i], minimum, maximum), clamp(raw[i][3][1], -8, 8)]);
    }
    anchors.push([1, 1]);
    var result = [];
    for (i = 0; i < count; i += 1) {
      var startPoint = anchors[i], endPoint = anchors[i + 1];
      result.push([
        startPoint.slice(),
        [clamp(raw[i][1][0], startPoint[0], endPoint[0]), clamp(raw[i][1][1], -8, 8)],
        [clamp(raw[i][2][0], startPoint[0], endPoint[0]), clamp(raw[i][2][1], -8, 8)],
        endPoint.slice()
      ]);
    }
    return result;
  }

  function normalizedHiddenAnchors(input, segments) {
    if (!(input instanceof Array)) return [];
    var result = [];
    input.forEach(function (value) {
      var x = Number(value);
      if (!isFinite(x)) return;
      for (var i = 0; i < segments.length - 1; i += 1) {
        if (Math.abs(segments[i][3][0] - x) <= 1e-12 && !result.some(function (existing) { return Math.abs(existing - x) <= 1e-12; })) {
          result.push(segments[i][3][0]);
          break;
        }
      }
    });
    return result.sort(function (a, b) { return a - b; });
  }

  function isShapeAnchor(input, index) {
    var state = normalize(input);
    if (!state.hiddenAnchors || index <= 0 || !state.segments || index >= state.segments.length) return false;
    var x = state.segments[index - 1][3][0];
    return state.hiddenAnchors.some(function (hidden) { return Math.abs(hidden - x) <= 1e-12; });
  }

  function visibleAnchorCount(input) {
    var state = normalize(input);
    return state.segments ? state.segments.length + 1 - (state.hiddenAnchors || []).length : 2;
  }

  function validSegments(input) {
    if (!(input instanceof Array) || input.length < 1 || input.length > MAX_SEGMENTS) return false;
    for (var i = 0; i < input.length; i += 1) {
      var segment = input[i];
      if (!(segment instanceof Array) || segment.length !== 4) return false;
      for (var j = 0; j < 4; j += 1) {
        if (!(segment[j] instanceof Array) || segment[j].length !== 2 || !numericPoint(segment[j])) return false;
      }
      if (segment[0][0] >= segment[3][0]) return false;
      if (segment[1][0] < segment[0][0] || segment[1][0] > segment[3][0] || segment[2][0] < segment[0][0] || segment[2][0] > segment[3][0]) return false;
      for (j = 0; j < 4; j += 1) if (segment[j][1] < -8 || segment[j][1] > 8) return false;
      if (i > 0 && (input[i - 1][3][0] !== segment[0][0] || input[i - 1][3][1] !== segment[0][1])) return false;
    }
    return input[0][0][0] === 0 && input[0][0][1] === 0 && input[input.length - 1][3][0] === 1 && input[input.length - 1][3][1] === 1;
  }

  function numericPoint(point) {
    return typeof point[0] === 'number' && isFinite(point[0]) && typeof point[1] === 'number' && isFinite(point[1]);
  }

  function normalize(input) {
    var state = copy(DEFAULTS);
    input = input || {};
    Object.keys(DEFAULTS).forEach(function (key) {
      if (input[key] !== undefined) state[key] = input[key];
    });
    state.model = MODEL;
    state.mode = /^(bezier|elastic|bounce)$/.test(state.mode) ? state.mode : 'bezier';
    state.direction = /^(in|out|inout)$/.test(state.direction) ? state.direction : 'out';
    state.x1 = clamp(finite(state.x1, DEFAULTS.x1), 0, 1);
    state.x2 = clamp(finite(state.x2, DEFAULTS.x2), 0, 1);
    state.y1 = clamp(finite(state.y1, DEFAULTS.y1), -8, 8);
    state.y2 = clamp(finite(state.y2, DEFAULTS.y2), -8, 8);
    state.elastic_gain = clamp(finite(state.elastic_gain, 0.5), 0, 1);
    state.frequency = clamp(finite(state.frequency, 2), 0.5, 10);
    state.decay = clamp(finite(state.decay, 5), 1, 20);
    state.restitution = clamp(finite(state.restitution, 0.5), 0, Math.sqrt(0.999));
    state.bounce_period = clamp(finite(state.bounce_period, 0.5), 0.0001, 2);
    state.precision = Math.round(clamp(finite(state.precision, 300), 50, 2000));
    if (input.segments instanceof Array && input.segments.length) {
      state.segments = normalizeSegments(input.segments);
      state.hiddenAnchors = normalizedHiddenAnchors(input.hiddenAnchors, state.segments);
      if (!state.hiddenAnchors.length) delete state.hiddenAnchors;
    }
    return state;
  }

  function presetState(id) {
    var preset = PRESETS[id];
    if (!preset) throw new Error('Unknown Velo preset: ' + id);
    var state = normalize({ mode: preset.mode, direction: preset.direction || 'out' });
    if (preset.points) {
      state.x1 = preset.points[0];
      state.y1 = preset.points[1];
      state.x2 = preset.points[2];
      state.y2 = preset.points[3];
    }
    return state;
  }

  function endpointSpeed(x1, y1, x2, y2, end) {
    if (end) {
      var oldX1 = x1, oldY1 = y1;
      x1 = 1 - x2; y1 = 1 - y2;
      x2 = 1 - oldX1; y2 = 1 - oldY1;
    }
    var xs = [3 * x1, 3 * x2 - 6 * x1, 1 + 3 * x1 - 3 * x2];
    var ys = [3 * y1, 3 * y2 - 6 * y1, 1 + 3 * y1 - 3 * y2];
    var ix = 0, iy = 0;
    while (ix < 2 && Math.abs(xs[ix]) <= 1e-12) ix += 1;
    while (iy < 2 && Math.abs(ys[iy]) <= 1e-12) iy += 1;
    if (iy > ix) return 0;
    if (iy < ix) return ys[iy] < 0 ? -Infinity : Infinity;
    return ys[iy] / xs[ix];
  }

  function bezierPair(u, state) {
    var x1 = state.x1, y1 = state.y1, x2 = state.x2, y2 = state.y2;
    u = clamp(u, 0, 1);
    if (u <= 0) return [0, endpointSpeed(x1, y1, x2, y2, false)];
    if (u >= 1) return [1, endpointSpeed(x1, y1, x2, y2, true)];
    var lo = 0, hi = 1, t = u;
    function xAt(value) {
      return 3 * (1 - value) * (1 - value) * value * x1 +
        3 * (1 - value) * value * value * x2 + value * value * value;
    }
    for (var i = 0; i < 16; i += 1) {
      var error = xAt(t) - u;
      if (Math.abs(error) < 1e-12) break;
      if (error < 0) lo = t; else hi = t;
      var dx = 3 * (1 - t) * (1 - t) * x1 + 6 * (1 - t) * t * (x2 - x1) + 3 * t * t * (1 - x2);
      var candidate = Math.abs(dx) > 1e-12 ? t - error / dx : (lo + hi) * 0.5;
      t = candidate > lo && candidate < hi ? candidate : (lo + hi) * 0.5;
    }
    for (var j = 0; j < 6; j += 1) {
      var x = xAt(t);
      if (Math.abs(x - u) < 1e-12) break;
      if (x < u) lo = t; else hi = t;
      t = (lo + hi) * 0.5;
    }
    var mt = 1 - t;
    var derivativeX = 3 * mt * mt * x1 + 6 * mt * t * (x2 - x1) + 3 * t * t * (1 - x2);
    var derivativeY = 3 * mt * mt * y1 + 6 * mt * t * (y2 - y1) + 3 * t * t * (1 - y2);
    var value = 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t * t * t;
    var speed = Math.abs(derivativeX) <= 1e-12 ? (derivativeY === 0 ? 0 : (derivativeY < 0 ? -Infinity : Infinity)) : derivativeY / derivativeX;
    return [value, speed];
  }

  function cubicPoint(segment, t) {
    var mt = 1 - t, mt2 = mt * mt, t2 = t * t;
    var p0 = segment[0], p1 = segment[1], p2 = segment[2], p3 = segment[3];
    return [
      mt2 * mt * p0[0] + 3 * mt2 * t * p1[0] + 3 * mt * t2 * p2[0] + t2 * t * p3[0],
      mt2 * mt * p0[1] + 3 * mt2 * t * p1[1] + 3 * mt * t2 * p2[1] + t2 * t * p3[1],
      3 * (mt2 * (p1[0] - p0[0]) + 2 * mt * t * (p2[0] - p1[0]) + t2 * (p3[0] - p2[0])),
      3 * (mt2 * (p1[1] - p0[1]) + 2 * mt * t * (p2[1] - p1[1]) + t2 * (p3[1] - p2[1]))
    ];
  }

  function cubicParameterAtX(segment, u) {
    if (u <= 0) return 0;
    if (u >= 1) return 1;
    var lo = 0, hi = 1, t = u;
    for (var i = 0; i < 16; i += 1) {
      var error = cubicPoint(segment, t)[0] - u;
      if (Math.abs(error) < 1e-12) break;
      if (error < 0) lo = t; else hi = t;
      var derivative = cubicPoint(segment, t)[2];
      var candidate = Math.abs(derivative) > 1e-12 ? t - error / derivative : (lo + hi) * 0.5;
      t = candidate > lo && candidate < hi ? candidate : (lo + hi) * 0.5;
    }
    for (var j = 0; j < 6; j += 1) {
      var x = cubicPoint(segment, t)[0];
      if (Math.abs(x - u) < 1e-12) break;
      if (x < u) lo = t; else hi = t;
      t = (lo + hi) * 0.5;
    }
    return t;
  }

  function derivativeSpeed(dx, dy) {
    if (Math.abs(dx) > 1e-12) return dy / dx;
    if (Math.abs(dy) <= 1e-12) return 0;
    return dy < 0 ? -Infinity : Infinity;
  }

  function multiBezierPair(u, segments) {
    u = clamp(u, 0, 1);
    var index = 0;
    while (index < segments.length - 1 && u > segments[index][3][0]) index += 1;
    var segment = segments[index];
    var point;
    if (u <= segment[0][0]) point = cubicPoint(segment, 0);
    else if (u >= segment[3][0]) point = cubicPoint(segment, 1);
    else point = cubicPoint(segment, cubicParameterAtX(segment, u));
    return [point[1], derivativeSpeed(point[2], point[3])];
  }

  function interpolatedPoint(a, b, t) {
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  }

  function segmentSpeedAt(segment, end) {
    var point = cubicPoint(segment, end ? 1 : 0);
    return derivativeSpeed(point[2], point[3]);
  }

  function splitAt(input, u) {
    var state = normalize(input);
    if (state.mode !== 'bezier') return state;
    var segments = state.segments || [[[0, 0], [state.x1, state.y1], [state.x2, state.y2], [1, 1]]];
    if (segments.length >= MAX_SEGMENTS || u <= 0.001 || u >= 0.999) return state;
    var index = 0;
    while (index < segments.length - 1 && u > segments[index][3][0]) index += 1;
    var segment = segments[index];
    for (var anchorIndex = 0; anchorIndex < segments.length - 1; anchorIndex += 1) {
      if (Math.abs(u - segments[anchorIndex][3][0]) < MIN_ANCHOR_GAP) return state;
    }
    var t = cubicParameterAtX(segment, u);
    var q0 = interpolatedPoint(segment[0], segment[1], t);
    var q1 = interpolatedPoint(segment[1], segment[2], t);
    var q2 = interpolatedPoint(segment[2], segment[3], t);
    var r0 = interpolatedPoint(q0, q1, t);
    var r1 = interpolatedPoint(q1, q2, t);
    var anchor = interpolatedPoint(r0, r1, t);
    var left = [segment[0].slice(), q0, r0, anchor.slice()];
    var right = [anchor.slice(), r1, q2, segment[3].slice()];
    var next = copy(state);
    next.segments = segments.slice(0, index).concat([left, right], segments.slice(index + 1));
    return normalize(next);
  }

  function cloneSegments(segments) {
    return segments.map(function (segment) {
      return segment.map(function (point) { return point.slice(); });
    });
  }

  function removeAnchor(input, index, preserveShape) {
    var state = normalize(input);
    if (!state.segments || index <= 0 || index >= state.segments.length) return state;
    var next = copy(state);
    if (preserveShape) {
      next.segments = cloneSegments(state.segments);
      next.hiddenAnchors = (state.hiddenAnchors || []).concat([state.segments[index - 1][3][0]]);
      return normalize(next);
    }
    var segments = cloneSegments(state.segments);
    var previous = segments[index - 1], following = segments[index];
    segments[index - 1] = [previous[0], previous[1], following[2], following[3]];
    segments.splice(index, 1);
    if (segments.length === 1) {
      next.x1 = segments[0][1][0];
      next.y1 = segments[0][1][1];
      next.x2 = segments[0][2][0];
      next.y2 = segments[0][2][1];
      delete next.segments;
      delete next.hiddenAnchors;
    } else {
      next.segments = segments;
    }
    return normalize(next);
  }

  function pointDistance(a, b) {
    return Math.hypot(b[0] - a[0], b[1] - a[1]);
  }

  function limitedTangentLength(anchor, direction, length, minimumX, maximumX) {
    var limit = length;
    if (Math.abs(direction[0]) > 1e-12) {
      var xLimit = (direction[0] > 0 ? maximumX - anchor[0] : minimumX - anchor[0]) / direction[0];
      limit = Math.min(limit, xLimit);
    }
    if (Math.abs(direction[1]) > 1e-12) {
      var yLimit = (direction[1] > 0 ? 8 - anchor[1] : -8 - anchor[1]) / direction[1];
      limit = Math.min(limit, yLimit);
    }
    return Math.max(0, limit);
  }

  function continuousTangent(segments, index) {
    var previous = segments[index - 1], following = segments[index];
    var anchor = previous[3];
    var incoming = [anchor[0] - previous[2][0], anchor[1] - previous[2][1]];
    var outgoing = [following[1][0] - anchor[0], following[1][1] - anchor[1]];
    var leftLength = Math.hypot(incoming[0], incoming[1]);
    var rightLength = Math.hypot(outgoing[0], outgoing[1]);
    var x = 0, y = 0;
    if (leftLength > 1e-12) { x += incoming[0] / leftLength; y += incoming[1] / leftLength; }
    if (rightLength > 1e-12) { x += outgoing[0] / rightLength; y += outgoing[1] / rightLength; }
    var length = Math.hypot(x, y);
    if (length <= 1e-12 || Math.abs(x) <= 1e-12) {
      x = following[3][0] - previous[0][0];
      y = following[3][1] - previous[0][1];
      if (Math.abs(x) <= 1e-12) { x = 1; y = 0; }
      length = Math.hypot(x, y);
    }
    return [x / length, y / length];
  }

  function smoothAnchor(input, index) {
    var state = normalize(input);
    if (!state.segments || index <= 0 || index >= state.segments.length) return state;
    var segments = cloneSegments(state.segments);
    var previous = segments[index - 1], following = segments[index];
    var anchor = previous[3];
    var direction = continuousTangent(segments, index);
    var leftLength = pointDistance(previous[2], anchor) || (anchor[0] - previous[0][0]) / 3;
    var rightLength = pointDistance(anchor, following[1]) || (following[3][0] - anchor[0]) / 3;
    leftLength = limitedTangentLength(anchor, [-direction[0], -direction[1]], leftLength, previous[0][0], anchor[0]);
    rightLength = limitedTangentLength(anchor, direction, rightLength, anchor[0], following[3][0]);
    previous[2] = [anchor[0] - direction[0] * leftLength, anchor[1] - direction[1] * leftLength];
    following[1] = [anchor[0] + direction[0] * rightLength, anchor[1] + direction[1] * rightLength];
    var next = copy(state);
    next.segments = segments;
    return normalize(next);
  }

  function snapHandleToTangent(input, segmentIndex, pointIndex, x, y, scaleX, scaleY) {
    var state = normalize(input);
    if (!state.segments || segmentIndex < 0 || segmentIndex >= state.segments.length || (pointIndex !== 1 && pointIndex !== 2)) {
      return { point: [x, y], snapped: false };
    }
    var segments = state.segments;
    var segment = segments[segmentIndex];
    var anchor = pointIndex === 1 ? segment[0] : segment[3];
    var minimumX = segment[0][0], maximumX = segment[3][0];
    var candidate = [clamp(finite(x, anchor[0]), minimumX, maximumX), clamp(finite(y, anchor[1]), -8, 8)];
    var opposite;
    if (pointIndex === 1 && segmentIndex > 0) opposite = segments[segmentIndex - 1][2];
    else if (pointIndex === 2 && segmentIndex < segments.length - 1) opposite = segments[segmentIndex + 1][1];
    if (!opposite) return { point: candidate, snapped: false };
    var direction = [anchor[0] - opposite[0], anchor[1] - opposite[1]];
    var directionLength = Math.hypot(direction[0], direction[1]);
    if (directionLength <= 1e-12) return { point: candidate, snapped: false };
    direction = [direction[0] / directionLength, direction[1] / directionLength];
    var vector = [candidate[0] - anchor[0], candidate[1] - anchor[1]];
    var projection = vector[0] * direction[0] + vector[1] * direction[1];
    if (projection <= 0) return { point: candidate, snapped: false };
    var residualX = vector[0] - direction[0] * projection;
    var residualY = vector[1] - direction[1] * projection;
    var pixelDistance = Math.hypot(residualX * Math.max(1e-12, Math.abs(finite(scaleX, 1))), residualY * Math.max(1e-12, Math.abs(finite(scaleY, 1))));
    if (pixelDistance > 8) return { point: candidate, snapped: false };
    var length = limitedTangentLength(anchor, direction, projection, minimumX, maximumX);
    if (length <= 1e-12) return { point: candidate, snapped: false };
    return {
      point: [anchor[0] + direction[0] * length, anchor[1] + direction[1] * length],
      snapped: true
    };
  }

  function curvatureRedundant(segments, index) {
    var previous = segments[index - 1], following = segments[index];
    var anchor = previous[3];
    var leftFirst = [3 * (anchor[0] - previous[2][0]), 3 * (anchor[1] - previous[2][1])];
    var rightFirst = [3 * (following[1][0] - anchor[0]), 3 * (following[1][1] - anchor[1])];
    var leftSpeed = derivativeSpeed(leftFirst[0], leftFirst[1]);
    var rightSpeed = derivativeSpeed(rightFirst[0], rightFirst[1]);
    if (leftSpeed !== rightSpeed && (!isFinite(leftSpeed) || !isFinite(rightSpeed) || Math.abs(leftSpeed - rightSpeed) > 1e-7 * Math.max(1, Math.abs(leftSpeed), Math.abs(rightSpeed)))) return false;
    function curvature(segment, first, second) {
      var denominator = Math.pow(first[0] * first[0] + first[1] * first[1], 1.5);
      return denominator > 1e-18 ? (first[0] * second[1] - first[1] * second[0]) / denominator : 0;
    }
    var leftSecond = [6 * (anchor[0] - 2 * previous[2][0] + previous[1][0]), 6 * (anchor[1] - 2 * previous[2][1] + previous[1][1])];
    var rightSecond = [6 * (following[2][0] - 2 * following[1][0] + anchor[0]), 6 * (following[2][1] - 2 * following[1][1] + anchor[1])];
    var leftCurvature = curvature(previous, leftFirst, leftSecond);
    var rightCurvature = curvature(following, rightFirst, rightSecond);
    return Math.abs(leftCurvature - rightCurvature) <= 1e-5 * Math.max(1, Math.abs(leftCurvature), Math.abs(rightCurvature));
  }

  function automaticMotionSlope(segments, index) {
    var previous = segments[index - 1], following = segments[index];
    var anchor = previous[3];
    var leftWidth = anchor[0] - previous[0][0], rightWidth = following[3][0] - anchor[0];
    var leftSlope = (anchor[1] - previous[0][1]) / leftWidth;
    var rightSlope = (following[3][1] - anchor[1]) / rightWidth;
    var leftSpeed = derivativeSpeed(anchor[0] - previous[2][0], anchor[1] - previous[2][1]);
    var rightSpeed = derivativeSpeed(following[1][0] - anchor[0], following[1][1] - anchor[1]);
    var stopped = leftSlope * rightSlope <= 0 || leftSpeed * rightSpeed < 0 ||
      (isFinite(leftSpeed) && Math.abs(leftSpeed) < 1e-8) || (isFinite(rightSpeed) && Math.abs(rightSpeed) < 1e-8);
    if (stopped) return { slope: 0, stopped: true };
    var w1 = 2 * rightWidth + leftWidth, w2 = rightWidth + 2 * leftWidth;
    return { slope: (w1 + w2) / (w1 / leftSlope + w2 / rightSlope), stopped: false };
  }

  function smoothAllAnchors(input) {
    var state = normalize(input);
    if (!state.segments) return { state: state, removed: 0, smoothed: 0, stops: 0 };
    var next = copy(state);
    next.segments = cloneSegments(state.segments);
    var hidden = (state.hiddenAnchors || []).slice();
    for (var i = 1; i < state.segments.length; i += 1) {
      if (isShapeAnchor(state, i)) continue;
      if (curvatureRedundant(state.segments, i)) hidden.push(state.segments[i - 1][3][0]);
    }
    next.hiddenAnchors = hidden;
    var stops = 0;
    for (i = 1; i < next.segments.length; i += 1) {
      var previous = next.segments[i - 1], following = next.segments[i];
      var anchor = previous[3];
      var motion = automaticMotionSlope(next.segments, i);
      var leftWidth = anchor[0] - previous[0][0], rightWidth = following[3][0] - anchor[0];
      previous[2] = [anchor[0] - leftWidth / 3, anchor[1] - leftWidth * motion.slope / 3];
      following[1] = [anchor[0] + rightWidth / 3, anchor[1] + rightWidth * motion.slope / 3];
      if (motion.stopped) stops += 1;
    }
    return {
      state: normalize(next),
      removed: hidden.length - (state.hiddenAnchors || []).length,
      smoothed: next.segments.length - 1,
      stops: stops
    };
  }

  function bezierBreakpoints(input) {
    var state = normalize(input);
    if (state.mode !== 'bezier' || !state.segments) return [];
    var events = [];
    for (var i = 0; i < state.segments.length - 1; i += 1) {
      var left = cubicPoint(state.segments[i], 1);
      var right = cubicPoint(state.segments[i + 1], 0);
      var a = derivativeSpeed(left[2], left[3]), b = derivativeSpeed(right[2], right[3]);
      if (a === b) continue;
      if (isFinite(a) && isFinite(b) && Math.abs(a - b) <= 1e-7 * Math.max(1, Math.abs(a), Math.abs(b))) continue;
      events.push(state.segments[i][3][0]);
    }
    return events;
  }

  function sampleTimes(input, count) {
    var state = normalize(input);
    count = Math.max(2, Math.min(498, Math.round(count || 257)));
    var times = [];
    for (var i = 0; i < count; i += 1) times.push(i / (count - 1));
    if (state.mode === 'bezier' && state.segments) {
      for (i = 0; i < state.segments.length - 1; i += 1) {
        if (!isShapeAnchor(state, i + 1)) times.push(state.segments[i][3][0]);
      }
    }
    times.sort(function (a, b) { return a - b; });
    return times.filter(function (time, index) { return index === 0 || Math.abs(time - times[index - 1]) > 1e-12; });
  }

  var peakCache = {};
  function elasticPeak(frequency, decay) {
    var key = frequency + ':' + decay;
    if (peakCache[key]) return peakCache[key];
    var w = TAU * frequency;
    var den = -Math.expm1(-decay);
    function raw(t) {
      var envelope = decay ? (Math.exp(-decay * t) - Math.exp(-decay)) / den : 1 - t;
      var slope = decay ? -decay * Math.exp(-decay * t) / den : -1;
      return [1 - envelope * Math.cos(w * t), -slope * Math.cos(w * t) + w * envelope * Math.sin(w * t)];
    }
    var lo = 0.25 / frequency, hi = Math.min(1, 0.5 / frequency);
    for (var i = 0; i < 44; i += 1) {
      var mid = (lo + hi) * 0.5;
      if (raw(mid)[1] > 0) lo = mid; else hi = mid;
    }
    var t = (lo + hi) * 0.5;
    peakCache[key] = [t, raw(t)[0]];
    return peakCache[key];
  }

  function elasticPair(t, state) {
    var f = state.frequency, d = state.decay, gain = state.elastic_gain;
    var peak = elasticPeak(f, d);
    var den = -Math.expm1(-d);
    var envelope = d ? (Math.exp(-d * t) - Math.exp(-d)) / den : 1 - t;
    var slope = d ? -d * Math.exp(-d * t) / den : -1;
    var w = TAU * f;
    var raw = 1 - envelope * Math.cos(w * t);
    var speed = -slope * Math.cos(w * t) + w * envelope * Math.sin(w * t);
    if (t < peak[0]) {
      var scale = (1 + gain * (peak[1] - 1)) / peak[1];
      return [raw * scale, speed * scale];
    }
    return [1 + gain * (raw - 1), gain * speed];
  }

  function bouncePair(t, state) {
    var c = state.restitution, d = state.bounce_period;
    if (c < 1e-10) {
      if (t >= d * 0.5) return [1, 0];
      return [4 * (t / d) * (t / d), 8 * t / (d * d)];
    }
    var settle = d * (1 / (1 - c) - 0.5);
    if (t >= settle) return [1, 0];
    var q = t / d;
    var arg = 1 - (1 - c) * (q + 0.5);
    if (arg <= 0) return [1, 0];
    var k = Math.max(0, Math.floor(Math.log(arg) / Math.log(c) + 1e-12));
    if (settle > 1) {
      var endArg = Math.max(1e-300, 1 - (1 - c) * (1 / d + 0.5));
      var endK = Math.max(0, Math.floor(Math.log(endArg) / Math.log(c)));
      var cutoff = d * ((1 - Math.pow(c, endK)) / (1 - c) - 0.5);
      if (t >= cutoff) return [1, 0];
    }
    var center = (1 - Math.pow(c, k)) / (1 - c) - 0.5 + Math.pow(c, k) * 0.5;
    var offset = q - center;
    return [1 + 4 * offset * offset - Math.pow(c, 2 * k), 8 * offset / d];
  }

  function directedPair(t, state) {
    var base = state.mode === 'elastic' ? elasticPair : bouncePair;
    if (state.direction === 'out') return base(t, state);
    var pair;
    if (state.direction === 'in') {
      pair = base(1 - t, state);
      return [1 - pair[0], pair[1]];
    }
    if (t < 0.5) {
      pair = base(1 - 2 * t, state);
      return [(1 - pair[0]) * 0.5, pair[1]];
    }
    pair = base(2 * t - 1, state);
    return [(1 + pair[0]) * 0.5, pair[1]];
  }

  function bounceBreakpoints(input, width) {
    var state = normalize(input);
    if (state.mode !== 'bounce') return [];
    var c = state.restitution, d = state.bounce_period;
    var events = [];
    if (c < 1e-10) {
      var single = d * 0.5;
      if (single > 0 && single < 1) events.push(single);
    } else {
      var settle = d * (1 / (1 - c) - 0.5);
      var cutoff;
      if (settle <= 1) {
        cutoff = settle;
      } else {
        var endArg = Math.max(1e-300, 1 - (1 - c) * (1 / d + 0.5));
        var endK = Math.max(0, Math.floor(Math.log(endArg) / Math.log(c)));
        cutoff = endK ? Math.min(1, d * ((1 - Math.pow(c, endK)) / (1 - c) - 0.5)) : 1;
      }
      var pixelU = width === undefined
        ? 2 / Math.max(128, state.precision)
        : 2 / Math.max(64, finite(width, 64) - 32);
      var amplitudeThreshold = Math.max(1e-3, pixelU * 1.5);
      for (var k = 1; k < 49; k += 1) {
        var amplitude = Math.pow(c, k);
        var t = d * ((1 - amplitude) / (1 - c) - 0.5);
        if (t >= cutoff - 1e-12 || t >= 1) break;
        if (t > 0) events.push(t);
        if (amplitude <= amplitudeThreshold || d * amplitude <= pixelU) break;
      }
      if (cutoff > 0 && cutoff < 1 && (!events.length || cutoff - events[events.length - 1] > pixelU)) events.push(cutoff);
    }
    if (state.direction === 'out') return events;
    function ascending(a, b) { return a - b; }
    if (state.direction === 'in') return events.map(function (t) { return 1 - t; }).sort(ascending);
    return events.map(function (t) { return (1 - t) * 0.5; })
      .concat(events.map(function (t) { return (1 + t) * 0.5; })).sort(ascending);
  }

  function pairAt(state, u) {
    u = clamp(u, 0, 1);
    if (state.mode === 'bezier') return state.segments ? multiBezierPair(u, state.segments) : bezierPair(u, state);
    if (u <= 0) return [0, directedPair(0, state)[1]];
    if (u >= 1) return [1, directedPair(1, state)[1]];
    return directedPair(u, state);
  }

  function valueAndSpeed(state, u) {
    return pairAt(normalize(state), u);
  }

  function sample(state, count) {
    state = normalize(state);
    count = Math.max(2, Math.round(count || 257));
    var values = [], speeds = [];
    for (var i = 0; i < count; i += 1) {
      var pair = pairAt(state, i / (count - 1));
      values.push(pair[0]);
      speeds.push(pair[1]);
    }
    values[0] = 0;
    values[count - 1] = 1;
    return { values: values, speeds: speeds };
  }

  function reverse(state) {
    state = normalize(state);
    if (state.mode === 'bezier' && state.segments) {
      var segments = state.segments.slice().reverse().map(function (segment) {
        return segment.slice().reverse().map(function (point) { return [1 - point[0], 1 - point[1]]; });
      });
      var multi = copy(state);
      multi.segments = segments;
      if (state.hiddenAnchors) multi.hiddenAnchors = state.hiddenAnchors.map(function (x) { return 1 - x; });
      return normalize(multi);
    }
    if (state.mode === 'bezier') {
      return normalize({
        mode: 'bezier',
        x1: 1 - state.x2,
        y1: 1 - state.y2,
        x2: 1 - state.x1,
        y2: 1 - state.y1
      });
    }
    var next = copy(state);
    next.direction = state.direction === 'in' ? 'out' : state.direction === 'out' ? 'in' : 'inout';
    return normalize(next);
  }

  function nativeEase(state, delta, duration) {
    state = normalize(state);
    if (state.mode !== 'bezier' || state.segments) throw new Error('Native AE temporal ease requires a single Bezier segment.');
    duration = Number(duration);
    if (!isFinite(duration) || duration <= 0) throw new Error('The selected keyframe segment must have a positive duration.');
    delta = Number(delta);
    if (!isFinite(delta)) throw new Error('The selected property must have a numeric value delta.');
    function endpoint(x, y, incoming) {
      var denominator = incoming ? 1 - x : x;
      var numerator = incoming ? 1 - y : y;
      return {
        speed: Math.abs(denominator) <= 1e-12 ? 0 : numerator / denominator * delta / duration,
        influence: clamp(denominator * 100, 0.1, 100)
      };
    }
    return { out: endpoint(state.x1, state.y1, false), in: endpoint(state.x2, state.y2, true) };
  }

  function serializable(state) {
    state = normalize(state);
    var result = {};
    Object.keys(DEFAULTS).forEach(function (key) { result[key] = state[key]; });
    if (state.segments) {
      result.segments = state.segments.map(function (segment) {
        return segment.map(function (point) { return point.slice(); });
      });
      if (state.hiddenAnchors) result.hiddenAnchors = state.hiddenAnchors.slice();
    }
    return result;
  }

  return {
    MODEL: MODEL,
    MAX_SEGMENTS: MAX_SEGMENTS,
    MIN_ANCHOR_GAP: MIN_ANCHOR_GAP,
    DEFAULTS: copy(DEFAULTS),
    PRESETS: PRESETS,
    clamp: clamp,
    normalize: normalize,
    presetState: presetState,
    valueAndSpeed: valueAndSpeed,
    bounceBreakpoints: bounceBreakpoints,
    bezierBreakpoints: bezierBreakpoints,
    splitAt: splitAt,
    segmentSpeedAt: segmentSpeedAt,
    removeAnchor: removeAnchor,
    smoothAnchor: smoothAnchor,
    snapHandleToTangent: snapHandleToTangent,
    smoothAllAnchors: smoothAllAnchors,
    isShapeAnchor: isShapeAnchor,
    visibleAnchorCount: visibleAnchorCount,
    sampleTimes: sampleTimes,
    validSegments: validSegments,
    sample: sample,
    reverse: reverse,
    nativeEase: nativeEase,
    serializable: serializable
  };
}));
