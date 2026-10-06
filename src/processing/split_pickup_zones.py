"""Apply approved rule: separate pickup IDs 264/265, preserving source values.

Run from the repository root with python -m src.processing.split_pickup_zones.
This remains a local experiment, not the final Spark cleaning pipeline.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from src.ingestion.check_pickup_zones import digest, load_lookup


def split_zones(source, reference, output_dir):
    hashes = {'source': digest(source), 'reference': digest(reference)}
    lookup = load_lookup(reference)
    if lookup.get(264, {}).get('Zone') != 'N/A' or lookup.get(265, {}).get('Zone') != 'Outside of NYC':
        raise ValueError('Lookup changed: review the approved rule before continuing')
    parquet = pq.ParquetFile(source)
    if 'quarantine_reason' in parquet.schema_arrow.names:
        raise ValueError('Expected the in-month dataset, not a previous quarantine output')
    for batch in parquet.iter_batches(columns=['PULocationID']):
        ids = batch.column(0)
        if ids.null_count or any(value not in lookup for value in pc.unique(ids).to_pylist()):
            raise ValueError('Missing or unlisted pickup ID: requires a separate decision')
    output_dir.mkdir(parents=True, exist_ok=False)
    candidates_path = output_dir / 'zone_candidates.parquet'
    quarantine_path = output_dir / 'unspecified_zones.parquet'
    quarantine_schema = parquet.schema_arrow.append(pa.field('quarantine_reason', pa.string()))
    candidates_count = 0
    reasons_count = {'unknown_pickup_zone_264': 0, 'outside_nyc_unspecified_265': 0}
    with ExitStack() as stack:
        kept_writer = stack.enter_context(pq.ParquetWriter(candidates_path, parquet.schema_arrow))
        quarantined_writer = stack.enter_context(pq.ParquetWriter(quarantine_path, quarantine_schema))
        for batch in parquet.iter_batches(batch_size=32768):
            table = pa.Table.from_batches([batch])
            ids = table['PULocationID']
            excluded = pc.or_(pc.equal(ids, 264), pc.equal(ids, 265))
            kept = table.filter(pc.invert(excluded))
            quarantined = table.filter(excluded)
            reason = pc.if_else(pc.equal(quarantined['PULocationID'], 264),
                                'unknown_pickup_zone_264', 'outside_nyc_unspecified_265')
            quarantined = quarantined.append_column('quarantine_reason', reason)
            if kept.num_rows:
                kept_writer.write_table(kept)
            if quarantined.num_rows:
                quarantined_writer.write_table(quarantined)
            candidates_count += kept.num_rows
            for value in reason.to_pylist():
                reasons_count[value] += 1
    quarantined_count = sum(reasons_count.values())
    assert candidates_count + quarantined_count == parquet.metadata.num_rows
    assert pq.ParquetFile(candidates_path).metadata.num_rows == candidates_count
    assert pq.ParquetFile(quarantine_path).metadata.num_rows == quarantined_count
    assert hashes == {'source': digest(source), 'reference': digest(reference)}
    result = {
        'source': source.as_posix(), 'reference': reference.as_posix(),
        'input_sha256': hashes, 'inputs_unchanged': True,
        'rule': 'separate PULocationID 264 and 265; no other values changed',
        'input_rows': parquet.metadata.num_rows, 'candidate_rows': candidates_count,
        'quarantined_rows': quarantined_count, 'reasons': reasons_count,
        'candidate_sha256': digest(candidates_path), 'quarantine_sha256': digest(quarantine_path),
        'pyarrow_version': pa.__version__,
        'note': 'Candidates are not fully cleaned. Newark Airport (ID 1) remains included.',
    }
    (output_dir / 'audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/interim/pickup_month_2024-01/in_month.parquet'))
    parser.add_argument('--reference', type=Path, default=Path('data/reference/taxi_zone_lookup.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/interim/pickup_zones_2024-01'))
    args = parser.parse_args()
    print(json.dumps(split_zones(args.input, args.reference, args.output_dir), indent=2))
