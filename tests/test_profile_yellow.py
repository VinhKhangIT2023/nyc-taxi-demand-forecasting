"""Small fixture checks for counts used to propose cleaning decisions."""
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from src.ingestion.profile_yellow import profile


class ProfileTest(unittest.TestCase):
    def test_cross_batch_duplicates_nulls_and_exclusive_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'raw').mkdir()
            (root / 'interim').mkdir()
            jan = datetime(2024, 1, 1)
            feb = datetime(2024, 2, 1)
            table = pa.table({
                'tpep_pickup_datetime': [jan, feb, jan, None],
                'tpep_dropoff_datetime': [jan, jan, jan, None],
                'PULocationID': [1, 2, 1, None],
                'trip_distance': [0.0, -1.0, 0.0, None],
                'passenger_count': [1.0, 0.0, 1.0, None],
                'fare_amount': [5.0, -2.0, 5.0, None],
                'total_amount': [5.0, -2.0, 5.0, None],
            })
            path = root / 'raw' / 'fixture.parquet'
            pq.write_table(table, path)
            result = profile(path, jan, feb, batch_size=2)
            self.assertEqual(result['rows'], 4)
            self.assertEqual(result['issues']['full_row_duplicate_excess'], 1)
            self.assertEqual(result['issues']['pickup_at_or_after_end'], 1)
            self.assertEqual(result['issues']['dropoff_before_pickup'], 1)
            self.assertEqual(result['columns']['tpep_pickup_datetime']['nulls'], 1)
            self.assertEqual(result['pickup_days_in_interval'], {'2024-01-01': 2})
            self.assertTrue(result['input_unchanged'])


if __name__ == '__main__':
    unittest.main()
