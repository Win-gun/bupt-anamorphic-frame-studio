"""Continuous planar–circular–planar LED geometry in metres.

Developed coordinate s always runs left → arc → right. Concave turns toward
negative Y, convex toward positive Y; yaw rotates the complete installation.
The curvature choice is a hypothesis until measured against the installation.
"""
import math
import numpy as np


def dimensions(screen):
    left, arc, right = [p * screen['pitch_mm'] / 1000 for p in screen['pixels']]
    angle = math.radians(screen['angle_deg'])
    radius = arc / angle
    measured = screen.get('radius_m')
    if measured is not None and not math.isclose(measured, radius, rel_tol=1e-6):
        raise ValueError('Radius, arc length and angle are inconsistent')
    if screen.get('curvature', 'concave') not in ('concave', 'convex'):
        raise ValueError('curvature must be concave or convex')
    end_x = radius * math.sin(angle) + right * math.cos(angle)
    max_x = max(0, end_x, radius if angle >= math.pi/2 else radius*math.sin(angle))
    min_x = min(-left, end_x)
    return dict(left=left, arc=arc, right=right, angle=angle, radius=radius,
                height=screen['height_px'] * screen['pitch_mm'] / 1000,
                length=left + arc + right, x_shift=(max_x+min_x)/2)


def _rotation(screen):
    a = math.radians(screen.get('yaw_deg', 0))
    return np.array([[math.cos(a), -math.sin(a), 0],
                     [math.sin(a), math.cos(a), 0], [0, 0, 1]])


def _sign(screen):
    return 1 if screen.get('curvature', 'concave') == 'convex' else -1


def surface_point(s, z, screen):
    """Point at developed distance s and centered physical height z."""
    return tuple(surface_grid(s, z, screen)[0].tolist())


def surface_grid(s, z, screen):
    """Broadcastable point/front-normal arrays, including installation yaw."""
    d = dimensions(screen)
    t = np.asarray(s)-d['left']
    a = np.clip(t/d['radius'], 0, d['angle'])
    q = np.maximum(t-d['arc'], 0)
    sign = _sign(screen)
    x = np.where(t < 0, t, d['radius']*np.sin(a)+q*np.cos(d['angle']))-d['x_shift']
    y = sign*(d['radius']*(1-np.cos(a))+q*np.sin(d['angle']))
    points = np.stack(np.broadcast_arrays(x, y, z), axis=-1)
    normals = np.stack(np.broadcast_arrays(sign*np.sin(a), -np.cos(a), np.zeros_like(a)), axis=-1)
    rotation = _rotation(screen)
    return points @ rotation.T, normals @ rotation.T


def ray_surface_hit(camera, directions, screen):
    """Nearest physical hit for arbitrary world rays; return distance parameter/front.

    Back surfaces occlude too. Finite panel height and both cylinder roots are
    tested before selecting the nearest hit, so hidden fronts cannot leak.
    """
    d = dimensions(screen)
    rotation = _rotation(screen)
    origin = np.asarray(camera, dtype=float) @ rotation
    rays = np.asarray(directions, dtype=float) @ rotation
    ox, oy, oz = origin
    dx, dy, dz = np.moveaxis(rays, -1, 0)
    best = np.full(rays.shape[:-1], np.inf)
    front = np.zeros(rays.shape[:-1], dtype=bool)
    sign, radius, angle = _sign(screen), d['radius'], d['angle']

    def hit(t, valid, nx, ny):
        nonlocal best, front
        valid = valid & np.isfinite(t) & (t > 1e-8) & (np.abs(oz+t*dz) <= d['height']/2+1e-8) & (t < best)
        front = np.where(valid, nx*dx+ny*dy < -1e-10, front)
        best = np.where(valid, t, best)

    with np.errstate(divide='ignore', invalid='ignore'):
        t = -oy/dy
        x = ox+t*dx+d['x_shift']
        hit(t, (x >= -d['left']-1e-9) & (x <= 1e-9), 0, -1)
        ex = radius*math.sin(angle)-d['x_shift']
        ey = sign*radius*(1-math.cos(angle))
        nx, ny = sign*math.sin(angle), -math.cos(angle)
        t = ((ex-ox)*nx+(ey-oy)*ny)/(dx*nx+dy*ny)
        q = (ox+t*dx-ex)*math.cos(angle)+(oy+t*dy-ey)*sign*math.sin(angle)
        hit(t, (q >= -1e-9) & (q <= d['right']+1e-9), nx, ny)
        cx, cy = -d['x_shift'], sign*radius
        bx, by = ox-cx, oy-cy
        aa = dx*dx+dy*dy
        bb = 2*(bx*dx+by*dy)
        cc = bx*bx+by*by-radius**2
        disc = bb*bb-4*aa*cc
        for root in (-1, 1):
            t = (-bb+root*np.sqrt(np.maximum(disc, 0)))/(2*aa)
            xx, yy = ox+t*dx-cx, oy+t*dy-cy
            a = np.arctan2(xx, -sign*yy)
            hit(t, (disc >= 0) & (a >= -1e-9) & (a <= angle+1e-9), sign*np.sin(a), -np.cos(a))
    return best, front


def visible_points(points, normals, camera, screen):
    """Actual front-facing visibility, including finite-height self-occlusion."""
    ray = np.asarray(points)-np.asarray(camera)
    nearest, _ = ray_surface_hit(camera, ray, screen)
    return (np.sum(np.asarray(normals)*(-ray), axis=-1) > 1e-8) & (nearest >= 1-1e-5)
