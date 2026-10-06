"""Read-only lookup audit of pickup zones in the January trial dataset."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_lookup(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        records = list(csv.DictReader(stream))
    lookup = {}
    for row in records:
        zone_id = int(row['LocationID'])
        if zone_id in lookup:
            raise ValueError(f'Duplicate LocationID in lookup: {zone_id}')
        lookup[zone_id] = row
    return lookup


def classify(zone_id, lookup):
    if zone_id is None:
        return 'missing_id'
    if zone_id not in lookup:
        return 'not_in_lookup'
    zone = lookup[zone_id]['Zone']
    if zone in ('N/A', 'Unknown', ''):
        return 'unknown_zone'
    if zone == 'Outside of NYC':
        return 'outside_nyc_unspecified'
    return 'named_zone'


def audit(source, reference):
    hashes = {'source': digest(source), 'reference': digest(reference)}
    lookup = load_lookup(reference)
    counts = Counter()
    parquet = pq.ParquetFile(source)
    for batch in parquet.iter_batches(columns=['PULocationID'], batch_size=32768):
        counts.update(batch.column(0).to_pylist())
    totals = Counter({category: 0 for category in (
        'missing_id', 'not_in_lookup', 'unknown_zone', 'outside_nyc_unspecified', 'named_zone')})
    details = []
    for zone_id, count in sorted(counts.items(), key=lambda item: -item[1]):
        category = classify(zone_id, lookup)
        totals[category] += count
        details.append({'LocationID': zone_id, **lookup.get(zone_id, {}),
                        'category': category, 'trips': count})
    assert sum(totals.values()) == parquet.metadata.num_rows
    assert hashes == {'source': digest(source), 'reference': digest(reference)}
    return {'source': source.as_posix(), 'reference': reference.as_posix(),
            'sha256': hashes, 'inputs_unchanged': True,
            'rows': parquet.metadata.num_rows, 'lookup_rows': len(lookup),
            'distinct_pickup_ids': len(counts), 'counts': dict(totals),
            'details': details,
            'limitations': ['Current lookup snapshot, not a verified January 2024 historical snapshot.',
                           'Named zone means a named entry in the lookup, not necessarily inside NYC.',
                           'No row removed or reassigned; only pickup IDs checked.']}


if __name__ == '__main__':
    result = audit(Path('data/interim/pickup_month_2024-01/in_month.parquet'),
                   Path('data/reference/taxi_zone_lookup.csv'))
    output = Path('artifacts/metrics/pickup_zones_2024-01.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'details'}, indent=2))
    print('Special entries:', [row for row in result['details'] if row['category'] != 'named_zone' or row['LocationID'] == '1'])
