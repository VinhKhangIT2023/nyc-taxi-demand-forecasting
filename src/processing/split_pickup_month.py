"""Split January trial data by pickup time only; preserve all source values.

This is a local PyArrow experiment, not the final Spark cleaning pipeline.
Null pickup timestamps stop the run: no missing-time rule has been approved.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def split_month(source, output_dir, start, end):
    if start >= end:
        raise ValueError('start must precede end')
    before = digest(source)
    parquet = pq.ParquetFile(source)
    # Preflight before creating outputs: unexpected missing values need a decision.
    for batch in parquet.iter_batches(columns=['tpep_pickup_datetime']):
        if batch.column(0).null_count:
            raise ValueError('Missing pickup timestamps: ask for a rule before splitting')
    output_dir.mkdir(parents=True, exist_ok=False)
    kept_path = output_dir / 'in_month.parquet'
    outside_path = output_dir / 'outside_month.parquet'
    outside_schema = parquet.schema_arrow.append(pa.field('quarantine_reason', pa.string()))
    kept_count = outside_count = 0
    with ExitStack() as stack:
        kept_writer = stack.enter_context(pq.ParquetWriter(kept_path, parquet.schema_arrow))
        outside_writer = stack.enter_context(pq.ParquetWriter(outside_path, outside_schema))
        for batch in parquet.iter_batches(batch_size=32768):
            table = pa.Table.from_batches([batch])
            pickup = table['tpep_pickup_datetime']
            within = pc.and_(pc.greater_equal(pickup, pa.scalar(start, type=pickup.type)),
                             pc.less(pickup, pa.scalar(end, type=pickup.type)))
            kept = table.filter(within)
            outside = table.filter(pc.invert(within))
            reasons = pc.if_else(pc.less(outside['tpep_pickup_datetime'], pa.scalar(start, type=pickup.type)),
                                 'pickup_before_start', 'pickup_at_or_after_end')
            outside = outside.append_column('quarantine_reason', reasons)
            if kept.num_rows:
                kept_writer.write_table(kept)
            if outside.num_rows:
                outside_writer.write_table(outside)
            kept_count += kept.num_rows
            outside_count += outside.num_rows
    assert kept_count + outside_count == parquet.metadata.num_rows
    assert pq.ParquetFile(kept_path).metadata.num_rows == kept_count
    assert pq.ParquetFile(outside_path).metadata.num_rows == outside_count
    assert digest(source) == before, 'Source changed during processing'
    result = {
        'source': source.as_posix(), 'source_sha256': before,
        'input_unchanged': True, 'rule': 'start <= pickup < end',
        'start': start.isoformat(), 'end_exclusive': end.isoformat(),
        'input_rows': parquet.metadata.num_rows,
        'in_month_rows': kept_count, 'outside_month_rows': outside_count,
        'in_month_sha256': digest(kept_path),
        'outside_month_sha256': digest(outside_path),
        'pyarrow_version': pa.__version__,
        'note': 'Only pickup interval applied; other quality issues remain. No timezone conversion.',
    }
    (output_dir / 'audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/raw/yellow_tripdata_2024-01.parquet'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/interim/pickup_month_2024-01'))
    args = parser.parse_args()
    print(json.dumps(split_month(args.input, args.output_dir, datetime(2024, 1, 1), datetime(2024, 2, 1)), indent=2))
