from datetime import datetime, date
import unittest
from src.processing.build_hourly_grid import grid_for_zone, dst_dates


class GridTest(unittest.TestCase):
    def test_dst_dates(self):
        self.assertEqual(dst_dates(2024), {date(2024, 3, 10), date(2024, 11, 3)})
        self.assertEqual(dst_dates(2025), {date(2025, 3, 9), date(2025, 11, 2)})

    def test_zero_missing_and_dst_are_not_interchangeable(self):
        hours = [datetime(2024, 1, 1, h) for h in range(3)] + [datetime(2024, 11, 3, 1)]
        recorded = {(1, hours[0]): 3, (1, hours[3]): 8}
        source = {hours[0], hours[1], hours[3]}
        result = grid_for_zone(1, hours, recorded, source, dst_dates(2024))
        self.assertEqual(result['recorded_trip_count'].to_pylist(), [3, 0, None, 8])
        self.assertEqual(result['target_trip_count'].to_pylist(), [3, 0, None, None])
        self.assertEqual(result['model_eligible'].to_pylist(), [True, True, False, False])
        self.assertEqual(result['q_zero_recorded'].to_pylist(), [False, True, False, False])
