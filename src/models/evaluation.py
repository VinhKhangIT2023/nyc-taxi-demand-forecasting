"""Small auditable metric reducers shared by fold selection and tests."""
import math


def finalize_sums(sums):
    n = int(sums['n'])
    if n <= 0:
        raise ValueError('No evaluation targets')
    return dict(sums, mae=sums['absolute_error'] / n,
                rmse=math.sqrt(sums['squared_error'] / n),
                wape=sums['absolute_error'] / sums['actual_sum'] if sums['actual_sum'] else None)


def pool_metrics(metrics):
    return finalize_sums({name: sum(item[name] for item in metrics)
                          for name in ('n', 'absolute_error', 'squared_error', 'actual_sum')})
