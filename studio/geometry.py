"""Continuous, concave planar–circular–planar LED surface in metres.

X follows the developed pixel axis, Z points up, the left plane is Y=0.
The surface is centered on its X bounding box. Front normals point toward
negative Y on the left and negative X on a 90 degree right panel.
"""
import math


def dimensions(screen):
    left, arc, right = [p * screen['pitch_mm'] / 1000 for p in screen['pixels']]
    angle = math.radians(screen['angle_deg'])
    radius = arc / angle
    measured = screen.get('radius_m')
    if measured is not None and not math.isclose(measured, radius, rel_tol=1e-6):
        raise ValueError('Radius, arc length and angle are inconsistent')
    end_x = radius * math.sin(angle) + right * math.cos(angle)
    max_x = max(0, end_x, radius if angle >= math.pi/2 else radius*math.sin(angle))
    min_x = min(-left, end_x)
    return dict(left=left, arc=arc, right=right, angle=angle, radius=radius,
                height=screen['height_px'] * screen['pitch_mm'] / 1000,
                length=left + arc + right, x_shift=(max_x+min_x)/2)


def surface_point(s, z, screen):
    """Developed horizontal distance s in [0, total length], centered height z."""
    d = dimensions(screen)
    t = s-d['left']
    if t <= 0:
        x, y = t, 0
    elif t < d['arc']:
        a = t/d['radius']
        x, y = d['radius']*math.sin(a), d['radius']*(math.cos(a)-1)
    else:
        q = t-d['arc']
        x = d['radius']*math.sin(d['angle']) + q*math.cos(d['angle'])
        y = d['radius']*(math.cos(d['angle'])-1) - q*math.sin(d['angle'])
    return (x-d['x_shift'], y, z)


def surface_grid(s, z, screen):
    """Vectorized point and front normal arrays; numpy available in Blender."""
    import numpy as np
    d = dimensions(screen)
    t = np.asarray(s)-d['left']
    a = np.clip(t/d['radius'], 0, d['angle'])
    q = np.maximum(t-d['arc'], 0)
    x = np.where(t < 0, t, d['radius']*np.sin(a)+q*np.cos(d['angle']))-d['x_shift']
    y = np.where(t < 0, 0, d['radius']*(np.cos(a)-1)-q*np.sin(d['angle']))
    points = np.stack(np.broadcast_arrays(x, y, z), axis=-1)
    normals = np.stack(np.broadcast_arrays(-np.sin(a), -np.cos(a), np.zeros_like(a)), axis=-1)
    return points, normals


def visible_points(points, normals, camera, screen):
    """Front face and analytic segment/surface occlusion, including finite Z.

    Tests the actual continuous planes and circular surface, not a homography.
    The destination itself is excluded by a small relative ray tolerance.
    """
    import numpy as np
    d = dimensions(screen)
    camera = np.asarray(camera, dtype=float)
    ray = points-camera
    visible = np.sum(normals*(-ray), axis=-1) > 1e-8
    ox, oy, oz = camera
    dx, dy, dz = np.moveaxis(ray, -1, 0)
    def hit(t, valid):
        nonlocal visible
        z = oz+t*dz
        visible &= ~(valid & (t > 1e-6) & (t < 1-1e-5) & (np.abs(z) <= d['height']/2))
    with np.errstate(divide='ignore', invalid='ignore'):
        t = -oy/dy
        x = ox+t*dx+d['x_shift']
        hit(t, (x >= -d['left']) & (x <= 0))
        ex = d['radius']*math.sin(d['angle'])-d['x_shift']
        ey = d['radius']*(math.cos(d['angle'])-1)
        nx, ny = -math.sin(d['angle']), -math.cos(d['angle'])
        t = ((ex-ox)*nx+(ey-oy)*ny)/(dx*nx+dy*ny)
        q = (ox+t*dx-ex)*math.cos(d['angle'])-(oy+t*dy-ey)*math.sin(d['angle'])
        hit(t, (q >= 0) & (q <= d['right']))
        cx, cy = -d['x_shift'], -d['radius']
        bx, by = ox-cx, oy-cy
        aa = dx*dx+dy*dy
        bb = 2*(bx*dx+by*dy)
        cc = bx*bx+by*by-d['radius']**2
        disc = bb*bb-4*aa*cc
        for root in (-1, 1):
            t = (-bb+root*np.sqrt(np.maximum(disc, 0)))/(2*aa)
            a = np.arctan2(ox+t*dx-cx, oy+t*dy-cy)
            hit(t, (disc >= 0) & (a >= 0) & (a <= d['angle']))
    return visible
