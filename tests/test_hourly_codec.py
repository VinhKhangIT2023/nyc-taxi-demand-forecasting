import unittest
from datetime import datetime
from src.storage.hourly_codec import encode


class CodecTest(unittest.TestCase):
    def row(self, **changes):
        base = dict(PULocationID=1, pickup_hour=datetime(2024, 1, 1),
                    recorded_trip_count=0, target_trip_count=0,
                    q_source_hour_missing=False, q_dst_day=False,
                    q_zero_recorded=True, model_eligible=True)
        return {**base, **changes}

    def test_zero_is_a_value_and_keys_sort_by_hour(self):
        key, cells, deletes = encode(self.row())
        self.assertEqual(key, b'001#2024010100')
        self.assertEqual(cells[b'd:target_trip_count'], b'0')
        self.assertEqual(deletes, [])
        later, _, _ = encode(self.row(pickup_hour=datetime(2024, 1, 1, 1)))
        self.assertLess(key, later)

    def test_missing_clears_stale_cells_instead_of_writing_zero(self):
        _, existing, _ = encode(self.row())
        _, cells, deletes = encode(self.row(recorded_trip_count=None, target_trip_count=None,
                                            q_source_hour_missing=True, q_zero_recorded=False, model_eligible=False))
        for column in deletes:
            existing.pop(column, None)
        existing.update(cells)
        self.assertNotIn(b'd:recorded_trip_count', existing)
        self.assertNotIn(b'd:target_trip_count', existing)
        self.assertEqual(existing[b'q:source_hour_missing'], b'1')

    def test_dst_retains_descriptive_count_but_clears_target(self):
        _, cells, deletes = encode(self.row(pickup_hour=datetime(2024, 3, 10, 1),
                                            recorded_trip_count=7, target_trip_count=None,
                                            q_dst_day=True, q_zero_recorded=False, model_eligible=False))
        self.assertEqual(cells[b'd:recorded_trip_count'], b'7')
        self.assertEqual(deletes, [b'd:target_trip_count'])

    def test_inconsistent_rows_are_rejected(self):
        with self.assertRaises(ValueError):
            encode(self.row(target_trip_count=None))
        with self.assertRaises(ValueError):
            encode(self.row(PULocationID=264))
        with self.assertRaises(ValueError):
            encode(self.row(pickup_hour=datetime(2024, 1, 1, 0, 1)))


if __name__ == '__main__':
    unittest.main()
