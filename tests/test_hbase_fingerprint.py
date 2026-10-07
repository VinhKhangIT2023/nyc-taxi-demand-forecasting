import hashlib
import unittest
from src.storage.verify_hbase_full import fingerprint


class FingerprintTests(unittest.TestCase):
    def digest(self, key, cells):
        h = hashlib.sha256()
        fingerprint(h, key, cells)
        return h.hexdigest()

    def test_cell_order_is_irrelevant(self):
        self.assertEqual(self.digest(b'key', {b'd:a': b'1', b'q:b': b'0'}),
                         self.digest(b'key', {b'q:b': b'0', b'd:a': b'1'}))

    def test_boundaries_and_missing_are_distinct(self):
        self.assertNotEqual(self.digest(b'key', {b'a': b'bc'}), self.digest(b'key', {b'ab': b'c'}))
        self.assertNotEqual(self.digest(b'key', {}), self.digest(b'key', {b'a': b'0'}))
