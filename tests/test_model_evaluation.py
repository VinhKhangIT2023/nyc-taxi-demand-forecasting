import unittest
from src.models.evaluation import finalize_sums, pool_metrics


class ModelEvaluationTest(unittest.TestCase):
    def test_pool_weights_rows_instead_of_averaging_fold_scores(self):
        result = pool_metrics([dict(n=1, absolute_error=10, squared_error=100, actual_sum=0),
                               dict(n=9, absolute_error=0, squared_error=0, actual_sum=10)])
        self.assertEqual(result['mae'], 1)
        self.assertEqual(result['wape'], 1)
        self.assertAlmostEqual(result['rmse'], 10 ** 0.5)

    def test_zero_denominator_has_no_wape(self):
        result = finalize_sums(dict(n=2, absolute_error=3, squared_error=5, actual_sum=0))
        self.assertIsNone(result['wape'])
        self.assertEqual(result['mae'], 1.5)

    def test_empty_evaluation_is_not_a_success(self):
        with self.assertRaises(ValueError):
            finalize_sums(dict(n=0, absolute_error=0, squared_error=0, actual_sum=0))
