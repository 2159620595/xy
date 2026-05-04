import random
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.slider_patch import _generate_slow_bezier_drag_path


class SliderPatchTrajectoryTest(unittest.TestCase):
    def test_bezier_drag_path_reaches_target_distance(self):
        random.seed(12345)

        target_distance = 286.0
        trajectory = _generate_slow_bezier_drag_path(target_distance)
        total_dx = sum(point["dx"] for point in trajectory)

        self.assertGreater(len(trajectory), 35)
        self.assertAlmostEqual(total_dx, target_distance, places=2)

    def test_bezier_drag_path_contains_slow_steps(self):
        random.seed(54321)

        trajectory = _generate_slow_bezier_drag_path(260.0)
        delays = [point["delay"] for point in trajectory]

        self.assertTrue(any(delay >= 0.02 for delay in delays))
        self.assertTrue(any(point["pause"] > 0 for point in trajectory))


if __name__ == "__main__":
    unittest.main()
