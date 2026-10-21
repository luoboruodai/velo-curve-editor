"""EaseCopy-style keyframe clipboard for the native Velo editor."""
import json
import math

FORMAT = 'velo-easecopy'
VERSION = 1


def logic(c):
    try:
        return c.op('curve_logic').module
    except AttributeError:
        import curve_logic
        return curve_logic


def empty_buffer(preserve=False):
    return {'format': FORMAT, 'version': VERSION,
            'preserve_passthrough': bool(preserve), 'keys': []}


def clipboard(c):
    target = c.op('easecopy_store')
    if not target:
        return empty_buffer()
    try:
        raw = json.loads(target.text) if target.text.strip() else {}
    except (ValueError, TypeError):
        return empty_buffer()
    if not isinstance(raw, dict) or raw.get('format') != FORMAT or raw.get('version') != VERSION:
        return empty_buffer()
    result = empty_buffer(raw.get('preserve_passthrough', False))
    m = logic(c)
    for item in raw.get('keys', []) if isinstance(raw.get('keys'), list) else []:
        try:
            value = float(item['v'])
            ease = [float(v) for v in item['ease']]
            if len(ease) != 4 or not all(math.isfinite(v) for v in [value] + ease):
                continue
            result['keys'].append({'v': value, 'ease': [
                m.clamp(ease[0], 0., 1.), m.clamp(ease[1], 0., m.math_model().VEL_MAX),
                m.clamp(ease[2], 0., 1.), m.clamp(ease[3], 0., m.math_model().VEL_MAX)]})
        except (KeyError, TypeError, ValueError):
            continue
    return result


def write_clipboard(c, data):
    target = c.op('easecopy_store')
    if target:
        target.text = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def select_keyframe(c, index, extend=False):
    m = logic(c)
    state = m.state_from_component(c)
    index = int(m.clamp(index, 0, len(state['keyframes']) - 1))
    q = m.st(c)
    if extend:
        anchor = int(m.clamp(q.get('easecopy_anchor', index), 0, len(state['keyframes']) - 1))
    else:
        anchor = index
    q['easecopy_anchor'] = anchor
    q['easecopy_range'] = (anchor, index)
    q['selected_keyframe'] = index
    c.op('selected_keyframe_shape').cook(force=True)


def selection_range(c):
    m = logic(c)
    count = len(m.state_from_component(c)['keyframes'])
    selected = m.st(c).get('easecopy_range')
    if not isinstance(selected, (list, tuple)) or len(selected) != 2:
        return 0, count - 1
    try:
        a, b = int(selected[0]), int(selected[1])
    except (TypeError, ValueError):
        return 0, count - 1
    a = int(m.clamp(a, 0, count - 1))
    b = int(m.clamp(b, 0, count - 1))
    return min(a, b), max(a, b)


def refresh(c):
    m = logic(c)
    m.st(c)['points'] = None
    m.update(c)
    m.layout_ui(c)


def copy_keyframes(c):
    m = logic(c)
    state = m.state_from_component(c)
    start, end = selection_range(c)
    previous = clipboard(c)
    data = empty_buffer(previous['preserve_passthrough'])
    keys = state['keyframes']
    for index in range(start, end + 1):
        ease_index = index if index < len(state['speed_params']) else index - 1
        data['keys'].append({'v': float(keys[index]['v']),
                             'ease': m.speed_parameters(state, ease_index)})
    write_clipboard(c, data)
    m.set_status(c, 'EaseCopy · 已复制 %d 个关键帧' % len(data['keys']))
    refresh(c)
    return True


def clear_clipboard(c):
    m = logic(c)
    preserve = clipboard(c)['preserve_passthrough']
    write_clipboard(c, empty_buffer(preserve))
    m.set_status(c, 'EaseCopy · 已清空复制缓冲区')
    refresh(c)
    return True


def toggle_passthrough(c):
    m = logic(c)
    data = clipboard(c)
    data['preserve_passthrough'] = not data['preserve_passthrough']
    write_clipboard(c, data)
    m.set_status(c, 'EaseCopy · ' + ('保留直通关键帧' if data['preserve_passthrough'] else '覆盖直通关键帧'))
    refresh(c)
    return True


def passthrough_keys(state):
    """Internal Bezier keys with matching left/right derivative limits."""
    import curve_logic as curves
    result = set()
    keys = state['keyframes']
    if state.get('mode') != 'bezier':
        return result

    def endpoint_speed(segment, local):
        a, b = keys[segment:segment + 2]
        params = curves.speed_parameters(state, segment)
        local_state = dict(zip(('vx1', 'vy1', 'vx2', 'vy2'), params))
        _, speed = curves.math_model().velocity_value_and_speed(local, local_state)
        return (b['v'] - a['v']) / max(1e-9, b['t'] - a['t']) * speed

    for index in range(1, len(keys) - 1):
        left = endpoint_speed(index - 1, 1.)
        right = endpoint_speed(index, 0.)
        if not math.isfinite(left) or not math.isfinite(right):
            continue
        if abs(left - right) <= 1e-5 * max(1.0, abs(left), abs(right)):
            result.add(index)
    return result


def paste(c, kind):
    m = logic(c)
    data = clipboard(c)
    source = data['keys']
    if not source:
        m.set_status(c, 'EaseCopy · 复制缓冲区为空')
        refresh(c)
        return False
    state = m.state_from_component(c)
    start, end = selection_range(c)
    target_count = end - start + 1
    source_count = len(source)
    if target_count % source_count:
        m.set_status(c, 'EaseCopy · 目标需为 %d 个关键帧或其整数倍' % source_count)
        refresh(c)
        return False
    protected = passthrough_keys(state) if data['preserve_passthrough'] else set()
    changed = 0
    if kind == 'ease':
        segments = list(range(start, end)) if end > start else [
            start if start < len(state['speed_params']) else start - 1]
        for segment in segments:
            if segment < 0 or segment >= len(state['speed_params']):
                continue
            if segment in protected or segment + 1 in protected:
                continue
            ease = source[(segment - start) % source_count]['ease']
            m.set_speed_parameters(state, segment, ease)
            changed += 1
    elif kind == 'value':
        original_eases = [m.speed_parameters(state, index) for index in range(len(state['speed_params']))]
        last = len(state['keyframes']) - 1
        for index in range(start, end + 1):
            # Velo's public CHOP contract remains fade 0 -> 1.
            if index in (0, last) or index in protected:
                continue
            state['keyframes'][index]['v'] = source[(index - start) % source_count]['v']
            changed += 1
        if changed:
            for index, ease in enumerate(original_eases):
                m.set_speed_parameters(state, index, ease)
    else:
        return False
    if changed:
        m.assign_state(c, state)
        m.st(c).pop('selected_preset', None)
    if kind == 'ease':
        message = '已粘贴缓动 · 数值不变'
    else:
        message = '已粘贴数值 · 缓动与端点不变'
    if not changed:
        message += ' · 没有可修改的目标'
    if protected:
        message += ' · 保留 %d 个直通' % len(protected)
    m.set_status(c, 'EaseCopy · ' + message)
    refresh(c)
    return True


def action(c, name):
    if name == 'easecopy_copy':
        return copy_keyframes(c)
    if name == 'easecopy_paste_ease':
        return paste(c, 'ease')
    if name == 'easecopy_paste_value':
        return paste(c, 'value')
    if name == 'easecopy_passthrough':
        return toggle_passthrough(c)
    if name == 'easecopy_clear':
        return clear_clipboard(c)
    return False
