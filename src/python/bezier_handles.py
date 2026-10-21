"""Free Bezier handle coordinates with exact monotonic-time protection."""
import math
import copy


def clamp(value, low, high):
    return max(low, min(high, value))


def finite(value, fallback):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return number if math.isfinite(number) else float(fallback)


def cubic_x_monotonic(points):
    """Exact non-negative x derivative on one segment; handles may cross."""
    (x0, _), (x1, _), (x2, _), (x3, _) = points
    a = -x0 + 3*x1 - 3*x2 + x3
    b = 2*(x0 - 2*x1 + x2)
    c = x1 - x0
    candidates = [0.0, 1.0]
    if abs(a) > 1e-14:
        t = -b/(2*a)
        if 0.0 < t < 1.0:
            candidates.append(t)
    return all(a*t*t + b*t + c >= -1e-9 for t in candidates)


def nearest_monotonic_x(points, control, current, desired):
    """Keep the furthest valid drag position instead of a fixed anchor clamp."""
    def valid(x):
        candidate = list(points)
        candidate[control] = (x, candidate[control][1])
        return cubic_x_monotonic(candidate)
    if valid(desired):
        return desired
    if not valid(current):
        return clamp(desired, points[0][0], points[3][0])
    good, bad = float(current), float(desired)
    for _ in range(40):
        middle = (good + bad) * .5
        if valid(middle):
            good = middle
        else:
            bad = middle
    return good


def move(state, index, side, x, y, normalize):
    state = normalize(state)
    keys = copy.deepcopy(state['keyframes'])
    if not 0 <= index < len(keys) or side not in ('left','right'):
        return state
    if (side == 'left' and index == 0) or (side == 'right' and index == len(keys)-1):
        return state
    item = keys[index]
    current = item[side][0]
    desired = finite(x, current)
    segment = index-1 if side == 'left' else index
    a,b = keys[segment:segment+2]
    points = [(a['t'],a['v']),tuple(a['right']),tuple(b['left']),(b['t'],b['v'])]
    control = 2 if side == 'left' else 1
    item[side] = [nearest_monotonic_x(points,control,current,desired),
                  finite(y,item[side][1])]
    state['keyframes'] = keys
    return normalize(state)


def ensure_parameters(c):
    """Use TD's real parameter API once; old cparm ranges must not clamp drags."""
    for name in ('X1','Y1','X2','Y2'):
        try:
            parameter = c.par[name]
        except Exception:
            continue
        for attr,value in (('min',-1000000.0),('max',1000000.0),('normMin',-1000000.0),('normMax',1000000.0)):
            try:
                if abs(getattr(parameter,attr)-value) > 1e-9:
                    setattr(parameter,attr,value)
            except Exception:
                pass
