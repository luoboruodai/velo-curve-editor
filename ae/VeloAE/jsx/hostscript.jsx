var VeloAE = (function () {
    var VERSION = "1.2.1";

    function stringify(value) {
        var i, parts, key;
        if (value === null || value === undefined) return "null";
        if (typeof value === "number") return isFinite(value) ? String(value) : "null";
        if (typeof value === "boolean") return value ? "true" : "false";
        if (typeof value === "string") {
            return "\"" + value.replace(/\\/g, "\\\\").replace(/\"/g, "\\\"").replace(/\r/g, "\\r").replace(/\n/g, "\\n").replace(/\t/g, "\\t") + "\"";
        }
        if (value instanceof Array) {
            parts = [];
            for (i = 0; i < value.length; i++) parts.push(stringify(value[i]));
            return "[" + parts.join(",") + "]";
        }
        if (typeof value === "object") {
            parts = [];
            for (key in value) {
                if (value.hasOwnProperty(key)) parts.push(stringify(key) + ":" + stringify(value[key]));
            }
            return "{" + parts.join(",") + "}";
        }
        return "null";
    }

    function ok(data) {
        data = data || {};
        data.ok = true;
        return stringify(data);
    }

    function fail(error, data) {
        data = data || {};
        data.ok = false;
        data.error = String(error);
        return stringify(data);
    }

    function activeComp() {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) throw new Error("请先激活一个合成 / Activate a composition first.");
        return comp;
    }

    function numeric(value) {
        return typeof value === "number" && isFinite(value);
    }

    function numericArray(value) {
        if (!(value instanceof Array) || value.length < 1) return false;
        for (var i = 0; i < value.length; i++) if (!numeric(value[i])) return false;
        return true;
    }

    function valueKind(start, end) {
        if (numeric(start) && numeric(end)) return "scalar";
        if (numericArray(start) && numericArray(end) && start.length === end.length) return "array";
        return "unsupported";
    }

    function sortedSelectedKeys(prop) {
        var keys = prop.selectedKeys.slice(0);
        keys.sort(function (a, b) { return prop.keyTime(a) - prop.keyTime(b); });
        return keys;
    }

    function collectTargets() {
        var comp = activeComp();
        var selected = comp.selectedProperties;
        var targets = [], skipped = [];
        for (var i = 0; i < selected.length; i++) {
            var prop = selected[i];
            if (!(prop instanceof Property) || !prop.selectedKeys || prop.selectedKeys.length < 2) continue;
            var keys = sortedSelectedKeys(prop);
            if (keys.length < 2) continue;
            var start = prop.keyValue(keys[0]);
            var end = prop.keyValue(keys[keys.length - 1]);
            var kind = valueKind(start, end);
            if (kind === "unsupported") {
                skipped.push({ property: prop.name, reason: "仅支持数值标量和等长数值数组；Shape/蒙版路径暂不写入。" });
                continue;
            }
            var contiguous = true;
            for (var j = 0; j < keys.length - 1; j++) {
                if (keys[j + 1] !== keys[j] + 1 || prop.keyTime(keys[j + 1]) <= prop.keyTime(keys[j])) contiguous = false;
            }
            if (!contiguous) {
                skipped.push({ property: prop.name, reason: "请选择时间上相邻的关键帧，不要在选区中跳过中间关键帧。" });
                continue;
            }
            targets.push({ property: prop, keys: keys, kind: kind, name: prop.name });
        }
        return { comp: comp, targets: targets, skipped: skipped };
    }

    function ping() {
        try {
            var project = app.project;
            var item = project.activeItem;
            return ok({
                engine: "VeloAE/" + VERSION,
                HOSTEXISTS: true,
                RESULT: "READY",
                AEVERSION: app.version,
                PROJECT: project && project.file ? project.file.fsName : "",
                NUMITEMS: project ? project.numItems : 0,
                activeItem: item ? item.name : ""
            });
        } catch (error) {
            return fail(error);
        }
    }

    function inspect() {
        try {
            var selection = collectTargets();
            var properties = [];
            var segments = 0;
            for (var i = 0; i < selection.targets.length; i++) {
                var target = selection.targets[i];
                var count = target.keys.length - 1;
                segments += count;
                properties.push({ name: target.name, keys: target.keys.length, segments: count, kind: target.kind });
            }
            return ok({
                engine: "VeloAE/" + VERSION,
                aeVersion: app.version,
                comp: selection.comp.name,
                canApply: selection.targets.length > 0,
                properties: properties,
                propertyCount: properties.length,
                segmentCount: segments,
                skipped: selection.skipped
            });
        } catch (error) {
            return fail(error);
        }
    }

    function dimensionDelta(start, end, dimension) {
        return typeof start === "number" ? end - start : end[dimension] - start[dimension];
    }

    function importedHandle(ease, x, y, width, delta, duration, incoming) {
        var influence = ease.influence / 100;
        if (!numeric(influence) || influence < 0 || influence > 1 || !numeric(ease.speed) || Math.abs(delta) <= 0.000000000001 || duration <= 0) {
            return [x + (incoming ? -1 : 1) * width / 3, y];
        }
        var offset = ease.speed * duration / delta * influence;
        if (incoming) return [x - influence * width, y - offset];
        return [x + influence * width, y + offset];
    }

    function importedSegment(prop, first, second, startTime, endTime) {
        var start = prop.keyValue(first), end = prop.keyValue(second);
        var dimensions = typeof start === "number" ? 1 : start.length;
        if (endTime <= startTime || (typeof end === "number" ? dimensions !== 1 : !(end instanceof Array) || end.length !== dimensions)) return { error: "关键帧数值维度无效。" };
        var width = endTime - startTime;
        if (prop.keyOutInterpolationType(first) === KeyframeInterpolationType.HOLD || prop.keyInInterpolationType(second) === KeyframeInterpolationType.HOLD) return { error: "Hold 关键帧不能表示为连续 Bezier 曲线。" };
        var linear = prop.keyOutInterpolationType(first) === KeyframeInterpolationType.LINEAR || prop.keyInInterpolationType(second) === KeyframeInterpolationType.LINEAR;
        var outgoing = prop.keyOutTemporalEase(first), incoming = prop.keyInTemporalEase(second);
        var reference = null, adjusted = false;
        for (var dimension = 0; dimension < dimensions; dimension++) {
            if ((outgoing.length !== 1 && outgoing.length !== dimensions) || (incoming.length !== 1 && incoming.length !== dimensions)) return { error: "关键帧缓动维度与数值不一致。" };
            var outEase = outgoing.length === 1 ? outgoing[0] : outgoing[dimension], inEase = incoming.length === 1 ? incoming[0] : incoming[dimension];
            var delta = dimensionDelta(start, end, dimension);
            var left = [0, 0], right = [1, 1];
            if (linear) {
                left = [1 / 3, 1 / 3];
                right = [2 / 3, 2 / 3];
            } else {
                left = importedHandle(outEase, 0, 0, width, delta, width, false);
                right = importedHandle(inEase, 1, 1, width, delta, width, true);
            }
            if (!numeric(left[0]) || !numeric(left[1]) || !numeric(right[0]) || !numeric(right[1])) return { error: "关键帧包含无法读取的非有限切线。" };
            if (Math.abs(left[1]) > 8 || Math.abs(right[1]) > 8) adjusted = true;
            var segment = [[0, 0], left, right, [1, 1]];
            if (Math.abs(delta) <= 0.000000000001) continue;
            if (!reference) reference = segment;
            else {
                for (var point = 1; point < 3; point++) {
                    if (Math.abs(reference[point][0] - segment[point][0]) > 0.000001 || Math.abs(reference[point][1] - segment[point][1]) > 0.000001) return { error: "各数值维度的归一化曲线不同，请逐个属性读取，不要压缩成一条曲线。" };
                }
            }
        }
        if (!reference) reference = [[0, 0], [1 / 3, 0], [2 / 3, 1], [1, 1]];
        return { points: reference, adjusted: adjusted };
    }

    function normalizedAnchorValues(prop, keys) {
        var first = prop.keyValue(keys[0]), last = prop.keyValue(keys[keys.length - 1]);
        var dimensions = typeof first === "number" ? 1 : first.length, result = [];
        for (var i = 0; i < keys.length; i++) {
            var value = prop.keyValue(keys[i]), ratio = null;
            for (var dimension = 0; dimension < dimensions; dimension++) {
                var delta = dimensionDelta(first, last, dimension), current;
                if (Math.abs(delta) <= 0.000000000001) {
                    if (dimensionDelta(first, value, dimension) !== 0) return { error: "起止值相同但中间值不同，无法在保持端点的情况下归一化。" };
                    continue;
                }
                current = dimensionDelta(first, value, dimension) / delta;
                if (ratio === null) ratio = current;
                else if (Math.abs(ratio - current) > 0.000001) return { error: "各数值维度的归一化关键帧值不同，请逐个属性读取。" };
            }
            if (ratio === null) ratio = i === keys.length - 1 ? 1 : 0;
            result.push(ratio);
        }
        return { values: result };
    }

    function readTargetCurve(target) {
        var prop = target.property, count = target.keys.length;
        var startTime = prop.keyTime(target.keys[0]), endTime = prop.keyTime(target.keys[count - 1]);
        var duration = endTime - startTime;
        if (!(duration > 0)) return { error: "所选关键帧的时间范围无效。" };
        var normalized = normalizedAnchorValues(prop, target.keys);
        if (normalized.error) return { error: normalized.error };
        var segments = [], times = [], values = [], adjusted = false;
        for (var i = 0; i < count; i++) {
            var index = target.keys[i];
            var value = prop.keyValue(index);
            if (valueKind(value, value) === "unsupported") return { error: "中间关键帧的数值维度不一致。" };
            times.push(prop.keyTime(index));
            values.push(value);
            if (i === count - 1) continue;
            var nextTime = prop.keyTime(target.keys[i + 1]);
            var result = importedSegment(prop, index, target.keys[i + 1], prop.keyTime(index), nextTime);
            if (result.error) return { error: result.error };
            var from = (times[i] - startTime) / duration, to = (nextTime - startTime) / duration;
            var y0 = normalized.values[i], y1 = normalized.values[i + 1], delta = y1 - y0, points = result.points;
            segments.push([[from, y0], [from + (to - from) * points[1][0], y0 + points[1][1] * delta], [from + (to - from) * points[2][0], y0 + points[2][1] * delta], [to, y1]]);
            adjusted = adjusted || result.adjusted;
        }
        return { name: target.name, kind: target.kind, dimensions: target.kind === "scalar" ? 1 : values[0].length, segments: segments, keyTimes: times, values: values, startTime: startTime, endTime: endTime, adjusted: adjusted };
    }

    function readCurve() {
        try {
            var selection = collectTargets(), skipped = selection.skipped.slice(0), curve = null, deferred = 0;
            for (var i = 0; i < selection.targets.length; i++) {
                var target = selection.targets[i];
                var result = readTargetCurve(target);
                if (result.error) skipped.push({ property: target.name, reason: result.error });
                else if (!curve) curve = result;
                else deferred++;
            }
            if (!curve) return fail(skipped.length ? skipped[0].reason : "没有可读取的 Bezier 曲线；请选择连续数值关键帧。", { skipped: skipped });
            return ok({ curve: curve, segments: curve.segments, propertyCount: selection.targets.length, deferredCount: deferred, skipped: skipped });
        } catch (error) {
            return fail("读取曲线失败：" + error, { line: error.line || 0 });
        }
    }

    function sampleAt(samples, u) {
        if (u <= 0) return samples[0];
        if (u >= 1) return samples[samples.length - 1];
        var position = u * (samples.length - 1);
        var index = Math.floor(position);
        var fraction = position - index;
        return samples[index] + (samples[index + 1] - samples[index]) * fraction;
    }

    function lerp(start, end, amount) {
        if (typeof start === "number") return start + (end - start) * amount;
        var result = [];
        for (var i = 0; i < start.length; i++) result.push(start[i] + (end[i] - start[i]) * amount);
        return result;
    }

    function keyAt(prop, time) {
        var index = prop.nearestKeyIndex(time);
        if (index < 1 || index > prop.numKeys || Math.abs(prop.keyTime(index) - time) > 0.0001) throw new Error("关键帧在写入过程中失效，请撤销后重试。");
        return index;
    }

    function easeFor(points, delta, duration, incoming) {
        var x = incoming ? points[2] : points[0];
        var y = incoming ? points[3] : points[1];
        var denominator = incoming ? 1 - x : x;
        var numerator = incoming ? 1 - y : y;
        var speed = Math.abs(denominator) <= 0.000000000001 ? 0 : numerator / denominator * delta / duration;
        var influence = Math.max(0.1, Math.min(100, denominator * 100));
        return new KeyframeEase(speed, influence);
    }

    function applyNative(target, startTime, endTime, points) {
        var prop = target.property;
        var startIndex = keyAt(prop, startTime);
        var endIndex = keyAt(prop, endTime);
        var startValue = prop.keyValue(startIndex);
        var endValue = prop.keyValue(endIndex);
        var duration = endTime - startTime;
        prop.setInterpolationTypeAtKey(startIndex, prop.keyInInterpolationType(startIndex), KeyframeInterpolationType.BEZIER);
        prop.setInterpolationTypeAtKey(endIndex, KeyframeInterpolationType.BEZIER, prop.keyOutInterpolationType(endIndex));
        prop.setTemporalEaseAtKey(startIndex, prop.keyInTemporalEase(startIndex), [easeFor(points, endValue - startValue, duration, false)]);
        prop.setTemporalEaseAtKey(endIndex, [easeFor(points, endValue - startValue, duration, true)], prop.keyOutTemporalEase(endIndex));
        prop.setSelectedAtKey(startIndex, true);
        prop.setSelectedAtKey(endIndex, true);
    }

    function hiddenAt(hidden, x) {
        for (var i = 0; i < hidden.length; i++) if (Math.abs(hidden[i] - x) <= 0.000000001) return true;
        return false;
    }

    function validNativeSegments(segments, hidden) {
        if (!(segments instanceof Array) || !segments.length || segments.length > 16 || !(hidden instanceof Array) || hidden.length >= segments.length) return false;
        if (segments[0][0][0] !== 0 || segments[0][0][1] !== 0 || segments[segments.length - 1][3][0] !== 1 || segments[segments.length - 1][3][1] !== 1) return false;
        for (var i = 0; i < segments.length; i++) {
            var segment = segments[i];
            if (!(segment instanceof Array) || segment.length !== 4) return false;
            for (var j = 0; j < 4; j++) {
                if (!(segment[j] instanceof Array) || segment[j].length !== 2 || !numeric(segment[j][0]) || !numeric(segment[j][1]) || Math.abs(segment[j][1]) > 8) return false;
                if (segment[j][0] < segment[0][0] || segment[j][0] > segment[3][0]) return false;
            }
            if (segment[0][0] >= segment[3][0]) return false;
            if (i && (Math.abs(segments[i - 1][3][0] - segment[0][0]) > 0.000000001 || Math.abs(segments[i - 1][3][1] - segment[0][1]) > 0.000000001)) return false;
        }
        for (i = 0; i < hidden.length; i++) {
            var found = false;
            if (!numeric(hidden[i]) || hidden[i] <= 0 || hidden[i] >= 1) return false;
            for (var j = 0; j < segments.length - 1; j++) if (Math.abs(segments[j][3][0] - hidden[i]) <= 0.000000001) found = true;
            if (!found) return false;
            for (j = i + 1; j < hidden.length; j++) if (Math.abs(hidden[i] - hidden[j]) <= 0.000000001) return false;
        }
        return true;
    }

    function multiPlan(target, payload, frameDuration) {
        var prop = target.property, segments = payload.segments, hidden = payload.hiddenAnchors;
        var startIndex = keyAt(prop, prop.keyTime(target.keys[0])), endIndex = keyAt(prop, prop.keyTime(target.keys[target.keys.length - 1]));
        var startTime = prop.keyTime(startIndex), endTime = prop.keyTime(endIndex), duration = endTime - startTime;
        if (!(duration > 0) || !(frameDuration > 0)) throw new Error("所选关键帧的时间范围无效。");
        var plan = {
            property: prop, startTime: startTime, endTime: endTime, duration: duration,
            startValue: prop.keyValue(startIndex), endValue: prop.keyValue(endIndex),
            firstInEase: prop.keyInTemporalEase(startIndex), lastOutEase: prop.keyOutTemporalEase(endIndex),
            firstInType: prop.keyInInterpolationType(startIndex), lastOutType: prop.keyOutInterpolationType(endIndex),
            beforeCount: prop.numKeys, anchors: [], spans: [], removeTimes: [], matched: 0
        };
        var sharedSpatial = target.kind === "array" && prop.isSpatial === true && prop.keyOutTemporalEase(startIndex).length === 1;
        var active = null;
        for (var i = 0; i < segments.length; i++) {
            if (!active) active = { first: i, from: segments[i][0][0], fromY: segments[i][0][1] };
            active.last = i;
            active.to = segments[i][3][0];
            active.toY = segments[i][3][1];
            if (!hiddenAt(hidden, active.to)) {
                active.baked = active.last > active.first;
                plan.spans.push(active);
                active = null;
            }
        }
        for (i = 0; i < plan.spans.length; i++) {
            var span = plan.spans[i], first = segments[span.first], last = segments[span.last];
            span.spatial = sharedSpatial && (first[1][1] < first[0][1] || last[3][1] < last[2][1]);
            span.baked = span.baked || span.spatial;
            if (!plan.anchors.length) plan.anchors.push({ point: first[0], incoming: null, outgoing: [first[1][0], first[1][1], 0, 0] });
            else plan.anchors[plan.anchors.length - 1].outgoing = [first[1][0], first[1][1], 0, 0];
            var anchor = { point: last[3], incoming: [0, 0, last[2][0], last[2][1]], outgoing: null };
            anchor.time = startTime + duration * anchor.point[0];
            anchor.frame = Math.round(anchor.time / frameDuration);
            if (plan.anchors.length && plan.anchors[plan.anchors.length - 1].frame === anchor.frame) throw new Error("锚点在 AE 帧精度下过近，请拉开点位后再应用。");
            if (span.baked && anchor.frame - plan.anchors[plan.anchors.length - 1].frame < 2) throw new Error("保形区段少于一帧，无法在不重建隐藏锚点的情况下保留形状。");
            plan.anchors.push(anchor);
        }
        plan.anchors[0].time = startTime;
        plan.anchors[0].frame = Math.round(startTime / frameDuration);
        for (i = 1; i < target.keys.length - 1; i++) {
            var time = prop.keyTime(target.keys[i]), keep = false;
            for (var j = 0; j < plan.anchors.length; j++) if (Math.abs(plan.anchors[j].time - time) <= 0.0001) keep = true;
            if (keep) plan.matched++;
            else plan.removeTimes.push(time);
        }
        for (i = 0; i < plan.anchors.length; i++) {
            time = plan.anchors[i].time;
            if (Math.abs(time - startTime) <= 0.0001 || Math.abs(time - endTime) <= 0.0001) plan.matched++;
        }
        return plan;
    }

    function easeSideFor(points, span, plan, incoming, easeCount) {
        var start = lerp(plan.startValue, plan.endValue, span.fromY), end = lerp(plan.startValue, plan.endValue, span.toY);
        var duration = plan.duration * (span.to - span.from), valueSpan = span.toY - span.fromY;
        var x = incoming ? points[2] : points[0], y = incoming ? points[3] : points[1];
        var localX = (x - span.from) / (span.to - span.from);
        var localY = Math.abs(valueSpan) <= 0.000000000001 ? (incoming ? 1 : 0) : (y - span.fromY) / valueSpan;
        var local = incoming ? [0, 0, localX, localY] : [localX, localY, 0, 0];
        var dimensions = typeof start === "number" ? 1 : start.length;
        if (easeCount < 1 || easeCount > dimensions) throw new Error("AE 返回的缓动组数与数值维度不兼容。");
        var result = [];
        for (var dimension = 0; dimension < dimensions; dimension++) result.push(easeFor(local, dimensionDelta(start, end, dimension), duration, incoming));
        return easeCount === 1 ? [result[0]] : result;
    }

    function sampleNativeSpan(plan, span, samples, frameDuration, hidden) {
        var prop = plan.property, startTime = plan.startTime + plan.duration * span.from, endTime = plan.startTime + plan.duration * span.to;
        var startIndex = keyAt(prop, startTime), endIndex = keyAt(prop, endTime), duration = endTime - startTime;
        var steps = Math.max(2, Math.ceil(duration / frameDuration)), capped = steps > 512;
        if (capped) steps = 512;
        prop.setInterpolationTypeAtKey(startIndex, prop.keyInInterpolationType(startIndex), KeyframeInterpolationType.LINEAR);
        var created = 0;
        for (var i = 1; i < steps; i++) {
            var fraction = i / steps, u = span.from + (span.to - span.from) * fraction;
            if (hiddenAt(hidden, u)) continue;
            var time = startTime + duration * fraction;
            prop.setValueAtTime(time, lerp(plan.startValue, plan.endValue, sampleAt(samples, u)));
            var index = keyAt(prop, time);
            prop.setInterpolationTypeAtKey(index, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR);
            prop.setSelectedAtKey(index, true);
            created++;
        }
        endIndex = keyAt(prop, endTime);
        prop.setInterpolationTypeAtKey(endIndex, KeyframeInterpolationType.LINEAR, prop.keyOutInterpolationType(endIndex));
        return { created: created, capped: capped };
    }

    function applyMulti(plan, payload, frameDuration) {
        var prop = plan.property, i, index;
        for (i = plan.removeTimes.length - 1; i >= 0; i--) prop.removeKey(keyAt(prop, plan.removeTimes[i]));
        for (i = 0; i < plan.anchors.length; i++) {
            var anchor = plan.anchors[i];
            prop.setValueAtTime(anchor.time, lerp(plan.startValue, plan.endValue, anchor.point[1]));
        }
        var created = 0, capped = 0, baked = 0, spatial = 0;
        for (i = 0; i < plan.spans.length; i++) {
            if (!plan.spans[i].baked) continue;
            var sampled = sampleNativeSpan(plan, plan.spans[i], payload.samples, frameDuration, payload.hiddenAnchors || []);
            created += sampled.created;
            capped += sampled.capped ? 1 : 0;
            baked++;
            if (plan.spans[i].spatial) spatial++;
        }
        for (i = 0; i < plan.anchors.length; i++) {
            anchor = plan.anchors[i];
            index = keyAt(prop, anchor.time);
            var incoming = i === 0 ? plan.firstInEase : easeSideFor(anchor.incoming, plan.spans[i - 1], plan, true, prop.keyInTemporalEase(index).length);
            var outgoing = i === plan.anchors.length - 1 ? plan.lastOutEase : easeSideFor(anchor.outgoing, plan.spans[i], plan, false, prop.keyOutTemporalEase(index).length);
            var inType = i === 0 ? plan.firstInType : KeyframeInterpolationType.BEZIER;
            var outType = i === plan.anchors.length - 1 ? plan.lastOutType : KeyframeInterpolationType.BEZIER;
            prop.setInterpolationTypeAtKey(index, inType, outType);
            prop.setTemporalEaseAtKey(index, incoming, outgoing);
            prop.setSelectedAtKey(index, true);
        }
        for (i = 0; i < plan.anchors.length; i++) prop.setSelectedAtKey(keyAt(prop, plan.anchors[i].time), true);
        created += plan.anchors.length - plan.matched;
        return { created: created, removed: plan.removeTimes.length, capped: capped, baked: baked, spatial: spatial, "native": plan.spans.length - baked, anchors: plan.anchors.length };
    }

    function applyBaked(target, startTime, endTime, samples, frameDuration, times) {
        var prop = target.property;
        var startIndex = keyAt(prop, startTime);
        var endIndex = keyAt(prop, endTime);
        var startValue = prop.keyValue(startIndex);
        var endValue = prop.keyValue(endIndex);
        var duration = endTime - startTime;
        var steps = times ? times.length - 1 : Math.max(2, Math.ceil(duration / frameDuration));
        var capped = steps > 512;
        if (capped) steps = 512;
        prop.setInterpolationTypeAtKey(startIndex, prop.keyInInterpolationType(startIndex), KeyframeInterpolationType.LINEAR);
        for (var i = 1; i < steps; i++) {
            var u = times ? times[i] : i / steps;
            var time = startTime + duration * u;
            var value = times ? samples[i] : sampleAt(samples, u);
            prop.setValueAtTime(time, lerp(startValue, endValue, value));
            var newIndex = keyAt(prop, time);
            prop.setInterpolationTypeAtKey(newIndex, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR);
            prop.setSelectedAtKey(newIndex, true);
        }
        endIndex = keyAt(prop, endTime);
        prop.setInterpolationTypeAtKey(endIndex, KeyframeInterpolationType.LINEAR, prop.keyOutInterpolationType(endIndex));
        prop.setSelectedAtKey(startIndex, true);
        prop.setSelectedAtKey(endIndex, true);
        return { created: steps - 1, capped: capped };
    }

    function validSamples(samples) {
        if (!(samples instanceof Array) || samples.length < 2 || samples.length > 4097) return false;
        for (var i = 0; i < samples.length; i++) if (!numeric(samples[i])) return false;
        return Math.abs(samples[0]) < 0.000001 && Math.abs(samples[samples.length - 1] - 1) < 0.000001;
    }

    function validTimes(times, samples) {
        if (!(times instanceof Array) || times.length < 2 || times.length > 513 || times.length !== samples.length) return false;
        if (times[0] !== 0 || times[times.length - 1] !== 1) return false;
        for (var i = 0; i < times.length; i++) if (!numeric(times[i]) || (i > 0 && times[i] <= times[i - 1])) return false;
        return true;
    }

    function validPoints(points) {
        if (!(points instanceof Array) || points.length !== 4) return false;
        for (var i = 0; i < 4; i++) if (!numeric(points[i])) return false;
        return points[0] >= 0 && points[0] <= 1 && points[2] >= 0 && points[2] <= 1;
    }

    function apply(payload) {
        var began = false;
        try {
            if (!payload || !/^(bezier|elastic|bounce)$/.test(payload.mode)) return fail("无效的曲线模式。");
            if (!validSamples(payload.samples)) return fail("曲线采样无效；请重置曲线后重试。");
            var nativeMulti = payload.mode === "bezier" && payload.segments !== undefined;
            var nativeBezier = payload.mode === "bezier" && payload.points !== undefined && !nativeMulti;
            if (nativeMulti && !validNativeSegments(payload.segments, payload.hiddenAnchors || [])) return fail("多段 Bezier 锚点或手柄无效。");
            if (nativeBezier && !validPoints(payload.points)) return fail("Bezier 手柄超出 AE 原生缓动范围。");
            if (payload.times !== undefined && (nativeMulti || nativeBezier || !validTimes(payload.times, payload.samples))) return fail("多段曲线时间采样无效。");
            var selection = collectTargets();
            if (!selection.targets.length) return fail("请在一个或多个数值属性上选择至少两个相邻关键帧。", { skipped: selection.skipped });
            var plans = [];
            if (nativeMulti) {
                for (var p = 0; p < selection.targets.length; p++) plans.push(multiPlan(selection.targets[p], payload, selection.comp.frameDuration));
            }
            app.beginUndoGroup("Velo AE — Apply " + payload.mode);
            began = true;
            var nativeSegments = 0, bakedSegments = 0, createdKeys = 0, removedKeys = 0, cappedSegments = 0, preservedSegments = 0, nativeAnchors = 0, methods = [];
            for (var i = 0; i < selection.targets.length; i++) {
                var target = selection.targets[i];
                if (nativeMulti) {
                    var multi = applyMulti(plans[i], payload, selection.comp.frameDuration);
                    nativeSegments += multi["native"];
                    bakedSegments += multi.baked;
                    preservedSegments += multi.baked;
                    createdKeys += multi.created;
                    removedKeys += multi.removed;
                    cappedSegments += multi.capped;
                    nativeAnchors += multi.anchors;
                    methods.push({ property: target.name, nativeSegments: multi["native"], bakedSegments: multi.baked, spatialSegments: multi.spatial, anchors: multi.anchors });
                    continue;
                }
                var nativeCount = 0, bakedCount = 0;
                for (var j = 0; j < target.keys.length - 1; j++) {
                    var startTime = target.property.keyTime(target.keys[j]);
                    var endTime = target.property.keyTime(target.keys[j + 1]);
                    if (nativeBezier && target.kind === "scalar") {
                        applyNative(target, startTime, endTime, payload.points);
                        nativeSegments++;
                        nativeCount++;
                    } else {
                        var baked = applyBaked(target, startTime, endTime, payload.samples, selection.comp.frameDuration, payload.times);
                        createdKeys += baked.created;
                        if (baked.capped) cappedSegments++;
                        bakedSegments++;
                        bakedCount++;
                    }
                }
                methods.push({ property: target.name, nativeSegments: nativeCount, bakedSegments: bakedCount });
            }
            app.endUndoGroup();
            began = false;
            return ok({
                engine: "VeloAE/" + VERSION,
                comp: selection.comp.name,
                propertyCount: selection.targets.length,
                segmentCount: nativeSegments + bakedSegments,
                nativeSegments: nativeSegments,
                bakedSegments: bakedSegments,
                shapePreservedSegments: preservedSegments,
                nativeAnchors: nativeAnchors,
                createdKeys: createdKeys,
                removedKeys: removedKeys,
                cappedSegments: cappedSegments,
                methods: methods,
                skipped: selection.skipped,
                message: "已应用 " + (nativeSegments + bakedSegments) + " 段曲线；可用一次撤销恢复。"
            });
        } catch (error) {
            if (began) {
                try { app.endUndoGroup(); } catch (endError) {}
            }
            return fail("写入失败：" + error + "。请在 AE 中检查状态，必要时执行一次撤销。", { line: error.line || 0 });
        }
    }

    function easeData(ease) {
        return { speed: ease.speed, influence: ease.influence };
    }

    function easeArrayData(eases) {
        var result = [];
        for (var i = 0; i < eases.length; i++) result.push(easeData(eases[i]));
        return result;
    }

    function easeTargets() {
        var comp = activeComp();
        var selected = comp.selectedProperties;
        var groups = [], skipped = [];
        for (var i = 0; i < selected.length; i++) {
            var prop = selected[i];
            if (!(prop instanceof Property) || !prop.selectedKeys || !prop.selectedKeys.length) continue;
            var indices = sortedSelectedKeys(prop);
            var first = prop.keyValue(indices[0]);
            var last = prop.keyValue(indices[indices.length - 1]);
            var kind = valueKind(first, last);
            if (kind === "unsupported") {
                skipped.push({ property: prop.name, reason: "EaseCopy 仅支持数值标量和等长数值数组。" });
                continue;
            }
            var keys = [];
            for (var j = 0; j < indices.length; j++) {
                var index = indices[j];
                keys.push({
                    index: index,
                    time: prop.keyTime(index),
                    value: prop.keyValue(index),
                    inEase: easeArrayData(prop.keyInTemporalEase(index)),
                    outEase: easeArrayData(prop.keyOutTemporalEase(index))
                });
            }
            groups.push({ name: prop.name, kind: kind, keys: keys, property: prop });
        }
        return { comp: comp, groups: groups, skipped: skipped };
    }

    function easeCopyCopy() {
        try {
            var selection = easeTargets();
            if (!selection.groups.length) return fail("请选择至少一个数值关键帧。", { skipped: selection.skipped });
            var count = 0, publicGroups = [];
            for (var i = 0; i < selection.groups.length; i++) {
                count += selection.groups[i].keys.length;
                publicGroups.push({ name: selection.groups[i].name, kind: selection.groups[i].kind, keys: selection.groups[i].keys });
            }
            return ok({ groups: publicGroups, keyCount: count, propertyCount: publicGroups.length, skipped: selection.skipped });
        } catch (error) { return fail("复制关键帧失败：" + error, { line: error.line || 0 }); }
    }

    function validEaseSide(side) {
        if (!(side instanceof Array) || !side.length || side.length > 16) return false;
        for (var i = 0; i < side.length; i++) {
            if (!side[i] || typeof side[i].speed !== "number" || !isFinite(side[i].speed) || typeof side[i].influence !== "number" || !isFinite(side[i].influence)) return false;
        }
        return true;
    }

    function validEaseGroups(groups, details) {
        if (!(groups instanceof Array) || groups.length < 1 || groups.length > 128) { details.reason = "groups container"; return false; }
        for (var i = 0; i < groups.length; i++) {
            var keys = groups[i] && groups[i].keys;
            if (!(keys instanceof Array) || !keys.length || keys.length > 4096) { details.reason = "keys container " + i; return false; }
            for (var j = 0; j < keys.length; j++) {
                var value = keys[j].value;
                var dimensions = 0;
                if (typeof value === "number" && isFinite(value)) dimensions = 1;
                else if (value instanceof Array && value.length) dimensions = value.length;
                if (!dimensions) { details.reason = "value dimensions " + i + "/" + j; return false; }
                if (!validEaseSide(keys[j].inEase)) { details.reason = "in ease " + i + "/" + j; return false; }
                if (!validEaseSide(keys[j].outEase)) { details.reason = "out ease " + i + "/" + j; return false; }
            }
        }
        return true;
    }

    function passthrough(prop, index) {
        if (index <= 1 || index >= prop.numKeys) return false;
        var incoming = prop.keyInTemporalEase(index), outgoing = prop.keyOutTemporalEase(index);
        for (var i = 0; i < incoming.length; i++) {
            var a = incoming[i].speed, b = outgoing[i].speed;
            if (Math.abs(a - b) > 0.00001 * Math.max(1, Math.abs(a), Math.abs(b))) return false;
        }
        return true;
    }

    function nativeEaseObjects(side, dimensions) {
        var result = [];
        for (var i = 0; i < dimensions; i++) {
            var item = side.length === 1 ? side[0] : side[i];
            result.push(new KeyframeEase(item.speed, Math.max(0.1, Math.min(100, item.influence))));
        }
        return result;
    }

    function pasteEaseSide(prop, index, incoming, side) {
        if (incoming) prop.setInterpolationTypeAtKey(index, KeyframeInterpolationType.BEZIER, prop.keyOutInterpolationType(index));
        else prop.setInterpolationTypeAtKey(index, prop.keyInInterpolationType(index), KeyframeInterpolationType.BEZIER);
        var current = incoming ? prop.keyOutTemporalEase(index) : prop.keyInTemporalEase(index);
        if (side.length !== 1 && side.length !== current.length) throw new Error("来源与目标缓动维度不一致。");
        if (incoming) prop.setTemporalEaseAtKey(index, nativeEaseObjects(side, current.length), current);
        else prop.setTemporalEaseAtKey(index, current, nativeEaseObjects(side, current.length));
    }

    function easeCopyPaste(payload) {
        var began = false;
        try {
            var validation = { reason: "" };
            if (!payload || !/^(ease|value)$/.test(payload.kind)) return fail("EaseCopy 缓冲区为空或数据无效。");
            if (!validEaseGroups(payload.groups, validation)) return fail("EaseCopy 缓冲区为空或数据无效：" + validation.reason);
            var selection = easeTargets();
            if (!selection.groups.length) return fail("请选择要粘贴的数值关键帧。", { skipped: selection.skipped });
            if (payload.groups.length !== 1 && payload.groups.length !== selection.groups.length) return fail("目标属性数量需与复制源相同，或使用单属性来源。");
            for (var i = 0; i < selection.groups.length; i++) {
                var target = selection.groups[i];
                var sourceGroup = payload.groups[payload.groups.length === 1 ? 0 : i];
                var sourceCount = sourceGroup.keys.length;
                if (target.keys.length % sourceCount) return fail("目标关键帧数量需为 " + sourceCount + " 个或其整数倍。", { property: target.name });
                if (payload.kind === "value") {
                    for (var v = 0; v < sourceGroup.keys.length; v++) {
                        var sourceValue = sourceGroup.keys[v].value;
                        if (valueKind(sourceValue, sourceValue) !== target.kind || (sourceValue instanceof Array && sourceValue.length !== target.keys[0].value.length)) return fail("来源与目标数值维度不一致：" + target.name);
                    }
                } else {
                    for (v = 0; v < sourceGroup.keys.length; v++) {
                        var targetIndex = target.keys[v % target.keys.length].index;
                        var inDimensions = target.property.keyInTemporalEase(targetIndex).length;
                        var outDimensions = target.property.keyOutTemporalEase(targetIndex).length;
                        if ((sourceGroup.keys[v].inEase.length !== 1 && sourceGroup.keys[v].inEase.length !== inDimensions) || (sourceGroup.keys[v].outEase.length !== 1 && sourceGroup.keys[v].outEase.length !== outDimensions)) return fail("来源与目标缓动维度不一致：" + target.name);
                    }
                }
            }
            app.beginUndoGroup("Velo AE — EaseCopy " + payload.kind);
            began = true;
            var changed = 0, protectedCount = 0;
            for (i = 0; i < selection.groups.length; i++) {
                target = selection.groups[i];
                var prop = target.property;
                var source = payload.groups[payload.groups.length === 1 ? 0 : i].keys;
                var targets = target.keys;
                var protectedKeys = {};
                if (payload.preserve) {
                    for (var p = 0; p < targets.length; p++) {
                        if (passthrough(prop, targets[p].index)) { protectedKeys[targets[p].index] = true; protectedCount++; }
                    }
                }
                if (payload.kind === "value") {
                    var originalEases = [];
                    for (v = 0; v < targets.length; v++) {
                        originalEases.push({ inEase: prop.keyInTemporalEase(targets[v].index), outEase: prop.keyOutTemporalEase(targets[v].index) });
                    }
                    for (v = 0; v < targets.length; v++) {
                        if (protectedKeys[targets[v].index]) continue;
                        prop.setValueAtKey(targets[v].index, source[v % source.length].value);
                        changed++;
                    }
                    for (v = 0; v < targets.length; v++) {
                        prop.setTemporalEaseAtKey(targets[v].index, originalEases[v].inEase, originalEases[v].outEase);
                    }
                } else if (targets.length === 1) {
                    if (!protectedKeys[targets[0].index]) {
                        pasteEaseSide(prop, targets[0].index, true, source[0].inEase);
                        pasteEaseSide(prop, targets[0].index, false, source[0].outEase);
                        changed += 2;
                    }
                } else {
                    for (var s = 0; s < targets.length - 1; s++) {
                        if (protectedKeys[targets[s].index] || protectedKeys[targets[s + 1].index]) continue;
                        pasteEaseSide(prop, targets[s].index, false, source[s % source.length].outEase);
                        pasteEaseSide(prop, targets[s + 1].index, true, source[(s + 1) % source.length].inEase);
                        changed += 2;
                    }
                }
            }
            app.endUndoGroup();
            began = false;
            return ok({ changed: changed, protectedCount: protectedCount, propertyCount: selection.groups.length, skipped: selection.skipped });
        } catch (error) {
            if (began) { try { app.endUndoGroup(); } catch (endError) {} }
            return fail("EaseCopy 写入失败：" + error + "。请检查状态，必要时执行一次撤销。", { line: error.line || 0 });
        }
    }

    function exportPresetFile(payload) {
        var file = null, opened = false;
        try {
            if (typeof payload !== "string" || payload.length < 2 || payload.length > 2000000) return fail("预设配置为空或过大。");
            var data = JSON.parse(payload);
            if (!data || data.format !== "velo-presets" || data.version !== 2 || !(data.presets instanceof Array)) return fail("预设配置格式无效。");
            file = File.saveDialog("导出 Velo 曲线预设 / Export Velo presets", "*.json");
            if (!file) return ok({ cancelled: true });
            if (!/\.json$/i.test(file.name)) file = new File(file.fsName + ".json");
            file.encoding = "UTF-8";
            if (!file.open("w")) return fail("无法打开所选文件进行写入。");
            opened = true;
            var written = file.write(payload);
            file.close();
            opened = false;
            if (!written) return fail("无法写入所选预设文件。");
            return ok({ cancelled: false, path: file.fsName });
        } catch (error) {
            if (file && opened) { try { file.close(); } catch (closeError) {} }
            return fail("导出预设失败：" + error, { line: error.line || 0 });
        }
    }

    return { ping: ping, inspect: inspect, readCurve: readCurve, apply: apply, exportPresetFile: exportPresetFile, easeCopyCopy: easeCopyCopy, easeCopyPaste: easeCopyPaste, stringify: stringify, version: VERSION };
}());

"VeloAE host ready";
