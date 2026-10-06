from collections import Counter
from datetime import datetime, timedelta
import unittest

from src.ingestion.profile_duration import band, duration_us, quantiles_minutes


class DurationTest(unittest.TestCase):
    def test_signed_duration_and_boundaries(self):
        pickup = datetime(2024, 1, 1)
        self.assertEqual(duration_us(pickup, pickup - timedelta(seconds=1)), -1000000)
        self.assertEqual(band(duration_us(pickup, None)), 'missing_time')
        self.assertEqual(band(-1), 'negative')
        self.assertEqual(band(0), 'zero')
        self.assertEqual(band(60000000), '(0,1] min')
        self.assertEqual(band(60000001), '(1,5] min')
        self.assertEqual(band(86400000000), '(6,24] hours')
        self.assertEqual(band(86400000001), '>24 hours')

    def test_weighted_quantiles_use_full_counts(self):
        # Sorted minutes are [1, 1, 3, 5]; interpolated median is 2.
        result = quantiles_minutes(Counter({60000000: 2, 180000000: 1, 300000000: 1}))
        self.assertEqual(result['0.5'], 2)
        self.assertEqual(result['0'], 1)
        self.assertEqual(result['1'], 5)
        self.assertEqual(quantiles_minutes(Counter()), {})
