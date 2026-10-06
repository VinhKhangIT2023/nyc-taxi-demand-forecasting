"""Read-only Yellow Taxi profiling. No cleaning rules are applied.

Run from the repository root. Duplicate detection uses a temporary SQLite
database on disk so it also detects duplicates across Arrow batches.
"""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def count_true(values):
    return pc.sum(pc.cast(pc.fill_null(values, False), pa.int64())).as_py() or 0


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def profile(path, start, end, batch_size=32768):
    started = time.perf_counter()
    original_hash = sha256(path)
    parquet = pq.ParquetFile(path)
    columns = {f.name: {'type': str(f.type), 'nulls': 0, 'nan': 0,
                       'min': None, 'max': None} for f in parquet.schema_arrow}
    issues = Counter()
    months, days, zones = Counter(), Counter(), Counter()
    rows = 0
    # Full-row serialized values, not a subset of pickup fields or a hash.
    # Null and NaN retain distinct representations; schema/order are fixed.
    with tempfile.TemporaryDirectory(prefix='profile-', dir=path.parent.parent / 'interim') as tmp:
        with closing(sqlite3.connect(str(Path(tmp) / 'duplicates.sqlite'))) as db:
            db.execute('PRAGMA journal_mode=OFF')
            db.execute('PRAGMA synchronous=OFF')
            db.execute('PRAGMA cache_size=-16384')
            db.execute('CREATE TABLE seen (row_value BLOB PRIMARY KEY) WITHOUT ROWID')
            for batch in parquet.iter_batches(batch_size=batch_size):
                for name, array in zip(batch.schema.names, batch.columns):
                    stat = columns[name]
                    stat['nulls'] += array.null_count
                    if pa.types.is_floating(array.type):
                        stat['nan'] += count_true(pc.is_nan(array))
                    if pa.types.is_temporal(array.type) or pa.types.is_integer(array.type) or pa.types.is_floating(array.type):
                        bounds = pc.min_max(array).as_py()
                        for key, op in [('min', min), ('max', max)]:
                            value = bounds[key]
                            if value is not None:
                                stat[key] = value if stat[key] is None else op(stat[key], value)
                pickup = batch.column('tpep_pickup_datetime')
                dropoff = batch.column('tpep_dropoff_datetime')
                issues['pickup_before_start'] += count_true(pc.less(pickup, pa.scalar(start, type=pickup.type)))
                issues['pickup_at_or_after_end'] += count_true(pc.greater_equal(pickup, pa.scalar(end, type=pickup.type)))
                issues['dropoff_before_pickup'] += count_true(pc.less(dropoff, pickup))
                issues['dropoff_equal_pickup'] += count_true(pc.equal(dropoff, pickup))
                for name in ['trip_distance', 'passenger_count', 'fare_amount', 'total_amount']:
                    issues[name + '_negative'] += count_true(pc.less(batch.column(name), 0))
                    issues[name + '_zero'] += count_true(pc.equal(batch.column(name), 0))
                for value in pickup.to_pylist():
                    if value is not None:
                        months[value.strftime('%Y-%m')] += 1
                        if start <= value < end:
                            days[value.strftime('%Y-%m-%d')] += 1
                zones.update(str(v) for v in batch.column('PULocationID').to_pylist())
                values = [array.to_pylist() for array in batch.columns]
                before = db.total_changes
                db.executemany('INSERT OR IGNORE INTO seen VALUES (?)',
                               ((repr(row).encode('utf-8'),) for row in zip(*values)))
                issues['full_row_duplicate_excess'] += batch.num_rows - (db.total_changes - before)
                db.commit()
                rows += batch.num_rows
                if rows % (batch_size * 10) == 0:
                    print(f'Profiled {rows:,} rows', flush=True)
    assert rows == parquet.metadata.num_rows
    assert sum(months.values()) + columns['tpep_pickup_datetime']['nulls'] == rows
    assert sum(zones.values()) == rows
    final_hash = sha256(path)
    assert final_hash == original_hash, 'Input changed during profiling'
    return {
        'input': path.as_posix(), 'sha256': original_hash,
        'input_unchanged': True, 'bytes': path.stat().st_size,
        'rows': rows, 'column_count': len(columns),
        'row_groups': parquet.metadata.num_row_groups,
        'python_arrow_version': pa.__version__, 'batch_size': batch_size,
        'expected_pickup_interval': [start.isoformat(), end.isoformat()],
        'interval_semantics': 'start inclusive, end exclusive; source wall-clock timestamps, no timezone conversion',
        'columns': columns, 'issues': dict(issues),
        'pickup_months': dict(sorted(months.items())),
        'pickup_days_in_interval': dict(sorted(days.items())),
        'pickup_zone_counts': dict(sorted(zones.items())),
        'duplicate_definition': 'extra rows beyond the first identical serialized full row, across all batches; no rows removed',
        'limitations': ['Zone IDs are not yet validated against an official lookup.',
                       'Flags overlap and must not be added as a removal count.',
                       'No outlier threshold, imputation, deduplication or timezone conversion applied.'],
        'elapsed_seconds': round(time.perf_counter() - started, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/raw/yellow_tripdata_2024-01.parquet'))
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--end', default='2024-02-01')
    parser.add_argument('--output', type=Path, default=Path('artifacts/metrics/profile_2024-01.json'))
    args = parser.parse_args()
    start, end = datetime.fromisoformat(args.start), datetime.fromisoformat(args.end)
    if start >= end:
        parser.error('--start must precede --end')
    if args.input.resolve() == args.output.resolve():
        parser.error('Output must not overwrite the input')
    result = profile(args.input, start, end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    print(f"Rows: {result['rows']:,}; columns: {result['column_count']}; output: {args.output}")


if __name__ == '__main__':
    main()
