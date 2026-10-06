"""Read-only duration profile; descriptive bands are NOT cleaning thresholds."""
import argparse
from collections import Counter
import heapq
import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.ingestion.check_pickup_zones import digest


BANDS = ['missing_time', 'negative', 'zero', '(0,1] min', '(1,5] min',
         '(5,15] min', '(15,30] min', '(30,60] min', '(1,2] hours',
         '(2,6] hours', '(6,24] hours', '>24 hours']
FIELDS = ['tpep_pickup_datetime', 'tpep_dropoff_datetime', 'PULocationID',
          'DOLocationID', 'trip_distance', 'fare_amount', 'total_amount', 'passenger_count']


def duration_us(pickup, dropoff):
    if pickup is None or dropoff is None:
        return None
    delta = dropoff - pickup
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


def band(value):
    if value is None:
        return 'missing_time'
    if value < 0:
        return 'negative'
    if value == 0:
        return 'zero'
    for minutes, label in zip([1, 5, 15, 30, 60, 120, 360, 1440], BANDS[3:-1]):
        if value <= minutes * 60 * 1000000:
            return label
    return '>24 hours'


def quantiles_minutes(histogram):
    """Exact linear-interpolated quantiles of the full duration histogram."""
    n = sum(histogram.values())
    if not n:
        return {}
    result = {}
    for q in [0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1]:
        index = (n - 1) * q
        low, high = math.floor(index), math.ceil(index)
        cumulative = 0
        lo_value = None
        for value, count in sorted(histogram.items()):
            cumulative += count
            if lo_value is None and cumulative > low:
                lo_value = value
            if cumulative > high:
                result[str(q)] = (lo_value + (value - lo_value) * (index - low)) / 60000000
                break
    return result


def profile(source):
    original = digest(source)
    parquet = pq.ParquetFile(source)
    groups = {label: Counter(rows=0, distance_zero=0, distance_negative=0,
                             distance_missing=0, fare_negative=0, total_negative=0,
                             total_zero=0, passenger_missing=0) for label in BANDS}
    samples = {label: [] for label in BANDS}
    histogram = Counter()
    longest = []
    row_number = 0
    for batch in parquet.iter_batches(columns=FIELDS, batch_size=32768):
        columns = [batch.column(name).to_pylist() for name in FIELDS]
        for values in zip(*columns):
            pickup, dropoff, pu, do, distance, fare, total, passenger = values
            value = duration_us(pickup, dropoff)
            label = band(value)
            group = groups[label]
            group['rows'] += 1
            group['distance_zero'] += distance == 0
            group['distance_negative'] += distance is not None and distance < 0
            group['distance_missing'] += distance is None
            group['fare_negative'] += fare is not None and fare < 0
            group['total_negative'] += total is not None and total < 0
            group['total_zero'] += total == 0
            group['passenger_missing'] += passenger is None
            if value is not None:
                histogram[value] += 1
            needs_sample = len(samples[label]) < 3
            needs_longest = value is not None and (len(longest) < 5 or value > longest[0][0])
            if needs_sample or needs_longest:
                record = dict(zip(FIELDS, values))
                record.update(input_row_index=row_number,
                              duration_minutes=None if value is None else value / 60000000)
                if needs_sample:
                    samples[label].append(record)
                if needs_longest:
                    heapq.heappush(longest, (value, row_number, record))
                    if len(longest) > 5:
                        heapq.heappop(longest)
            row_number += 1
    assert row_number == parquet.metadata.num_rows == sum(g['rows'] for g in groups.values())
    assert digest(source) == original
    return {
        'source': source.as_posix(), 'sha256': original, 'input_unchanged': True,
        'rows': row_number, 'pyarrow_version': pa.__version__,
        'duration_definition': 'dropoff minus pickup in source wall-clock time; no timezone conversion',
        'groups': groups,
        'quantiles_all_nonmissing_minutes': quantiles_minutes(histogram),
        'quantiles_positive_minutes': quantiles_minutes(Counter({v: n for v, n in histogram.items() if v > 0})),
        'first_three_examples_per_band': samples,
        'five_longest': [item[2] for item in sorted(longest, reverse=True)],
        'limitations': ['Bands are descriptive only, not approved removal thresholds.',
                       'Examples are first rows per band, not random representative samples.',
                       'Cross-check columns overlap; their counts must not be summed as removals.',
                       'No cleaning, imputation or causal explanation applied.'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/interim/pickup_zones_2024-01/zone_candidates.parquet'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/metrics/duration_2024-01.json'))
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Output must differ from input')
    result = profile(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ['rows', 'groups', 'quantiles_positive_minutes', 'five_longest']}, indent=2, default=str))
