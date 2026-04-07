"""Parametric shape primitives library.

Each function generates a list of 3D points (list[tuple[float, float, float]])
that can be passed directly to OpenBrushClient.draw_path() or draw_paths().

All shapes are generated relative to a center/origin position.
"""

import math
from typing import Generator


# ─── Basic Curves ─────────────────────────────────────────────────

def circle(
    center: tuple[float, float, float] = (0, 0, 0),
    radius: float = 1.0,
    points: int = 32,
    plane: str = "xz",
    close: bool = True,
) -> list[tuple[float, float, float]]:
    """Generate a circle in the specified plane.

    Args:
        center: Center position (x, y, z).
        radius: Circle radius.
        points: Number of points.
        plane: 'xy', 'xz', or 'yz'.
        close: If True, close the circle.
    """
    result = []
    n = points + 1 if close else points
    cx, cy, cz = center
    for i in range(n):
        angle = 2 * math.pi * i / points
        a = radius * math.cos(angle)
        b = radius * math.sin(angle)
        if plane == "xy":
            result.append((cx + a, cy + b, cz))
        elif plane == "xz":
            result.append((cx + a, cy, cz + b))
        elif plane == "yz":
            result.append((cx, cy + a, cz + b))
    return result


def helix(
    center: tuple[float, float, float] = (0, 0, 0),
    radius: float = 1.0,
    height: float = 5.0,
    turns: float = 5.0,
    points: int = 80,
    direction: str = "up",
) -> list[tuple[float, float, float]]:
    """Generate a helix/spiral.

    Args:
        center: Base center position.
        radius: Helix radius.
        height: Total height.
        turns: Number of complete turns.
        points: Number of points.
        direction: 'up' or 'down'.
    """
    result = []
    cx, cy, cz = center
    for i in range(points):
        t = i / (points - 1)
        angle = 2 * math.pi * turns * t
        x = cx + radius * math.cos(angle)
        y = cy + (height * t if direction == "up" else height * (1 - t))
        z = cz + radius * math.sin(angle)
        result.append((x, y, z))
    return result


def spiral(
    center: tuple[float, float, float] = (0, 0, 0),
    start_radius: float = 0.1,
    end_radius: float = 3.0,
    turns: float = 5.0,
    points: int = 80,
    plane: str = "xz",
) -> list[tuple[float, float, float]]:
    """Generate a flat spiral (Archimedean spiral)."""
    result = []
    cx, cy, cz = center
    for i in range(points):
        t = i / (points - 1)
        angle = 2 * math.pi * turns * t
        r = start_radius + (end_radius - start_radius) * t
        a = r * math.cos(angle)
        b = r * math.sin(angle)
        if plane == "xy":
            result.append((cx + a, cy + b, cz))
        elif plane == "xz":
            result.append((cx + a, cy, cz + b))
        elif plane == "yz":
            result.append((cx, cy + a, cz + b))
    return result


def lissajous(
    center: tuple[float, float, float] = (0, 0, 0),
    a_freq: float = 3.0,
    b_freq: float = 2.0,
    c_freq: float = 1.0,
    a_amp: float = 2.0,
    b_amp: float = 2.0,
    c_amp: float = 2.0,
    phase_a: float = 0,
    phase_b: float = 0,
    phase_c: float = 0,
    points: int = 300,
) -> list[tuple[float, float, float]]:
    """Generate a 3D Lissajous curve."""
    result = []
    cx, cy, cz = center
    for i in range(points):
        t = 2 * math.pi * i / (points - 1)
        x = cx + a_amp * math.sin(a_freq * t + phase_a)
        y = cy + b_amp * math.sin(b_freq * t + phase_b)
        z = cz + c_amp * math.sin(c_freq * t + phase_c)
        result.append((x, y, z))
    return result


# ─── Polygons & Stars ─────────────────────────────────────────────

def polygon(
    center: tuple[float, float, float] = (0, 0, 0),
    sides: int = 6,
    radius: float = 1.0,
    plane: str = "xz",
) -> list[tuple[float, float, float]]:
    """Generate a regular polygon."""
    result = []
    cx, cy, cz = center
    for i in range(sides + 1):
        angle = 2 * math.pi * i / sides
        a = radius * math.cos(angle)
        b = radius * math.sin(angle)
        if plane == "xy":
            result.append((cx + a, cy + b, cz))
        elif plane == "xz":
            result.append((cx + a, cy, cz + b))
        elif plane == "yz":
            result.append((cx, cy + a, cz + b))
    return result


def star(
    center: tuple[float, float, float] = (0, 0, 0),
    points_count: int = 5,
    outer_radius: float = 2.0,
    inner_radius: float = 0.8,
    plane: str = "xz",
) -> list[tuple[float, float, float]]:
    """Generate a star shape."""
    result = []
    cx, cy, cz = center
    total = points_count * 2
    for i in range(total + 1):
        angle = 2 * math.pi * i / total - math.pi / 2
        r = outer_radius if i % 2 == 0 else inner_radius
        a = r * math.cos(angle)
        b = r * math.sin(angle)
        if plane == "xy":
            result.append((cx + a, cy + b, cz))
        elif plane == "xz":
            result.append((cx + a, cy, cz + b))
        elif plane == "yz":
            result.append((cx, cy + a, cz + b))
    return result


# ─── 3D Wireframes ────────────────────────────────────────────────

def sphere_wireframe(
    center: tuple[float, float, float] = (0, 0, 0),
    radius: float = 1.0,
    lat_lines: int = 8,
    lon_lines: int = 12,
    points_per_line: int = 32,
) -> list[list[tuple[float, float, float]]]:
    """Generate a sphere as a list of latitude and longitude circle paths.

    Returns multiple paths (use with draw_paths or iterate with draw_path).
    """
    paths = []
    cx, cy, cz = center

    # Latitude lines
    for i in range(1, lat_lines):
        phi = math.pi * i / lat_lines
        r = radius * math.sin(phi)
        y = cy + radius * math.cos(phi)
        path = []
        for j in range(points_per_line + 1):
            theta = 2 * math.pi * j / points_per_line
            x = cx + r * math.cos(theta)
            z = cz + r * math.sin(theta)
            path.append((x, y, z))
        paths.append(path)

    # Longitude lines
    for i in range(lon_lines):
        theta = 2 * math.pi * i / lon_lines
        path = []
        for j in range(points_per_line + 1):
            phi = math.pi * j / points_per_line
            x = cx + radius * math.sin(phi) * math.cos(theta)
            y = cy + radius * math.cos(phi)
            z = cz + radius * math.sin(phi) * math.sin(theta)
            path.append((x, y, z))
        paths.append(path)

    return paths


def cube_wireframe(
    center: tuple[float, float, float] = (0, 0, 0),
    size: float = 1.0,
) -> list[list[tuple[float, float, float]]]:
    """Generate a cube wireframe as 12 edge paths."""
    s = size / 2
    cx, cy, cz = center
    # 8 vertices
    verts = [
        (cx - s, cy - s, cz - s), (cx + s, cy - s, cz - s),
        (cx + s, cy + s, cz - s), (cx - s, cy + s, cz - s),
        (cx - s, cy - s, cz + s), (cx + s, cy - s, cz + s),
        (cx + s, cy + s, cz + s), (cx - s, cy + s, cz + s),
    ]
    # 12 edges
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # front face
        (4, 5), (5, 6), (6, 7), (7, 4),  # back face
        (0, 4), (1, 5), (2, 6), (3, 7),  # connecting edges
    ]
    return [[verts[a], verts[b]] for a, b in edges]


def torus(
    center: tuple[float, float, float] = (0, 0, 0),
    major_radius: float = 2.0,
    minor_radius: float = 0.5,
    rings: int = 24,
    points_per_ring: int = 16,
) -> list[list[tuple[float, float, float]]]:
    """Generate a torus as a series of ring paths."""
    paths = []
    cx, cy, cz = center
    for i in range(rings):
        theta = 2 * math.pi * i / rings
        ring = []
        for j in range(points_per_ring + 1):
            phi = 2 * math.pi * j / points_per_ring
            x = cx + (major_radius + minor_radius * math.cos(phi)) * math.cos(theta)
            y = cy + minor_radius * math.sin(phi)
            z = cz + (major_radius + minor_radius * math.cos(phi)) * math.sin(theta)
            ring.append((x, y, z))
        paths.append(ring)
    return paths


def cylinder_wireframe(
    center: tuple[float, float, float] = (0, 0, 0),
    radius: float = 1.0,
    height: float = 3.0,
    segments: int = 16,
    rings: int = 2,
) -> list[list[tuple[float, float, float]]]:
    """Generate a cylinder wireframe with top/bottom circles and vertical lines."""
    paths = []
    cx, cy, cz = center

    # Top and bottom circles
    for ring_y in [cy, cy + height]:
        circle_path = []
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            x = cx + radius * math.cos(angle)
            z = cz + radius * math.sin(angle)
            circle_path.append((x, ring_y, z))
        paths.append(circle_path)

    # Vertical lines
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = cx + radius * math.cos(angle)
        z = cz + radius * math.sin(angle)
        paths.append([(x, cy, z), (x, cy + height, z)])

    return paths


def cone_wireframe(
    center: tuple[float, float, float] = (0, 0, 0),
    radius: float = 1.0,
    height: float = 3.0,
    segments: int = 16,
) -> list[list[tuple[float, float, float]]]:
    """Generate a cone wireframe."""
    paths = []
    cx, cy, cz = center
    apex = (cx, cy + height, cz)

    # Base circle
    base = []
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        x = cx + radius * math.cos(angle)
        z = cz + radius * math.sin(angle)
        base.append((x, cy, z))
    paths.append(base)

    # Lines from base to apex
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = cx + radius * math.cos(angle)
        z = cz + radius * math.sin(angle)
        paths.append([(x, cy, z), apex])

    return paths


# ─── Organic / Nature ─────────────────────────────────────────────

def tree_branches(
    base: tuple[float, float, float] = (0, 0, 0),
    length: float = 3.0,
    angle: float = 30.0,
    depth: int = 6,
    shrink: float = 0.7,
    spread_3d: bool = True,
) -> list[list[tuple[float, float, float]]]:
    """Generate a recursive fractal tree as a list of branch paths.

    Args:
        base: Base position of the tree.
        length: Initial branch length.
        angle: Branching angle in degrees.
        depth: Recursion depth.
        shrink: Length multiplier per level.
        spread_3d: If True, branches spread in 3D; if False, stays in XY plane.
    """
    branches: list[list[tuple[float, float, float]]] = []

    def _branch(start, direction_angle_y, direction_angle_xz, current_length, current_depth):
        if current_depth == 0 or current_length < 0.05:
            return

        # Calculate end point
        rad_y = math.radians(direction_angle_y)
        rad_xz = math.radians(direction_angle_xz)
        dx = current_length * math.sin(rad_y) * math.cos(rad_xz)
        dy = current_length * math.cos(rad_y)
        dz = current_length * math.sin(rad_y) * math.sin(rad_xz) if spread_3d else 0

        end = (start[0] + dx, start[1] + dy, start[2] + dz)
        branches.append([start, end])

        # Two main branches
        new_len = current_length * shrink
        _branch(end, direction_angle_y + angle, direction_angle_xz, new_len, current_depth - 1)
        _branch(end, direction_angle_y - angle, direction_angle_xz, new_len, current_depth - 1)

        # Extra 3D branches
        if spread_3d and current_depth > 2:
            _branch(end, direction_angle_y, direction_angle_xz + angle, new_len, current_depth - 1)

    _branch(base, 0, 0, length, depth)
    return branches


def wave_surface(
    center: tuple[float, float, float] = (0, 0, 0),
    width: float = 6.0,
    depth_size: float = 6.0,
    amplitude: float = 0.5,
    frequency: float = 2.0,
    grid_x: int = 20,
    grid_z: int = 20,
) -> list[list[tuple[float, float, float]]]:
    """Generate a wave surface as a grid of paths.

    Returns paths along the X axis (iterate to also draw Z axis lines).
    """
    paths = []
    cx, cy, cz = center

    # X-direction lines
    for zi in range(grid_z):
        z = cz - depth_size / 2 + depth_size * zi / (grid_z - 1)
        path = []
        for xi in range(grid_x):
            x = cx - width / 2 + width * xi / (grid_x - 1)
            dist = math.sqrt((x - cx) ** 2 + (z - cz) ** 2)
            y = cy + amplitude * math.sin(frequency * dist)
            path.append((x, y, z))
        paths.append(path)

    # Z-direction lines
    for xi in range(grid_x):
        x = cx - width / 2 + width * xi / (grid_x - 1)
        path = []
        for zi in range(grid_z):
            z = cz - depth_size / 2 + depth_size * zi / (grid_z - 1)
            dist = math.sqrt((x - cx) ** 2 + (z - cz) ** 2)
            y = cy + amplitude * math.sin(frequency * dist)
            path.append((x, y, z))
        paths.append(path)

    return paths


def mountain_range(
    center: tuple[float, float, float] = (0, 0, 0),
    width: float = 10.0,
    depth_size: float = 6.0,
    max_height: float = 4.0,
    peaks: int = 3,
    grid_x: int = 30,
    grid_z: int = 20,
) -> list[list[tuple[float, float, float]]]:
    """Generate a mountain range using simple noise-like summation."""
    import random
    paths = []
    cx, cy, cz = center

    # Generate random peak positions
    rng = random.Random(42)
    peak_positions = [(rng.uniform(-width / 3, width / 3), rng.uniform(-depth_size / 3, depth_size / 3)) for _ in range(peaks)]

    def height_at(x, z):
        h = 0
        for px, pz in peak_positions:
            dist = math.sqrt((x - px) ** 2 + (z - pz) ** 2)
            h += max_height * math.exp(-dist * 0.5)
        return h

    for zi in range(grid_z):
        z = cz - depth_size / 2 + depth_size * zi / (grid_z - 1)
        path = []
        for xi in range(grid_x):
            x = cx - width / 2 + width * xi / (grid_x - 1)
            y = cy + height_at(x - cx, z - cz)
            path.append((x, y, z))
        paths.append(path)

    return paths


# ─── Utility ──────────────────────────────────────────────────────

def line(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    points: int = 2,
) -> list[tuple[float, float, float]]:
    """Generate a straight line between two points."""
    if points <= 2:
        return [start, end]
    result = []
    for i in range(points):
        t = i / (points - 1)
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t
        z = start[2] + (end[2] - start[2]) * t
        result.append((x, y, z))
    return result


def grid_lines(
    center: tuple[float, float, float] = (0, 0, 0),
    size: float = 10.0,
    divisions: int = 10,
    plane: str = "xz",
) -> list[list[tuple[float, float, float]]]:
    """Generate a grid of lines."""
    paths = []
    cx, cy, cz = center
    half = size / 2
    step = size / divisions

    for i in range(divisions + 1):
        offset = -half + step * i
        if plane == "xz":
            paths.append([(cx - half, cy, cz + offset), (cx + half, cy, cz + offset)])
            paths.append([(cx + offset, cy, cz - half), (cx + offset, cy, cz + half)])
        elif plane == "xy":
            paths.append([(cx - half, cy + offset, cz), (cx + half, cy + offset, cz)])
            paths.append([(cx + offset, cy - half, cz), (cx + offset, cy + half, cz)])
        elif plane == "yz":
            paths.append([(cx, cy - half, cz + offset), (cx, cy + half, cz + offset)])
            paths.append([(cx, cy + offset, cz - half), (cx, cy + offset, cz + half)])

    return paths


def transform_points(
    points: list[tuple[float, float, float]],
    translate: tuple[float, float, float] = (0, 0, 0),
    scale: float = 1.0,
) -> list[tuple[float, float, float]]:
    """Apply translation and uniform scale to a list of points."""
    return [
        (p[0] * scale + translate[0], p[1] * scale + translate[1], p[2] * scale + translate[2])
        for p in points
    ]


def transform_paths(
    paths: list[list[tuple[float, float, float]]],
    translate: tuple[float, float, float] = (0, 0, 0),
    scale: float = 1.0,
) -> list[list[tuple[float, float, float]]]:
    """Apply translation and uniform scale to multiple paths."""
    return [transform_points(p, translate, scale) for p in paths]


# ─── Shape Registry ──────────────────────────────────────────────

SHAPE_REGISTRY = {
    "circle": {
        "fn": circle,
        "multi": False,
        "description": "A circle in a given plane",
        "params": ["center", "radius", "points", "plane", "close"],
    },
    "helix": {
        "fn": helix,
        "multi": False,
        "description": "A 3D helix/spiral rising vertically",
        "params": ["center", "radius", "height", "turns", "points", "direction"],
    },
    "spiral": {
        "fn": spiral,
        "multi": False,
        "description": "A flat Archimedean spiral",
        "params": ["center", "start_radius", "end_radius", "turns", "points", "plane"],
    },
    "lissajous": {
        "fn": lissajous,
        "multi": False,
        "description": "A 3D Lissajous curve",
        "params": ["center", "a_freq", "b_freq", "c_freq", "a_amp", "b_amp", "c_amp", "phase_a", "phase_b", "phase_c", "points"],
    },
    "polygon": {
        "fn": polygon,
        "multi": False,
        "description": "A regular polygon",
        "params": ["center", "sides", "radius", "plane"],
    },
    "star": {
        "fn": star,
        "multi": False,
        "description": "A star shape with inner and outer radius",
        "params": ["center", "points_count", "outer_radius", "inner_radius", "plane"],
    },
    "sphere_wireframe": {
        "fn": sphere_wireframe,
        "multi": True,
        "description": "A wireframe sphere made of latitude and longitude lines",
        "params": ["center", "radius", "lat_lines", "lon_lines", "points_per_line"],
    },
    "cube_wireframe": {
        "fn": cube_wireframe,
        "multi": True,
        "description": "A wireframe cube with 12 edges",
        "params": ["center", "size"],
    },
    "torus": {
        "fn": torus,
        "multi": True,
        "description": "A torus (donut) made of ring paths",
        "params": ["center", "major_radius", "minor_radius", "rings", "points_per_ring"],
    },
    "cylinder_wireframe": {
        "fn": cylinder_wireframe,
        "multi": True,
        "description": "A wireframe cylinder with circles and vertical lines",
        "params": ["center", "radius", "height", "segments", "rings"],
    },
    "cone_wireframe": {
        "fn": cone_wireframe,
        "multi": True,
        "description": "A wireframe cone",
        "params": ["center", "radius", "height", "segments"],
    },
    "tree": {
        "fn": tree_branches,
        "multi": True,
        "description": "A recursive fractal tree with branching",
        "params": ["base", "length", "angle", "depth", "shrink", "spread_3d"],
    },
    "wave_surface": {
        "fn": wave_surface,
        "multi": True,
        "description": "A rippling wave surface grid",
        "params": ["center", "width", "depth_size", "amplitude", "frequency", "grid_x", "grid_z"],
    },
    "mountain_range": {
        "fn": mountain_range,
        "multi": True,
        "description": "A terrain of mountain peaks",
        "params": ["center", "width", "depth_size", "max_height", "peaks", "grid_x", "grid_z"],
    },
    "line": {
        "fn": line,
        "multi": False,
        "description": "A straight line between two points",
        "params": ["start", "end", "points"],
    },
    "grid": {
        "fn": grid_lines,
        "multi": True,
        "description": "A grid of lines in a given plane",
        "params": ["center", "size", "divisions", "plane"],
    },
}


def get_shape_descriptions() -> str:
    """Return a formatted string describing all available shapes and their parameters."""
    lines = []
    for name, info in SHAPE_REGISTRY.items():
        params_str = ", ".join(info["params"])
        lines.append(f"- **{name}**: {info['description']}. Parameters: ({params_str})")
    return "\n".join(lines)
