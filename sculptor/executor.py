"""Executor: Translates art plans into Open Brush API commands.

Takes an ArtPlan and executes it step-by-step against a running
Open Brush instance via the HTTP API.
"""

import logging
import time
from copy import deepcopy

log = logging.getLogger("sculptor.executor")
from typing import Any, Callable

from .openbrush_client import OpenBrushClient, OpenBrushError
from .planner import ArtPlan
from . import primitives


class ExecutionError(Exception):
    """Error during plan execution."""
    pass


class Executor:
    """Executes art plans against Open Brush.

    Translates high-level art plan actions into low-level API commands
    and sends them to a running Open Brush instance.
    """

    def __init__(
        self,
        client: OpenBrushClient,
        on_step: Callable[[int, int, str], None] | None = None,
    ):
        """
        Args:
            client: Open Brush HTTP API client.
            on_step: Optional callback(step_index, total_steps, description)
                     called before each step is executed.
        """
        self.client = client
        self.on_step = on_step

    def execute(self, plan: ArtPlan) -> dict[str, Any]:
        """Execute an art plan.

        Args:
            plan: The art plan to execute.

        Returns:
            Summary dict with execution stats.

        Raises:
            ExecutionError: If a step fails critically.
        """
        total = len(plan.steps)
        results = {
            "title": plan.title,
            "total_steps": total,
            "completed": 0,
            "errors": [],
            "paths_drawn": 0,
        }

        for i, step in enumerate(plan.steps):
            normalized_step = self._normalize_step(step)
            action = normalized_step.get("action", "unknown")
            desc = self._describe_step(step)

            if self.on_step:
                self.on_step(i, total, desc)

            try:
                log.debug("Executing step %d/%d: %s", i + 1, total, desc)
                paths_drawn = self._execute_step(normalized_step)
                results["completed"] += 1
                results["paths_drawn"] += paths_drawn
                log.debug("Step %d complete, %d paths drawn", i + 1, paths_drawn)
            except OpenBrushError as e:
                error_msg = f"Step {i + 1} ({action}): {e}"
                log.warning("Step %d failed (OpenBrush): %s", i + 1, e)
                results["errors"].append(error_msg)
            except Exception as e:
                error_msg = f"Step {i + 1} ({action}): {type(e).__name__}: {e}"
                results["errors"].append(error_msg)

        return results

    def _normalize_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Normalize loosely structured LLM steps into executor-compatible schema."""
        s = deepcopy(step)

        # Expand one-key shorthand objects used by some model outputs.
        if "action" not in s and len(s) == 1:
            key, value = next(iter(s.items()))
            if key == "set_brush_size":
                s = {"action": "set_brush", "size": value}
            elif key == "set_color_html":
                s = {"action": "set_color_html", "color": value}
            elif key == "set_color_rgb":
                s = {"action": "set_color", "rgb": value}
            elif key == "set_color_hsv":
                s = {"action": "set_color_hsv", "hsv": value}
            elif key in ("draw_shape", "draw_path", "draw_svg_path") and isinstance(value, dict):
                s = {"action": key, **value}

        # Normalize common brush key variants.
        if s.get("action") == "set_brush":
            if "type" not in s:
                s["type"] = s.get("brush") or s.get("name") or "ink"

        # Normalize common color key variants.
        if s.get("action") == "set_color_html":
            color_value = s.get("color") or s.get("html") or s.get("hex") or s.get("value")
            if color_value:
                s["color"] = color_value

        # Normalize draw_path variants.
        if s.get("action") == "draw_path":
            if "points" not in s and "path" in s:
                s["points"] = s.get("path")

        # Normalize draw_shape variants.
        if s.get("action") == "draw_shape":
            if "shape" not in s and "type" in s:
                s["shape"] = s.get("type")

            shape_aliases = {
                "sphere": "sphere_wireframe",
                "cone": "cone_wireframe",
                "cylinder": "cylinder_wireframe",
                "cube": "cube_wireframe",
            }
            if isinstance(s.get("shape"), str):
                s["shape"] = shape_aliases.get(s["shape"], s["shape"])

            # Most primitives are centered; convert position -> center.
            if "center" not in s and "position" in s:
                s["center"] = s.get("position")

            # line primitive expects start/end points.
            if s.get("shape") == "line":
                if "start" not in s and "position" in s:
                    s["start"] = s.get("position")
                if "end" not in s and "position_end" in s:
                    s["end"] = s.get("position_end")
                if "end" not in s and "start" in s and "size" in s:
                    start = s.get("start")
                    if isinstance(start, list) and len(start) == 3:
                        s["end"] = [start[0], start[1] + float(s.get("size", 0.1)), start[2]]

        return s

    def _execute_step(self, step: dict[str, Any]) -> int:
        """Execute a single step. Returns number of paths drawn."""
        action = step.get("action", "")
        paths_drawn = 0

        # ── Brush Settings ─────────────────────────────────────
        if action == "set_brush":
            kwargs = {}
            if "type" in step:
                kwargs["brush_type"] = step["type"]
            else:
                kwargs["brush_type"] = "ink"
            if "size" in step:
                kwargs["size"] = float(step["size"])
            self.client.set_brush(**kwargs)

        elif action == "set_color":
            rgb = step.get("rgb", [1, 1, 1])
            self.client.set_color_rgb(float(rgb[0]), float(rgb[1]), float(rgb[2]))

        elif action == "set_color_html":
            self.client.set_color_html(step.get("color", "white"))

        elif action == "set_color_hsv":
            hsv = step.get("hsv", [0, 0, 1])
            self.client.set_color_hsv(float(hsv[0]), float(hsv[1]), float(hsv[2]))

        # ── Drawing Shapes ─────────────────────────────────────
        elif action == "draw_shape":
            paths_drawn = self._draw_shape(step)

        elif action == "draw_path":
            points = [tuple(p) for p in step.get("points", [])]
            if points:
                self.client.draw_path(points)
                paths_drawn = 1

        elif action == "draw_polygon":
            sides = int(step.get("sides", 6))
            radius = float(step.get("radius", 1.0))
            angle = float(step.get("angle", 0))
            self.client.draw_polygon(sides, radius, angle)
            paths_drawn = 1

        elif action == "draw_text":
            self.client.draw_text(step.get("text", ""))
            paths_drawn = 1

        elif action == "draw_svg_path":
            svg_path = step.get("svg_path", "")
            pos = step.get("position", [0, 0, 0])
            # depth_slices: how many Z-depth copies to draw (default 1 = flat)
            depth_slices = int(step.get("depth_slices", 1))
            depth_spacing = float(step.get("depth_spacing", 0.5))

            for slice_idx in range(depth_slices):
                z = float(pos[2]) + slice_idx * depth_spacing
                self.client.move_brush_to(float(pos[0]), float(pos[1]), z)
                self.client.draw_svg_path(svg_path)
                paths_drawn += 1

        # ── Brush Position ─────────────────────────────────────
        elif action == "move_to":
            pos = step.get("position", [0, 0, 0])
            self.client.move_brush_to(float(pos[0]), float(pos[1]), float(pos[2]))

        elif action == "brush_home":
            self.client.brush_home_reset()

        # ── Scene ──────────────────────────────────────────────
        elif action == "new_sketch":
            self.client.new_sketch()
            time.sleep(0.5)  # Give OB time to clear

        elif action == "set_environment":
            self.client.set_environment(step.get("name", "default"))

        elif action == "add_guide":
            guide_type = step.get("type", "cube")
            self.client.add_guide(guide_type)
            # TODO: set position/scale if provided

        # ── Layers ─────────────────────────────────────────────
        elif action == "add_layer":
            self.client.add_layer()

        elif action == "activate_layer":
            self.client.activate_layer(int(step.get("layer", 0)))

        # ── Symmetry ───────────────────────────────────────────
        elif action == "set_symmetry":
            mode = step.get("mode", "mirror")
            if mode == "mirror":
                self.client.set_symmetry_mirror()
            pos = step.get("position")
            if pos:
                self.client.set_symmetry_position(float(pos[0]), float(pos[1]), float(pos[2]))

        # ── Path Smoothing ─────────────────────────────────────
        elif action == "set_smoothing":
            self.client.set_path_smoothing(float(step.get("amount", 0.1)))

        # ── Unknown action ─────────────────────────────────────
        else:
            pass  # Silently skip unknown actions

        return paths_drawn

    def _draw_shape(self, step: dict[str, Any]) -> int:
        """Execute a draw_shape action. Returns number of paths drawn."""
        shape_name = step.get("shape", "")

        if shape_name not in primitives.SHAPE_REGISTRY:
            raise ExecutionError(f"Unknown shape: '{shape_name}'")

        shape_info = primitives.SHAPE_REGISTRY[shape_name]
        fn = shape_info["fn"]
        is_multi = shape_info["multi"]

        # Build kwargs from step, filtering out action/shape keys
        kwargs = {}
        for key, value in step.items():
            if key in ("action", "shape"):
                continue
            # Convert lists to tuples for center/base/start/end params
            if isinstance(value, list) and key in ("center", "base", "start", "end"):
                value = tuple(value)
            kwargs[key] = value

        # Generate points
        result = fn(**kwargs)

        # Draw the result
        if is_multi:
            # result is list of paths
            paths = result
            # Move brush to position before drawing
            center = step.get("center") or step.get("base") or [0, 0, 0]
            if isinstance(center, list):
                self.client.move_brush_to(float(center[0]), float(center[1]), float(center[2]))

            for path in paths:
                self.client.draw_path(path)
            return len(paths)
        else:
            # result is a single path
            center = step.get("center") or step.get("start") or [0, 0, 0]
            if isinstance(center, list):
                self.client.move_brush_to(float(center[0]), float(center[1]), float(center[2]))
            self.client.draw_path(result)
            return 1

    def _describe_step(self, step: dict[str, Any]) -> str:
        """Return a short human-readable description of a step."""
        step = self._normalize_step(step)
        action = step.get("action", "unknown")

        if action == "set_brush":
            return f"Set brush: {step.get('type', '?')} (size={step.get('size', '?')})"
        elif action in ("set_color", "set_color_html", "set_color_hsv"):
            color = step.get("rgb") or step.get("color") or step.get("hsv") or "?"
            return f"Set color: {color}"
        elif action == "draw_shape":
            return f"Draw {step.get('shape', '?')}"
        elif action == "draw_path":
            n = len(step.get("points", []))
            return f"Draw path ({n} points)"
        elif action == "draw_polygon":
            return f"Draw {step.get('sides', '?')}-sided polygon"
        elif action == "draw_text":
            return f"Draw text: '{step.get('text', '')}'"
        elif action == "draw_svg_path":
            path = step.get('svg_path', '')
            preview = path[:20] + "..." if len(path) > 20 else path
            return f"Draw SVG Path: '{preview}'"
        elif action == "move_to":
            return f"Move brush to {step.get('position', '?')}"
        elif action == "new_sketch":
            return "New sketch"
        elif action == "set_environment":
            return f"Set environment: {step.get('name', '?')}"
        elif action == "set_smoothing":
            return f"Set smoothing: {step.get('amount', '?')}"
        elif action == "add_layer":
            return "Add layer"
        elif action == "activate_layer":
            return f"Activate layer {step.get('layer', '?')}"
        else:
            return f"{action}"
