import unittest
import pyarrow as pa
from src.processing.normalize_schema import common_schema, normalize


class NormalizeTest(unittest.TestCase):
    def test_known_alias_and_null_values(self):
        schema = common_schema()
        arrays = [pa.array([None], type=field.type) for field in schema]
        table = pa.Table.from_arrays(arrays, schema=schema)
        names = ['airport_fee' if n == 'Airport_fee' else n for n in table.column_names]
        result = normalize(table.rename_columns(names))
        self.assertTrue(result.equals(table))

    def test_unknown_field_fails(self):
        with self.assertRaises(ValueError):
            normalize(pa.table({'unexpected': [1]}))

    def test_older_schema_keeps_new_fee_missing_not_zero(self):
        schema = common_schema()
        table = pa.Table.from_arrays([pa.array([None], type=f.type) for f in schema], schema=schema)
        result = normalize(table.drop(['cbd_congestion_fee']))
        self.assertEqual(result['cbd_congestion_fee'].to_pylist(), [None])
