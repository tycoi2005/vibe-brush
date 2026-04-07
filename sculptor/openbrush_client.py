"""HTTP client for the Open Brush API.

Controls Open Brush via its HTTP API running on localhost:40074.
Provides methods for drawing, brush settings, scene management, and export.
"""

import time
import urllib.parse
import logging
from typing import Any

import requests

log = logging.getLogger("sculptor.client")

class OpenBrushError(Exception):
    """Error communicating with Open Brush."""
    pass


class OpenBrushClient:
    """HTTP client for the Open Brush API.

    Open Brush exposes an HTTP API on port 40074 that accepts commands
    as query string parameters on GET requests (or form-encoded POST).

    Example:
        client = OpenBrushClient()
        client.set_brush("ink", size=0.3, color_html="crimson")
        client.draw_path([(0,0,0), (1,0,0), (1,1,0), (0,0,0)])
    """

    def __init__(self, host: str = "localhost", port: int = 40074, command_delay: float = 0.05):
        self.base_url = f"http://{host}:{port}/api/v1"
        self.help_url = f"http://{host}:{port}/help"
        self.command_delay = command_delay
        self._last_command_time = 0.0

    def _throttle(self):
        """Apply minimum delay between commands."""
        elapsed = time.time() - self._last_command_time
        if elapsed < self.command_delay:
            time.sleep(self.command_delay - elapsed)
        self._last_command_time = time.time()

    def send_raw(self, query_string: str) -> requests.Response:
        """Send a raw query string to the API."""
        self._throttle()
        url = f"{self.base_url}?{query_string}"
        log.debug("API Request: %s", url)
        try:
            resp = requests.get(url, timeout=10)
            return resp
        except requests.ConnectionError:
            raise OpenBrushError(
                f"Cannot connect to Open Brush at {self.base_url}. "
                "Is Open Brush running with API enabled?"
            )
        except requests.Timeout:
            raise OpenBrushError("Open Brush API request timed out.")

    def send(self, **commands: Any) -> requests.Response:
        """Send one or more commands to Open Brush.

        Args:
            **commands: Command names as keys, parameters as values.
                Use empty string for commands with no parameters.

        Example:
            client.send(**{"brush.type": "ink", "color.set.html": "red"})
        """
        parts = []
        for cmd, param in commands.items():
            if param == "" or param is None:
                parts.append(cmd)
            else:
                parts.append(f"{cmd}={param}")
        query = "&".join(parts)
        return self.send_raw(query)

    def send_commands(self, commands: list[tuple[str, str | None]]) -> list[requests.Response]:
        """Send a list of (command, param) tuples sequentially."""
        responses = []
        for cmd, param in commands:
            if param is None or param == "":
                resp = self.send_raw(cmd)
            else:
                resp = self.send_raw(f"{cmd}={param}")
            responses.append(resp)
        return responses

    # ─── Connection ───────────────────────────────────────────────

    def is_connected(self) -> bool:
        """Check if Open Brush is running and API is accessible."""
        try:
            resp = requests.get(f"{self.help_url}", timeout=3)
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    # ─── Scene Management ─────────────────────────────────────────

    def new_sketch(self):
        """Clear the scene and start a new sketch."""
        return self.send(new="")

    def save(self, name: str | None = None):
        """Save the current sketch."""
        if name:
            return self.send(**{"save.as": name})
        return self.send(**{"save.new": ""})

    def save_overwrite(self):
        """Save overwriting the last save."""
        return self.send(**{"save.overwrite": ""})

    def load(self, name: str):
        """Load a sketch by filename."""
        return self.send(**{"load.named": name})

    def undo(self):
        """Undo the last action."""
        return self.send(undo="")

    def redo(self):
        """Redo the last undone action."""
        return self.send(redo="")

    # ─── Brush Settings ───────────────────────────────────────────

    def set_brush(self, brush_type: str, size: float | None = None,
                  color_html: str | None = None,
                  color_rgb: tuple[float, float, float] | None = None,
                  color_hsv: tuple[float, float, float] | None = None):
        """Set brush type, size, and color in one call."""
        cmds = {"brush.type": brush_type}
        if size is not None:
            cmds["brush.size.set"] = str(size)
        if color_html:
            cmds["color.set.html"] = color_html
        if color_rgb:
            cmds["color.set.rgb"] = f"{color_rgb[0]},{color_rgb[1]},{color_rgb[2]}"
        if color_hsv:
            cmds["color.set.hsv"] = f"{color_hsv[0]},{color_hsv[1]},{color_hsv[2]}"
        return self.send(**cmds)

    def set_brush_type(self, brush_type: str):
        """Change the brush type (e.g., 'ink', 'light', 'smoke', etc.)."""
        return self.send(**{"brush.type": brush_type})

    def set_brush_size(self, size: float):
        """Set brush size (typical range 0.01 to 1.0)."""
        return self.send(**{"brush.size.set": str(size)})

    def set_color_rgb(self, r: float, g: float, b: float):
        """Set brush color using RGB values (0.0 to 1.0)."""
        return self.send(**{"color.set.rgb": f"{r},{g},{b}"})

    def set_color_hsv(self, h: float, s: float, v: float):
        """Set brush color using HSV values (0.0 to 1.0)."""
        return self.send(**{"color.set.hsv": f"{h},{s},{v}"})

    def set_color_html(self, color: str):
        """Set brush color using a CSS color name or hex value."""
        return self.send(**{"color.set.html": color})

    def set_path_smoothing(self, amount: float):
        """Set path smoothing amount. 0 = no smoothing, default = 0.1."""
        return self.send(**{"brush.pathsmoothing": str(amount)})

    # ─── Brush Movement ───────────────────────────────────────────

    def move_brush_to(self, x: float, y: float, z: float):
        """Move brush to absolute position without drawing."""
        return self.send(**{"brush.move.to": f"{x},{y},{z}"})

    def move_brush_by(self, dx: float, dy: float, dz: float):
        """Move brush by relative offset without drawing."""
        return self.send(**{"brush.move.by": f"{dx},{dy},{dz}"})

    def brush_move(self, distance: float):
        """Move brush forward by distance (without drawing)."""
        return self.send(**{"brush.move": str(distance)})

    def brush_draw(self, distance: float):
        """Move brush forward by distance AND draw a line."""
        return self.send(**{"brush.draw": str(distance)})

    def brush_turn_y(self, angle: float):
        """Turn brush left/right by angle in degrees."""
        return self.send(**{"brush.turn.y": str(angle)})

    def brush_turn_x(self, angle: float):
        """Pitch brush up/down by angle in degrees."""
        return self.send(**{"brush.turn.x": str(angle)})

    def brush_turn_z(self, angle: float):
        """Roll brush clockwise/counterclockwise by angle in degrees."""
        return self.send(**{"brush.turn.z": str(angle)})

    def brush_look_at(self, x: float, y: float, z: float):
        """Point brush toward a specific position."""
        return self.send(**{"brush.look.at": f"{x},{y},{z}"})

    def brush_look_direction(self, direction: str):
        """Point brush in a named direction: forwards, backwards, up, down, left, right."""
        valid = {"forwards", "backwards", "up", "down", "left", "right"}
        if direction not in valid:
            raise ValueError(f"Direction must be one of {valid}")
        return self.send(**{f"brush.look.{direction}": ""})

    def brush_home_reset(self):
        """Reset brush position and direction to origin."""
        return self.send(**{"brush.home.reset": ""})

    def brush_push(self):
        """Push current brush position/direction to stack."""
        return self.send(**{"brush.transform.push": ""})

    def brush_pop(self):
        """Pop brush position/direction from stack."""
        return self.send(**{"brush.transform.pop": ""})

    def force_painting_on(self, active: bool = True):
        """Force painting to be always on."""
        return self.send(**{"brush.force.painting.on": str(active).lower()})

    def force_painting_off(self, active: bool = True):
        """Force painting to be always off."""
        return self.send(**{"brush.force.painting.off": str(active).lower()})

    def new_stroke(self):
        """End current stroke, start a new one."""
        return self.send(**{"brush.new.stroke": ""})

    # ─── Drawing Primitives ───────────────────────────────────────

    def draw_path(self, points: list[tuple[float, float, float]]):
        """Draw a path from a list of (x, y, z) points.

        Points are relative to the current brush position.
        Does not move the brush position afterward.
        """
        path_str = ",".join(f"[{x},{y},{z}]" for x, y, z in points)
        return self.send(**{"draw.path": path_str})

    def draw_paths(self, paths: list[list[tuple[float, float, float]]]):
        """Draw multiple paths at once.

        Each path is a list of (x, y, z) points.
        """
        paths_strs = []
        for path in paths:
            p = ",".join(f"[{x},{y},{z}]" for x, y, z in path)
            paths_strs.append(f"[{p}]")
        all_paths = ",".join(paths_strs)
        return self.send(**{"draw.paths": all_paths})

    def draw_stroke(self, points: list[tuple[float, float, float, float, float, float, float]]):
        """Draw a stroke with full control: (x, y, z, rx, ry, rz, pressure)."""
        stroke_str = ",".join(f"[{x},{y},{z},{rx},{ry},{rz},{p}]" for x, y, z, rx, ry, rz, p in points)
        return self.send(**{"draw.stroke": stroke_str})

    def draw_polygon(self, sides: int, radius: float, angle: float = 0):
        """Draw a regular polygon at the current brush position."""
        return self.send(**{"draw.polygon": f"{sides},{radius},{angle}"})

    def draw_text(self, text: str):
        """Draw text as brush strokes at the current brush position."""
        encoded = urllib.parse.quote(text)
        return self.send(**{"draw.text": encoded})

    def draw_svg_path(self, svg_path: str):
        """Draw an SVG path string at the current brush position."""
        encoded = urllib.parse.quote(svg_path)
        return self.send(**{"draw.svg.path": encoded})

    # ─── Camera ───────────────────────────────────────────────────

    def spectator_move_to(self, x: float, y: float, z: float):
        """Move spectator camera to position."""
        return self.send(**{"spectator.move.to": f"{x},{y},{z}"})

    def spectator_look_at(self, x: float, y: float, z: float):
        """Point spectator camera at a position."""
        return self.send(**{"spectator.look.at": f"{x},{y},{z}"})

    def user_move_to(self, x: float, y: float, z: float):
        """Move user viewpoint to position."""
        return self.send(**{"user.move.to": f"{x},{y},{z}"})

    # ─── Environment ──────────────────────────────────────────────

    def set_environment(self, name: str):
        """Set the environment/background (e.g., 'pistachio', 'space', etc.)."""
        return self.send(**{"environment.type": name})

    def import_skybox(self, location: str):
        """Set skybox from URL or filename in BackgroundImages."""
        return self.send(**{"skybox.import": location})

    # ─── Models & Media ───────────────────────────────────────────

    def import_model(self, filename: str):
        """Import a 3D model from Media Library/Models."""
        return self.send(**{"model.import": filename})

    def import_model_web(self, url: str):
        """Import a 3D model from a URL."""
        return self.send(**{"model.webimport": url})

    def import_image(self, location: str):
        """Import an image from URL or Media Library/Images."""
        return self.send(**{"image.import": location})

    def add_text_widget(self, text: str):
        """Add a text widget to the sketch."""
        return self.send(**{"text.add": urllib.parse.quote(text)})

    # ─── Guides ───────────────────────────────────────────────────

    def add_guide(self, guide_type: str):
        """Add a guide shape: cube, sphere, capsule, cone, ellipsoid."""
        return self.send(**{"guide.add": guide_type})

    def guide_position(self, index: int, x: float, y: float, z: float):
        """Move a guide to position."""
        return self.send(**{"guide.position": f"{index},{x},{y},{z}"})

    def guide_scale(self, index: int, sx: float, sy: float, sz: float):
        """Set non-uniform scale of a guide."""
        return self.send(**{"guide.scale": f"{index},{sx},{sy},{sz}"})

    # ─── Layers ───────────────────────────────────────────────────

    def add_layer(self):
        """Add a new layer."""
        return self.send(**{"layer.add": ""})

    def activate_layer(self, layer: int):
        """Make a layer the active layer."""
        return self.send(**{"layer.activate": str(layer)})

    # ─── Symmetry ─────────────────────────────────────────────────

    def set_symmetry_mirror(self):
        """Enable mirror symmetry."""
        return self.send(**{"symmetry.mirror": ""})

    def set_symmetry_position(self, x: float, y: float, z: float):
        """Move symmetry widget to position."""
        return self.send(**{"symmetry.position": f"{x},{y},{z}"})

    # ─── Selection & Strokes ──────────────────────────────────────

    def select_all(self):
        """Select all strokes on current layer."""
        return self.send(**{"select.all": ""})

    def select_none(self):
        """Deselect everything."""
        return self.send(**{"select.none": ""})

    def select_stroke(self, index: int):
        """Select a stroke by index."""
        return self.send(**{"stroke.select": str(index)})

    def delete_stroke(self, index: int):
        """Delete a stroke by index."""
        return self.send(**{"stroke.delete": str(index)})

    def selection_delete(self):
        """Delete the current selection."""
        return self.send(**{"selection.delete": ""})

    def selection_duplicate(self):
        """Duplicate the current selection."""
        return self.send(**{"selection.duplicate": ""})

    # ─── Export ───────────────────────────────────────────────────

    def export_current(self):
        """Export the current sketch to the Exports folder."""
        return self.send(**{"export.current": ""})

    def export_selected(self):
        """Export only the selected strokes."""
        return self.send(**{"export.selected": ""})

    # ─── Scene Scale ──────────────────────────────────────────────

    def set_scene_scale(self, scale: float):
        """Set absolute scene scale."""
        return self.send(**{"scene.scale.to": str(scale)})

    def scale_scene_by(self, factor: float):
        """Scale scene by a factor."""
        return self.send(**{"scene.scale.by": str(factor)})

    # ─── Straight Edge & Snapping ─────────────────────────────────

    def toggle_straight_edge(self):
        """Toggle straight edge tool."""
        return self.send(**{"straightedge.toggle": ""})

    def set_snap_grid(self, size: float):
        """Set snap grid size (0.1, 0.25, 0.5, 1, 2, 3, 5)."""
        return self.send(**{"snap.grid": str(size)})

    def set_snap_angle(self, angle: int):
        """Set snap angle (15, 30, 45, 60, 75, 90)."""
        return self.send(**{"snap.angle": str(angle)})
