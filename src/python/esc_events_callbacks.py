def onKey(dat, key, character, alt, lAlt, rAlt, ctrl, lCtrl, rCtrl, shift, lShift, rShift, state, time, cmd, lCmd, rCmd):
    try:
        parent().op('curve_logic').module.st(parent())['key_shift'] = bool(state and (shift or lShift or rShift))
    except Exception:
        pass
    if key == 'escape' and state:
        m = parent().op('curve_logic').module
        if m.st(parent()).get('settings_open'):
            m.button(parent(), 'settings_close')
        else:
            m.cancel_drag(parent())
    return
