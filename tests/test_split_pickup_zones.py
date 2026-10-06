from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from src.processing.split_pickup_zones import split_zones


class SplitZonesTest(unittest.TestCase):
    def test_only_approved_ids_are_separated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / 'lookup.csv'
            reference.write_text('LocationID,Zone\n1,Newark Airport\n2,Jamaica Bay\n264,N/A\n265,Outside of NYC\n', encoding='utf-8')
            source = root / 'source.parquet'
            table = pa.table({'PULocationID': [1, 264, 2, 265],
                              'passenger_count': [None, 1, 0, 2],
                              'total_amount': [-10.0, 5.0, 0.0, 8.0]})
            pq.write_table(table, source)
            result = split_zones(source, reference, root / 'out')
            self.assertEqual(result['candidate_rows'], 2)
            self.assertEqual(result['quarantined_rows'], 2)
            self.assertTrue(pq.read_table(root / 'out/zone_candidates.parquet').equals(table.take([0, 2])))
            quarantine = pq.read_table(root / 'out/unspecified_zones.parquet')
            self.assertTrue(quarantine.drop(['quarantine_reason']).equals(table.take([1, 3])))
            self.assertEqual(quarantine['quarantine_reason'].to_pylist(),
                             ['unknown_pickup_zone_264', 'outside_nyc_unspecified_265'])
            with self.assertRaises(FileExistsError):
                split_zones(source, reference, root / 'out')
            for unknown in [None, 999]:
                pq.write_table(pa.table({'PULocationID': pa.array([unknown], type=pa.int32())}), source)
                with self.assertRaises(ValueError):
                    split_zones(source, reference, root / 'unexpected')
                self.assertFalse((root / 'unexpected').exists())
