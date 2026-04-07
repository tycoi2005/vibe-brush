import unittest

from sculptor.executor import Executor


class _FakeClient:
    def __init__(self):
        self.calls = []

    def set_brush(self, **kwargs):
        self.calls.append(("set_brush", kwargs))

    def set_color_rgb(self, r, g, b):
        self.calls.append(("set_color_rgb", (r, g, b)))

    def set_color_html(self, color):
        self.calls.append(("set_color_html", color))

    def set_color_hsv(self, h, s, v):
        self.calls.append(("set_color_hsv", (h, s, v)))

    def draw_path(self, points):
        self.calls.append(("draw_path", points))

    def draw_polygon(self, sides, radius, angle):
        self.calls.append(("draw_polygon", (sides, radius, angle)))

    def draw_text(self, text):
        self.calls.append(("draw_text", text))

    def move_brush_to(self, x, y, z):
        self.calls.append(("move_brush_to", (x, y, z)))

    def draw_svg_path(self, svg_path):
        self.calls.append(("draw_svg_path", svg_path))

    def brush_home_reset(self):
        self.calls.append(("brush_home_reset", None))

    def new_sketch(self):
        self.calls.append(("new_sketch", None))

    def set_environment(self, name):
        self.calls.append(("set_environment", name))

    def add_guide(self, guide_type):
        self.calls.append(("add_guide", guide_type))

    def add_layer(self):
        self.calls.append(("add_layer", None))

    def activate_layer(self, layer):
        self.calls.append(("activate_layer", layer))

    def set_symmetry_mirror(self):
        self.calls.append(("set_symmetry_mirror", None))

    def set_symmetry_position(self, x, y, z):
        self.calls.append(("set_symmetry_position", (x, y, z)))

    def set_path_smoothing(self, amount):
        self.calls.append(("set_path_smoothing", amount))


class ExecutorNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.client = _FakeClient()
        self.executor = Executor(self.client)

    def test_normalize_shorthand_set_color_html(self):
        normalized = self.executor._normalize_step({"set_color_html": "#ffffff"})
        self.assertEqual(normalized["action"], "set_color_html")
        self.assertEqual(normalized["color"], "#ffffff")

    def test_normalize_draw_shape_alias_and_position(self):
        normalized = self.executor._normalize_step(
            {"action": "draw_shape", "shape": "sphere", "position": [1, 2, 3], "radius": 0.5}
        )
        self.assertEqual(normalized["shape"], "sphere_wireframe")
        self.assertEqual(normalized["center"], [1, 2, 3])

    def test_normalize_line_position_fields(self):
        normalized = self.executor._normalize_step(
            {
                "action": "draw_shape",
                "shape": "line",
                "position": [0, 0, 0],
                "position_end": [0, 1, 0],
            }
        )
        self.assertEqual(normalized["start"], [0, 0, 0])
        self.assertEqual(normalized["end"], [0, 1, 0])

    def test_normalize_draw_path_alias(self):
        normalized = self.executor._normalize_step(
            {"action": "draw_path", "path": [[0, 0, 0], [1, 0, 0]]}
        )
        self.assertIn("points", normalized)
        self.assertEqual(len(normalized["points"]), 2)


if __name__ == "__main__":
    unittest.main()
