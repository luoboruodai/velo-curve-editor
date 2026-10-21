import bisect
import copy
import json
import math
import time as wallclock

SAMPLES = 257
PARAM_NAMES = ('X1', 'Y1', 'X2', 'Y2')
MODES = ('bezier', 'elastic', 'bounce')
DIRECTIONS = ('in', 'out', 'inout')
DEFAULTS = {
    'mode': 'bezier',
    'direction': 'out',
    'x1': 1/3,
    'y1': 1/3,
    'x2': 2/3,
    'y2': 2/3,
    'amplitude': 1.0,
    'period': 0.3,
    'bounces': 4,
    'damping': 0.45,
    'compact': False,
    'preset_location': 'right',
    'preset_size': 80.0,
    'show_speed': True,
    'reduce_motion': False,
    'model': 'continuous-v3',
    'edit_space': 'value', 'vx1': 1/3, 'vy1': 1.0, 'vx2': 2/3, 'vy2': 1.0,
    'keyframes': [], 'speed_params': [],
    'elastic_gain': 0.5, 'frequency': 2.0, 'decay': 5.0,
    'restitution': 0.5, 'bounce_period': 0.5,
    'grid_x': 4, 'grid_y': 4, 'precision': 300,
    'speed_strength': 0.28, 'theme_color': '#4a90e2',
    'theme_background': '#222222', 'theme_handles': '#dcdcdc',
    'auto_load_preset': True,
    'view_xmin': -0.15, 'view_xmax': 1.15,
    'view_ymin': -0.15, 'view_ymax': 1.25,
    'preset_order': [], 'hidden_builtins': [],
}
PRESETS = {
    'linear': {'mode': 'bezier', 'points': (0.0, 0.0, 1.0, 1.0)},
    'fast': {'mode': 'bezier', 'points': (1 / 3, 2 / 3, 2 / 3, 1.0)},
    'slow': {'mode': 'bezier', 'points': (0.65, 0.0, 0.9, 0.3)},
    'smooth': {'mode': 'bezier', 'points': (0.42, 0.0, 0.58, 1.0)},
    'sine_in': {'mode': 'bezier', 'points': (0.47, 0.0, 0.745, 0.715)},
    'sine_out': {'mode': 'bezier', 'points': (0.39, 0.575, 0.565, 1.0)},
    'sine_inout': {'mode': 'bezier', 'points': (0.445, 0.05, 0.55, 0.95)},
    'quad_in': {'mode': 'bezier', 'points': (0.55, 0.085, 0.68, 0.53)},
    'quad_out': {'mode': 'bezier', 'points': (0.25, 0.46, 0.45, 0.94)},
    'quad_inout': {'mode': 'bezier', 'points': (0.455, 0.03, 0.515, 0.955)},
    'cubic_in': {'mode': 'bezier', 'points': (0.55, 0.055, 0.675, 0.19)},
    'cubic_out': {'mode': 'bezier', 'points': (0.215, 0.61, 0.355, 1.0)},
    'cubic_inout': {'mode': 'bezier', 'points': (0.645, 0.045, 0.645, 1.0)},
    'quart_in': {'mode': 'bezier', 'points': (0.895, 0.03, 0.895, 0.22)},
    'quart_out': {'mode': 'bezier', 'points': (0.165, 0.84, 0.44, 1.0)},
    'quart_inout': {'mode': 'bezier', 'points': (0.77, 0.0, 0.77, 1.0)},
    'elastic_in': {'mode': 'elastic', 'direction': 'in'},
    'elastic_out': {'mode': 'elastic', 'direction': 'out'},
    'elastic_inout': {'mode': 'elastic', 'direction': 'inout'},
    'bounce_in': {'mode': 'bounce', 'direction': 'in'},
    'bounce_out': {'mode': 'bounce', 'direction': 'out'},
    'bounce_inout': {'mode': 'bounce', 'direction': 'inout'},
}
PRESET_LABELS = {
    'linear': '线性', 'fast': '快速', 'slow': '缓慢', 'smooth': '平滑',
    'sine_in': 'Sine In', 'sine_out': 'Sine Out', 'sine_inout': 'Sine I/O',
    'quad_in': 'Quad In', 'quad_out': 'Quad Out', 'quad_inout': 'Quad I/O',
    'cubic_in': 'Cubic In', 'cubic_out': 'Cubic Out', 'cubic_inout': 'Cubic I/O',
    'quart_in': 'Quart In', 'quart_out': 'Quart Out', 'quart_inout': 'Quart I/O',
    'elastic_in': 'Elastic In', 'elastic_out': 'Elastic Out', 'elastic_inout': 'Elastic I/O',
    'bounce_in': 'Bounce In', 'bounce_out': 'Bounce Out', 'bounce_inout': 'Bounce I/O',
}
CACHE = {}
UI_KEYS = ('compact','preset_location','preset_size','show_speed','reduce_motion','grid_x','grid_y','precision','speed_strength','theme_color','theme_background','theme_handles','auto_load_preset','preset_order','hidden_builtins','view_xmin','view_xmax','view_ymin','view_ymax')

def math_model():
    try:
        owner=me.parent()
    except NameError:
        import curve_model
        return curve_model
    return owner.op('curve_model').module


def clamp(value, low, high):
    return max(low, min(high, value))


def _sync_legacy_controls(state):
    first, second = state['keyframes'][0], state['keyframes'][1]
    state['x1'], state['y1'] = first['right']
    state['x2'], state['y2'] = second['left']
    state['vx1'], state['vy1'], state['vx2'], state['vy2'] = state['speed_params'][0]
    return state


def _handle_pair(value, fallback):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return [float(value[0]), float(value[1])]
        except (TypeError, ValueError):
            pass
    return list(fallback)


def handle_model():
    try:
        owner = me.parent()
    except NameError:
        import bezier_handles
        return bezier_handles
    return owner.op('bezier_handles').module


def _finite_coordinate(value, fallback):
    return handle_model().finite(value, fallback)


def _cubic_x_monotonic(points):
    return handle_model().cubic_x_monotonic(points)


def _nearest_monotonic_x(points, control, current, desired):
    return handle_model().nearest_monotonic_x(points, control, current, desired)


def _normalized_keyframes(state):
    raw = state.get('keyframes')
    result = []
    if isinstance(raw, list) and 2 <= len(raw) <= 16:
        for item in raw:
            if not isinstance(item, dict):
                result = []
                break
            try:
                t, v = float(item['t']), float(item['v'])
            except (KeyError, TypeError, ValueError):
                result = []
                break
            result.append({'t': t, 'v': v,
                           'left': _handle_pair(item.get('left'), (t - .1, v)),
                           'right': _handle_pair(item.get('right'), (t + .1, v))})
    if not result:
        result = [
            {'t': 0.0, 'v': 0.0, 'left': [0.0, 0.0], 'right': [state['x1'], state['y1']]},
            {'t': 1.0, 'v': 1.0, 'left': [state['x2'], state['y2']], 'right': [1.0, 1.0]},
        ]
    result.sort(key=lambda item: item['t'])
    times = [clamp(item['t'], 0.0, 1.0) for item in result]
    for i in range(1, len(times)):
        times[i] = max(times[i], times[i - 1] + .001)
    for i in range(len(times) - 2, -1, -1):
        times[i] = min(times[i], times[i + 1] - .001)
    if times[0] < 0.0:
        return _normalized_keyframes({})
    times[0], times[-1] = 0.0, 1.0
    for i, item in enumerate(result):
        t = times[i]
        item['t'] = t
        item['v'] = 0.0 if i == 0 else 1.0 if i == len(result) - 1 else _finite_coordinate(item['v'], 0.0)
        left, right = item['left'], item['right']
        if i == 0:
            left = [0.0, 0.0]
        if i == len(result) - 1:
            right = [1.0, 1.0]
        # Y is intentionally unbounded (finite only). X is checked against the
        # actual cubic derivative below rather than a fixed anchor/unit clamp.
        item['left'] = [_finite_coordinate(left[0], t), _finite_coordinate(left[1], item['v'])]
        item['right'] = [_finite_coordinate(right[0], t), _finite_coordinate(right[1], item['v'])]
    return _time_ordered_keys(result)


def normalized_state(source=None):
    source=source or {}
    state=dict(DEFAULTS)
    aliases={'X1':'x1','Y1':'y1','X2':'x2','Y2':'y2','Curvemode':'mode','Curvedirection':'direction','Presetboxsize':'preset_size','Showspeed':'show_speed'}
    for key,value in source.items(): state[aliases.get(key,key)]=value
    if 'model' not in source and any(k in source for k in ('amplitude','period','bounces','damping')):
        state['model']='legacy-v2'
    state['mode']=state['mode'] if state['mode'] in MODES else 'bezier'
    state['direction']=state['direction'] if state['direction'] in DIRECTIONS else 'out'
    for key in ('compact','show_speed','reduce_motion','auto_load_preset'):state[key]=bool(state[key])
    if state['preset_location'] not in ('right','left','top','bottom'):state['preset_location']='right'
    for key in ('x1','y1','x2','y2'):state[key]=_finite_coordinate(state[key],DEFAULTS[key])
    for key,low,high in (('amplitude',1.,2.),('period',.05,1.),('damping',0.,1.),('preset_size',40.,104.),
                         ('elastic_gain',0.,1.),('frequency',.5,32.),('decay',1.,20.),
                         ('restitution',0.,math.sqrt(.999)),('bounce_period',1e-4,2.),('speed_strength',.05,.65)):
        state[key]=clamp(float(state[key]),low,high)
    state['bounces']=int(clamp(round(float(state['bounces'])),1,8))
    state['preset_order']=[str(v) for v in state.get('preset_order',[]) if isinstance(v,(str,int))] if isinstance(state.get('preset_order'),list) else []
    state['hidden_builtins']=[v for v in state.get('hidden_builtins',[]) if isinstance(v,str) and v in PRESETS] if isinstance(state.get('hidden_builtins'),list) else []
    for key,low,high in (('grid_x',1,20),('grid_y',1,20),('precision',50,1000)):
        state[key]=int(clamp(round(float(key and state[key])),low,high))
    if state.get('edit_space') not in ('value','speed'):state['edit_space']='value'
    for key in ('vx1','vx2'):state[key]=clamp(float(state[key]),0.,1.)
    for key in ('vy1','vy2'):state[key]=clamp(float(state[key]),0.,math_model().VEL_MAX)
    for key in ('view_xmin','view_xmax','view_ymin','view_ymax'):state[key]=float(state[key])
    for key in ('theme_color','theme_background','theme_handles'):
        v=str(state[key]);state[key]=v if len(v)==7 and v.startswith('#') and all(k in '0123456789abcdefABCDEF' for k in v[1:]) else DEFAULTS[key]
    state['keyframes']=_normalized_keyframes(state)
    raw_speed=state.get('speed_params')
    params=[]
    for i in range(len(state['keyframes'])-1):
        legacy=[state['vx1'],state['vy1'],state['vx2'],state['vy2']]
        if i==0 and any(k in source for k in ('vx1','vy1','vx2','vy2')):
            candidate=legacy
        else:
            candidate=raw_speed[i] if isinstance(raw_speed,list) and i<len(raw_speed) else None
        if not isinstance(candidate,(list,tuple)) or len(candidate)!=4:
            candidate=legacy if i==0 else [1/3,1.,2/3,1.]
        try:
            vx1,vy1,vx2,vy2=(float(v) for v in candidate)
        except (TypeError,ValueError):
            vx1,vy1,vx2,vy2=1/3,1.,2/3,1.
        params.append([clamp(vx1,0.,1.),clamp(vy1,0.,math_model().VEL_MAX),
                       clamp(vx2,0.,1.),clamp(vy2,0.,math_model().VEL_MAX)])
    state['speed_params']=params
    return _sync_legacy_controls(state)


def state_key(state, ignore_ui=False):
    return json.dumps({k:v for k,v in state.items() if not ignore_ui or k not in UI_KEYS},
                      ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def speed_parameters(state,index=0):
    index=int(clamp(index,0,len(state['speed_params'])-1))
    if index==0:
        return [state['vx1'],state['vy1'],state['vx2'],state['vy2']]
    return list(state['speed_params'][index])


def set_speed_parameters(state,index,params):
    """Apply Motion4-style influences/endpoint speeds to the shared value cubic."""
    index=int(clamp(index,0,len(state['speed_params'])-1))
    requested=[float(v) for v in params]
    a,b=state['keyframes'][index:index+2]
    span=max(1e-9,b['t']-a['t']);delta=b['v']-a['v']
    x1=clamp(requested[0],1e-4,1.-1e-4)
    x2=clamp(requested[2],1e-4,1.-1e-4)
    x2=max(x1,x2)
    if abs(delta)<1e-9:
        a['right']=[a['t']+x1*span,a['v']]
        b['left']=[a['t']+x2*span,a['v']]
        effective=[x1,0.,x2,0.]
    else:
        # Endpoint speed is dy/dx, not a sampled interior speed.  Clamp the
        # corresponding local value controls to keep the speed-editor fade
        # monotone and report the effective (possibly limited) speed back.
        y1=clamp(clamp(requested[1],0.,math_model().VEL_MAX)*x1,0.,1.)
        y2=clamp(1.-clamp(requested[3],0.,math_model().VEL_MAX)*(1.-x2),0.,1.)
        a['right']=[a['t']+x1*span,a['v']+y1*delta]
        b['left']=[a['t']+x2*span,a['v']+y2*delta]
        effective=[x1,y1/x1,x2,(1.-y2)/(1.-x2)]
    state['speed_params'][index]=effective
    if index==0:
        state['vx1'],state['vy1'],state['vx2'],state['vy2']=effective
    return state


def keyframe_count(state):
    return len(state.get('keyframes',[]))



def preset_state(name):
    if name not in PRESETS:
        raise ValueError('unknown preset')
    spec = PRESETS[name]
    state = normalized_state()
    state['mode'] = spec['mode']
    state['direction'] = spec.get('direction', 'out')
    if 'points' in spec:
        state['x1'], state['y1'], state['x2'], state['y2'] = spec['points']
        # normalized_state() has already created default keyframes; legacy
        # preset coordinates must replace them rather than be ignored.
        state['keyframes'] = []
        state['speed_params'] = []
    return normalized_state(state)


def bezier_coordinate(t, a, b):
    return 3 * (1 - t) * (1 - t) * t * a + 3 * (1 - t) * t * t * b + t * t * t


def bezier_derivative(t, a, b):
    return 3 * (1 - t) * (1 - t) * a + 6 * (1 - t) * t * (b - a) + 3 * t * t * (1 - b)


def _segment_index(state,u):
    times=[item['t'] for item in state['keyframes']]
    return int(clamp(bisect.bisect_right(times,u)-1,0,len(times)-2))


def _segment_points(state,index):
    a,b=state['keyframes'][index:index+2]
    return [(a['t'],a['v']),tuple(a['right']),tuple(b['left']),(b['t'],b['v'])]


def _cubic(points,t):
    u=1-t
    weights=(u*u*u,3*u*u*t,3*u*t*t,t*t*t)
    return tuple(sum(w*p[i] for w,p in zip(weights,points)) for i in (0,1))


def _cubic_derivative(points,t):
    u=1-t
    return tuple(3*((points[1][i]-points[0][i])*u*u+
                    (points[2][i]-points[1][i])*2*u*t+
                    (points[3][i]-points[2][i])*t*t) for i in (0,1))


def _cubic_parameter_x(points,u):
    lo,hi,t=0.0,1.0,clamp(u,0.,1.)
    for _ in range(14):
        x=_cubic(points,t)[0];error=x-u
        if abs(error)<1e-10:break
        if error<0:lo=t
        else:hi=t
        dx=_cubic_derivative(points,t)[0]
        candidate=t-error/dx if abs(dx)>1e-10 else (lo+hi)*.5
        t=candidate if lo<candidate<hi else (lo+hi)*.5
    for _ in range(8):
        if abs(_cubic(points,t)[0]-u)<1e-9:break
        t=(lo+hi)*.5
        if _cubic(points,t)[0]<u:lo=t
        else:hi=t
    return clamp(t,0.,1.)


def _segment_endpoint_speed(points,end=False):
    if end:a,b=points[3],points[2]
    else:a,b=points[0],points[1]
    dx,dy=b[0]-a[0],b[1]-a[1]
    if abs(dx)<1e-12:
        return 0.0 if abs(dy)<1e-12 else math.copysign(math.inf,dy)
    return dy/dx


def bezier_value_and_speed(u, state):
    if u<=0.:return state['keyframes'][0]['v'],None
    if u>=1.:return state['keyframes'][-1]['v'],None
    points=_segment_points(state,_segment_index(state,u))
    t=_cubic_parameter_x(points,u)
    dx,dy=_cubic_derivative(points,t)
    speed=dy/dx if abs(dx)>0.01 else None
    return _cubic(points,t)[1],speed



def elastic_out(u, state):
    if u <= 0.0 or u >= 1.0:
        return 0.0 if u <= 0.0 else 1.0
    amplitude = state['amplitude']
    period = state['period']
    shift = period / (2 * math.pi) * math.asin(1.0 / amplitude)
    return 1.0 + amplitude * 2 ** (-10 * u) * math.sin((u - shift) * 2 * math.pi / period)


def bounce_out(u, state):
    if u <= 0.0 or u >= 1.0:
        return 0.0 if u <= 0.0 else 1.0
    exponent = 1.0 + 3.0 * state['damping']
    envelope = (1.0 - u) ** exponent
    return 1.0 - envelope * abs(math.cos(state['bounces'] * math.pi * u))


def directed_value(u, state, base):
    direction = state['direction']
    if direction == 'in':
        return 1.0 - base(1.0 - u, state)
    if direction == 'out':
        return base(u, state)
    if u < 0.5:
        return (1.0 - base(1.0 - 2.0 * u, state)) * 0.5
    return 1.0 - (1.0 - base(2.0 * u - 1.0, state)) * 0.5


def evaluate(state,u):
    state=normalized_state(state) if not isinstance(state,dict) else state
    u=clamp(float(u),0.,1.)
    if state['mode']=='bezier' and state.get('edit_space')=='speed':return value_and_speed(state,u)[0]
    if state['mode']=='bezier':return bezier_value_and_speed(u,state)[0]
    if u<=0:return 0.0
    if u>=1:return 1.0
    if state.get('model')=='continuous-v3':return math_model().directed_pair(u,state)[0]
    return directed_value(u,state,elastic_out if state['mode']=='elastic' else bounce_out)


def value_and_speed(state,u):
    u=clamp(float(u),0.,1.)
    if state['mode']=='bezier' and state.get('edit_space')=='speed':
        index=_segment_index(state,u)
        a,b=state['keyframes'][index:index+2]
        span=max(1e-9,b['t']-a['t']);local=clamp((u-a['t'])/span,0.,1.)
        params=speed_parameters(state,index)
        local_state=dict(zip(('vx1','vy1','vx2','vy2'),params))
        value,speed=math_model().velocity_value_and_speed(local,local_state)
        delta=b['v']-a['v']
        return a['v']+delta*value,delta/span*speed
    if state['mode']=='bezier':
        value,speed=bezier_value_and_speed(u,state)
        if u in (0.,1.):
            if len(state['keyframes'])==2:
                speed=math_model().endpoint_speed(state['x1'],state['y1'],state['x2'],state['y2'],u==1.)
            else:
                speed=_segment_endpoint_speed(_segment_points(state,0 if u==0 else len(state['keyframes'])-2),u==1.)
        if speed is not None:return value,speed
    elif state.get('model')=='continuous-v3':
        value,speed=math_model().directed_pair(u,state)
        return (0. if u==0 else 1. if u==1 else value),speed
    value=evaluate(state,u)
    h=1e-5
    if u<=h:speed=(evaluate(state,2*h)-evaluate(state,h))/h
    elif u>=1-h:speed=(evaluate(state,1-h)-evaluate(state,1-2*h))/h
    else:speed=(evaluate(state,u+h)-evaluate(state,u-h))/(2*h)
    return value,speed



def sample_curve(state, count=SAMPLES):
    state = normalized_state(state)
    count = max(2, int(count))
    values = []
    speeds = []
    for index in range(count):
        u = index / (count - 1)
        value, speed = value_and_speed(state, u)
        values.append(value)
        speeds.append(speed)
    values[0], values[-1] = 0.0, 1.0
    return values, speeds


def speed_breakpoints(state, width=None):
    if state['mode']=='bezier' and len(state['keyframes'])>2:
        return tuple(item['t'] for item in state['keyframes'][1:-1])
    if state['mode']!='bounce':return ()
    if state.get('model')=='continuous-v3':return math_model().breakpoints(state, width=width)
    cusps=[(i+.5)/state['bounces'] for i in range(state['bounces'])]
    if state['direction']=='out':return tuple(cusps)
    if state['direction']=='in':return tuple(sorted(1-u for u in cusps))
    return tuple(sorted([(1-u)*.5 for u in cusps]+[(1+u)*.5 for u in cusps]))



def reverse_state(state):
    state = normalized_state(state)
    if state['mode'] == 'bezier':
        reversed_keys=[]
        for item in reversed(state['keyframes']):
            reversed_keys.append({'t':1.-item['t'],'v':1.-item['v'],
                                  'left':[1.-item['right'][0],1.-item['right'][1]],
                                  'right':[1.-item['left'][0],1.-item['left'][1]]})
        state['keyframes']=reversed_keys
        state['speed_params']=[]
        return normalized_state(state)
    if state['direction'] != 'inout':
        state['direction'] = 'out' if state['direction'] == 'in' else 'in'
    return state



def dumps_state(state):
    state=normalized_state(state)
    curve={key:state[key] for key in ('mode','direction','model','elastic_gain','frequency','decay','restitution','bounce_period','amplitude','period','bounces','damping')}
    curve['bezier']=[state[k] for k in ('x1','y1','x2','y2')]
    curve['edit_space']=state['edit_space']
    curve['velocity']=[state[k] for k in ('vx1','vy1','vx2','vy2')]
    curve['keyframes']=copy.deepcopy(state['keyframes'])
    curve['speed_params']=copy.deepcopy(state['speed_params'])
    return json.dumps({'format':'td-curve-editor','version':4,'curve':curve},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)



def loads_state(text):
    data=json.loads(text)
    if data.get('format')!='td-curve-editor' or data.get('version') not in (2,3,4):raise ValueError('unsupported curve format')
    cv=data['curve'];points=cv['bezier']
    if len(points)!=4 or not all(math.isfinite(float(v)) for v in points):raise ValueError('invalid control points')
    state={'mode':cv['mode'],'direction':cv.get('direction','out')}
    state.update(dict(zip(('x1','y1','x2','y2'),points)))
    if data['version']==2:
        state.update({'model':'legacy-v2','amplitude':cv['elastic']['amplitude'],'period':cv['elastic']['period'],'bounces':cv['bounce']['bounces'],'damping':cv['bounce']['damping']})
    else:
        for key in ('model','elastic_gain','frequency','decay','restitution','bounce_period','amplitude','period','bounces','damping'):
            if key in cv:state[key]=cv[key]
        if cv.get('edit_space') in ('value','speed'):state['edit_space']=cv['edit_space']
        vel=cv.get('velocity')
        if isinstance(vel,list) and len(vel)==4 and all(math.isfinite(float(v)) for v in vel):
            state.update(dict(zip(('vx1','vy1','vx2','vy2'),vel)))
        if data['version']==4:
            if isinstance(cv.get('keyframes'),list):state['keyframes']=cv['keyframes']
            if isinstance(cv.get('speed_params'),list):state['speed_params']=cv['speed_params']
    return normalized_state(state)



def value_points_from_velocity(state, samples=9):
    """Materialize speed controls into value handles; no least-squares refit."""
    state=normalized_state(state)
    if state['mode']!='bezier' or state.get('edit_space')!='speed':return state
    for index in range(len(state['keyframes'])-1):
        set_speed_parameters(state,index,speed_parameters(state,index))
    return normalized_state(state)


def fit_velocity_points(state):
    """Read exact endpoint derivatives and influences from every value segment."""
    state=normalized_state(state)
    if state['mode']!='bezier':return state
    state['keyframes']=_time_ordered_keys(copy.deepcopy(state['keyframes']))
    params=[]
    for index in range(len(state['keyframes'])-1):
        a,b=state['keyframes'][index:index+2]
        span=max(1e-9,b['t']-a['t']);delta=b['v']-a['v']
        if abs(delta)<1e-9:
            params.append([1/3,0.,2/3,0.]);continue
        x1=(a['right'][0]-a['t'])/span;y1=(a['right'][1]-a['v'])/delta
        x2=(b['left'][0]-a['t'])/span;y2=(b['left'][1]-a['v'])/delta
        # Every linear segment has infinitely many identical handle layouts;
        # choose the conventional 33%/67% controls so speed editing starts sane.
        if abs(y1-x1)<1e-7 and abs(y2-x2)<1e-7:
            params.append([1/3,1.,2/3,1.]);continue
        start=math_model().endpoint_speed(x1,y1,x2,y2,False)
        end=math_model().endpoint_speed(x1,y1,x2,y2,True)
        if not math.isfinite(start):start=math_model().VEL_MAX if start>0 else 0.
        if not math.isfinite(end):end=math_model().VEL_MAX if end>0 else 0.
        params.append([clamp(x1,0.,1.),clamp(start,0.,math_model().VEL_MAX),
                       clamp(x2,0.,1.),clamp(end,0.,math_model().VEL_MAX)])
    state['speed_params']=params
    state['vx1'],state['vy1'],state['vx2'],state['vy2']=params[0]
    return normalized_state(state)


def add_keyframe_at(state,u):
    """Split one cubic at an exact x position, preserving the visible curve."""
    state=normalized_state(state)
    if state['mode']!='bezier' or len(state['keyframes'])>=16:return state,None
    u=clamp(float(u),.001,.999)
    index=_segment_index(state,u)
    points=_segment_points(state,index)
    t=_cubic_parameter_x(points,u)
    p01=tuple(points[0][i]+(points[1][i]-points[0][i])*t for i in (0,1))
    p12=tuple(points[1][i]+(points[2][i]-points[1][i])*t for i in (0,1))
    p23=tuple(points[2][i]+(points[3][i]-points[2][i])*t for i in (0,1))
    p012=tuple(p01[i]+(p12[i]-p01[i])*t for i in (0,1))
    p123=tuple(p12[i]+(p23[i]-p12[i])*t for i in (0,1))
    point=tuple(p012[i]+(p123[i]-p012[i])*t for i in (0,1))
    keys=copy.deepcopy(state['keyframes'])
    keys[index]['right']=list(p01)
    keys[index+1]['left']=list(p23)
    keys.insert(index+1,{'t':point[0],'v':point[1],'left':list(p012),'right':list(p123)})
    state['keyframes']=keys
    state=fit_velocity_points(state)
    return normalized_state(state),index+1


def _time_ordered_keys(keys):
    # Handle order itself is not the requirement: x'(t) >= 0 is. Preserve
    # crossing/out-of-segment handles when valid; repair only invalid segments.
    for a,b in zip(keys,keys[1:]):
        points = [(a['t'],a['v']),tuple(a['right']),tuple(b['left']),(b['t'],b['v'])]
        if not _cubic_x_monotonic(points):
            a['right'][0] = clamp(a['right'][0],a['t'],b['t'])
            b['left'][0] = clamp(b['left'][0],a['t'],b['t'])
    return keys


def move_keyframe(state,index,x,y):
    state=normalized_state(state);keys=copy.deepcopy(state['keyframes'])
    if not 0<index<len(keys)-1:return state
    old=keys[index]
    x=clamp(x,keys[index-1]['t']+.02,keys[index+1]['t']-.02)
    y=_finite_coordinate(y,old['v']);dx,dy=x-old['t'],y-old['v']
    old['t'],old['v']=x,y
    old['left']=[old['left'][0]+dx,old['left'][1]+dy]
    old['right']=[old['right'][0]+dx,old['right'][1]+dy]
    state['keyframes']=_time_ordered_keys(keys)
    return normalized_state(state)


def move_keyframe_handle(state,index,side,x,y):
    return handle_model().move(state,index,side,x,y,normalized_state)


def _ensure_handle_parameters(c):
    cache = st(c)
    if cache.get('handle_ranges_ready'):
        return
    handle_model().ensure_parameters(c)
    cache['handle_ranges_ready'] = True


def st(c):
    return CACHE.setdefault(c.id, {
        'points': None, 'drag': None, 'time': 0.0, 'last': None, 'u': 0.0,
        'sample_key': None, 'status': '双击曲线添加关键帧', 'sync_key': None,
        'speed_segment': 0, 'selected_keyframe': 1, 'easecopy_range': None,
    })


def par_value(c, name, default):
    try:
        return getattr(c.par, name).eval()
    except Exception:
        return default


def state_from_component(c):
    _ensure_handle_parameters(c)
    target = c.op('state_store')
    raw = target.text if target else ''
    points = tuple(par_value(c, name, DEFAULTS[key])
                   for name, key in zip(PARAM_NAMES, ('x1','y1','x2','y2')))
    cache = st(c)
    key = (raw, points)
    if cache.get('component_state_key') != key:
        stored = {}
        if raw.strip():
            try:
                candidate = json.loads(raw)
                if isinstance(candidate, dict):stored = candidate
            except (ValueError, TypeError):pass
        if stored.get('keyframes'):
            baseline = normalized_state(stored)
            legacy = (baseline['x1'], baseline['y1'], baseline['x2'], baseline['y2'])
            if any(abs(a-b)>1e-12 for a,b in zip(points,legacy)):
                keys = copy.deepcopy(stored['keyframes'])
                keys[0]['right'] = [points[0], points[1]]
                keys[1]['left'] = [points[2], points[3]]
                stored['keyframes'] = keys
        stored.update(zip(PARAM_NAMES, points))
        cache['component_state'] = normalized_state(stored)
        cache['component_state_key'] = key
    # Callers edit their returned state before assigning it; never expose the cache.
    return copy.deepcopy(cache['component_state'])


def assign_state(c, state, preserve_ui=False):
    _ensure_handle_parameters(c)
    state = normalized_state(state)
    if preserve_ui:
        current = state_from_component(c)
        for key in UI_KEYS:
            state[key] = current[key]
    target = c.op('state_store')
    if target:
        target.text = json.dumps(state, ensure_ascii=False, sort_keys=True)
    for name, key in zip(PARAM_NAMES, ('x1', 'y1', 'x2', 'y2')):
        try:
            c.par[name] = state[key]
        except Exception:
            pass



def samples(c):
    cache=st(c);state=state_from_component(c)
    key=state_key(state,ignore_ui=True)
    if cache.get('sample_key')!=key:
        v,s=sample_curve(state)
        cache.update({'sample_key':key,'values':v,'speeds':s})
    return cache['values'],cache['speeds']



def values(c):
    return samples(c)[0]


def speed_values(c):
    return samples(c)[1]


def display_range(data, required):
    finite = [v for v in data if math.isfinite(v)]
    low = min(finite + list(required))
    high = max(finite + list(required))
    span = high - low
    if span < 1e-6:
        low -= 0.1
        high += 0.1
        span = high - low
    padding = span * 0.08
    return low - padding, high + padding


def ranges(c):
    state=state_from_component(c)
    data=[v for v in speed_values(c) if math.isfinite(v)]
    extent=max([abs(v) for v in data]+[1e-3])
    return ((state['view_ymin'],state['view_ymax']),(-extent,extent))


def graph_layout(c):
    graph = c.op('graph')
    width = max(1.0, float(graph.par.w.eval()))
    height = max(1.0, float(graph.par.h.eval()))
    left, top, right, bottom = 16.0, 16.0, 16.0, 16.0
    return width, height, left, top, max(1.0, width - left - right), max(1.0, height - top - bottom)


def update_equation(c, state):
    if state['mode'] == 'bezier':
        text = dumps_state(state)
    elif state['mode'] == 'elastic':
        text = 'elastic-%s  A %.2f  P %.2f' % (state['direction'], state['amplitude'], state['period'])
    else:
        text = 'bounce-%s  N %d  D %.2f' % (state['direction'], state['bounces'], state['damping'])
    if c.par.Equation.eval() != text:
        c.par.Equation = text


def set_status(c, text):
    st(c)['status'] = text
    target = c.op('status')
    if target and target.par.text.eval() != text:
        target.par.text = text


def status_text(c):
    return st(c)['status']


BUTTON_NEUTRAL = (0.235, 0.235, 0.235)
BUTTON_SELECTED = (0.29, 0.565, 0.886)


def set_button_state(c, name, selected):
    if not c.op(name):
        return
    targets = st(c).setdefault('button_targets', {})
    targets[name] = st(c).get('accent_color',BUTTON_SELECTED) if selected else BUTTON_NEUTRAL



def update_button_styles(c, state):
    cache = st(c)
    cache['accent_color']=c.op('graph_engine').module.rgb(state['theme_color'])
    selected_handle = int(par_value(c, 'Selectedhandle', 1))
    key = (state['mode'], selected_handle, state.get('compact'), state.get('preset_location'), cache.get('settings_open'), state.get('edit_space'), state['theme_color'])
    if cache.get('button_style_key') == key:
        return
    cache['button_style_key'] = key
    for mode in MODES:
        set_button_state(c, 'mode_' + mode, state['mode'] == mode)
    for index in (1, 2):
        set_button_state(c, 'select%d' % index, state['mode'] == 'bezier' and selected_handle == index)
    set_button_state(c, 'settings_open', bool(cache.get('settings_open', False)))
    set_button_state(c, 'settings_compact', bool(state.get('compact', False)))
    set_button_state(c, 'easecopy_passthrough', bool(c.op('easecopy').module.clipboard(c)['preserve_passthrough']))
    set_button_state(c, 'settings_location', state.get('preset_location') == 'bottom')
    set_button_state(c, 'space_value', state.get('edit_space') != 'speed')
    set_button_state(c, 'space_speed', state.get('edit_space') == 'speed')
    for name in (
        'direction_cycle', 'preset_next', 'action_copy', 'action_paste', 'action_reset',
        'action_reverse', 'action_save', 'nudge_left', 'nudge_right', 'nudge_up',
        'nudge_down', 'param1_down', 'param1_up', 'param2_down', 'param2_up', 'settings_close',
        'view_fit','view_in','view_out','preset_prev_page','preset_next_page','preset_apply',
        'segment_prev','segment_next','preset_context_delete','preset_context_export',
        'easecopy_copy','easecopy_paste_ease','easecopy_paste_value','easecopy_clear',
    ):
        set_button_state(c, name, False)



def update_button_motion(c, dt):
    c.op('ui_style').module.motion(c, dt)


def update(c):
    cache = st(c)
    state = state_from_component(c)
    curve_key = state_key(state,ignore_ui=True)
    view_key = tuple(state[k] for k in ('view_xmin','view_xmax','view_ymin','view_ymax'))
    entries = page_entries(c)
    catalogue_key = (cache.get('preset_entries_key'), cache.get('preset_page',0),
                     tuple(cache.get('preset_cells',())), cache.get('preset_visible'))
    # Selection follows preset identity, not content equality: two saved presets
    # may hold identical curves and must never light up together.  When the
    # curve diverges from the selected entry, the highlight clears.
    selected_id = cache.get('selected_preset')
    selected = ()
    if selected_id:
        match = next((i for i, entry in enumerate(entries) if entry[0] == selected_id), None)
        if match is None and selected_id and not selected_id.startswith('preset_hit_'):
            match = next((i for i, entry in enumerate(preset_entries(c)) if entry[0] == selected_id), None)
            if match is not None:
                match = next((i for i, entry in enumerate(entries) if entry[0] == selected_id), -1)
        if isinstance(match, int) and match >= 0:
            if same_curve(state, entries[match][2]):
                selected = (match,)
            else:
                cache.pop('selected_preset', None)
    keys = {
        'output': curve_key,
        'plot': (curve_key, view_key, state['precision'], state['show_speed'], cache.get('speed_segment',0), cache.get('selected_keyframe',1),cache.get('easecopy_range')),
        'grid': (view_key, state['grid_x'], state['grid_y']),
        'catalogue': catalogue_key,
        'selection': (catalogue_key, selected),
    }
    previous = cache.setdefault('render_update_keys', {})
    groups = {
        'output': ('curve_values',),
        'plot': ('curve_shape','speed_shape','handle_shape','anchor_shape','selected_keyframe_shape','playhead_shape'),
        'grid': ('grid_shape','grid_main_shape'),
        'catalogue': ('preset_cards_shape','preset_curves_shape'),
        'selection': ('preset_frames_shape','preset_selected_shape','preset_hover_shape'),
    }
    for group, names in groups.items():
        if previous.get(group) != keys[group]:
            previous[group] = keys[group]
            for name in names:
                target = c.op(name)
                if target:target.cook(force=True)
            if group == 'catalogue':update_preset_labels(c)
    key = (tuple(state.items()), float(par_value(c,'Duration',2.0)))
    if key != cache.get('points'):
        cache['points'] = key
        update_equation(c, state)
        update_controls(c, state)
    update_button_styles(c, state)
    sync_to_parent(c)


def fill_chop(scriptOp):
    c = scriptOp.parent()
    scriptOp.clear()
    scriptOp.numSamples = SAMPLES
    scriptOp.appendChan('fade').vals = values(c)


def elastic_handle_positions(state):
    if state.get('model')=='continuous-v3':return math_model().handles(state)
    return {'elastic_control':(.5*state['period'],2-state['amplitude']),'elastic_decay':(1.,state['period'])}


def bounce_handle_position(state):
    if state.get('model')=='continuous-v3':return math_model().handles(state)['bounce_control']
    return (state['period']*(state['damping']+1)*.5,1-state['damping']**2)


def shape(scriptOp,kind):
    scriptOp.parent().op('graph_engine').module.shape(scriptOp,kind)


def set_node_text(c, name, text):
    target = c.op(name)
    if target and target.par.text.eval() != text:
        target.par.text = text


def set_button_label(c, name, text):
    target = c.op(name)
    if any(ord(character) > 127 for character in text) and not text.startswith('\ufeff'):
        text = '\ufeff' + text
    if target and target.par.label.eval() != text:
        target.par.label = text


def set_visible(c, name, visible):
    target = c.op(name)
    if not target:
        return
    for par_name in ('display', 'enable'):
        if hasattr(target.par, par_name):
            current = bool(getattr(target.par, par_name).eval())
            if current != bool(visible):
                target.par[par_name] = bool(visible)


def place(c, name, x, top, width, height):
    target = c.op(name)
    if not target:
        return
    root_height = float(c.par.h.eval())
    for par_name, value in (
        ('x', float(x)), ('y', float(root_height - top - height)),
        ('w', float(width)), ('h', float(height)),
    ):
        current = getattr(target.par, par_name).eval()
        # Integer panel parameters round on assignment. Comparing their rounded
        # readback with a fractional target otherwise writes/cooks every frame.
        if isinstance(current, int):value = int(round(value))
        if abs(current - value) > 1e-6:
            target.par[par_name] = value
    rounded = c.op(name + '_rounded')
    if rounded:
        for par_name, value in (('resolutionw', int(round(width))), ('resolutionh', int(round(height)))):
            if int(rounded.par[par_name].eval()) != value:
                rounded.par[par_name] = max(1, value)


def preset_entries(c):
    state=state_from_component(c);cache=st(c)
    target=c.op('user_presets');raw=target.text if target else ''
    key=(state['mode'],raw,tuple(state.get('preset_order',[])),tuple(state.get('hidden_builtins',[])))
    if cache.get('preset_entries_key')!=key:
        names=[name for name,spec in PRESETS.items() if spec['mode']==state['mode']]
        entries=[(name,PRESET_LABELS[name],preset_state(name)) for name in names]
        for i,entry in enumerate(user_presets(c)):
            value=normalized_state(entry['curve']);value['_thumbnail']=entry.get('thumbnail',{'type':'graph'});value['_library_name']=entry['name']
            entries.append(('preset_user_%d'%(i+1),entry['name'],value))
        entries=c.op('preset_layout').module.sort_entries(c,entries)
        cache['preset_entries']=entries;cache['preset_entries_key']=key
    return cache['preset_entries']


def page_entries(c):
    page=st(c).get('preset_page',0)
    return preset_entries(c)[page*16:page*16+16]


def preset_grid_spec(c, count, wide):
    """Keep card geometry stable when entries are added or removed."""
    count = max(1, count)
    # A partially filled page keeps the same grid as a full one. In particular,
    # deleting the second side-bar card must not expand the survivor to one column.
    columns = 2 if wide else (4 if count <= 8 else 8)
    rows = (count + columns - 1) // columns
    return columns, rows


def preset_grid_cells(c):
    grid=c.op('preset_grid');width,height=float(grid.par.w.eval()),float(grid.par.h.eval())
    count=len(page_entries(c));s=state_from_component(c);card=s['preset_size']
    wide=s['preset_location'] in ('left','right') and c.par.w.eval()>=680 and c.par.h.eval()>=480 and not s['compact']
    columns,rows=preset_grid_spec(c,count,wide)
    margin,gap=(5.,4.) if wide else (8.,8.)
    cell_width=max(8.,(width-margin*2-gap*(columns-1))/columns)
    cell_height=max(8.,min(card,(height-margin*2-gap*(rows-1))/rows))
    return [(margin+(slot%columns)*(cell_width+gap),margin+(slot//columns)*(cell_height+gap),cell_width,cell_height) for slot in range(count)]


def update_preset_labels(c):
    q=st(c);cells=q.get('preset_cells',[]);entries=page_entries(c);show=q.get('preset_visible',False)
    ox,oy=q.get('preset_origin',(0.,0.))
    for i in range(16):
        suffix='%02d'%(i+1);active=show and i<len(entries) and i<len(cells)
        names=('preset_slot_'+suffix,'preset_hit_'+suffix,'preset_thumbtext_'+suffix,'preset_thumbimage_'+suffix)
        thumb=entries[i][2].get('_thumbnail',{}) if i<len(entries) else {}
        label=entries[i][1] if i<len(entries) else ''
        if i<len(cells):
            limit=max(3,int((cells[i][2]-8)/5.5))
            if len(label)>limit:label=label[:limit-1]+'…'
        set_node_text(c,names[0],label)
        if i<len(cells):
            x,y,w,h=cells[i]
            place(c,names[0],ox+x+4,oy+y+h-19,max(1,w-8),15)
            place(c,names[1],ox+x,oy+y,w,h)
            for name in names[2:]:place(c,name,ox+x+6,oy+y+5,max(1,w-12),max(1,h-28))
        set_visible(c,names[0],active);set_visible(c,names[1],active)
        set_visible(c,names[2],active and thumb.get('type')=='text')
        set_visible(c,names[3],active and thumb.get('type')=='image' and bool(c.op(thumb.get('node',''))))
        if active and thumb.get('type')=='text':set_node_text(c,names[2],thumb.get('value',entries[i][1]))
        if active and thumb.get('type')=='image' and c.op(thumb.get('node','')):c.op(names[3]).par.top=thumb['node']


def parameter_control(state,group):
    if state.get('model')=='continuous-v3':
        spec={'elastic':(('elastic_gain',0.,1.),('frequency',.5,10.)), 'bounce':(('restitution',0.,math.sqrt(.999)),('bounce_period',1e-4,2.))}
    else:spec={'elastic':(('amplitude',1.,2.),('period',.05,1.)), 'bounce':(('bounces',1,8),('damping',0.,1.))}
    if state['mode'] not in spec or not 1<=group<=len(spec[state['mode']]):return None
    return spec[state['mode']][group-1]


def slider_value(state, group, u):
    control = parameter_control(state, group)
    if control is None:
        return None
    parameter, low, high = control
    value = low + clamp(float(u), 0.0, 1.0) * (high - low)
    return int(round(value)) if parameter == 'bounces' else value


def update_slider_knobs(c, state):
    c.op('ui_style').module.update_slider_knobs(c, state)


def update_controls(c, state):
    c.op('ui_style').module.controls(c, state)


def update_settings_visibility(c):
    c.op('plugin_dialogs').module.sync(c)


def update_settings_layout(c):
    c.op('plugin_dialogs').module.layout(c)


def layout_ui(c):
    c.op('ui_style').module.layout_ui(c)


def slider_display_ratio(state, group, segment=0):
    """Normalized knob position; ease-out is displayed as influence, not vx2."""
    if state.get('edit_space') == 'speed':
        params=speed_parameters(state,segment)
        if group == 1:return clamp(params[0], 0.0, 1.0)
        if group == 2:return clamp(1.0 - params[2], 0.0, 1.0)
        if group == 3:return clamp(params[1] / 4.0, 0.0, 1.0)
        if group == 4:return clamp(params[3] / 4.0, 0.0, 1.0)
        return 0.0
    spec = parameter_control(state, group)
    if spec is None:return 0.0
    key, low, high = spec
    return clamp((state[key] - low) / (high - low), 0.0, 1.0)



def slider_event(c, group, kind):
    if kind not in ('press', 'move'):
        return
    state = state_from_component(c)
    if state.get('edit_space') == 'speed':
        segment=int(clamp(st(c).get('speed_segment',0),0,len(state['speed_params'])-1))
        params=speed_parameters(state,segment)
        u = clamp(c.op('ui_style').module.slider_ratio(c, group), 0.0, 1.0)
        if group == 1:params[0] = u
        elif group == 2:params[2] = 1.0 - u
        elif group == 3:params[1] = clamp(u * 4.0, 0.0, math_model().VEL_MAX)
        elif group == 4:params[3] = clamp(u * 4.0, 0.0, math_model().VEL_MAX)
        else:return
        set_speed_parameters(state,segment,params)
        assign_state(c, state)
        update(c)
        return
    control = parameter_control(state, group)
    if control is None:
        return
    hit = c.op('param%d_hit' % group)
    value = slider_value(state, group, c.op('ui_style').module.slider_ratio(c, group))
    parameter = control[0]
    if state[parameter] == value:
        return
    state[parameter] = value
    assign_state(c, state)
    update(c)



def settings_slider_event(c, kind):
    if kind not in ('press', 'move'):
        return
    hit = c.op('settings_preset_size_hit')
    if not hit:
        return
    state = state_from_component(c)
    state['preset_size'] = 56.0 + c.op('ui_style').module.settings_ratio(c) * 48.0
    assign_state(c, state)
    st(c)['layout_key'] = None
    update(c)
    layout_ui(c)


def same_curve(first,second):
    first,second=normalized_state(first),normalized_state(second)
    if first['mode']!=second['mode'] or first['direction']!=second['direction']:return False
    if first['mode']=='bezier':
        if first.get('edit_space','value')!=second.get('edit_space','value'):return False
        if first.get('edit_space','value')=='value' and (len(first['keyframes'])>2 or len(second['keyframes'])>2):
            return first['keyframes']==second['keyframes']
        if first.get('edit_space','value')=='speed' and (len(first['speed_params'])>1 or len(second['speed_params'])>1):
            return first['speed_params']==second['speed_params']
        keys=('x1','y1','x2','y2') if first.get('edit_space','value')=='value' else ('vx1','vy1','vx2','vy2')
    elif first.get('model')!=second.get('model'):return False
    elif first.get('model')=='continuous-v3':keys=('elastic_gain','frequency','decay') if first['mode']=='elastic' else ('restitution','bounce_period')
    else:keys=('amplitude','period') if first['mode']=='elastic' else ('bounces','damping')
    return all(abs(first[k]-second[k])<1e-5 for k in keys)


def shape_preset(scriptOp, name):
    c = scriptOp.parent()
    scriptOp.clear()
    grid = c.op('preset_grid')
    width = max(1.0, float(grid.par.w.eval()))
    height = max(1.0, float(grid.par.h.eval()))

    def line(points, closed=False):
        if not points:
            return
        poly = scriptOp.appendPoly(len(points), closed=closed, addPoints=True)
        for vertex, (x, y) in zip(poly, points):
            vertex.point.x, vertex.point.y, vertex.point.z = x - width * 0.5, y - height * 0.5, 0.0

    def rounded_points(x, y, cell_width, cell_height, radius=4):
        radius = min(radius, cell_width * 0.5, cell_height * 0.5)
        points = [(x + radius, y), (x + cell_width - radius, y)]
        corners = (
            (x + cell_width - radius, y + radius, -90),
            (x + cell_width - radius, y + cell_height - radius, 0),
            (x + radius, y + cell_height - radius, 90),
            (x + radius, y + radius, 180),
        )
        for cx, cy, start in corners:
            for step in range(5):
                angle = math.radians(start + step * 22.5)
                points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        return points

    if name == 'preset_bg_shape':
        line([(0, 0), (width, 0), (width, height), (0, height)], closed=True)
        return
    cells = st(c).get('preset_cells') or preset_grid_cells(c)
    entries = page_entries(c)
    current = state_from_component(c)
    for slot, entry in enumerate(entries[:len(cells)]):
        action, label, state = entry
        x, top, cell_width, cell_height = cells[slot]
        cell_y = height - top - cell_height
        rounded = rounded_points(x + 1, cell_y + 1, cell_width - 2, cell_height - 2)
        if name == 'preset_cards_shape':
            line(rounded, closed=True)
            continue
        selected_here = action == st(c).get('selected_preset') and same_curve(state, current)
        if name == 'preset_hover_shape':
            if slot == st(c).get('hover_draw_slot', -1) and not selected_here:
                line(rounded)
            continue
        if name in ('preset_frames_shape', 'preset_selected_shape'):
            if (name == 'preset_frames_shape' and not selected_here) or (name == 'preset_selected_shape' and selected_here):
                line(rounded)
            continue
        if state.get('_thumbnail',{}).get('type','graph')!='graph':continue
        data = sample_curve(state, 65)[0]
        low, high = display_range(data, (0.0, 1.0))
        thumb_width = max(1.0, cell_width - 16)
        thumb_height = max(6.0, cell_height - 34)
        points = []
        for index, value in enumerate(data):
            px = x + 8 + index / (len(data) - 1) * thumb_width
            py = cell_y + 26 + (value - low) / (high - low) * thumb_height
            points.append((px, py))
        line(points)
        for px, py in (points[0], points[-1]):
            line([
                (px + 2 * math.cos(i * math.tau / 16), py + 2 * math.sin(i * math.tau / 16))
                for i in range(17)
            ])


def preset_event(c):
    if not st(c).get('preset_visible'):
        return
    grid = c.op('preset_grid')
    x = float(grid.panel.u) * float(grid.par.w.eval())
    y = float(grid.panel.v) * float(grid.par.h.eval())
    grid_height = float(grid.par.h.eval())
    entries = page_entries(c)
    for slot, (cx, cy, width, cell_height) in enumerate(st(c).get('preset_cells', [])):
        cell_y = grid_height - cy - cell_height
        if cx <= x <= cx + width and cell_y <= y <= cell_y + cell_height and slot < len(entries):
            st(c)['cycle_index'] = slot
            button(c, entries[slot][0])
            return


def delete_user_preset(c, index):
    return c.op('preset_layout').module.delete_user(c,index)


def move_user_preset(c, source_index, target_slot):
    target=target_slot if target_slot<len(page_entries(c)) else 10**9
    return c.op('preset_layout').module.move(c,'preset_user_%d'%(source_index+1),target)


def preset_drop_slot(c,x,y):
    grid=c.op('preset_grid');cells=st(c).get('preset_cells',[])
    if not cells:return None
    gx,gy=float(grid.par.x.eval()),float(grid.par.y.eval());gh=float(grid.par.h.eval())
    nearest=None;distance=1e12
    for slot,(cx,cy,w,h) in enumerate(cells):
        px=gx+cx+w*.5;py=gy+gh-cy-h*.5
        d=(x-px)**2+(y-py)**2
        if d<distance:distance,nearest=d,slot
    limit=max(36.,max(max(cell[2],cell[3]) for cell in cells)*1.2)
    return nearest if distance<=limit*limit else None


def preset_card_pointer(c, slot):
    """Global component coords from the pressed card's own panel values."""
    hit = c.op('preset_hit_%02d' % (slot + 1))
    if not hit:
        return None
    return (float(hit.par.x.eval()) + float(hit.panel.u) * float(hit.par.w.eval()),
            float(hit.par.y.eval()) + float(hit.panel.v) * float(hit.par.h.eval()))


def preset_card_event(c, slot, kind):
    """Left click loads; right click manages; drag reorders any preset card."""
    cache = st(c)
    entries = page_entries(c)
    if kind=='context':
        if 0<=slot<len(entries):
            cache['preset_context']=slot;cache['selected_preset']=entries[slot][0]
            cache['preset_drag']=None;cache['preset_drop_target']=None
            layout_ui(c)
        return
    if kind == 'press':
        cache.pop('preset_context',None)
        point = preset_card_pointer(c, slot)
        cache['preset_press'] = (slot,) + (point or (0.0, 0.0))
        cache['preset_drag'] = None;cache['preset_drop_target']=None
        layout_ui(c)
        return
    press = cache.get('preset_press')
    if not press or press[0] != slot:
        return
    point = preset_card_pointer(c, slot)
    if point is None:
        return
    x, y = point
    if kind == 'move':
        if abs(x - press[1]) + abs(y - press[2]) > 8 and 0<=slot<len(entries):
            cache['preset_drag'] = slot
            target=preset_drop_slot(c,x,y)
            if target!=cache.get('preset_drop_target'):
                cache['preset_drop_target']=target;layout_ui(c)
        return
    if kind != 'release':
        return
    cache.pop('preset_press', None)
    drag = cache.pop('preset_drag', None)
    target=cache.pop('preset_drop_target',None)
    if drag is not None:
        if target is not None:
            c.op('preset_layout').module.move(c,entries[drag][0],target)
        else:
            layout_ui(c)
        return
    if 0 <= slot < len(entries):
        cache['cycle_index'] = slot
        button(c, entries[slot][0])



def cycle_preset(c):
    entries = preset_entries(c)
    if not entries:
        set_status(c, '当前没有可载入的预设')
        return
    cache = st(c)
    index = (cache.get('cycle_index', -1) + 1) % len(entries)
    cache['cycle_index'] = index
    button(c, entries[index][0])


def sync_to_parent(c):
    root = c.parent()
    if not root or not hasattr(root.par, 'Curve1x'):
        return
    state = state_from_component(c)
    duration = float(par_value(c, 'Duration', 2.0))
    key = tuple(state.items()) + (duration,)
    cache = st(c)
    if cache.get('sync_key') == key:
        return
    cache['sync_key'] = key
    if state['mode'] == 'bezier':
        for name, value in (
            ('Curve1x', state['x1']), ('Curve1y', state['y1']),
            ('Curve2x', state['x2']), ('Curve2y', state['y2']),
        ):
            if hasattr(root.par, name) and abs(getattr(root.par, name).eval() - value) > 1e-8:
                root.par[name] = value
    if hasattr(root.par, 'Fadeduration') and abs(root.par.Fadeduration.eval() - duration) > 1e-8:
        root.par.Fadeduration = duration
    if hasattr(root.par, 'Curvepreset'):
        preset = 'custom'
        if state['mode'] == 'bezier':
            points = (state['x1'], state['y1'], state['x2'], state['y2'])
            preset = next((name for name, spec in PRESETS.items() if spec['mode'] == 'bezier' and 'points' in spec and all(abs(a - b) < 0.002 for a, b in zip(points, spec['points']))), 'custom')
        if root.par.Curvepreset.eval() != preset:
            root.par.Curvepreset = preset


def update_preset_hover(c):
    c.op('ui_style').module.preset_hover(c)


def on_tick(c):
    c.op('plugin_dialogs').module.load_library(c)
    layout_ui(c)
    cache = st(c)
    # Interaction animations must progress even when the host's absolute-time
    # clock is paused (observed frozen absTime in TD 2025.31550 while me.time
    # advances).  Wall-clock dt keeps hover/tween feedback alive regardless of
    # timeline or focus state; absTime was making every tween stuck at dt=0.
    now = wallclock.time()
    if cache['last'] is None:
        cache['last'] = now
    dt = min(0.1, max(0.0, now - cache['last']))
    cache['last'] = now
    duration = max(0.01, float(par_value(c, 'Duration', 2.0)))
    if par_value(c, 'Previewplay', True):
        cache['time'] += dt
    u = (cache['time'] % (duration + 0.8) - 0.08) / duration
    old_u = cache['u']
    cache['u'] = clamp(u, 0.0, 1.0)
    if cache['u'] != old_u:c.op('playhead_shape').cook(force=True)
    update(c)
    update_button_motion(c, dt)


def panel_event(c,kind):
    c.op('graph_engine').module.panel_event(c,kind)


def cancel_drag(c):
    cache = st(c)
    if cache.get('drag') is None or not cache.get('drag_before'):
        return False
    assign_state(c, loads_state(cache['drag_before']), preserve_ui=True)
    cache['drag'] = None
    cache['range_lock'] = None
    update(c)
    set_status(c, '已取消本次拖拽')
    return True


def clipboard_write(text):
    CACHE['clipboard'] = text
    try:
        ui.clipboard = text
        CACHE['clipboard_system'] = True
        return True
    except Exception:
        CACHE['clipboard_system'] = False
        return False


def clipboard_read():
    if CACHE.get('clipboard_system') is False:
        return CACHE.get('clipboard', ''), False
    try:
        return str(ui.clipboard), True
    except Exception:
        return CACHE.get('clipboard', ''), False


def settings_backdrop_event(c):
    c.op('plugin_dialogs').module.backdrop(c)


def user_presets(c):
    target = c.op('user_presets')
    if not target or not target.text.strip():
        return []
    try:
        data = json.loads(target.text)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def button(c, name):
    cache = st(c)
    state = state_from_component(c)
    if name not in ('preset_context_delete','preset_context_export') and cache.get('preset_context') is not None:
        cache.pop('preset_context',None);layout_ui(c)
    if name in ('segment_prev','segment_next'):
        count=len(state['speed_params']);current=cache.get('speed_segment',0)
        cache['speed_segment']=(current+(-1 if name=='segment_prev' else 1))%count
        cache['points']=None;set_status(c,'速度段 · %d / %d'%(cache['speed_segment']+1,count));update(c)
        return
    if name in ('preset_context_delete','preset_context_export'):
        entries=page_entries(c);slot=cache.get('preset_context')
        if not isinstance(slot,int) or not 0<=slot<len(entries):return
        entry=entries[slot]
        if name=='preset_context_delete':
            c.op('preset_layout').module.delete_entry(c,entry[0])
        else:
            cache.pop('preset_context',None);layout_ui(c)
            c.op('plugin_dialogs').module.preset_file(c,'export',entries=[{'name':entry[1],'curve':entry[2],'thumbnail':entry[2].get('_thumbnail',{'type':'graph'})}])
        return
    if cache.get('modal_kind') and not (name.startswith('dlg_') or name in ('settings_open','settings_close')):return
    if name.startswith('easecopy_'):
        c.op('easecopy').module.action(c,name)
        return
    if c.op('plugin_dialogs').module.action(c,name):return
    if (cache.get('settings_open') or cache.get('modal_amount', 0.0) > 0.0) and not name.startswith('settings_'):
        return
    if name in PRESETS:
        name = 'preset_' + name
    if name == 'preset_next':
        cycle_preset(c)
        return
    if name.startswith('preset_hit_'):
        slot = int(name.rsplit('_', 1)[1]) - 1
        entries = page_entries(c)
        if 0 <= slot < len(entries):
            cache['cycle_index'] = slot
            cache.pop('pending_preset',None)
            button(c, entries[slot][0])
        return
    if name.startswith('preset_user'):
        index = int(name[len('preset_user'):].lstrip('_')) - 1
        presets = user_presets(c)
        if 0 <= index < len(presets):
            assign_state(c, presets[index]['curve'], preserve_ui=True)
            cache['selected_preset'] = name
            cache.pop('easecopy_range',None);cache.pop('easecopy_anchor',None)
            set_status(c, '已载入 ' + presets[index]['name'])
        else:
            set_status(c, '该用户预设槽为空')
        update(c)
        return
    if name.startswith('preset_'):
        preset_name = name[7:]
        if preset_name in PRESETS:
            assign_state(c, preset_state(preset_name), preserve_ui=True)
            cache['selected_preset'] = name
            cache['selected_keyframe']=1;cache['speed_segment']=0
            cache.pop('easecopy_range',None);cache.pop('easecopy_anchor',None)
            set_status(c, '预设 · ' + PRESET_LABELS[preset_name])
            update(c)
        return
    if name in ('space_value','space_speed'):
        target='value' if name=='space_value' else 'speed'
        if state['mode']!='bezier':return
        if target=='speed' and state['edit_space']!='speed':
            state=fit_velocity_points(state)
        converted=False
        if target=='speed' and state['edit_space']!='speed':
            pass
        elif target=='value' and state['edit_space']=='speed':
            state=value_points_from_velocity(state)
            converted=True
        state['edit_space']=target
        cache['speed_segment']=0;cache['selected_keyframe']=1
        cache['layout_key']=None
        assign_state(c,state)
        # Value and velocity use different vertical domains.  Re-fit on every
        # space switch so the previous space's zoom cannot strand the curve at
        # an edge of the graph; explicit Fit keeps the same behaviour.
        c.op('graph_engine').module.action(c,'view_fit')
        set_status(c,'已从速度曲线转换为值曲线' if converted else ('编辑 · '+('速度曲线' if target=='speed' else '值曲线')))
        update(c)
        layout_ui(c)
        return
    if name == 'settings_open':
        cache['settings_open'] = not cache.get('settings_open', False)
        update(c)
        update_settings_visibility(c)
        return
    if name == 'settings_close':
        cache['settings_open'] = False
        update(c)
        update_settings_visibility(c)
        return
    if name == 'settings_compact':
        state['compact'] = not state.get('compact', False)
        cache['layout_key'] = None
        assign_state(c, state)
        update(c)
        layout_ui(c)
        return
    if name == 'settings_motion':
        state['reduce_motion'] = not state['reduce_motion']
        assign_state(c, state)
        update(c)
        return
    if name == 'settings_location':
        state['preset_location'] = 'bottom' if state.get('preset_location') == 'right' else 'right'
        cache['layout_key'] = None
        assign_state(c, state)
        update(c)
        layout_ui(c)
        return
    if name == 'settings_speed':
        state['show_speed'] = not state.get('show_speed', True)
        assign_state(c, state)
        set_status(c, '速度背景 · ' + ('显示' if state['show_speed'] else '隐藏'))
        update(c)
        return
    if name == 'settings_restore':
        state['compact'] = False
        state['preset_location'] = 'right'
        state['preset_size'] = 80.0
        state['show_speed'] = True
        state['reduce_motion'] = False
        cache['layout_key'] = None
        assign_state(c, state)
        set_status(c, '已恢复界面默认')
        update(c)
        layout_ui(c)
        return
    if name.startswith('mode_'):
        state['mode'] = name[5:]
        state['edit_space'] = 'value'
        if state['mode']!='bezier' and state.get('model')!='continuous-v3':
            state['model']='continuous-v3';state['direction']='out'
        cache['cycle_index'] = -1
        cache.pop('easecopy_range',None);cache.pop('easecopy_anchor',None)
        cache['layout_key'] = None
        assign_state(c, state)
        set_status(c, '模式 · ' + state['mode'].capitalize())
        update(c)
        layout_ui(c)
        return
    if name == 'direction_cycle':
        index = (DIRECTIONS.index(state['direction']) + 1) % len(DIRECTIONS)
        state['direction'] = DIRECTIONS[index]
        assign_state(c, state)
        set_status(c, '方向 · ' + state['direction'])
        update(c)
        return
    if name == 'action_copy':
        system = clipboard_write(dumps_state(state))
        set_status(c, '曲线已复制' if system else '曲线已复制到会话剪贴板')
        return
    if name == 'action_paste':
        text, system = clipboard_read()
        try:
            loaded = loads_state(text)
            loaded['edit_space'] = loaded.get('edit_space', 'value')
            assign_state(c, loaded, preserve_ui=True)
            cache.pop('easecopy_range',None);cache.pop('easecopy_anchor',None)
            set_status(c, '曲线已粘贴' if system else '已从会话剪贴板粘贴')
            update(c)
        except Exception:
            set_status(c, '粘贴失败：不是有效的 v2 曲线数据')
        return
    if name == 'action_reset':
        reset = preset_state('linear'); reset['edit_space'] = 'value'
        assign_state(c,reset,preserve_ui=True)
        cache.pop('easecopy_range',None);cache.pop('easecopy_anchor',None)
        st(c)['layout_key']=None
        set_status(c,'已重置为线性 · y = x')
        update(c)
        return
    if name == 'action_reverse':
        reversed_state = reverse_state(state); reversed_state['edit_space'] = 'value'
        assign_state(c, reversed_state)
        cache.pop('easecopy_range',None);cache.pop('easecopy_anchor',None)
        set_status(c, '已反向当前曲线')
        update(c)
        return
    if name.startswith('param'):
        if state['mode'] == 'bezier':
            return
        group = int(name[5])
        direction = 1 if name.endswith('_up') else -1
        parameter = {
            'elastic': ('amplitude', 'period'),
            'bounce': ('bounces', 'damping'),
        }[state['mode']][group - 1]
        settings = {
            'amplitude': (0.05, 1.0, 2.0),
            'period': (0.02, 0.05, 1.0),
            'bounces': (1, 1, 8),
            'damping': (0.05, 0.0, 1.0),
        }
        step, low, high = settings[parameter]
        value = clamp(float(state[parameter]) + direction * step, low, high)
        state[parameter] = int(round(value)) if parameter == 'bounces' else value
        assign_state(c, state)
        update(c)
        return
    if name.startswith('select'):
        c.par.Selectedhandle = int(name[-1])
    elif name.startswith('nudge_'):
        dx, dy = {'left': (-0.01, 0), 'right': (0.01, 0), 'up': (0, 0.01), 'down': (0, -0.01)}[name[6:]]
        index = c.par.Selectedhandle.eval()
        c.par['X' + str(index)] = clamp(float(c.par['X' + str(index)].eval()) + dx, 0.0, 1.0)
        c.par['Y' + str(index)] = clamp(float(c.par['Y' + str(index)].eval()) + dy, -2.0, 3.0)
    elif name.startswith('tweak_'):
        _, parameter, direction = name.split('_')
        amount = 1 if direction == 'up' else -1
        settings = {
            'amplitude': (0.05, 1.0, 2.0),
            'period': (0.02, 0.05, 1.0),
            'bounces': (1, 1, 8),
            'damping': (0.05, 0.0, 1.0),
        }
        step, low, high = settings[parameter]
        value = clamp(float(state[parameter]) + amount * step, low, high)
        state[parameter] = int(round(value)) if parameter == 'bounces' else value
        assign_state(c, state)
    update(c)
