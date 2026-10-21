def onOffToOn(panelValue):
    if panelValue.name == 'lselect':
        parent().op('curve_logic').module.panel_event(parent(), 'press')
    elif panelValue.name == 'rselect':
        parent().op('curve_logic').module.panel_event(parent(), 'context')
    return


def onOnToOff(panelValue):
    if panelValue.name == 'lselect':
        parent().op('curve_logic').module.panel_event(parent(), 'release')
    return


def onValueChange(panelValue, prev):
    if panelValue.name == 'character' and panelValue.val == 27:
        parent().op('curve_logic').module.cancel_drag(parent())
        return
    if panelValue.name in ('u', 'v') and parent().op('graph').panel.lselect:
        parent().op('curve_logic').module.panel_event(parent(), 'move')
    return
