import unittest
from src.ingestion.check_pickup_zones import classify


class ZoneAuditTest(unittest.TestCase):
    def test_membership_is_not_the_same_as_known_location(self):
        lookup = {1: {'Zone': 'Newark Airport'}, 264: {'Zone': 'N/A'},
                  265: {'Zone': 'Outside of NYC'}}
        self.assertEqual(classify(None, lookup), 'missing_id')
        self.assertEqual(classify(999, lookup), 'not_in_lookup')
        self.assertEqual(classify(264, lookup), 'unknown_zone')
        self.assertEqual(classify(265, lookup), 'outside_nyc_unspecified')
        self.assertEqual(classify(1, lookup), 'named_zone')
