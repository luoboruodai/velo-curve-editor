"""Opt-in export of the current Velo curve to native TD animation keyframes."""


def unique_name(c, base):
    parent = c
    names = {child.name for child in parent.children}
    if base not in names:
        return base
    index = 1
    while f'{base}_{index:02d}' in names:
        index += 1
    return f'{base}_{index:02d}'


def export(c):
    m = c.op('curve_logic').module
    try:
        state = m.state_from_component(c)
        values, _ = m.sample_curve(state)
        animation = c.op('out1').convertToKeyframes(tolerance=0.001)
        animation.name = unique_name(c, 'velo_animation')
        for index, value in enumerate(values):
            animation.setKeyframe(index, channel='fade', value=float(value), function='linear()')
        m.set_status(c, '已写入关键帧 · ' + animation.path)
        return animation.path
    except Exception as error:
        m.set_status(c, '关键帧写入失败 · ' + str(error))
        return None
