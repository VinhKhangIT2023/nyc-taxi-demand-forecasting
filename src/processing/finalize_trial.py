"""Finalize the approved January trial; keep flagged values, quarantine duration <= 0.

Run with python -m src.processing.finalize_trial from the repository root.
Hourly output contains observed groups only, without imputing absent hours.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import csv
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from src.ingestion.check_pickup_zones import digest


FLAGS = ['q_duration_gt_24h', 'q_distance_zero', 'q_distance_negative',
         'q_fare_negative', 'q_total_negative', 'q_passenger_missing', 'q_passenger_zero']


def enrich(table):
    # Preserve sub-second precision; source timestamps have no timezone offset.
    pickup = pc.cast(table['tpep_pickup_datetime'], pa.timestamp('us'))
    dropoff = pc.cast(table['tpep_dropoff_datetime'], pa.timestamp('us'))
    micros = pc.subtract(pc.cast(dropoff, pa.int64()), pc.cast(pickup, pa.int64()))
    duration = pc.divide(pc.cast(micros, pa.float64()), 60000000.0)
    flags = [pc.greater(micros, 86400000000),
             pc.equal(table['trip_distance'], 0), pc.less(table['trip_distance'], 0),
             pc.less(table['fare_amount'], 0), pc.less(table['total_amount'], 0),
             pc.is_null(table['passenger_count']), pc.equal(table['passenger_count'], 0)]
    result = table.append_column('duration_minutes', duration)
    for name, flag in zip(FLAGS, flags):
        result = result.append_column(name, pc.fill_null(flag, False))
    return result


def finalize(source, output_dir):
    original = digest(source)
    parquet = pq.ParquetFile(source)
    derived = set(FLAGS + ['duration_minutes', 'quarantine_reason'])
    if derived.intersection(parquet.schema_arrow.names):
        raise ValueError('Input must be the zone candidates, not a previous output')
    for batch in parquet.iter_batches(columns=['tpep_pickup_datetime', 'tpep_dropoff_datetime', 'PULocationID']):
        if any(column.null_count for column in batch.columns):
            raise ValueError('Missing time/zone requires an explicit new rule')
        if any(zone in (264, 265) for zone in pc.unique(batch.column('PULocationID')).to_pylist()):
            raise ValueError('Run the approved zone split first')
    output_dir.mkdir(parents=True, exist_ok=False)
    schema = parquet.schema_arrow.append(pa.field('duration_minutes', pa.float64()))
    for name in FLAGS:
        schema = schema.append(pa.field(name, pa.bool_()))
    kept_path, quarantine_path = output_dir / 'trips.parquet', output_dir / 'duration_quarantine.parquet'
    reasons = Counter(negative_duration=0, zero_duration=0)
    flag_counts = Counter({name: 0 for name in FLAGS})
    retained, excluded = Counter(), Counter()
    kept_count = 0
    with ExitStack() as stack:
        kept_writer = stack.enter_context(pq.ParquetWriter(kept_path, schema))
        rejected_writer = stack.enter_context(pq.ParquetWriter(quarantine_path, schema.append(pa.field('quarantine_reason', pa.string()))))
        for batch in parquet.iter_batches(batch_size=32768):
            table = enrich(pa.Table.from_batches([batch]))
            mask = pc.greater(table['duration_minutes'], 0)
            kept = table.filter(mask)
            rejected = table.filter(pc.invert(mask))
            reason = pc.if_else(pc.less(rejected['duration_minutes'], 0), 'negative_duration', 'zero_duration')
            rejected = rejected.append_column('quarantine_reason', reason)
            if kept.num_rows:
                kept_writer.write_table(kept)
            if rejected.num_rows:
                rejected_writer.write_table(rejected)
            kept_count += kept.num_rows
            reasons.update(reason.to_pylist())
            for name in FLAGS:
                flag_counts[name] += pc.sum(pc.cast(kept[name], pa.int64())).as_py() or 0
            for part, counts in [(kept, retained), (rejected, excluded)]:
                counts.update((zone, stamp.replace(minute=0, second=0, microsecond=0))
                              for zone, stamp in zip(part['PULocationID'].to_pylist(), part['tpep_pickup_datetime'].to_pylist()))
    assert kept_count + sum(reasons.values()) == parquet.metadata.num_rows
    assert sum(retained.values()) == kept_count
    assert sum(excluded.values()) == sum(reasons.values())
    assert pq.ParquetFile(kept_path).metadata.num_rows == kept_count
    assert pq.ParquetFile(quarantine_path).metadata.num_rows == sum(reasons.values())
    assert digest(source) == original
    with (output_dir / 'hourly_observed.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['PULocationID', 'pickup_hour', 'trip_count'])
        for (zone, hour), count in sorted(retained.items()):
            writer.writerow([zone, hour.isoformat(), count])
    with (output_dir / 'duration_sensitivity.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['PULocationID', 'pickup_hour', 'count_with_nonpositive', 'count_without_nonpositive', 'difference'])
        for (zone, hour), count in sorted(excluded.items()):
            writer.writerow([zone, hour.isoformat(), retained[(zone, hour)] + count, retained[(zone, hour)], count])
    report = {
        'source': source.as_posix(), 'source_sha256': original, 'input_unchanged': True,
        'input_rows': parquet.metadata.num_rows, 'retained_rows': kept_count,
        'quarantined_rows': sum(reasons.values()), 'quarantine_reasons': dict(reasons),
        'retained_flag_counts': dict(flag_counts),
        'observed_zone_hours': len(retained), 'affected_zone_hours': len(excluded),
        'max_hourly_count_difference': max(excluded.values(), default=0),
        'pyarrow_version': pa.__version__,
        'output_sha256': {p.name: digest(p) for p in [kept_path, quarantine_path,
                         output_dir / 'hourly_observed.csv', output_dir / 'duration_sensitivity.csv']},
        'limitations': ['Trial counts of served trips, not latent demand.',
                       'No absent zone-hours filled with zero; hourly file is not a model-ready dense grid.',
                       'Quality flags can overlap. Values of source columns were not imputed or corrected.',
                       'Retrospective cleaning uses dropoff information; not a real-time availability simulation.',
                       'No upper-distance exclusion threshold is applied. Extremely large distances remain unchanged.'],
    }
    (output_dir / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/interim/pickup_zones_2024-01/zone_candidates.parquet'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/processed/trial_2024-01_v1'))
    args = parser.parse_args()
    print(json.dumps(finalize(args.input, args.output_dir), indent=2))
