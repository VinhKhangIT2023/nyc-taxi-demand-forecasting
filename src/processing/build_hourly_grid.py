"""Build the approved conservative wall-clock grid without inventing DST offsets."""
import argparse
from collections import Counter
import csv
from datetime import date, datetime, timedelta
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from src.ingestion.check_pickup_zones import digest, load_lookup


def dst_dates(year):
    # Current US rule, valid for the project years (2023–2025).
    if year < 2007:
        raise ValueError('Earlier years require different DST rules')
    march = date(year, 3, 1)
    november = date(year, 11, 1)
    return {march + timedelta(days=(6 - march.weekday()) % 7 + 7),
            november + timedelta(days=(6 - november.weekday()) % 7)}


def grid_for_zone(zone, hours, recorded, source_hours, dst):
    counts, targets, missing, masked, eligible, zero = [], [], [], [], [], []
    for hour in hours:
        absent = hour not in source_hours
        ambiguous_day = hour.date() in dst
        count = None if absent else recorded.get((zone, hour), 0)
        valid = not absent and not ambiguous_day
        counts.append(count)
        targets.append(count if valid else None)
        missing.append(absent)
        masked.append(ambiguous_day)
        eligible.append(valid)
        zero.append(count == 0 and not absent)
    return {'PULocationID': pa.array([zone] * len(hours), type=pa.int64()),
            'pickup_hour': pa.array(hours, type=pa.timestamp('us')),
            'recorded_trip_count': pa.array(counts, type=pa.int64()),
            'target_trip_count': pa.array(targets, type=pa.int64()),
            'q_source_hour_missing': pa.array(missing), 'q_dst_day': pa.array(masked),
            'q_zero_recorded': pa.array(zero), 'model_eligible': pa.array(eligible)}


def build(year):
    raw_manifest_path = Path(f'artifacts/metrics/download_manifest_{year}.json')
    clean_manifest_path = Path(f'data/processed/yellow_{year}_v1/dataset_manifest.json')
    raw = json.loads(raw_manifest_path.read_text())
    clean = json.loads(clean_manifest_path.read_text())
    if not raw['complete'] or not clean['complete']:
        raise ValueError('Complete raw and cleaned manifests required')
    start, end = datetime(year, 1, 1), datetime(year + 1, 1, 1)
    source_hours = Counter()
    # Coverage is measured on raw pickups, before quality exclusions.
    for item in raw['files']:
        path = Path(item['file'])
        if digest(path) != item['sha256']:
            raise ValueError(f'Changed source: {path}')
        month = int(path.stem[-2:])
        month_start = datetime(year, month, 1)
        month_end = datetime(year + (month == 12), month % 12 + 1, 1)
        with pq.ParquetFile(path) as parquet:
            for batch in parquet.iter_batches(columns=['tpep_pickup_datetime']):
                values = batch.column(0)
                within = pc.and_(pc.greater_equal(values, pa.scalar(month_start, type=values.type)),
                                 pc.less(values, pa.scalar(month_end, type=values.type)))
                floors = pc.floor_temporal(pc.filter(values, within), unit='hour')
                source_hours.update({item['values']: item['counts'] for item in pc.value_counts(floors).to_pylist()})
    hourly_path = Path(f'data/processed/yellow_{year}_v1/hourly_observed.csv')
    if digest(hourly_path) != clean['hourly_sha256']:
        raise ValueError('Changed hourly input')
    counts = {}
    with hourly_path.open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            key = (int(row['PULocationID']), datetime.fromisoformat(row['pickup_hour']))
            if key in counts:
                raise ValueError('Duplicate zone-hour key')
            counts[key] = int(row['trip_count'])
    assert sum(counts.values()) == clean['totals']['retained_rows']
    reference = Path('data/reference/taxi_zone_lookup.csv')
    if digest(reference) != clean['reference_sha256']:
        raise ValueError('Changed lookup')
    zones = sorted(set(load_lookup(reference)) - {264, 265})
    assert all(zone in zones and hour in source_hours for zone, hour in counts)
    hours = [start + timedelta(hours=i) for i in range(int((end-start).total_seconds() // 3600))]
    assert set(source_hours) <= set(hours)
    output_dir = Path(f'data/processed/hourly_grid_v1/{year}')
    output_dir.mkdir(parents=True, exist_ok=False)
    path = output_dir / 'zone_hours.parquet'
    totals = Counter()
    writer = None
    try:
        for zone in zones:
            table = pa.table(grid_for_zone(zone, hours, counts, source_hours, dst_dates(year)))
            if writer is None:
                writer = pq.ParquetWriter(path, table.schema)
            writer.write_table(table)
            totals['rows'] += table.num_rows
            for field in ['q_source_hour_missing', 'q_dst_day', 'q_zero_recorded', 'model_eligible']:
                totals[field] += pc.sum(pc.cast(table[field], pa.int64())).as_py() or 0
            totals['recorded_sum'] += pc.sum(table['recorded_trip_count']).as_py() or 0
            totals['target_sum'] += pc.sum(table['target_trip_count']).as_py() or 0
    finally:
        if writer is not None:
            writer.close()
    assert totals['rows'] == len(zones) * len(hours)
    assert totals['recorded_sum'] == clean['totals']['retained_rows']
    assert pq.ParquetFile(path).metadata.num_rows == totals['rows']
    result = {'year': year, 'complete': True, 'file': path.as_posix(), 'sha256': digest(path),
              'zones': zones, 'wall_clock_hours': len(hours), 'totals': dict(totals),
              'dst_dates': sorted(str(day) for day in dst_dates(year)),
              'missing_source_hours': sorted(h.isoformat() for h in set(hours) - set(source_hours)),
              'input_hourly_sha256': clean['hourly_sha256'],
              'raw_manifest_sha256': digest(raw_manifest_path), 'clean_manifest_sha256': digest(clean_manifest_path),
              'source_coverage_definition': 'at least one raw pickup in its source month at this local hour',
              'limitations': ['Presence of raw records is not proof of complete vendor reporting.',
                 'Zero means no retained record in this zone-hour, not absence of latent demand.',
                 'Local labels are not UTC. Both DST transition dates have null targets.',
                 'recorded_trip_count on DST days is descriptive only; use target_trip_count and model_eligible for modeling.']}
    text = json.dumps(result, indent=2) + '\n'
    (output_dir / 'audit.json').write_text(text, encoding='utf-8')
    Path(f'artifacts/metrics/hourly_grid_{year}.json').write_text(text, encoding='utf-8')
    print(json.dumps({'year':year, 'totals':dict(totals), 'missing_source_hours':result['missing_source_hours']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    build(parser.parse_args().year)
