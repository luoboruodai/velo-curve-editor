var VeloAE = (function () {
    var VERSION = "1.2.0";

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
            var nativeBezier = payload.mode === "bezier" && payload.points !== undefined;
            if (nativeBezier && !validPoints(payload.points)) return fail("Bezier 手柄超出 AE 原生缓动范围。");
            if (payload.times !== undefined && (nativeBezier || !validTimes(payload.times, payload.samples))) return fail("多段曲线时间采样无效。");
            var selection = collectTargets();
            if (!selection.targets.length) return fail("请在一个或多个数值属性上选择至少两个相邻关键帧。", { skipped: selection.skipped });
            app.beginUndoGroup("Velo AE — Apply " + payload.mode);
            began = true;
            var nativeSegments = 0, bakedSegments = 0, createdKeys = 0, cappedSegments = 0, methods = [];
            for (var i = 0; i < selection.targets.length; i++) {
                var target = selection.targets[i];
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
                createdKeys: createdKeys,
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

    return { ping: ping, inspect: inspect, apply: apply, exportPresetFile: exportPresetFile, easeCopyCopy: easeCopyCopy, easeCopyPaste: easeCopyPaste, stringify: stringify, version: VERSION };
}());

"VeloAE host ready";
