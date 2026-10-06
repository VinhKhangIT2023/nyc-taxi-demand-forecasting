import csv
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from src.processing.finalize_trial import finalize


class FinalizeTest(unittest.TestCase):
    def test_quarantine_flags_and_hourly_conservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pickup = datetime(2024, 1, 1)
            table = pa.table({
                'tpep_pickup_datetime': [pickup] * 4,
                'tpep_dropoff_datetime': [pickup - timedelta(seconds=1), pickup,
                                          pickup + timedelta(minutes=10), pickup + timedelta(hours=25)],
                'PULocationID': [1, 1, 1, 1], 'trip_distance': [1.0, 0.0, 0.0, 300000.0],
                'fare_amount': [2.0, 2.0, -5.0, 10.0], 'total_amount': [3.0, 3.0, -7.0, 12.0],
                'passenger_count': [1, 1, None, 0],
            })
            source = root / 'source.parquet'
            pq.write_table(table, source)
            result = finalize(source, root / 'out')
            self.assertEqual(result['retained_rows'], 2)
            self.assertEqual(result['quarantine_reasons'], {'negative_duration': 1, 'zero_duration': 1})
            kept = pq.read_table(root / 'out/trips.parquet')
            self.assertTrue(kept.select(table.column_names).equals(table.slice(2)))
            self.assertEqual(kept['q_duration_gt_24h'].to_pylist(), [False, True])
            self.assertEqual(kept['q_passenger_missing'].to_pylist(), [True, False])
            with (root / 'out/duration_sensitivity.csv').open() as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual((row['count_with_nonpositive'], row['count_without_nonpositive'], row['difference']), ('4', '2', '2'))
            self.assertEqual(result['max_hourly_count_difference'], 2)
            with self.assertRaises(FileExistsError):
                finalize(source, root / 'out')
