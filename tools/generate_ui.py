from pathlib import Path
import json
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'src' / 'curve_editor.tox.dir'
COMP = BASE / 'CurveEditor'
TOC = ROOT / 'src' / 'curve_editor.tox.toc'
MANAGED = []


def put(relative, content):
    path = COMP / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')
    MANAGED.append('CurveEditor/' + relative)


def set_parm(text, key, value):
    pattern = rf'(?m)^{re.escape(key)} .*$'
    line = f'{key} 0 {value}'
    if re.search(pattern, text):
        return re.sub(pattern, line, text)
    return text.rsplit('?', 1)[0] + line + '\n?'


def encode_text(relative, payload, template='curve_shape_callbacks.text'):
    data = (COMP / template).read_bytes()
    header = data[:27]
    payload = payload.encode('utf-8')
    header = header[:0x19] + len(payload).to_bytes(2, 'big') + header[0x1b:]
    put(relative, header + payload)


def make_rounded_top(name, radius, color=(0.322, 0.322, 0.322), source=None,
                     source_prefix='color', input_name=None, border=None):
    node_lines = ['TOP:rectangle', 'tile 0 0 130 90', 'flags =  parlanguage 0']
    if input_name:
        node_lines.extend(['inputs', '{', f'0 \t{input_name}', '}'])
    node_lines.extend(['color 0.67 0.67 0.67 ', 'end', ''])
    put(f'{name}.n', '\n'.join(node_lines))
    lines = [
        '?', 'outputresolution 0 custom', 'resolutionw 0 96', 'resolutionh 0 32',
        'sizex 0 1', 'sizey 0 1', 'sizeunit 0 fraction',
        'centerx 0 0', 'centery 0 0', 'centerunit 0 fraction',
        'justifyh 0 center', 'justifyv 0 center',
        f'cornerradius 0 {radius}', 'cornerradiusunit 0 pixels',
        'fillalpha 0 1', 'bgalpha 0 0', 'antialias 0 on',
        'softness 0 0', 'borderwidthunit 0 pixels',
    ]
    if source:
        for channel in 'rgb':
            lines.append(f'fillcolor{channel} 49 0 "op(\'{source}\').par.{source_prefix}{channel} * .9"')
    else:
        for channel, value in zip('rgb', color):
            lines.append(f'fillcolor{channel} 0 {value}')
    if border:
        lines.extend(['borderwidth 0 1', 'borderalpha 0 1'])
        for channel, value in zip('rgb', border):
            lines.append(f'border{channel} 0 {value}')
    else:
        lines.extend(['borderwidth 0 0', 'borderalpha 0 0'])
    if input_name:
        lines.extend(['compoverinput 0 on', 'operand 0 over', 'swaporder 0 on'])
    lines.extend(['?', ''])
    put(f'{name}.parm', '\n'.join(lines))


def attach_rounded(name, radius, color=(0.322, 0.322, 0.322), **kwargs):
    rounded_name = name + '_rounded'
    make_rounded_top(rounded_name, radius, color, **kwargs)
    path = COMP / f'{name}.parm'
    parm = path.read_text(encoding='utf-8')
    for key, value in {'top': rounded_name, 'topfill': 'off', 'bgalpha': 0}.items():
        parm = set_parm(parm, key, value)
    put(f'{name}.parm', parm)


def make_button(name, label, action=None):
    action = action or name
    source = COMP / 'preset_linear'
    target = COMP / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    for suffix in ('n', 'parm', 'panel'):
        shutil.copy2(COMP / f'preset_linear.{suffix}', COMP / f'{name}.{suffix}')
    put(f'{name}.n', (COMP / f'{name}.n').read_text(encoding='utf-8'))
    parm = (COMP / f'{name}.parm').read_text(encoding='utf-8')
    label_value = ('\ufeff' + label) if any(ord(character) > 127 for character in label) else label
    for key, value in {
        'label': label_value, 'x': 24, 'y': 600,
        'w': 96, 'h': 32, 'bgcolorr': 0.09, 'bgcolorg': 0.09, 'bgcolorb': 0.09,
        'colorr': 0.235, 'colorg': 0.235, 'colorb': 0.235,
    }.items():
        parm = set_parm(parm, key, value)
    put(f'{name}.parm', parm)
    panel = (COMP / f'{name}.panel').read_text(encoding='utf-8')
    panel = re.sub(r'(?m)^screenw .*$', 'screenw 96', panel)
    panel = re.sub(r'(?m)^screenh .*$', 'screenh 32', panel)
    panel = re.sub(r'(?m)^screenwm .*$', 'screenwm 96', panel)
    panel = re.sub(r'(?m)^screenhm .*$', 'screenhm 32', panel)
    put(f'{name}.panel', panel)
    for relative in (
        'out1.n', 'par1.n', 'par1.parm', 'text.n', 'text.parm', 'text.panel',
        'parexec1.n', 'parexec1.parm', 'parexec1.text',
        'panelexec1.n', 'panelexec1.parm', 'panelexec1.text',
    ):
        MANAGED.append(f'CurveEditor/{name}/{relative}')
    put(f'event_{action}.n', (COMP / 'event_preset_linear.n').read_text(encoding='utf-8'))
    event_parm = (COMP / 'event_preset_linear.parm').read_text(encoding='utf-8')
    event_parm = event_parm.replace('preset_linear', name)
    put(f'event_{action}.parm', event_parm)
    callback = f"def onOffToOn(panelValue):\n    parent().op('curve_logic').module.button(parent(),'{action}')\n    return\n"
    encode_text(f'event_{action}.text', callback, 'event_preset_linear.text')
    attach_rounded(name, 4, source=name)


def make_preset_hit(name):
    target = COMP / name
    if target.exists():
        shutil.rmtree(target)
    put(f'{name}.n', (COMP / 'preset_linear.n').read_text(encoding='utf-8'))
    put(f'{name}.parm', '\n'.join([
        '?', 'label 0 ', 'x 0 24', 'y 0 600', 'w 0 96', 'h 0 32',
        'bgcolorr 0 0', 'bgcolorg 0 0', 'bgcolorb 0 0', 'bgalpha 0 0',
        'borderover 0 off', 'enablecloning 0 off', 'layer 0 60', '?', '',
    ]))
    panel = (COMP / 'preset_linear.panel').read_text(encoding='utf-8')
    panel = re.sub(r'(?m)^screenw .*$', 'screenw 96', panel)
    panel = re.sub(r'(?m)^screenh .*$', 'screenh 32', panel)
    panel = re.sub(r'(?m)^screenwm .*$', 'screenwm 96', panel)
    panel = re.sub(r'(?m)^screenhm .*$', 'screenhm 32', panel)
    put(f'{name}.panel', panel)
    put(f'event_{name}.n', (COMP / 'event_preset_linear.n').read_text(encoding='utf-8'))
    event_parm = (COMP / 'event_preset_linear.parm').read_text(encoding='utf-8')
    event_parm = event_parm.replace('preset_linear', name).replace('panelvalue 0 state', 'panelvalue 0 lselect')
    # Panel Execute DATs need the Off-to-On edge enabled for native Button
    # COMP hits. Without this flag the modal controls render but never dispatch
    # their onOffToOn callbacks, leaving the whole settings surface inert.
    event_parm = set_parm(event_parm, 'offtoon', 'on')
    event_parm = set_parm(event_parm, 'ontooff', 'off')
    event_parm = set_parm(event_parm, 'valuechange', 'off')
    if name.startswith('preset_hit_'):
        slot = int(name.rsplit('_', 1)[1]) - 1
        event_parm = set_parm(event_parm, 'panelvalue', '"lselect rselect u v"')
        event_parm = set_parm(event_parm, 'ontooff', 'on')
        event_parm = set_parm(event_parm, 'valuechange', 'on')
        callback = (
            f"def onOffToOn(panelValue):\n    if panelValue.name=='lselect':parent().op('curve_logic').module.preset_card_event(parent(),{slot},'press')\n    if panelValue.name=='rselect':parent().op('curve_logic').module.preset_card_event(parent(),{slot},'context')\n"
            f"def onOnToOff(panelValue):\n    if panelValue.name=='lselect':parent().op('curve_logic').module.preset_card_event(parent(),{slot},'release')\n"
            f"def onValueChange(panelValue, prev):\n    if panelValue.name in ('u','v') and parent().op('{name}').panel.lselect:parent().op('curve_logic').module.preset_card_event(parent(),{slot},'move')\n"
        )
    else:
        callback = f"def onOffToOn(panelValue):\n    parent().op('curve_logic').module.button(parent(),'{name}')\n    return\n"
    put(f'event_{name}.parm', event_parm)
    encode_text(f'event_{name}.text', callback, 'event_preset_linear.text')


def make_container(name, color, layer):
    put(f'{name}.n', (COMP / 'graph.n').read_text(encoding='utf-8'))
    put(f'{name}.parm', '\n'.join([
        '?', 'x 0 24', 'y 0 600', 'w 0 96', 'h 0 12',
        f'bgcolorr 0 {color}', f'bgcolorg 0 {color}', f'bgcolorb 0 {color}',
        'bgalpha 0 1', 'clickthrough 0 on', f'layer 0 {layer}', '?', '',
    ]))
    put(f'{name}.panel', '1\n3\n4\nscreenw 96\nscreenh 12\nscreenwm 96\nscreenhm 12\n')


def make_slider(group):
    make_container(f'param{group}_track', 0.28, 10)
    attach_rounded(f'param{group}_track', 2.5, (0.267, 0.267, 0.267))
    make_container(f'param{group}_halo', 0.0, 19)
    attach_rounded(f'param{group}_halo', 12, (0.0, 0.47, 0.83))
    make_container(f'param{group}_knob', 0.86, 20)
    attach_rounded(f'param{group}_knob', 8.5, (0.86, 0.86, 0.86))
    name = f'param{group}_hit'
    make_preset_hit(name)
    event_path = COMP / f'event_{name}.parm'
    event_parm = event_path.read_text(encoding='utf-8')
    for key, value in {'panelvalue': '"lselect u v"', 'offtoon': 'on', 'valuechange': 'on'}.items():
        event_parm = set_parm(event_parm, key, value)
    put(f'event_{name}.parm', event_parm)
    callback = f"""def onOffToOn(panelValue):
    if panelValue.name == 'lselect':
        parent().op('curve_logic').module.slider_event(parent(), {group}, 'press')
    return


def onOnToOff(panelValue):
    if panelValue.name == 'lselect':
        parent().op('curve_logic').module.slider_event(parent(), {group}, 'release')
    return


def onValueChange(panelValue, prev):
    if panelValue.name in ('u', 'v') and parent().op('{name}').panel.lselect:
        parent().op('curve_logic').module.slider_event(parent(), {group}, 'move')
    return
"""
    encode_text(f'event_{name}.text', callback, 'event_preset_linear.text')


def make_settings_ui():
    make_container('settings_backdrop', 0.0, 100)
    data = (COMP / 'settings_backdrop.parm').read_text()
    put('settings_backdrop.parm', set_parm(data, 'bgalpha', 0.6))
    make_preset_hit('settings_backdrop_hit')
    put('settings_backdrop_hit.parm', set_parm((COMP / 'settings_backdrop_hit.parm').read_text(), 'layer', 101))
    encode_text('event_settings_backdrop_hit.text', "def onOffToOn(panelValue):\n    parent().op('curve_logic').module.settings_backdrop_event(parent())\n", 'event_preset_linear.text')
    make_container('settings_panel', 0.235, 102)
    attach_rounded('settings_panel', 8, (0.235, 0.235, 0.235), border=(0.333, 0.333, 0.333))
    for key in ('interface', 'presets', 'theme', 'graph'):
        make_container('settings_' + key + '_bg', 0.235, 103)
        attach_rounded('settings_' + key + '_bg', 4, (0.235, 0.235, 0.235), border=(0.333, 0.333, 0.333))
        name = 'settings_' + key + '_label'
        make_text(name, key.capitalize(), fontsize=10, color=0.67, layer=107)
        text = (COMP / (name + '.parm')).read_text()
        for par_name, value in {'bgalpha': 1, 'bgcolorr': .235, 'bgcolorg': .235, 'bgcolorb': .235}.items():
            text = set_parm(text, par_name, value)
        put(name + '.parm', text)
    for name in ('settings_header_line', 'settings_footer_line'):
        make_container(name, 0.333, 104)
    for name in ('settings_location', 'settings_close', 'settings_restore', 'settings_compact', 'settings_motion', 'settings_speed'):
        make_container(name + '_bg', 0.322, 105)
        attach_rounded(name + '_bg', 10 if name.endswith(('compact', 'motion', 'speed')) else 4, source=name + '_bg', source_prefix='bgcolor', border=(.32,.32,.32) if name.endswith(('compact', 'motion', 'speed')) else None)
        make_preset_hit(name)
        put(name + '.parm', set_parm((COMP / (name + '.parm')).read_text(), 'layer', 108))
        encode_text('event_' + name + '.text', "def onOffToOn(panelValue):\n    if panelValue.name=='lselect':parent().op('plugin_dialogs').module.action(parent(),'" + name + "')\n", 'event_preset_linear.text')
    for name in ('settings_compact', 'settings_motion', 'settings_speed'):
        make_container(name + '_knob', 0.96, 107)
        attach_rounded(name + '_knob', 7, (0.96, 0.96, 0.96))
    for name in ('settings_location_caption', 'settings_compact_label', 'settings_motion_label', 'settings_speed_label',
                 'settings_preset_size_info', 'settings_theme_value'):
        make_text(name, '', fontsize=11, layer=107)
    make_text('settings_graph_info', '', fontsize=9, color=0.67, layer=107)
    make_text('settings_preset_size_value', '', fontsize=10, align='right', layer=107)
    for name in ('settings_location_label', 'settings_close_label', 'settings_restore_label'):
        make_text(name, '', fontsize=11 if name != 'settings_close_label' else 18, align='center', layer=107)
    make_text('settings_title', '', fontsize=14, layer=107)
    make_container('settings_theme_swatch', 0.196, 105)
    attach_rounded('settings_theme_swatch', 3, (0.196, 0.196, 0.196), border=(0.4, 0.4, 0.4))
    make_container('settings_preset_size_track', 0.267, 105)
    attach_rounded('settings_preset_size_track', 2.5, (0.267, 0.267, 0.267))
    make_container('settings_preset_size_knob', 0.86, 107)
    attach_rounded('settings_preset_size_knob', 7.5, (0.86, 0.86, 0.86))
    make_preset_hit('settings_preset_size_hit')
    hit = (COMP / 'settings_preset_size_hit.parm').read_text()
    put('settings_preset_size_hit.parm', set_parm(hit, 'layer', 108))
    event = (COMP / 'event_settings_preset_size_hit.parm').read_text()
    for key, value in {'panelvalue': '"lselect u v"', 'offtoon': 'on', 'ontooff': 'off', 'valuechange': 'on'}.items():
        event = set_parm(event, key, value)
    put('event_settings_preset_size_hit.parm', event)
    encode_text('event_settings_preset_size_hit.text', """def onOffToOn(panelValue):
    if panelValue.name == 'lselect':
        parent().op('curve_logic').module.settings_slider_event(parent(), 'press')


def onValueChange(panelValue, prev):
    if panelValue.name in ('u', 'v') and parent().op('settings_preset_size_hit').panel.lselect:
        parent().op('curve_logic').module.settings_slider_event(parent(), 'move')
""", 'event_preset_linear.text')


def make_text(name, value, fontsize=11, align='left', color=0.86, layer=None):
    put(f'{name}.n', (COMP / 'equation.n').read_text(encoding='utf-8'))
    parm = '\n'.join([
        '?', f'text 0 {json.dumps(value, ensure_ascii=False)}', 'font 0 "PingFang SC"',
        f'fontsize 0 {fontsize}', f'fontcolorr 0 {color}', f'fontcolorg 0 {color}',
        f'fontcolorb 0 {color}', f'alignx 0 {align}', 'clickthrough 0 on',
        'x 0 24', 'y 0 100', 'w 0 120', 'h 0 20', '?', '',
    ])
    if layer is not None:
        parm = set_parm(parm, 'layer', layer)
    put(f'{name}.parm', parm)
    put(f'{name}.panel', '1\n3\n4\nscreenw 120\nscreenh 20\nscreenwm 120\nscreenhm 20\n')


def make_shape(name):
    put(f'{name}.n', 'SOP:script\ntile 0 0 130 90\nflags =  parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
    put(f'{name}.parm', f'?\ncallbacks 0 {name}_callbacks\n?\n')
    put(f'{name}_callbacks.n', f'DAT:text\ntile 0 -120 130 90\nflags =  viewer 1 parlanguage 0\ncolor 0.67 0.67 0.67 \ndock {name}\nend\n')
    put(f'{name}_callbacks.parm', '?\nlanguage 0 python\n?\n')
    encode_text(f'{name}_callbacks.text', f"def onCook(scriptOp):\n    parent().op('curve_logic').module.shape_preset(scriptOp, '{name}')\n")


def make_mat(name, color, alpha=1.0):
    red, green, blue = color if isinstance(color, (tuple, list)) else (color, color, color)
    put(f'{name}.n', 'MAT:constant\ntile 0 0 130 90\nflags =  parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
    put(f'{name}.parm', f'?\ncolorr 0 {red}\ncolorg 0 {green}\ncolorb 0 {blue}\nalpha 0 {alpha}\ndepthtest 0 off\ndepthwriting 0 off\n?\n')


def make_geo(name, shape, material, priority=None):
    put(f'{name}.n', 'COMP:geo\ntile 0 0 160 130\nflags =  render on display on pickable on parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
    parm = f'?\nmaterial 0 {material}\n'
    if priority is not None:
        parm += f'drawpriority 0 {priority}\n'
    put(f'{name}.parm', parm + '?\n')
    put(f'{name}.network', f'1\ncompinputs\n{{\n0 \t{shape}\n\tin1\n\tSOP\n}}\nend\n')
    matrix = '1\n' + 'UT_DMatrix4 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1\n' * 4
    put(f'{name}.gnode', matrix)
    put(f'{name}/in1.n', 'SOP:in\ntile 0 0 130 90\nflags =  current on render on display on parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')


def make_graph_addition(name, kind, color):
    put(f'{name}.n', (COMP / 'grid_shape.n').read_text(encoding='utf-8'))
    parm = (COMP / 'grid_shape.parm').read_text(encoding='utf-8').replace('grid_shape_callbacks', f'{name}_callbacks')
    put(f'{name}.parm', parm)
    callback_n = (COMP / 'grid_shape_callbacks.n').read_text(encoding='utf-8').replace('grid_shape', name)
    put(f'{name}_callbacks.n', callback_n)
    put(f'{name}_callbacks.parm', (COMP / 'grid_shape_callbacks.parm').read_text(encoding='utf-8'))
    encode_text(f'{name}_callbacks.text', f"def onCook(scriptOp):\n    parent().op('curve_logic').module.shape(scriptOp, '{kind}')\n", 'grid_shape_callbacks.text')
    material = name.replace('_shape', '_mat')
    make_mat(material, color)
    make_geo(name.replace('_shape', '_geo'), name, material)


def make_preset_surface():
    put('preset_grid.n', (COMP / 'graph.n').read_text(encoding='utf-8'))
    parm = (COMP / 'graph.parm').read_text(encoding='utf-8')
    for key, value in {'x': 24, 'y': 18, 'w': 512, 'h': 116, 'top': 'preset_render', 'bgcolorr': 0.165, 'bgcolorg': 0.165, 'bgcolorb': 0.165, 'bgalpha': 1, 'clickthrough': 'on', 'layer': 30}.items():
        parm = set_parm(parm, key, value)
    put('preset_grid.parm', parm)
    put('preset_grid.panel', '1\n3\n10\nu 0\nv 0\ntrueu 0\ntruev 0\nrollu 0\nrollv 0\nscreenw 512\nscreenh 116\nscreenwm 512\nscreenhm 116\n')
    put('preset_render.n', (COMP / 'plot_render.n').read_text(encoding='utf-8'))
    put('preset_render.parm', '?\ncamera 0 preset_camera\ngeometry 0 "preset_cards_geo preset_frames_geo preset_selected_geo preset_curves_geo"\nresolutionw 0 512\nresolutionh 0 116\nbgcolorr 0 0.165\nbgcolorg 0 0.165\nbgcolorb 0 0.165\nbgalpha 0 0\n?\n')
    put('preset_camera.n', (COMP / 'plot_camera.n').read_text(encoding='utf-8'))
    put('preset_camera.gnode', (COMP / 'plot_camera.gnode').read_text(encoding='utf-8'))
    put('preset_camera.parm', '?\ntx 0 0\nty 0 0\ntz 0 10\nprojection 0 ortho\northowidth 0 512\n?\n')
    put('preset_camera/file1.n', (COMP / 'plot_camera/file1.n').read_text(encoding='utf-8'))
    put('preset_camera/file1.parm', (COMP / 'plot_camera/file1.parm').read_text(encoding='utf-8'))
    for shape in ('preset_cards_shape', 'preset_frames_shape', 'preset_selected_shape', 'preset_curves_shape'):
        make_shape(shape)
    make_mat('preset_cards_mat', (0.196, 0.196, 0.196))
    make_mat('preset_frames_mat', (0.196, 0.196, 0.196))
    make_mat('preset_selected_mat', (0.0, 0.52, 0.95))
    make_mat('preset_curves_mat', (0.29, 0.565, 0.886))
    make_geo('preset_cards_geo', 'preset_cards_shape', 'preset_cards_mat', priority=30)
    make_geo('preset_frames_geo', 'preset_frames_shape', 'preset_frames_mat', priority=20)
    make_geo('preset_selected_geo', 'preset_selected_shape', 'preset_selected_mat', priority=0)
    make_geo('preset_curves_geo', 'preset_curves_shape', 'preset_curves_mat', priority=10)
    put('preset_events.n', (COMP / 'drag_events.n').read_text(encoding='utf-8'))
    put('preset_events.parm', '?\npanels 16 preset_grid parent()\npanelvalue 0 "lselect u v"\nontooff 0 off\nvaluechange 0 on\nlanguage 0 python\n?\n')
    encode_text('preset_events.text', "def onValueChange(panelValue, prev):\n    if panelValue.name == 'lselect' and panelValue.eval():\n        parent().op('curve_logic').module.preset_event(parent())\n    return\n", 'drag_events.text')
    for index in range(16):
        make_text(f'preset_slot_{index + 1:02d}', '', fontsize=9, align='center', layer=40)


for name, label in (
    ('mode_bezier', 'Bezier'), ('mode_elastic', 'Elastic'), ('mode_bounce', 'Bounce'),
    ('direction_cycle', '方向 I/O'), ('preset_next', '选择预设'), ('action_copy', '复制曲线'),
    ('action_paste', '粘贴曲线'), ('action_reset', '重置当前'), ('action_reverse', '反向曲线'),
    ('action_save', '保存预设'), ('settings_open', '⚙'), ('param1_down', '-'), ('param1_up', '+'),
    ('param2_down', '-'), ('param2_up', '+'),
):
    make_button(name, label)

make_text('status', '', fontsize=9, color=0.62, layer=22)
for group in (1, 2, 3, 4):
    for part, value in (('label', '参数 %d' % group), ('value', '1.00')):
        make_text('param%d_%s' % (group, part), value, fontsize=10, align='right' if part == 'value' else 'left', color=0.76)
make_preset_surface()
make_shape('preset_hover_shape')
make_mat('preset_hover_mat', (0.29, 0.565, 0.886), alpha=0.0)
make_geo('preset_hover_geo', 'preset_hover_shape', 'preset_hover_mat', priority=5)
preset_parm = (COMP / 'preset_render.parm').read_text()
put('preset_render.parm', set_parm(preset_parm, 'geometry', '"preset_cards_geo preset_frames_geo preset_selected_geo preset_hover_geo preset_curves_geo"'))
make_container('ui_icons', 0.0, 80)
icons = (COMP / 'ui_icons.parm').read_text()
for key, value in {'top': 'ui_icons_render', 'bgalpha': 0, 'topfill': 'off'}.items():
    icons = set_parm(icons, key, value)
put('ui_icons.parm', icons)
make_shape('ui_icons_shape')
encode_text('ui_icons_shape_callbacks.text', "def onCook(scriptOp):\n    parent().op('ui_style').module.shape_icons(scriptOp)\n")
make_mat('ui_icons_mat', (0.86, 0.86, 0.86))
make_geo('ui_icons_geo', 'ui_icons_shape', 'ui_icons_mat')
put('ui_icons_render.n', (COMP / 'plot_render.n').read_text())
put('ui_icons_render.parm', '?\ncamera 0 ui_icons_camera\ngeometry 0 ui_icons_geo\nresolutionw 0 760\nresolutionh 0 760\nbgalpha 0 0\n?\n')
for suffix in ('n', 'gnode', 'parm'):
    put('ui_icons_camera.' + suffix, (COMP / ('preset_camera.' + suffix)).read_bytes())
for relative in ('file1.n', 'file1.parm'):
    put('ui_icons_camera/' + relative, (COMP / ('preset_camera/' + relative)).read_bytes())
put('ui_style.n', 'DAT:text\ntile 0 -120 130 90\nflags =  viewer 1 parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
put('ui_style.parm', '?\nlanguage 0 python\n?\n')
encode_text('ui_style.text', (ROOT / 'src/python/ui_style.py').read_text(), 'curve_logic.text')
make_graph_addition('grid_main_shape', 'grid_main', (0.282, 0.282, 0.282))
make_graph_addition('anchor_shape', 'anchor', (0.863, 0.863, 0.863))
make_graph_addition('selected_keyframe_shape', 'selected_keyframe', (0.29, 0.565, 0.886))
for index in range(16):
    make_preset_hit(f'preset_hit_{index + 1:02d}')
for group in (1, 2, 3, 4):
    make_slider(group)
make_settings_ui()
attach_rounded('graph', 4, (0.133, 0.133, 0.133), input_name='plot_render')
plot_render = (COMP / 'plot_render.parm').read_text(encoding='utf-8')
plot_render = set_parm(plot_render, 'geometry', '"grid_main_geo grid_geo speed_geo curve_geo handle_geo anchor_geo selected_keyframe_geo playhead_geo"')
put('plot_render.parm', set_parm(plot_render, 'bgalpha', 0))
copy_parm = (COMP / 'action_copy.parm').read_text()
put('action_copy.parm', set_parm(copy_parm, 'layer', 2))
make_container('equation_bg', 0.145, 0)
attach_rounded('equation_bg', 4, (0.145, 0.145, 0.145), border=(0.267, 0.267, 0.267))
equation = (COMP / 'equation.parm').read_text(encoding='utf-8')
for key, value in {'layer': 1, 'text': '""', 'font': '"Menlo"', 'fontsize': 10, 'wordwrap': 'off'}.items():
    equation = set_parm(equation, key, value)
put('equation.parm', equation)
for name, label in (('easecopy_copy', '复制'), ('easecopy_paste_ease', '缓动'), ('easecopy_paste_value', '数值'), ('easecopy_passthrough', '保留直通'), ('easecopy_clear', '清空 0')):
    make_button(name, label)
make_container('easecopy_bg', 0.145, 0)
attach_rounded('easecopy_bg', 4, (0.145, 0.145, 0.145), border=(0.267, 0.267, 0.267))
make_text('easecopy_title', 'EaseCopy', fontsize=11, color=0.78, layer=2)
make_text('easecopy_caption', '0 个关键帧', fontsize=9, color=0.55, align='right', layer=2)
put('easecopy_store.n', 'DAT:text\ntile 0 0 130 90\nflags =  parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
put('easecopy_store.parm', '?\nlanguage 0 text\n?\n')
encode_text('easecopy_store.text', '{"format":"velo-easecopy","version":1,"preserve_passthrough":false,"keys":[]}', 'curve_logic.text')
for path in COMP.glob('*/text.parm'):
    text = path.read_text(encoding='utf-8')
    updated = text.replace('[c/.5 for c in [.2, .4, .15, .35]]', '[c/.5 for c in [.45, .6, .4, .55]]')
    for channel in 'rgb':
        updated = updated.replace(f'* parent().par.color{channel} + .5', f'* parent().par.color{channel} + .85')
    updated = set_parm(updated, 'bgalpha', 0)
    updated = set_parm(updated, 'fontsize', 11)
    for key in ('leftborder', 'rightborder', 'bottomborder', 'topborder'):
        updated = set_parm(updated, key, 'off')
    put(path.relative_to(COMP).as_posix(), updated)

root_parm=(BASE/'CurveEditor.parm').read_text()
for key,value in {'X1':1/3,'Y1':1/3,'X2':2/3,'Y2':2/3}.items():root_parm=set_parm(root_parm,key,value)
(BASE/'CurveEditor.parm').write_text(root_parm,encoding='utf-8')

# U014: native curve engine and real dialogs; source remains in editable Python modules.
import runpy
for module in ('curve_model','graph_engine','plugin_dialogs','preset_layout','easecopy','bezier_handles'):
    put(module+'.n', 'DAT:text\ntile 0 -120 130 90\nflags =  viewer 1 parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
    put(module+'.parm','?\nlanguage 0 python\n?\n')
    encode_text(module+'.text',(ROOT/'src/python'/(module+'.py')).read_text(encoding='utf-8'),'curve_logic.text')
for name,label in (('view_fit','适配'),('view_in','＋'),('view_out','−'),('preset_prev_page','‹'),('preset_next_page','›'),('preset_apply','载入'),('segment_prev','‹'),('segment_next','›'),('preset_context_delete','删除所选'),('preset_context_export','导出所选')):
    make_preset_hit(name)
    MANAGED[:]=[rel for rel in MANAGED if not rel.startswith('CurveEditor/'+name+'/')]
    data=(COMP/(name+'.parm')).read_text()
    for key,value in {'layer':65,'colorr':.235,'colorg':.235,'colorb':.235}.items():data=set_parm(data,key,value)
    put(name+'.parm',data)
    make_container(name+'_bg',.29,61)
    attach_rounded(name+'_bg',4,source=name,source_prefix='color')
    make_text(name+'_label',label,fontsize=10,align='center',layer=64)
    for suffix in ('.n','.parm'):
        (COMP/(name+'_rounded'+suffix)).unlink(missing_ok=True)
make_container('view_group_bg', 0.12, 60)
attach_rounded('view_group_bg', 4, (0.12, 0.12, 0.12), border=(0.38, 0.38, 0.38))
make_container('segment_group_bg', 0.12, 60)
attach_rounded('segment_group_bg', 4, (0.12, 0.12, 0.12), border=(0.38, 0.38, 0.38))
for _name in ('view_group_bg', 'segment_group_bg'):
    _data=(COMP/(_name+'_rounded.parm')).read_text()
    _data=set_parm(_data,'fillalpha',0.42);_data=set_parm(_data,'borderalpha',0.58)
    put(_name+'_rounded.parm',_data)
for _name in ('view_fit_bg','view_in_bg','view_out_bg','segment_prev_bg','segment_next_bg'):
    _data=(COMP/(_name+'_rounded.parm')).read_text()
    put(_name+'_rounded.parm',set_parm(_data,'fillalpha',0.72))
make_text('segment_info','1 / 1',fontsize=10,align='center',layer=66)
make_container('preset_context_bg',0.165,90)
attach_rounded('preset_context_bg',4,(0.165,0.165,0.165),border=(0.29,0.29,0.29))
for name, label in (('space_value', '值'), ('space_speed', '速度')):
    make_preset_hit(name)
    MANAGED[:] = [rel for rel in MANAGED if not rel.startswith('CurveEditor/' + name + '/')]
    data = (COMP / (name + '.parm')).read_text()
    for key, value in {'layer': 65, 'colorr': .235, 'colorg': .235, 'colorb': .235}.items():
        data = set_parm(data, key, value)
    put(name + '.parm', data)
    make_container(name + '_bg', .29, 61)
    attach_rounded(name + '_bg', 4, source=name, source_prefix='color')
    make_text(name + '_label', label, fontsize=10, align='center', layer=64)
make_container('preset_delete_zone', 0.29, 45)
attach_rounded('preset_delete_zone', 4, (0.20, 0.32, 0.44), border=(0.29, 0.565, 0.886))
make_text('preset_delete_label', '松开以移动预设', fontsize=10, align='center', color=0.9, layer=46)
for _name in ('preset_delete_zone', 'preset_delete_label'):
    _data = (COMP / (_name + '.parm')).read_text()
    put(_name + '.parm', set_parm(_data, 'display', 'off'))
make_text('preset_page_info','1 / 1',fontsize=9,align='center',layer=66)
for index in range(16):
    suffix='%02d'%(index+1)
    make_text('preset_thumbtext_'+suffix,'',fontsize=13,align='center',layer=44)
    make_container('preset_thumbimage_'+suffix,0.133,44)
    data=(COMP/('preset_thumbimage_'+suffix+'.parm')).read_text()
    data=set_parm(data,'bgalpha',0)
    put('preset_thumbimage_'+suffix+'.parm',data)
# A real Line MAT gives identical antialiased stroke widths, not inconsistent one-pixel GL lines.
for name,width,color in (('curve_mat',2.2,(.29,.565,.886)),('speed_mat',1.1,(.18,.23,.29)),('handle_mat',1.0,(.58,.58,.58))):
    put(name+'.n','MAT:line\ntile 0 0 130 90\nflags =  parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
    data=['?', 'widthnear 0 '+str(width),'widthfar 0 '+str(width),'depthtest 0 off','depthwriting 0 off','pointnearalpha 0 0','pointfaralpha 0 0','linenearalpha 0 1','linefaralpha 0 1']
    for prefix in ('linenearcolor','linefarcolor'):
        data += [prefix+ch+' 0 '+str(value) for ch,value in zip('rgb',color)]
    put(name+'.parm','\n'.join(data+['?','']))
api=runpy.run_path(str(ROOT/'src/python/plugin_dialogs.py'))
for name,(kind,_) in api['catalogue']().items():
    if kind in ('hit','slider'):
        make_preset_hit(name)
        data=(COMP/(name+'.parm')).read_text()
        put(name+'.parm',set_parm(data,'layer',110))
        if kind=='hit':
            encode_text('event_'+name+'.text',"def onOffToOn(panelValue):\n    if panelValue.name=='lselect':parent().op('plugin_dialogs').module.action(parent(),'"+name+"')\n",'event_preset_linear.text')
        if kind=='slider':
            data=(COMP/('event_'+name+'.parm')).read_text()
            for key,value in {'panelvalue':'"lselect u v"','offtoon':'on','ontooff':'off','valuechange':'on'}.items():data=set_parm(data,key,value)
            put('event_'+name+'.parm',data)
            encode_text('event_'+name+'.text',"def onOffToOn(panelValue):\n    if panelValue.name=='lselect':parent().op('plugin_dialogs').module.slider(parent(),'"+name+"')\n\ndef onValueChange(panelValue,prev):\n    if panelValue.name in ('u','v') and parent().op('"+name+"').panel.lselect:parent().op('plugin_dialogs').module.slider(parent(),'"+name+"')\n",'event_preset_linear.text')
    elif kind in ('text','input'):
        make_text(name,'',fontsize=11,align='center' if name.endswith('_label') else 'left',layer=109)
        data=(COMP/(name+'.parm')).read_text()
        if name in ('dlg_title',):data=set_parm(data,'fontsize',14)
        if name.startswith('dlg_legend'):
            for key,value in {'fontsize':10,'bgalpha':0,'fontcolorr':.62,'fontcolorg':.62,'fontcolorb':.62}.items():data=set_parm(data,key,value)
        if name=='dlg_row4':
            for key,value in {'fontsize':10,'fontcolorr':.58,'fontcolorg':.58,'fontcolorb':.58}.items():data=set_parm(data,key,value)
        if kind=='input':
            for key,value in {'layer':111,'editmode':'editable','type':'string','clickthrough':'off','callbacks':'dlg_input_callbacks','bgalpha':0,'bgcolorr':.133,'bgcolorg':.133,'bgcolorb':.133,'wordwrap':'off'}.items():data=set_parm(data,key,value)
        put(name+'.parm',data)
    else:
        layer=103 if name=='dlg_panel' else (104 if name.startswith('dlg_section') or name.endswith('_line') else 108 if name.endswith('_knob') else 107 if name=='dlg_preview_image' else 106)
        make_container(name,0.235,layer)
        if name=='dlg_backdrop':
            data=(COMP/(name+'.parm')).read_text()
            for key,value in {'layer':100,'bgcolorr':0,'bgcolorg':0,'bgcolorb':0,'bgalpha':.6}.items():data=set_parm(data,key,value)
            put(name+'.parm',data)
        elif name in ('dlg_header_line','dlg_footer_line'):
            data=(COMP/(name+'.parm')).read_text()
            for ch in 'rgb':data=set_parm(data,'bgcolor'+ch,.28)
            put(name+'.parm',data)
        elif name=='dlg_preview_image':
            data=(COMP/(name+'.parm')).read_text();data=set_parm(data,'bgalpha',0);data=set_parm(data,'topfill','off');put(name+'.parm',data)
        else:
            radius=8 if name=='dlg_panel' else 4
            if name.endswith('_knob'):radius=7.5
            if name.endswith('_track'):radius=2.5
            if name.endswith('_bg') and any(k in name for k in ('compact','motion','auto_load','show_speed')):radius=10
            if name.endswith('_knob'):
                for ch in 'rgb':
                    data=(COMP/(name+'.parm')).read_text();put(name+'.parm',set_parm(data,'bgcolor'+ch,.90))
            if name in {'dlg_'+field+'_bg' for field in api['INPUTS']}:
                attach_rounded(name,4,(.133,.133,.133),border=(.267,.267,.267))
            elif name=='dlg_panel':
                attach_rounded(name,radius,(.18,.18,.18),border=(.30,.30,.30))
            elif name in ('dlg_section1','dlg_section2','dlg_section3','dlg_section4'):
                attach_rounded(name,radius,(.215,.215,.215),border=(.29,.29,.29))
            elif name.endswith('_bg') and any(k in name for k in ('compact','motion','auto_load','show_speed')):
                attach_rounded(name,radius,source=name,source_prefix='bgcolor',border=(.32,.32,.32))
            else:attach_rounded(name,radius,source=name,source_prefix='bgcolor')
    data=(COMP/(name+'.parm')).read_text();data=set_parm(data,'display','off');put(name+'.parm',data)
# The backdrop's one native hit layer shields ALL underlying input until the close animation finishes.
put('dlg_backdrop_hit.parm',set_parm((COMP/'dlg_backdrop_hit.parm').read_text(),'layer',101))
encode_text('event_dlg_backdrop_hit.text',"def onOffToOn(panelValue):\n    parent().op('plugin_dialogs').module.backdrop(parent())\n",'event_preset_linear.text')
put('dlg_input_callbacks.n','DAT:text\ntile 0 -120 130 90\nflags =  viewer 1 parlanguage 0\ncolor 0.67 0.67 0.67 \nend\n')
put('dlg_input_callbacks.parm','?\nlanguage 0 python\n?\n')
encode_text('dlg_input_callbacks.text',"def onTextEditEnd(comp,value,prev):\n    comp.parent().op('plugin_dialogs').module.input_changed(comp.parent(),comp.name,value)\n\ndef onFocusEnd(comp,info):\n    comp.parent().op('plugin_dialogs').module.input_changed(comp.parent(),comp.name,comp.par.text.eval())\n",'equation_callbacks.text')

manifest = ROOT / 'tools' / 'ui_manifest.txt'
previous = set(manifest.read_text(encoding='utf-8').splitlines()) if manifest.exists() else set()
entries = list(dict.fromkeys(MANAGED))
for relative in previous-set(entries):
    stale=BASE/relative
    if stale.is_file():stale.unlink()
lines = TOC.read_text(encoding='utf-8').splitlines()
lines = [line for line in lines if (line == '.build' or line.startswith('CurveEditor.') or line.startswith('CurveEditor/')) and line not in previous]
required = ['.build', 'CurveEditor.n', 'CurveEditor.cparm', 'CurveEditor.parm', 'CurveEditor.panel']
ordered = ['# 4 0 0 0 1'] + list(dict.fromkeys(required + lines + entries))
missing=[rel for rel in ordered[1:] if not (BASE/rel).is_file()]
if missing:raise ValueError('TOC references missing generated files: '+repr(missing))
TOC.write_text('\n'.join(ordered) + '\n', encoding='utf-8')
manifest.write_text('\n'.join(entries) + '\n', encoding='utf-8')
print(f'generated {len(entries)} UI files')

for _name, _layer in (('preset_context_bg',89),('preset_context_delete_bg',90),('preset_context_delete',92),('preset_context_delete_label',93),('preset_context_export_bg',90),('preset_context_export',92),('preset_context_export_label',93)):
    _data=(COMP/(_name+'.parm')).read_text()
    put(_name+'.parm',set_parm(_data,'layer',_layer))
