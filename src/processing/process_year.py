"""Run the approved monthly rules on a complete official year manifest.

Resume only completed steps whose input/output hashes still match. Each month
is independent. Original source columns and rejected records are retained.
"""
import argparse
from datetime import datetime
import csv
import json
from pathlib import Path
import time

import pyarrow as pa
import pyarrow.parquet as pq

from src.ingestion.check_pickup_zones import digest
from src.processing.split_pickup_month import split_month
from src.processing.split_pickup_zones import split_zones
from src.processing.finalize_trial import finalize
from src.processing.normalize_schema import normalize_file


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def resume_step(directory, inputs, outputs, run):
    audit_path = directory / 'audit.json'
    if not directory.exists():
        return run()
    if not audit_path.exists():
        raise ValueError(f'Incomplete output needs review: {directory}')
    report = json.loads(audit_path.read_text(encoding='utf-8'))
    for file, expected in inputs(report):
        if digest(file) != expected:
            raise ValueError(f'Input changed: {file}')
    for filename, expected in outputs(report):
        if digest(directory / filename) != expected:
            raise ValueError(f'Output changed: {directory / filename}')
    return report


def process_year(year):
    manifest_path = Path(f'artifacts/metrics/download_manifest_{year}.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not manifest['complete'] or len(manifest['files']) != 12:
        raise ValueError('Complete download manifest required')
    reference = Path('data/reference/taxi_zone_lookup.csv')
    reports = []
    root = Path(f'data/processed/yellow_{year}_v1')
    root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    for month, entry in enumerate(sorted(manifest['files'], key=lambda item: item['file']), 1):
        tag = f'{year}-{month:02d}'
        source = Path(entry['file'])
        if source.name != f'yellow_tripdata_{tag}.parquet' or digest(source) != entry['sha256']:
            raise ValueError(f'Manifest mismatch: {source}')
        start = datetime(year, month, 1)
        end = datetime(year + (month == 12), month % 12 + 1, 1)
        print(f'{tag}: begin ({entry["rows"]:,} rows)', flush=True)
        step1 = Path(f'data/interim/pickup_month_{tag}')
        a = resume_step(step1,
            lambda r: [(source, r['source_sha256'])],
            lambda r: [('in_month.parquet', r['in_month_sha256']), ('outside_month.parquet', r['outside_month_sha256'])],
            lambda: split_month(source, step1, start, end))
        step2 = Path(f'data/interim/pickup_zones_{tag}')
        b = resume_step(step2,
            lambda r: [(step1 / 'in_month.parquet', r['input_sha256']['source']), (reference, r['input_sha256']['reference'])],
            lambda r: [('zone_candidates.parquet', r['candidate_sha256']), ('unspecified_zones.parquet', r['quarantine_sha256'])],
            lambda: split_zones(step1 / 'in_month.parquet', reference, step2))
        step3 = root / tag
        c = resume_step(step3,
            lambda r: [(step2 / 'zone_candidates.parquet', r['source_sha256'])],
            lambda r: list(r['output_sha256'].items()),
            lambda: finalize(step2 / 'zone_candidates.parquet', step3))
        report = {'month': tag, 'raw_rows': a['input_rows'], 'outside_month': a['outside_month_rows'],
                  'unspecified_zone': b['quarantined_rows'], 'nonpositive_duration': c['quarantined_rows'],
                  'retained_rows': c['retained_rows'], 'flags': c['retained_flag_counts'],
                  'trips_file': (step3 / 'trips.parquet').as_posix(),
                  'trips_sha256': c['output_sha256']['trips.parquet']}
        assert report['raw_rows'] == sum(report[k] for k in ['outside_month', 'unspecified_zone', 'nonpositive_duration', 'retained_rows'])
        reports.append(report)
        write_json(Path(f'artifacts/metrics/processed_{year}.json'),
                   {'year': year, 'complete': False, 'months': reports})
        print(f'{tag}: done, retained {c["retained_rows"]:,}', flush=True)
    totals = {key: sum(r[key] for r in reports) for key in
              ['raw_rows', 'outside_month', 'unspecified_zone', 'nonpositive_duration', 'retained_rows']}
    # Only per-month trip files are part of the dataset; do not scan audit or quarantine files.
    normalized_dir = root / 'trips'
    normalized_dir.mkdir(exist_ok=True)
    for report in reports:
        original_path = Path(report['trips_file'])
        target = normalized_dir / f"part-{report['month']}.parquet"
        sidecar = target.with_suffix('.json')
        if target.exists():
            if not sidecar.exists():
                raise ValueError(f'Incomplete normalization: {target}')
            check = json.loads(sidecar.read_text())
            if check['input_sha256'] != digest(original_path) or check['output_sha256'] != digest(target):
                raise ValueError(f'Changed normalization inputs/outputs: {target}')
        else:
            normalize_file(original_path, target)
            check = {'input_sha256': digest(original_path), 'output_sha256': digest(target)}
            write_json(sidecar, check)
        report['pre_normalization_file'] = report['trips_file']
        report['trips_file'] = target.as_posix()
        report['trips_sha256'] = check['output_sha256']
        print(f"{report['month']}: common schema ready", flush=True)
    schemas = [pq.read_schema(r['trips_file']) for r in reports]
    assert all(schema.equals(schemas[0], check_metadata=False) for schema in schemas)
    hourly_rows = hourly_sum = 0
    with (root / 'hourly_observed.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['PULocationID', 'pickup_hour', 'trip_count'])
        for report in reports:
            with (root / report['month'] / 'hourly_observed.csv').open(encoding='utf-8', newline='') as part:
                for row in csv.DictReader(part):
                    writer.writerow([row['PULocationID'], row['pickup_hour'], row['trip_count']])
                    hourly_rows += 1
                    hourly_sum += int(row['trip_count'])
    assert hourly_sum == totals['retained_rows']
    complete = {'year': year, 'complete': True, 'months': reports, 'totals': totals,
                'hourly_observed_rows': hourly_rows, 'elapsed_seconds': round(time.perf_counter() - started, 2),
                'schema': str(schemas[0]), 'pyarrow_version': pa.__version__,
                'reference_sha256': digest(reference),
                'hourly_sha256': digest(root / 'hourly_observed.csv'),
                'limitations': ['Full-row duplicate audit is separate; no automatic deduplication.',
                  'Out-of-source-month rows retained in quarantine, not reassigned across files.',
                  'Local wall-clock timestamps: DST repeated hours may be collapsed; no UTC reconstruction.',
                  'Absent zone-hours are not imputed. Flags are not model predictors.']}
    write_json(root / 'dataset_manifest.json', complete)
    write_json(Path(f'artifacts/metrics/processed_{year}.json'), complete)
    print(json.dumps(totals), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    process_year(parser.parse_args().year)
