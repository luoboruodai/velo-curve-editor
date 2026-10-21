"""Native Velo layout and finite interaction feedback; no external UI runtime."""
import math

NEUTRAL = (0.235, 0.235, 0.235)
SELECTED = (0.29, 0.565, 0.886)
TEXT = (0.86, 0.86, 0.86)
MODAL_NAMES = (
    'settings_backdrop', 'settings_backdrop_hit', 'settings_panel',
    'settings_title', 'settings_close', 'settings_close_bg', 'settings_close_label',
    'settings_header_line', 'settings_footer_line',
    'settings_interface_bg', 'settings_interface_label', 'settings_location_caption',
    'settings_location', 'settings_location_bg', 'settings_location_label',
    'settings_compact', 'settings_compact_bg', 'settings_compact_label', 'settings_compact_knob',
    'settings_motion', 'settings_motion_bg', 'settings_motion_label', 'settings_motion_knob',
    'settings_presets_bg', 'settings_presets_label', 'settings_preset_size_info',
    'settings_preset_size_value', 'settings_preset_size_track', 'settings_preset_size_knob',
    'settings_preset_size_hit', 'settings_theme_bg', 'settings_theme_label',
    'settings_theme_value', 'settings_theme_swatch', 'settings_graph_bg',
    'settings_graph_label', 'settings_graph_info', 'settings_speed',
    'settings_speed_bg', 'settings_speed_label', 'settings_speed_knob',
    'settings_restore', 'settings_restore_bg', 'settings_restore_label',
)
ACTIONS = ('action_paste', 'action_reset', 'action_reverse', 'action_save')
HINTS = {
    'settings_open': '设置 · 界面、预设与动效',
    'direction_cycle': '方向 · 点击切换 In / Out / I/O',
    'action_copy': '复制完整曲线数据（兼容读取旧v2）', 'action_paste': '从剪贴板载入曲线',
    'action_reset': '重置为线性 · y = x', 'action_reverse': '反向当前曲线',
    'action_save': '保存到本组件的用户预设',
}


def logic(c):
    return c.op('curve_logic').module


def par(node, key, value):
    if node and abs(float(node.par[key].eval()) - value) > 1e-6:
        node.par[key] = value


def color(node, prefix, rgb):
    for channel, value in zip('rgb', rgb):
        par(node, prefix + channel, value)


def row_widths(total, count, gap=4):
    """Integer widths whose actual TD readback preserves exact inter-item gaps."""
    pixels = int(round(total))
    available = pixels - gap * (count - 1)
    base = available // count
    widths = [base] * count
    for index in range(available - base * count):
        widths[index] += 1
    return widths


def tween(cache, key, target, dt, duration, immediate=False, initial=None):
    """Retarget from the current visible value; settle exactly and stop writing."""
    tracks = cache.setdefault('ui_tweens', {})
    if key not in tracks:
        value = target if initial is None else initial
        tracks[key] = {'value': value, 'from': value, 'target': value, 'elapsed': duration}
    item = tracks[key]
    if item['target'] != target:
        item.update({'from': item['value'], 'target': target, 'elapsed': 0.0})
    if immediate:
        item.update({'value': target, 'from': target, 'target': target, 'elapsed': duration})
        return target
    if item['value'] == target:
        return target
    item['elapsed'] = min(duration, item['elapsed'] + max(0.0, dt))
    t = min(1.0, item['elapsed'] / duration)
    if t == 1.0:
        item['value'] = target
    else:
        eased = 1.0 - (1.0 - t) ** 3
        a = item['from']
        item['value'] = tuple(x + (y - x) * eased for x, y in zip(a, target)) if isinstance(target, tuple) else a + (target - a) * eased
    return item['value']


def json_preview(c):
    m = logic(c)
    state = m.state_from_component(c)
    if state.get('edit_space') == 'speed':
        text = '{"speed":[' + ','.join('%.3f' % state[key] for key in ('vx1', 'vy1', 'vx2', 'vy2')) + ']}'
    else:
        text = '{"bezier":[' + ','.join('%.3f' % state[key] for key in ('x1', 'y1', 'x2', 'y2')) + ']}'
    capacity = max(12, int(float(c.op('equation').par.w.eval()) / 6.1))
    return text if len(text) <= capacity else text[:capacity - 1] + '…'


def controls(c, state):
    m = logic(c)
    bezier = state['mode'] == 'bezier'
    compact = state['compact']
    for name in ('select1', 'select2', 'nudge_left', 'nudge_right', 'nudge_up', 'nudge_down',
                 'param1_down', 'param1_up', 'param2_down', 'param2_up', 'preset_next',
                 'title', 'instructions', 'preview_word', 'axis'):
        m.set_visible(c, name, False)
    for name in ('equation_bg', 'equation', 'action_copy'):
        m.set_visible(c, name, bezier and not compact)
    for name in ('easecopy_bg', 'easecopy_copy', 'easecopy_paste_ease', 'easecopy_paste_value', 'easecopy_passthrough', 'easecopy_clear'):
        m.set_visible(c, name, True)
    easecopy = c.op('easecopy').module.clipboard(c)
    verbose = float(c.par.w.eval()) >= 480
    m.set_node_text(c, 'easecopy_title', 'EaseCopy')
    m.set_node_text(c, 'easecopy_caption', ('%d 个关键帧' % len(easecopy['keys'])) if verbose else str(len(easecopy['keys'])))
    m.set_button_label(c, 'easecopy_copy', '复制')
    m.set_button_label(c, 'easecopy_paste_ease', '粘贴缓动' if verbose else '缓动')
    m.set_button_label(c, 'easecopy_paste_value', '粘贴数值' if verbose else '数值')
    m.set_button_label(c, 'easecopy_passthrough', '保留直通' if verbose else '直通')
    m.set_button_label(c, 'easecopy_clear', '清空')
    for name in ('settings_open', 'status', 'ui_icons') + ACTIONS:
        m.set_visible(c, name, True)
    m.set_visible(c, 'speed_info', False)
    m.set_visible(c, 'speed_badge', False)
    for name in ('space_value', 'space_speed'):
        m.set_visible(c, name, bezier)
        for suffix in ('_bg', '_label'):
            m.set_visible(c, name + suffix, bezier)
    m.set_button_label(c, 'space_value', '值')
    m.set_button_label(c, 'space_speed', '速度')
    for group in (1, 2, 3, 4):
        visible = (group <= 2 and not bezier) or state.get('edit_space') == 'speed'
        for part in ('track', 'knob', 'hit', 'label', 'value', 'halo'):
            m.set_visible(c, 'param%d_%s' % (group, part), visible)
    for name in ('preset_linear', 'preset_fast', 'preset_slow', 'preset_smooth', 'preset_apply'):
        m.set_visible(c, name, False)
    for suffix in ('_bg','_label'):
        m.set_visible(c,'preset_apply'+suffix,False)
    segment_count=max(1,len(state.get('speed_params',[])))
    segment=int(m.clamp(m.st(c).get('speed_segment',0),0,segment_count-1))
    m.st(c)['speed_segment']=segment
    m.st(c)['selected_keyframe']=int(m.clamp(m.st(c).get('selected_keyframe',1),0,len(state['keyframes'])-1))
    show_segments=bezier and state.get('edit_space')=='speed' and segment_count>1 and float(c.op('graph').par.w.eval())>=280
    for name in ('segment_group_bg','segment_info'):
        m.set_visible(c,name,show_segments)
    for name in ('segment_prev','segment_next'):
        for suffix in ('','_bg','_label'):
            m.set_visible(c,name+suffix,show_segments)
    m.set_node_text(c,'segment_info','%d / %d'%(segment+1,segment_count))
    m.set_visible(c, 'direction_cycle', not bezier)
    short = float(c.par.w.eval()) < 420
    for mode, abbr in (('bezier', 'BE'), ('elastic', 'EL'), ('bounce', 'BO')):
        m.set_button_label(c, 'mode_' + mode, abbr if short else mode.capitalize())
    for name, text in (('settings_open', ''), ('action_copy', '复制'),
                       ('action_paste', '   粘贴'), ('action_reset', '   重置'),
                       ('action_reverse', '   反向'), ('action_save', '   保存')):
        m.set_button_label(c, name, text)
    m.set_button_label(c, 'direction_cycle', {'in': 'In  ▾', 'out': 'Out  ▾', 'inout': 'I/O  ▾'}[state['direction']])
    modern=state.get('model')=='continuous-v3'
    if state.get('edit_space') == 'speed':
        params=m.speed_parameters(state,segment)
        for group, (label, value) in {
            1: ('缓入影响', '%.0f%%' % (params[0] * 100)),
            2: ('缓出影响', '%.0f%%' % ((1.0 - params[2]) * 100)),
            3: ('起始速度', '%.2f' % params[1]),
            4: ('结束速度', '%.2f' % params[3]),
        }.items():
            m.set_node_text(c, 'param%d_label' % group, label)
            m.set_node_text(c, 'param%d_value' % group, value)
    else:
        labels = {'elastic': ('振幅', '频率') if modern else ('旧振幅','旧周期'), 'bounce': ('恢复系数','周期') if modern else ('旧次数','旧阻尼')}.get(state['mode'], ('', ''))
        values = (('%.3f'%state['elastic_gain'],'%.4g'%state['frequency']) if state['mode']=='elastic' else ('%.3f'%state['restitution'],'%.3f'%state['bounce_period'])) if modern else (('%.2f'%state['amplitude'],'%.2f'%state['period']) if state['mode']=='elastic' else (str(state['bounces']),'%.2f'%state['damping']))
        for group in (1, 2):
            m.set_node_text(c, 'param%d_label' % group, labels[group - 1])
            m.set_node_text(c, 'param%d_value' % group, values[group - 1])
    data = c.op('graph_engine').module.render_data(c)
    duration = max(0.01, float(m.par_value(c, 'Duration', 2.0)))
    text = ('背景 v  ±%.2g /s'% (data['scale']/duration)+(' · ∞端点' if data['singular'] else '')) if state['show_speed'] else '速度背景 · 隐藏'
    m.set_node_text(c, 'speed_info', text)
    m.set_node_text(c, 'equation', json_preview(c))
    update_slider_knobs(c, state)
    c.op('graph_engine').module.apply_visuals(c)
    for name in ('view_fit','view_in','view_out','preset_prev_page','preset_next_page','preset_page_info'):
        active=True if name.startswith('view_') else m.st(c).get('preset_visible',False)
        m.set_visible(c,name,active)
        for suffix in ('_bg','_label'):m.set_visible(c,name+suffix,active)
    settings_visibility(c)



def update_slider_knobs(c, state):
    m = logic(c)
    segment=m.st(c).get('speed_segment',0) if state.get('edit_space')=='speed' else 0
    for group, (x, y, width) in m.st(c).get('slider_layout', {}).items():
        ratio = m.slider_display_ratio(state, group, segment)
        center = x + ratio * width
        size = m.st(c).get('knob_size_%d' % group, 15.0)
        offset=15 if state.get('edit_space')=='speed' else 13
        m.place(c, 'param%d_knob' % group, center - size / 2, y + offset - size / 2, size, size)
        m.place(c, 'param%d_halo' % group, center - 12, y + 3, 24, 24)



def slider_ratio(c, group):
    m = logic(c)
    hit = c.op('param%d_hit' % group)
    width = m.st(c)['slider_layout'][group][2]
    return m.clamp((float(hit.panel.u) * (width + 16.0) - 8.0) / width, 0.0, 1.0)


def settings_ratio(c):
    m = logic(c)
    hit = c.op('settings_preset_size_hit')
    width = float(hit.par.w.eval()) - 16.0
    return m.clamp((float(hit.panel.u) * (width + 16.0) - 8.0) / width, 0.0, 1.0)


def settings_visibility(c):
    c.op('plugin_dialogs').module.sync(c)


def settings_layout(c):
    c.op('plugin_dialogs').module.layout(c)


def layout_ui(c):
    m = logic(c)
    cache = m.st(c)
    state = m.state_from_component(c)
    width, height = max(280.0, float(c.par.w.eval())), max(360.0, float(c.par.h.eval()))
    mode, compact, location = state['mode'], state['compact'], state['preset_location']
    wide = location in ('left','right') and not compact and width >= 680 and height >= 480
    key = (width, height, mode, compact, location, state['edit_space'], state['preset_size'],
           len(m.preset_entries(c)), cache.get('preset_page',0),cache.get('preset_context'),
           cache.get('preset_drop_target'),cache.get('speed_segment',0))
    if cache.get('layout_key') == key:
        return
    cache['layout_key'] = key
    margin = 8.0 if compact else 10.0
    header_top = margin
    available = width - margin * 2
    sidebar = 180.0
    lw = available - sidebar - 10 if wide else available
    columns, rows = m.preset_grid_spec(c, len(m.preset_entries(c)), wide)
    natural = 16 + rows * state['preset_size'] + max(0, rows - 1) * 8
    show_presets = wide or (not compact and width>=480 and height>=620)
    dedicated_tools = False  # Glass tools float above the graph, not in a separate toolbar row.
    toolbar_bay = 0.0
    if wide:
        gx = margin if location=='left' else width-margin-sidebar
        gt = header_top + 42 + toolbar_bay
        gw, gh = sidebar, height - (header_top + 42 + toolbar_bay) - margin
    else:
        gx, gw, gh = margin, available, min(natural, max(80, height * 0.26))
        gt = height - margin - gh
    if wide and location=='left':margin += sidebar+10
    if show_presets and not wide and location=='top':
        gt=margin+40
    bottom = gt - 10 if show_presets and not wide and location!='top' else height - (8 if compact else 10)
    # EaseCopy is a separate bottom utility group, below the main action row.
    easecopy_h = 56.0
    easecopy_top = bottom - easecopy_h
    actions_top = easecopy_top - 8 - 32
    status_top = actions_top - 20
    speed_bay = 64 if mode == 'bezier' and state.get('edit_space') == 'speed' else 0
    base_params = (0 if compact else 40) if mode == 'bezier' else 56
    params_h = base_params + speed_bay
    params_top = status_top - params_h - (6 if params_h else 0)
    equation_top = params_top + speed_bay
    graph_top = (gt+gh+8) if show_presets and not wide and location=='top' else header_top+42+toolbar_bay
    min_graph_h = 150.0 if height >= 520 else 80.0
    graph_h = max(min_graph_h, params_top - 10 - graph_top)
    # Three mode buttons share 4px gaps; the right-side group is separated by 8px.
    direction_w = 62.0
    space_group_w = 52.0 * 2 + 4.0
    right_group_w = space_group_w if mode == 'bezier' else direction_w
    right_total = 32.0 + 8.0 + right_group_w
    mode_widths = row_widths(lw - right_total - 8.0, 3)
    mode_x = margin
    for name, button_width in zip(('mode_bezier', 'mode_elastic', 'mode_bounce'), mode_widths):
        m.place(c, name, mode_x, header_top, button_width, 32)
        mode_x += button_width + 4
    m.place(c, 'settings_open', margin + lw - 32, header_top, 32, 32)
    m.place(c, 'direction_cycle', margin + lw - 32 - 8 - direction_w, header_top, direction_w if mode != 'bezier' else 1, 32)
    m.place(c, 'graph', margin, graph_top, lw, graph_h)
    # JSON and the other recessed utility groups share the 40px / 4px-inset contract.
    m.place(c, 'equation_bg', margin, equation_top, lw, 40)
    m.place(c, 'equation', margin + 10, equation_top + 10, max(20, lw - 86), 20)
    m.place(c, 'action_copy', margin + lw - 68, equation_top + 4, 64, 32)
    m.place(c, 'easecopy_bg', margin, easecopy_top, lw, easecopy_h)
    show_easecopy_title = lw >= 240
    m.set_visible(c, 'easecopy_title', show_easecopy_title)
    m.set_visible(c, 'easecopy_caption', show_easecopy_title)
    m.place(c, 'easecopy_title', margin + 10, easecopy_top + 5, 100, 13)
    m.place(c, 'easecopy_caption', margin + lw - 110, easecopy_top + 6, 100, 12)
    inner = 4.0
    easecopy_widths = row_widths(lw - inner * 2, 5)
    x = margin + inner
    for name, button_width in zip(('easecopy_copy', 'easecopy_paste_ease', 'easecopy_paste_value', 'easecopy_passthrough', 'easecopy_clear'), easecopy_widths):
        m.place(c, name, x, easecopy_top + 20, button_width, 32)
        x += button_width + 4
    m.place(c, 'status', margin + 2, status_top + 1, lw - 4, 16)
    action_widths = row_widths(lw, 4)
    action_x = margin
    cache['icon_rects'] = {}
    for name, button_width in zip(ACTIONS, action_widths):
        m.place(c, name, action_x, actions_top, button_width, 32)
        cache['icon_rects'][name] = (action_x + button_width / 2 - 22, actions_top + 8, 16)
        action_x += button_width + 4
    cache['icon_rects']['settings_open'] = (margin + lw - 26, header_top + 6, 20)
    sliders = {}
    if state.get('edit_space') == 'speed':
        colw = (lw - 8) / 2
        for group in (1, 2, 3, 4):
            col, rowi = (group - 1) % 2, (group - 1) // 2
            row = params_top + rowi * 32
            x = margin + col * (colw + 8)
            m.place(c, 'param%d_label' % group, x + 1, row + 7, 68, 18)
            m.place(c, 'param%d_value' % group, x + colw - 44, row + 7, 44, 18)
            tx, tw = x + 76, max(20, colw - 124)
            m.place(c, 'param%d_track' % group, tx, row + 13.5, tw, 5)
            m.place(c, 'param%d_hit' % group, tx - 8, row, tw + 16, 30)
            sliders[group] = (tx, row, tw)
    else:
        for group in (1, 2):
            row = params_top + (group - 1) * 28
            tx, tw = margin + 46, max(30, lw - 98)
            m.place(c, 'param%d_label' % group, margin + 1, row + 4, 40, 18)
            m.place(c, 'param%d_value' % group, margin + lw - 43, row + 4, 42, 18)
            m.place(c, 'param%d_track' % group, tx, row + 10.5, tw, 5)
            m.place(c, 'param%d_hit' % group, tx - 8, row, tw + 16, 26)
            sliders[group] = (tx, row, tw)
    cache['slider_layout'] = sliders
    m.set_button_label(c,'view_fit','适配');m.set_button_label(c,'view_in','＋');m.set_button_label(c,'view_out','−')
    view_tools_top = graph_top + 8
    m.set_visible(c,'view_group_bg',True)
    m.place(c,'view_group_bg',margin+8,view_tools_top,144,40)
    vx=margin+12
    for name,bw in zip(('view_fit','view_in','view_out'),(64,32,32)):
        m.place(c,name,vx,view_tools_top+4,bw,32);vx+=bw+4
    segment_x=margin+lw-136
    m.place(c,'segment_group_bg',segment_x,view_tools_top,136,40)
    m.place(c,'segment_prev',segment_x+4,view_tools_top+4,32,32)
    m.place(c,'segment_info',segment_x+40,view_tools_top+9,56,22)
    m.place(c,'segment_next',segment_x+100,view_tools_top+4,32,32)
    m.set_node_text(c,'segment_info','%d / %d'%(cache.get('speed_segment',0)+1,max(1,len(state.get('speed_params',[])))))
    preset_nav_top = header_top if wide else gt-38
    m.place(c,'preset_prev_page',gx,preset_nav_top,32,32)
    m.place(c,'preset_next_page',gx+gw-32,preset_nav_top,32,32)
    m.place(c,'preset_page_info',gx+36,preset_nav_top+2,gw-72,28)
    pages=max(1,math.ceil(len(m.preset_entries(c))/16));page=min(cache.get('preset_page',0),pages-1);cache['preset_page']=page
    m.set_node_text(c,'preset_page_info','%d / %d'%(page+1,pages))
    space_w=52.0
    space_x=margin+lw-32-8-(space_w*2+4)
    m.place(c,'space_value',space_x,header_top,space_w,32)
    m.place(c,'space_speed',space_x+space_w+4,header_top,space_w,32)
    for name in ('space_value','space_speed'):
        target=c.op(name);x=target.par.x.eval();bottom=target.par.y.eval()
        for suffix in ('_bg','_label'):m.place(c,name+suffix,x,height-bottom-32,space_w,32)
    m.set_node_text(c,'space_value_label','值');m.set_node_text(c,'space_speed_label','速度')
    drag_slot = cache.get('preset_drag')
    drop = cache.get('preset_drop_target')
    zone_w=min(240.0,lw-40)
    zone_x=margin+(lw-zone_w)/2;zone_top=graph_top+graph_h-38
    m.place(c,'preset_delete_zone',zone_x,zone_top,zone_w,30)
    m.place(c,'preset_delete_label',zone_x,zone_top+6,zone_w,18)
    m.set_node_text(c,'preset_delete_label','移动到位置 %02d'%((drop if drop is not None else 0)+1))
    m.set_visible(c,'preset_delete_zone',drag_slot is not None and drop is not None)
    m.set_visible(c,'preset_delete_label',drag_slot is not None and drop is not None)
    for name,label in (('view_fit','适配'),('view_in','＋'),('view_out','−'),('preset_prev_page','‹'),('preset_next_page','›'),('segment_prev','‹'),('segment_next','›')):
        target=c.op(name)
        x=target.par.x.eval();bottom=target.par.y.eval();w=target.par.w.eval();h=target.par.h.eval()
        for suffix in ('_bg','_label'):m.place(c,name+suffix,x,height-bottom-h,w,h)
        m.set_node_text(c,name+'_label',label)
    context=cache.get('preset_context');entries=m.page_entries(c)
    context_ok=isinstance(context,int) and 0<=context<len(entries)
    for name in ('preset_context_bg','preset_context_delete','preset_context_delete_bg','preset_context_delete_label','preset_context_export','preset_context_export_bg','preset_context_export_label'):
        m.set_visible(c,name,context_ok)
    if context_ok:
        cells=cache.get('preset_cells',[]);ox,oy=cache.get('preset_origin',(0.,0.));cx,cy,cw,ch=cells[context]
        px=max(8.,min(width-148.,ox+cx+cw+6));py=max(8.,min(height-82.,oy+cy+4))
        m.place(c,'preset_context_bg',px,py,140,74)
        m.place(c,'preset_context_delete',px+6,py+6,128,28)
        m.place(c,'preset_context_export',px+6,py+40,128,28)
        for name in ('preset_context_delete','preset_context_export'):
            target=c.op(name);x0=target.par.x.eval();bottom=target.par.y.eval()
            for suffix in ('_bg','_label'):m.place(c,name+suffix,x0,height-bottom-28,128,28)
        m.set_node_text(c,'preset_context_delete_label','删除所选')
        m.set_node_text(c,'preset_context_export_label','导出所选')
        for ch,value in zip('rgb',(.95,.32,.32)):c.op('preset_context_delete_label').par['fontcolor'+ch]=value
    m.place(c, 'preset_grid', gx, gt, gw, gh)
    m.set_visible(c, 'preset_grid', show_presets)
    c.op('plot_render').par.resolutionw = int(round(lw))
    c.op('plot_render').par.resolutionh = int(round(graph_h))
    c.op('plot_camera').par.orthowidth = lw
    c.op('preset_render').par.resolutionw = int(round(gw))
    c.op('preset_render').par.resolutionh = int(round(gh))
    c.op('preset_camera').par.orthowidth = gw
    cache['preset_cells'] = m.preset_grid_cells(c)
    cache['preset_origin'], cache['preset_visible'] = (gx, gt), show_presets
    for name in ('preset_prev_page','preset_next_page','preset_page_info'):
        for suffix in ('','_bg','_label'):m.set_visible(c,name+suffix,show_presets)
    m.update_preset_labels(c)
    m.set_node_text(c, 'equation', json_preview(c))
    update_slider_knobs(c, state)
    settings_layout(c)
    m.place(c, 'ui_icons', 0, 0, width, height)
    c.op('ui_icons_render').par.resolutionw = int(round(width))
    c.op('ui_icons_render').par.resolutionh = int(round(height))
    c.op('ui_icons_camera').par.orthowidth = width
    for name in ('curve_shape', 'speed_shape', 'handle_shape', 'anchor_shape', 'selected_keyframe_shape', 'grid_shape',
                 'grid_main_shape', 'playhead_shape', 'preset_cards_shape', 'preset_frames_shape',
                 'preset_selected_shape', 'preset_curves_shape', 'preset_hover_shape', 'ui_icons_shape',
                 'plot_render', 'preset_render'):
        target=c.op(name)
        if target:target.cook(force=True)



def preset_hover(c):
    m = logic(c)
    cache = m.st(c)
    hover = -1
    if cache.get('preset_visible') and not cache.get('modal_kind') and not cache.get('modal_amount', 0):
        for index in range(min(16, len(m.preset_entries(c)))):
            node = c.op('preset_hit_%02d' % (index + 1))
            if node and node.panel.rollover:
                hover = index
                break
    if cache.get('preset_hover_slot', -1) == hover:
        return
    cache['preset_hover_slot'] = hover
    if hover >= 0:
        cache['hover_draw_slot'] = hover
        c.op('preset_hover_shape').cook(force=True)


def motion(c, dt):
    m = logic(c)
    cache = m.st(c)
    state = m.state_from_component(c)
    reduced = state['reduce_motion']
    opened = bool(cache.get('settings_open', False))
    blocked = bool(cache.get('modal_kind')) or cache.get('modal_amount', 0.0) > 0
    for name, base in cache.get('button_targets', {}).items():
        node = c.op(name)
        if not node or not node.par.display.eval():
            continue
        hover = bool(node.panel.rollover) and not blocked
        pressed = bool(node.panel.lselect) and not blocked
        desired = base
        if hover:
            desired = (0.29, 0.29, 0.29) if base == NEUTRAL else cache.get('accent_color', SELECTED)
        if pressed:
            desired = tuple(v * 0.82 for v in desired)
        current = tween(cache, 'color_' + name, desired, dt, 0.15, reduced)
        color(node, 'color', current)
    preset_hover(c)
    hover_alpha = tween(cache, 'preset_alpha', 0.78 if cache.get('preset_hover_slot', -1) >= 0 else 0.0, dt, 0.15, reduced, 0.0)
    par(c.op('preset_hover_mat'), 'alpha', hover_alpha)
    for group in (1, 2, 3, 4):
        node = c.op('param%d_hit' % group)
        active = not blocked and (state['mode'] != 'bezier' or state.get('edit_space') == 'speed') and bool(node.panel.rollover or node.panel.lselect)
        pressed = not blocked and bool(node.panel.lselect)
        amount = tween(cache, 'slider_' + str(group), float(active), dt, 0.15, reduced, 0.0)
        cache['knob_size_%d' % group] = 15 + 2 * amount
        color(c.op('param%d_track_rounded' % group), 'fillcolor', (0.34 + 0.08 * amount,) * 3)
        par(c.op('param%d_halo' % group), 'opacity', amount * (0.24 if pressed else 0.12))
    update_slider_knobs(c, state)
    c.op('plugin_dialogs').module.motion(c, dt)
    message = cache.get('status', '就绪')
    if message != cache.get('status_seen'):
        cache['status_seen'], cache['status_age'] = message, 0.0
    cache['status_age'] = cache.get('status_age', 0.0) + dt
    hint = next((text for name, text in HINTS.items() if c.op(name) and c.op(name).par.display.eval() and c.op(name).panel.rollover), None)
    text = message if cache['status_age'] < 2.0 and message != '就绪' else (hint or '实时输出  ·  fade  /  257 samples')
    m.set_node_text(c, 'status', text)


def shape_icons(scriptOp):
    c = scriptOp.parent()
    m = logic(c)
    scriptOp.clear()
    width, height = float(c.par.w.eval()), float(c.par.h.eval())
    def line(points):
        poly = scriptOp.appendPoly(len(points), closed=False, addPoints=True)
        for vertex, (x, y) in zip(poly, points):
            vertex.point.x, vertex.point.y, vertex.point.z = x - width / 2, height / 2 - y, 0
    for name, (x, y, size) in m.st(c).get('icon_rects', {}).items():
        def stroke(points):
            line([(x + px * size, y + py * size) for px, py in points])
        if name == 'action_paste':
            stroke([(0.35,0.12),(0.8,0.12),(0.8,0.83),(0.2,0.83),(0.2,0.12),(0.35,0.12)])
            stroke([(0.35,0.06),(0.65,0.06),(0.65,0.26),(0.35,0.26),(0.35,0.06)])
        elif name == 'action_reset':
            # Connected rotate-ccw silhouette: 300-degree arc, then two arrow
            # wings at the same tip.  The previous arrow floated away from the arc.
            arc=[(0.5+0.375*math.cos(math.pi-i*(5*math.pi/3)/28),
                  0.5+0.375*math.sin(math.pi-i*(5*math.pi/3)/28)) for i in range(29)]
            stroke(arc+[(3/24,8/24)])
            stroke([(3/24,3/24),(3/24,8/24),(8/24,8/24)])
        elif name == 'action_reverse':
            stroke([(0.12,0.3),(0.88,0.3),(0.66,0.1)])
            stroke([(0.88,0.7),(0.12,0.7),(0.34,0.9)])
        elif name == 'action_save':
            stroke([(0.15,0.1),(0.7,0.1),(0.9,0.3),(0.9,0.9),(0.15,0.9),(0.15,0.1)])
            stroke([(0.32,0.1),(0.32,0.4),(0.65,0.4),(0.65,0.1)])
            stroke([(0.32,0.9),(0.32,0.6),(0.7,0.6),(0.7,0.9)])
        elif name == 'settings_open':
            stroke([(0.5+0.32*math.cos(i*math.tau/32),0.5+0.32*math.sin(i*math.tau/32)) for i in range(33)])
            stroke([(0.5+0.12*math.cos(i*math.tau/20),0.5+0.12*math.sin(i*math.tau/20)) for i in range(21)])
            for i in range(8):
                a=i*math.pi/4
                stroke([(0.5+0.32*math.cos(a),0.5+0.32*math.sin(a)),(0.5+0.44*math.cos(a),0.5+0.44*math.sin(a))])
