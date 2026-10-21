"""Continuous easing models and display topology, independent of the TD UI."""
import math
from functools import lru_cache

MODEL = 'continuous-v3'
EPS_X = 1e-4  # Same geometric protection as the reference handle, not an integer-step limit.


def clamp(x, a, b):
    return max(a, min(b, float(x)))


@lru_cache(maxsize=256)
def elastic_peak(frequency, decay):
    w = math.tau * frequency
    den = -math.expm1(-decay)
    def raw(t):
        envelope = (math.exp(-decay*t)-math.exp(-decay))/den if decay else 1-t
        slope = -decay*math.exp(-decay*t)/den if decay else -1
        return 1-envelope*math.cos(w*t), -slope*math.cos(w*t)+w*envelope*math.sin(w*t)
    lo, hi = .25/frequency, min(1.0, .5/frequency)
    for _ in range(44):
        mid = (lo+hi)*.5
        if raw(mid)[1] > 0: lo = mid
        else: hi = mid
    t = (lo+hi)*.5
    return t, raw(t)[0]


def elastic_pair(t, state):
    f, d, gain = state['frequency'], state['decay'], state['elastic_gain']
    peak_t, peak = elastic_peak(f,d)
    den = -math.expm1(-d)
    envelope = (math.exp(-d*t)-math.exp(-d))/den if d else 1-t
    slope = -d*math.exp(-d*t)/den if d else -1
    w = math.tau*f
    raw = 1-envelope*math.cos(w*t)
    speed = -slope*math.cos(w*t)+w*envelope*math.sin(w*t)
    if t < peak_t:
        scale = (1+gain*(peak-1))/peak
        return raw*scale, speed*scale
    return 1+gain*(raw-1), gain*speed


def bounce_events(state, width=None):
    """Return only screen-visible bounce cusps, not the infinite numerical tail.

    The physical model has infinitely many impacts converging on the settle time.
    Rendering every one creates sub-pixel segments and makes the background speed
    trace look like a fan of diagonal lines.  The cutoff is derived from the
    current graph resolution so the mathematical curve stays unchanged while the
    display stops splitting once an impact is no longer visible.
    """
    c,d = state['restitution'], state['bounce_period']
    if c < 1e-10:
        event = d*.5
        return ([event] if 0 < event < 1 else []), min(1.0, event)
    settle = d*(1/(1-c)-.5)
    if settle <= 1:
        cutoff = settle
    else:
        n = max(0,math.floor(math.log(max(1e-300,1+(c-1)*(1/d+.5)))/math.log(c)))
        cutoff = min(1.0,d*((1-c**n)/(1-c)-.5)) if n else 1.0

    # Two pixels is enough to keep a visible gap at a discontinuous derivative.
    # Without a width (for callers outside the renderer), precision is the best
    # available proxy for the graph resolution.
    pixel_u = (2.0 / max(64.0, float(width) - 32.0) if width is not None
               else 2.0 / max(128.0, float(state.get('precision', 300))))
    amplitude_threshold = max(1e-3, pixel_u * 1.5)
    events=[]
    for k in range(1, 49):
        amplitude = c**k
        t=d*((1-amplitude)/(1-c)-.5)
        if t >= cutoff-1e-12 or t >= 1.0:
            break
        if t > 0:
            events.append(t)
        # Later impacts are both too small and too close to resolve separately.
        if amplitude <= amplitude_threshold or d*amplitude <= pixel_u:
            break
    if 0 < cutoff < 1 and (not events or cutoff-events[-1] > pixel_u):
        events.append(cutoff)
    return tuple(sorted(set(events))),cutoff


def bounce_pair(t,state):
    c,d=state['restitution'],state['bounce_period']
    if c < 1e-10:
        if t >= d*.5: return 1.0,0.0
        return 4*(t/d)**2, 8*t/d**2
    settle=d*(1/(1-c)-.5)
    if t >= settle: return 1.0,0.0
    q=t/d
    arg=1-(1-c)*(q+.5)
    if arg<=0: return 1.0,0.0
    k=max(0,math.floor(math.log(arg)/math.log(c)+1e-12))
    if settle>1:
        end_arg=max(1e-300,1-(1-c)*(1/d+.5))
        end_k=max(0,math.floor(math.log(end_arg)/math.log(c)))
        cutoff=d*((1-c**end_k)/(1-c)-.5) if end_k else 1.0
        if t>=cutoff: return 1.0,0.0
    center=(1-c**k)/(1-c)-.5+c**k*.5
    offset=q-center
    return 1+4*offset*offset-c**(2*k),8*offset/d


def directed_pair(t,state):
    base=elastic_pair if state['mode']=='elastic' else bounce_pair
    direction=state['direction']
    if direction=='out': return base(t,state)
    if direction=='in':
        value,speed=base(1-t,state)
        return 1-value,speed
    if t<.5:
        value,speed=base(1-2*t,state)
        return (1-value)*.5,speed
    value,speed=base(2*t-1,state)
    return (1+value)*.5,speed


def breakpoints(state, width=None):
    if state['mode']!='bounce': return ()
    raw,_=bounce_events(state, width=width)
    if state['direction']=='out': return tuple(raw)
    if state['direction']=='in': return tuple(sorted(1-t for t in raw))
    return tuple(sorted([(1-t)*.5 for t in raw]+[(1+t)*.5 for t in raw]))


def handles(state):
    reverse=state['direction']=='in'
    if state['mode']=='elastic':
        point=(.5/state['frequency'],1-state['elastic_gain'])
        decay=(1.,(state['decay']-1)/19)
        if reverse:
            point=(1-point[0],1-point[1]);decay=(0.,1-decay[1])
        # In Out uses the editable Out half, consistent with its transformed curve.
        if state['direction']=='inout':
            point=(.5+point[0]*.5,.5+point[1]*.5)
            decay=(1.,.5+decay[1]*.5)
        return {'elastic_control':point,'elastic_decay':decay}
    if state['mode']=='bounce':
        point=(state['bounce_period']*(1+state['restitution'])*.5,1-state['restitution']**2)
        if reverse: point=(1-point[0],1-point[1])
        if state['direction']=='inout': point=(.5+point[0]*.5,.5+point[1]*.5)
        return {'bounce_control':point}
    return {}


def drag_handle(state,kind,x,y):
    result=dict(state)
    if state['direction']=='in': x,y=1-x,1-y
    elif state['direction']=='inout': x,y=2*x-1,2*y-1
    x,y=clamp(x,0,1),clamp(y,0,1)
    if kind=='elastic_control':
        result['frequency']=.5/max(x,EPS_X)
        result['elastic_gain']=1-y
    elif kind=='elastic_decay': result['decay']=1+19*y
    elif kind=='bounce_control':
        cor=math.sqrt(1-max(.001,y))
        result['restitution']=cor
        result['bounce_period']=max(EPS_X,2*x/(1+cor))
    return result


def sampling_count(state,width):
    base=max(129,int(state.get('precision',300))+1,int(width*1.5))
    if state.get('model')==MODEL and state['mode']=='elastic':
        base=max(base,math.ceil(state['frequency']*24)+1)
    return min(8193,base)


def endpoint_speed(x1,y1,x2,y2,end=False):
    if end:x1,y1,x2,y2=1-x2,1-y2,1-x1,1-y1
    xs=(3*x1,3*x2-6*x1,1+3*x1-3*x2)
    ys=(3*y1,3*y2-6*y1,1+3*y1-3*y2)
    ix=next((i for i,a in enumerate(xs) if abs(a)>1e-12),2)
    iy=next((i for i,a in enumerate(ys) if abs(a)>1e-12),2)
    if iy>ix:return 0.0
    if iy<ix:return math.copysign(math.inf,ys[iy]/xs[ix])
    return ys[iy]/xs[ix]


# --- Velocity-space editing (U018) -------------------------------------------------
# Speed controls describe the same cubic fade as the value editor.  vx is the
# normalized horizontal influence; vy is the endpoint derivative dy/dx.  The
# corresponding value-control coordinates are y1=vy1*vx1 and
# y2=1-vy2*(1-vx2).  Thus speed is always the real derivative of the displayed
# value curve, rather than an unrelated Bezier through sampled speed values.
VEL_MAX = 8.0


def _velocity_points(vx1, vy1, vx2, vy2):
    vx1, vx2 = clamp(vx1, 0.0, 1.0), clamp(vx2, 0.0, 1.0)
    vy1, vy2 = clamp(vy1, 0.0, VEL_MAX), clamp(vy2, 0.0, VEL_MAX)
    # Keeping local value controls inside 0..1 preserves a monotone fade while
    # still allowing the full useful range of Motion4-style endpoint speeds.
    y1 = clamp(vy1 * vx1, 0.0, 1.0)
    y2 = clamp(1.0 - vy2 * (1.0 - vx2), 0.0, 1.0)
    return vx1, y1, vx2, y2


def velocity_value_and_speed(u, state):
    """Return the cubic fade and its exact dy/dx derivative for speed controls."""
    x1, y1, x2, y2 = _velocity_points(*(float(state[k]) for k in ('vx1','vy1','vx2','vy2')))
    u = clamp(float(u), 0.0, 1.0)
    if u <= 0.0:
        return 0.0, endpoint_speed(x1, y1, x2, y2, False)
    if u >= 1.0:
        return 1.0, endpoint_speed(x1, y1, x2, y2, True)
    lo, hi, t = 0.0, 1.0, u
    for _ in range(16):
        x = 3*(1-t)*(1-t)*t*x1 + 3*(1-t)*t*t*x2 + t*t*t
        error = x-u
        if abs(error) < 1e-12:
            break
        if error < 0: lo = t
        else: hi = t
        dx = 3*(1-t)*(1-t)*x1 + 6*(1-t)*t*(x2-x1) + 3*t*t*(1-x2)
        candidate = t-error/dx if abs(dx) > 1e-12 else (lo+hi)*0.5
        t = candidate if lo < candidate < hi else (lo+hi)*0.5
    for _ in range(6):
        x = 3*(1-t)*(1-t)*t*x1 + 3*(1-t)*t*t*x2 + t*t*t
        if abs(x-u) < 1e-12:
            break
        if x < u: lo = t
        else: hi = t
        t = (lo+hi)*0.5
    dx = 3*(1-t)*(1-t)*x1 + 6*(1-t)*t*(x2-x1) + 3*t*t*(1-x2)
    dy = 3*(1-t)*(1-t)*y1 + 6*(1-t)*t*(y2-y1) + 3*t*t*(1-y2)
    value = 3*(1-t)*(1-t)*t*y1 + 3*(1-t)*t*t*y2 + t*t*t
    if abs(dx) <= 1e-12:
        speed = 0.0 if abs(dy) <= 1e-12 else math.copysign(math.inf, dy)
    else:
        speed = dy/dx
    return value, speed


def velocity_curve_speed(u, vx1, vy1, vx2, vy2):
    """Compatibility selector for the derivative of the shared value cubic."""
    state = dict(zip(('vx1','vy1','vx2','vy2'), (vx1,vy1,vx2,vy2)))
    return velocity_value_and_speed(u, state)[1]


@lru_cache(maxsize=128)
def _velocity_table_cached(vx1, vy1, vx2, vy2, count):
    state = dict(zip(('vx1','vy1','vx2','vy2'), (vx1,vy1,vx2,vy2)))
    pairs = [velocity_value_and_speed(i/(count-1), state) for i in range(count)]
    # The third item remains for API compatibility; the shared cubic is already
    # normalized to value(0)=0 and value(1)=1, so no second integration is needed.
    return (tuple(item[0] for item in pairs), tuple(item[1] for item in pairs), 1.0)


def velocity_value_table(state, count=257):
    """Immutable direct samples of the shared value/derivative mapping."""
    count = max(2, int(count))
    return _velocity_table_cached(float(state['vx1']), float(state['vy1']),
                                  float(state['vx2']), float(state['vy2']), count)
