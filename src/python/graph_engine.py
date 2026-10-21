"""One viewport, derivative scale and handle mapping for every native graph mode."""
import math
import bisect
import time as wallclock


def logic(c):return c.op('curve_logic').module


def rgb(text):return tuple(int(text[i:i+2],16)/255 for i in (1,3,5))


def transform(c):
    m=logic(c);s=m.state_from_component(c)
    w,h,l,b,pw,ph=m.graph_layout(c)
    xmin,xmax=s['view_xmin'],s['view_xmax'];ymin,ymax=s['view_ymin'],s['view_ymax']
    def screen(x,y):return l+(x-xmin)/(xmax-xmin)*pw,b+(y-ymin)/(ymax-ymin)*ph
    def graph(x,y):return xmin+(x-l)/pw*(xmax-xmin),ymin+(y-b)/ph*(ymax-ymin)
    return (w,h,l,b,pw,ph),screen,graph


def speed_screen(data,l,b,pw,ph,u,value):
    normalized=.5 if data['speed_constant'] else max(0.,min(1.,(value-data['speed_min'])/data['speed_range']))
    return (l+u*pw,b+ph*(.04+.92*normalized))


def speed_handle_positions(c,state,segment):
    m=logic(c);data=render_data(c)
    w,h,l,b,pw,ph=m.graph_layout(c)
    a,z=state['keyframes'][segment:segment+2]
    span=max(1e-9,z['t']-a['t']);delta=z['v']-a['v']
    params=m.speed_parameters(state,segment)
    result={}
    for index in (0,1):
        u=a['t']+params[index*2]*span
        value=delta/span*params[index*2+1]
        result['speed'+str(index+1)]=speed_screen(data,l,b,pw,ph,u,value)
    return result


def render_data(c):
    m=logic(c);cache=m.st(c);s=m.state_from_component(c)
    key=(m.state_key(s,ignore_ui=True),s['precision'],int(c.op('graph').par.w.eval()))
    if cache.get('render_key')==key:return cache['render_data']
    width=float(c.op('graph').par.w.eval())
    count=m.math_model().sampling_count(s,width)
    cuts=m.speed_breakpoints(s, width=width)
    cut_gap=max(2.0/max(64.0,width-32.0), 2.0/max(2.0,count-1))
    us=sorted(set([i/(count-1) for i in range(count)]+[p for t in cuts for p in (max(0,t-cut_gap),t,min(1,t+cut_gap))]))
    values=[];speeds=[]
    for u in us:
        v,d=m.value_and_speed(s,u)
        if any(abs(cut-u)<=cut_gap for cut in cuts):d=math.nan
        values.append(v);speeds.append(d)
    finite=[v for v in speeds if math.isfinite(v)]
    ordered=sorted(abs(v) for v in finite)
    scale=max(ordered[min(len(ordered)-1,int(0.95*max(0,len(ordered)-1)))] if ordered else 0.0,1e-3)
    deltas=[abs(speeds[i]-speeds[i-1]) for i in range(1,len(speeds))
            if math.isfinite(speeds[i]) and math.isfinite(speeds[i-1])]
    median_delta=sorted(deltas)[len(deltas)//2] if deltas else 0.0
    jump_limit=max((max(finite)-min(finite))*0.35 if finite else 1.0,
                   median_delta*10.0, 0.25)
    ordered_values=sorted(finite)
    actual_min=ordered_values[0] if ordered_values else 0.0
    actual_max=ordered_values[-1] if ordered_values else 1.0
    speed_constant=abs(actual_max-actual_min)<1e-9
    # Use the robust display scale for both value-background and speed-page
    # mapping. Actual infinite/extreme derivatives remain mathematical data;
    # they no longer compress the useful trace or throw handles off-canvas.
    absolute_max=ordered[-1] if ordered else 1.0
    # Normal curves always keep their complete peak. Only genuine outliers use
    # the robust cap; values beyond that cap are broken, not drawn as a plateau.
    display_limit=min(absolute_max,scale*4.0)
    speed_min=-display_limit if actual_min<0 else 0.0
    speed_max=display_limit
    data={'u':us,'values':values,'speeds':speeds,'cuts':cuts,'scale':scale,
          'speed_jump_limit':jump_limit,
          'singular':any(math.isinf(x) for x in speeds),
          'speed_min':speed_min,
          'speed_max':speed_max,
          'speed_range':max(1e-3,speed_max-speed_min),
          'speed_constant':speed_constant}
    cache['render_key']=key;cache['render_data']=data
    return data



def apply_visuals(c):
    m=logic(c);s=m.state_from_component(c);cache=m.st(c)
    speed_view = s['mode']=='bezier' and s.get('edit_space')=='speed'
    key=(s['theme_color'],s['theme_background'],s['theme_handles'],s['speed_strength'],speed_view)
    if cache.get('graph_theme_key')==key:return
    cache['graph_theme_key']=key
    background=rgb(s['theme_background']);value=rgb(s['theme_color'])
    # Handles and knobs are intentionally independent of the accent theme.
    handles=rgb(s['theme_handles'])
    dim=tuple(a+(b-a)*s['speed_strength'] for a,b in zip(background,value))
    curve_color,speed_color=(dim,value) if speed_view else (value,dim)
    for name,color in (('curve_mat',curve_color),('handle_mat',tuple(x*.67 for x in handles)),
                       ('speed_mat',speed_color)):
        mat=c.op(name)
        if mat:
            for prefix in ('linenearcolor','linefarcolor'):
                for ch,v in zip('rgb',color):mat.par[prefix+ch]=v
    # Every accent-bearing native material shares the same theme role. Neutral
    # surfaces, text, danger colors and actual color-picker swatches stay semantic.
    for name,color in (('anchor_mat',handles),('selected_keyframe_mat',value),
                       ('preset_curves_mat',value),('preset_selected_mat',value),
                       ('preset_hover_mat',value),('ui_icons_mat',value)):
        mat=c.op(name)
        if mat:
            for ch,v in zip('rgb',color):mat.par['color'+ch]=v
    for name in ('param1_knob_rounded','param2_knob_rounded','param3_knob_rounded','param4_knob_rounded',
                 'param1_halo_rounded','param2_halo_rounded','param3_halo_rounded','param4_halo_rounded',
                 'settings_compact_knob_rounded','settings_motion_knob_rounded',
                 'settings_preset_size_knob_rounded','settings_speed_knob_rounded',
                 'dlg_compact_knob_rounded','dlg_motion_knob_rounded','dlg_auto_load_knob_rounded',
                 'dlg_show_speed_knob_rounded','dlg_precision_knob_rounded',
                 'dlg_speed_strength_knob_rounded','dlg_box_size_knob_rounded'):
        node=c.op(name)
        if node:
            for ch,v in zip('rgb',handles):node.par['fillcolor'+ch]=v
    for name in ('settings_preset_size_track_rounded','dlg_box_size_track_rounded',
                 'dlg_precision_track_rounded','dlg_speed_strength_track_rounded'):
        node=c.op(name)
        if node:
            for ch in 'rgb':node.par['fillcolor'+ch]=.38
    for ch,v in zip('rgb',background):c.op('graph_rounded').par['fillcolor'+ch]=v
    swatch=c.op('settings_theme_swatch_rounded')
    if swatch:
        for ch,v in zip('rgb',value):swatch.par['fillcolor'+ch]=v
    for name,color in (('dlg_swatch_curve',value),('dlg_swatch_handles',handles),('dlg_swatch_background',background)):
        node=c.op(name)
        if node:
            for ch,v in zip('rgb',color):node.par['bgcolor'+ch]=v



def shape(scriptOp,kind):
    c=scriptOp.parent();m=logic(c);s=m.state_from_component(c);cache=m.st(c)
    scriptOp.clear()
    (w,h,l,b,pw,ph),screen,_=transform(c)
    speed_view=s['mode']=='bezier' and s.get('edit_space')=='speed'
    def raw_line(points,closed=False):
        if len(points)<2:return
        poly=scriptOp.appendPoly(len(points),closed=closed,addPoints=True)
        for vertex,(x,y) in zip(poly,points):vertex.point.x,vertex.point.y,vertex.point.z=x-w*.5,y-h*.5,0
    def clip(a,z):
        dx,dy=z[0]-a[0],z[1]-a[1];lo,hi=0.,1.
        for p,q in ((-dx,a[0]-l),(dx,l+pw-a[0]),(-dy,a[1]-b),(dy,b+ph-a[1])):
            if abs(p)<1e-12:
                if q<0:return None
            else:
                t=q/p
                if p<0:lo=max(lo,t)
                else:hi=min(hi,t)
                if lo>hi:return None
        return ((a[0]+lo*dx,a[1]+lo*dy),(a[0]+hi*dx,a[1]+hi*dy))
    def line(points):
        segment=[]
        for a,z in zip(points,points[1:]):
            edge=clip(a,z)
            if not edge:
                raw_line(segment);segment=[];continue
            first,last=edge
            if segment and abs(segment[-1][0]-first[0])+abs(segment[-1][1]-first[1])>1e-5:
                raw_line(segment);segment=[]
            if not segment:segment=[first]
            segment.append(last)
        raw_line(segment)
    def marker(x,y,square=False,radius=3.8):
        px,py=screen(x,y)
        if not l-1<=px<=l+pw+1 or not b-1<=py<=b+ph+1:return
        r=radius
        if square:points=[(px-r,py-r),(px+r,py-r),(px+r,py+r),(px-r,py+r)]
        else:points=[(px+r*math.cos(i*math.tau/24),py+r*math.sin(i*math.tau/24)) for i in range(24)]
        raw_line(points,True)
    if kind in ('grid','grid_main'):
        nx,ny=s['grid_x'],s['grid_y']
        if kind=='grid':
            for i in range(1,nx):line([screen(i/nx,s['view_ymin']),screen(i/nx,s['view_ymax'])])
            for i in range(1,ny):line([screen(s['view_xmin'],i/ny),screen(s['view_xmax'],i/ny)])
        else:
            for x in (0,1):line([screen(x,s['view_ymin']),screen(x,s['view_ymax'])])
            for y in (0,1):line([screen(s['view_xmin'],y),screen(s['view_xmax'],y)])
        return
    if kind in ('curve','speed'):
        if kind=='curve' and speed_view:return
        if kind=='speed' and not speed_view and (not s['show_speed'] or s['mode']!='bezier'):return
        data=render_data(c);points=[];last_u=None;last_value=None
        for u,value in zip(data['u'],data['values'] if kind=='curve' else data['speeds']):
            interrupted=not math.isfinite(value)
            if kind=='speed' and not interrupted and abs(value)>data['speed_max']:interrupted=True
            if kind=='speed' and last_u is not None:
                k=bisect.bisect_right(data['cuts'],last_u+1e-11)
                crosses_cut=k<len(data['cuts']) and data['cuts'][k]<u-1e-11
                jumps=(last_value is not None and abs(value-last_value)>data['speed_jump_limit'])
                if crosses_cut or jumps:
                    line(points);points=[]
            if interrupted:
                line(points);points=[];last_u=u;last_value=None;continue
            point=screen(u,value) if kind=='curve' else speed_screen(data,l,b,pw,ph,u,value)
            points.append(point);last_u=u;last_value=value
        line(points);return
    if kind=='handle':
        if speed_view:
            segment=int(m.clamp(cache.get('speed_segment',0),0,len(s['speed_params'])-1))
            data=render_data(c)
            for point in speed_handle_positions(c,s,segment).values():
                zero=speed_screen(data,l,b,pw,ph,0,0)
                line([(point[0],zero[1]),point])
        elif s['mode']=='bezier':
            keys=s['keyframes']
            if len(keys)==2:
                line([screen(keys[0]['t'],keys[0]['v']),screen(*keys[0]['right'])])
                line([screen(keys[-1]['t'],keys[-1]['v']),screen(*keys[-1]['left'])])
            else:
                index=int(m.clamp(cache.get('selected_keyframe',1),0,len(keys)-1));item=keys[index]
                if index>0:line([screen(item['t'],item['v']),screen(*item['left'])])
                if index+1<len(keys):line([screen(item['t'],item['v']),screen(*item['right'])])
        elif s['mode']=='elastic':
            positions=m.elastic_handle_positions(s)
            for name,(x,y) in positions.items():
                root=0. if s['direction']=='in' else 1.
                if s['direction']=='inout':root=1.
                line([screen(x,root),screen(x,y)])
        return
    if kind=='anchor':
        if speed_view:
            segment=int(m.clamp(cache.get('speed_segment',0),0,len(s['speed_params'])-1))
            for px,py in speed_handle_positions(c,s,segment).values():
                raw_line([(px+3.8*math.cos(i*math.tau/24),py+3.8*math.sin(i*math.tau/24)) for i in range(24)],True)
            return
        if s['mode']=='bezier':
            keys=s['keyframes']
            for item in keys:
                marker(item['t'],item['v'],item['t'] in (0.,1.))
            # Handle endpoints are real controls, not just decorative lines.
            # Visible circles make their hit targets discoverable in both the
            # legacy single-segment editor and the multi-keyframe editor.
            if len(keys)==2:
                marker(*keys[0]['right'])
                marker(*keys[-1]['left'])
            else:
                index=int(m.clamp(cache.get('selected_keyframe',1),0,len(keys)-1))
                if index>0:marker(*keys[index]['left'])
                if index+1<len(keys):marker(*keys[index]['right'])
        elif s['mode']=='elastic':
            for x,y in m.elastic_handle_positions(s).values():marker(x,y,True)
        else:marker(*m.bounce_handle_position(s))
        return
    if kind=='selected_keyframe':
        if s['mode']=='bezier' and not speed_view and len(s['keyframes'])>2:
            selected=int(m.clamp(cache.get('selected_keyframe',1),0,len(s['keyframes'])-1))
            indices={selected}
            selected_range=cache.get('easecopy_range')
            if isinstance(selected_range,(tuple,list)) and len(selected_range)==2:
                a,b=sorted((int(selected_range[0]),int(selected_range[1])))
                indices.update(range(max(0,a),min(len(s['keyframes'])-1,b)+1))
            for index in indices:
                item=s['keyframes'][index];px,py=screen(item['t'],item['v'])
                raw_line([(px+6.5*math.cos(i*math.tau/32),py+6.5*math.sin(i*math.tau/32)) for i in range(32)],True)
        return
    if kind=='head':
        u=cache.get('u',0.)
        if speed_view:
            _,speed=m.value_and_speed(s,u)
            if speed is None or not math.isfinite(speed):return
            x,y=speed_screen(render_data(c),l,b,pw,ph,u,speed)
        else:
            v=m.evaluate(s,u);x,y=screen(u,v)
        if l<=x<=l+pw and b<=y<=b+ph:
            line([(x-3,y),(x+3,y)]);line([(x,y-3),(x,y+3)])



def panel_event(c,kind):
    m=logic(c);cache=m.st(c)
    if cache.get('modal_kind') or cache.get('modal_amount',0)>0:return
    if cache.pop('preset_context',None) is not None:m.layout_ui(c)
    s=m.state_from_component(c);graph=c.op('graph')
    (w,h,l,b,pw,ph),screen,to_graph=transform(c)
    x,y=float(graph.panel.u)*w,float(graph.panel.v)*h
    speed_view=s['mode']=='bezier' and s.get('edit_space')=='speed'
    if kind=='context':
        if speed_view or s['mode']!='bezier':return
        keys=s['keyframes']
        nearest=min((((x-screen(item['t'],item['v'])[0])**2+(y-screen(item['t'],item['v'])[1])**2,i)
                     for i,item in enumerate(keys)),default=(1e12,-1))
        if nearest[0]<=14**2:
            index=nearest[1]
            easecopy=c.op('easecopy')
            if easecopy:easecopy.module.select_keyframe(c,index,True)
        return
    if kind=='press':
        cache['drag_before']=m.dumps_state(s);cache['drag']=None
        if speed_view:
            segment=int(m.clamp(cache.get('speed_segment',0),0,len(s['speed_params'])-1))
            points=speed_handle_positions(c,s,segment)
            distance,name=min(((x-px)**2+(y-py)**2,n) for n,(px,py) in points.items())
            if distance<=18**2:
                cache['drag']=name
            elif len(s['speed_params'])>1:
                u=m.clamp((x-l)/pw,0.,1.)
                cache['speed_segment']=m._segment_index(s,u)
                cache['points']=None;m.update(c)
            return
        if s['mode']=='bezier':
            keys=s['keyframes'];candidates=[]
            if len(keys)==2:
                candidates=[('bezier1',screen(*keys[0]['right'])),('bezier2',screen(*keys[-1]['left']))]
            else:
                selected=int(m.clamp(cache.get('selected_keyframe',1),0,len(keys)-1));item=keys[selected]
                if selected>0:candidates.append(('handle_%d_left'%selected,screen(*item['left'])))
                if selected+1<len(keys):candidates.append(('handle_%d_right'%selected,screen(*item['right'])))
            keypoints=[('keyframe_%d'%i,screen(item['t'],item['v'])) for i,item in enumerate(keys)]
            nearest_handle=min((((x-px)**2+(y-py)**2,n) for n,(px,py) in candidates),default=(1e12,''))
            nearest_key=min((((x-px)**2+(y-py)**2,n) for n,(px,py) in keypoints),default=(1e12,''))
            if nearest_key[0]<=14**2 and nearest_key[0]<=nearest_handle[0]:
                index=int(nearest_key[1].rsplit('_',1)[1]);cache['selected_keyframe']=index
                try: extend=bool(float(graph.panel.shift)) or bool(cache.get('key_shift',False))
                except Exception: extend=bool(cache.get('key_shift',False))
                easecopy=c.op('easecopy')
                if easecopy:easecopy.module.select_keyframe(c,index,extend)
                cache['drag']=nearest_key[1] if 0<index<len(keys)-1 else None
                cache.pop('curve_press',None)
                for node in ('handle_shape','anchor_shape','selected_keyframe_shape'):c.op(node).cook(force=True)
                return
            if nearest_handle[0]<=14**2:
                cache['drag']=nearest_handle[1];cache.pop('curve_press',None);return
            gx,gy=to_graph(x,y);u=m.clamp(gx,0.,1.)
            value=m.evaluate(s,u);px,py=screen(u,value)
            near=abs(y-py)<=14 and l<=x<=l+pw
            now=wallclock.time();previous=cache.get('curve_press')
            double=previous and now-previous[0]<.38 and abs(x-previous[1])+abs(y-previous[2])<=18
            if near and double:
                updated,index=m.add_keyframe_at(s,u)
                if index is not None:
                    cache['selected_keyframe']=index;m.assign_state(c,updated)
                    m.set_status(c,'已添加关键帧 %02d · 拖动点或手柄调整'%(index+1))
                    m.update(c)
                cache.pop('curve_press',None)
            else:
                cache['curve_press']=(now,x,y) if near else None
            return
        points=m.elastic_handle_positions(s) if s['mode']=='elastic' else {'bounce_control':m.bounce_handle_position(s)}
        distance,name=min(((x-screen(*p)[0])**2+(y-screen(*p)[1])**2,name) for name,p in points.items())
        if distance<=18**2:cache['drag']=name
    name=cache.get('drag')
    if name and kind in ('press','move','release'):
        gx,gy=to_graph(x,y)
        if name.startswith('speed'):
            segment=int(m.clamp(cache.get('speed_segment',0),0,len(s['speed_params'])-1))
            a,z=s['keyframes'][segment:segment+2];span=max(1e-9,z['t']-a['t']);delta=z['v']-a['v']
            params=m.speed_parameters(s,segment);i=int(name[-1])-1
            params[i*2]=m.clamp(((x-l)/pw-a['t'])/span,0.,1.)
            data=render_data(c)
            current_global=delta/span*params[i*2+1]
            current=speed_screen(data,l,b,pw,ph,a['t']+params[i*2]*span,current_global)
            desired_global=current_global+(y-current[1])*data['speed_range']/(.92*ph)
            params[i*2+1]=m.clamp(desired_global/(delta/span) if abs(delta)>1e-9 else 0.,0.,m.math_model().VEL_MAX)
            m.set_speed_parameters(s,segment,params)
            m.assign_state(c,s);m.update(c)
            if kind=='release':cache['drag']=None;cache['range_lock']=None
            return
        if name.startswith('keyframe_'):
            index=int(name.rsplit('_',1)[1]);updated=m.move_keyframe(s,index,gx,gy)
            m.assign_state(c,updated);m.update(c)
        elif name.startswith('handle_'):
            _,idx,side=name.rsplit('_',2);updated=m.move_keyframe_handle(s,int(idx),side,gx,gy)
            m.assign_state(c,updated);m.update(c)
        elif name.startswith('bezier'):
            index=0 if name=='bezier1' else 1;side='right' if name=='bezier1' else 'left'
            updated=m.move_keyframe_handle(s,index,side,gx,gy)
            c.par.Selectedhandle=1 if name=='bezier1' else 2
            m.assign_state(c,updated);m.update(c)
        else:
            if s.get('model')!='continuous-v3':
                s['model']='continuous-v3'
                s['frequency']=max(.5,1/max(s['period'],.0001));s['elastic_gain']=s['amplitude']-1
                s['restitution']=s['damping'];s['bounce_period']=max(.0001,1/max(1,s['bounces']))
            current=m.math_model().drag_handle(s,name,gx,gy)
            m.assign_state(c,current,preserve_ui=True);m.update(c)
        if kind=='release' and s['mode']=='bezier':
            current=m.state_from_component(c);keys=current['keyframes'];point=None
            if name.startswith('bezier'):
                point=keys[0]['right'] if name=='bezier1' else keys[-1]['left']
            elif name.startswith('handle_'):
                _,idx,side=name.rsplit('_',2);point=keys[int(idx)][side]
            elif name.startswith('keyframe_'):
                item=keys[int(name.rsplit('_',1)[1])];point=(item['t'],item['v'])
            if point and expand_view_to_point(current,*point):
                m.assign_state(c,current);m.update(c)
    if kind=='release':cache['drag']=None;cache['range_lock']=None



def bezier_control_points(state):
    if state['mode']!='bezier':return []
    points=[]
    for item in state['keyframes']:
        points.extend([(item['t'],item['v']),tuple(item['left']),tuple(item['right'])])
    return points


def expand_view_to_point(state,x,y):
    """Expand only when needed; never shrink or recenter the user's current view."""
    if not all(math.isfinite(v) for v in (x,y)):return False
    changed=False
    for axis,value in (('x',x),('y',y)):
        low=state['view_'+axis+'min'];high=state['view_'+axis+'max']
        pad=max(.05,(high-low)*.06)
        if value<low:
            state['view_'+axis+'min']=value-pad;changed=True
        elif value>high:
            state['view_'+axis+'max']=value+pad;changed=True
    return changed


def action(c,name):
    if name not in ('view_fit','view_in','view_out'):return False
    m=logic(c);s=m.state_from_component(c)
    if name=='view_fit' and s['mode']=='bezier' and s.get('edit_space')=='speed':
        s.update({'view_xmin':-0.05,'view_xmax':1.05,'view_ymin':m.DEFAULTS['view_ymin'],'view_ymax':m.DEFAULTS['view_ymax']})
        m.assign_state(c,s);m.st(c)['layout_key']=None;m.update(c)
        return True
    if name=='view_fit':
        data=render_data(c)
        vals=[v for v in data['values'] if math.isfinite(v)]+[0.,1.]
        points=[]
        if s['mode']=='bezier':points.extend(bezier_control_points(s))
        elif s['mode']=='elastic':points.extend(m.elastic_handle_positions(s).values())
        elif s['mode']=='bounce':points.append(m.bounce_handle_position(s))
        for px,py in points:
            if math.isfinite(px) and math.isfinite(py):
                vals.append(py)
        low,high=min(vals),max(vals);pad=max(.1,(high-low)*.12)
        xs=[0.,1.]+[px for px,py in points if math.isfinite(px)]
        xmin,xmax=min(xs),max(xs)
        xpad=max(.12,(xmax-xmin)*.12)
        s.update({'view_xmin':xmin-xpad,'view_xmax':xmax+xpad,'view_ymin':low-pad,'view_ymax':high+pad})
    else:
        scale=.8 if name=='view_in' else 1.25
        for axis in ('x','y'):
            a,b=s['view_'+axis+'min'],s['view_'+axis+'max'];mid=(a+b)/2;span=(b-a)*scale/2
            s['view_'+axis+'min'],s['view_'+axis+'max']=mid-span,mid+span
    m.assign_state(c,s);m.st(c)['layout_key']=None;m.update(c)
    return True
