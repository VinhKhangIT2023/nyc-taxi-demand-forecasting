"""Audit identical source rows in retained monthly files; never deduplicate.

Group one month in memory at a time. Derived quality flags are excluded from
the equality key. Monthly retained pickup intervals are disjoint, so identical
rows cannot occur in two retained monthly partitions.
"""
import argparse
import gc
import json
from pathlib import Path

import pyarrow.compute as pc
import pyarrow as pa
import pyarrow.parquet as pq
from src.ingestion.check_pickup_zones import digest
from src.processing.finalize_trial import FLAGS


def audit(year):
    manifest_path = Path(f'data/processed/yellow_{year}_v1/dataset_manifest.json')
    manifest = json.loads(manifest_path.read_text())
    records = []
    output = Path(f'artifacts/metrics/duplicate_audit_{year}.json')
    for item in manifest['months']:
        path = Path(item['trips_file'])
        if digest(path) != item['trips_sha256']:
            raise ValueError(f'Changed input: {path}')
        columns = [name for name in pq.read_schema(path).names if name not in FLAGS + ['duration_minutes']]
        table = pq.read_table(path, columns=columns)
        null_counts = {name: table[name].null_count for name in columns}
        nonfinite_counts = {name: (pc.sum(pc.cast(pc.fill_null(pc.invert(pc.is_finite(table[name])), False), pa.int64())).as_py() or 0)
                            for name in columns if pa.types.is_floating(table[name].type)}
        grouped = table.group_by(columns).aggregate([([], 'count_all')])
        repeated = grouped.filter(pc.greater(grouped['count_all'], 1))
        excess = table.num_rows - grouped.num_rows
        records.append({'month': item['month'], 'retained_rows': table.num_rows,
                        'identical_groups': repeated.num_rows, 'duplicate_excess': excess,
                        'examples': repeated.slice(0, 3).to_pylist(),
                        'null_counts': null_counts, 'nonfinite_counts': nonfinite_counts})
        output.write_text(json.dumps({'year': year, 'complete': len(records) == 12,
            'months': records, 'duplicate_excess': sum(r['duplicate_excess'] for r in records),
            'policy': 'Audit only. Same attributes do not prove same trip; no unique trip ID.'},
            indent=2, default=str) + '\n', encoding='utf-8')
        print(f"{item['month']}: duplicate excess={excess}", flush=True)
        del table, grouped, repeated
        gc.collect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    audit(parser.parse_args().year)
