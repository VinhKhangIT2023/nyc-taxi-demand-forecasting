from datetime import datetime
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from src.processing.split_pickup_month import split_month


class MonthSplitTest(unittest.TestCase):
    def test_boundaries_values_and_dropoff_next_month(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.parquet'
            table = pa.table({
                'tpep_pickup_datetime': [datetime(2023, 12, 31), datetime(2024, 1, 1),
                                         datetime(2024, 1, 31, 23, 59), datetime(2024, 2, 1)],
                'tpep_dropoff_datetime': [datetime(2024, 2, 2)] * 4,
                'passenger_count': [1, None, 0, 2],
                'total_amount': [10.0, -5.0, 0.0, 2.0],
            })
            pq.write_table(table, source)
            output = root / 'out'
            result = split_month(source, output, datetime(2024, 1, 1), datetime(2024, 2, 1))
            self.assertEqual(result['in_month_rows'], 2)
            self.assertEqual(result['outside_month_rows'], 2)
            self.assertTrue(pq.read_table(output / 'in_month.parquet').equals(table.slice(1, 2)))
            self.assertEqual(pq.read_table(output / 'outside_month.parquet')['quarantine_reason'].to_pylist(),
                             ['pickup_before_start', 'pickup_at_or_after_end'])
            with self.assertRaises(FileExistsError):
                split_month(source, output, datetime(2024, 1, 1), datetime(2024, 2, 1))

    def test_null_timestamp_requires_new_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.parquet'
            pq.write_table(pa.table({'tpep_pickup_datetime': pa.array([None], type=pa.timestamp('us'))}), source)
            with self.assertRaises(ValueError):
                split_month(source, root / 'out', datetime(2024, 1, 1), datetime(2024, 2, 1))
            self.assertFalse((root / 'out').exists())
