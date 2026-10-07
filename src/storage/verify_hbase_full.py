"""Bounded-memory, ordered, complete cell comparison against all stage-2 grids."""
import argparse
from datetime import datetime, timezone
import hashlib
import heapq
from itertools import zip_longest
import json
from pathlib import Path
import time
import happybase
import pyarrow.parquet as pq
from src.storage.hourly_codec import encode, FLAG_COLUMNS

TABLE = 'transport_demand_hourly_v1'


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def source_rows(year):
    previous = None
    for batch in pq.ParquetFile(f'data/processed/hourly_grid_v1/{year}/zone_hours.parquet').iter_batches(batch_size=8192):
        for row in batch.to_pylist():
            key, cells, _ = encode(row)
            if previous is not None and key <= previous:
                raise ValueError('Expected unique sorted source')
            previous = key
            yield key, cells, row


def fingerprint(digest, key, cells):
    # Length-prefix every element so keys/values cannot create ambiguous concatenations.
    for value in [key] + [v for pair in sorted(cells.items()) for v in pair]:
        digest.update(len(value).to_bytes(4, 'big'))
        digest.update(value)
    digest.update(b'\xff\xff\xff\xff')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=19090)
    parser.add_argument('--report', required=True)
    parser.add_argument('--compare')
    args = parser.parse_args()
    started = time.monotonic()
    report = dict(complete=False, table=TABLE, port=args.port, rows=0, started_at_utc=datetime.now(timezone.utc).isoformat())
    def save():
        Path(args.report).write_text(json.dumps(report, indent=2)+'\n')
    save()
    audits = {y: json.loads(Path(f'data/processed/hourly_grid_v1/{y}/audit.json').read_text()) for y in (2023, 2024, 2025)}
    for audit in audits.values():
        if not audit['complete'] or checksum(audit['file']) != audit['sha256']:
            raise ValueError('Source checksum mismatch')
    connection = happybase.Connection('127.0.0.1', port=args.port, timeout=120000)
    try:
        table = connection.table(TABLE)
        families = table.families()
        assert set(families) == {b'd', b'q', b'm'} and all(f['max_versions'] == 1 for f in families.values())
        totals = {y: dict(rows=0, recorded_sum=0, target_sum=0, **{k: 0 for k in FLAG_COLUMNS}) for y in audits}
        digest = hashlib.sha256()
        expected = heapq.merge(*(source_rows(y) for y in audits), key=lambda x: x[0])
        actual = table.scan(batch_size=1000)
        count = 0
        samples = {}
        # Capture three bounded ranges: year boundary, missing spring hour, autumn DST.
        ranges = [(b'001#2023123100', b'001#2024010200'), (b'161#2024031000', b'161#2024031200'), (b'263#2025110200', b'263#2025110400')]
        for wanted, got in zip_longest(expected, actual):
            if wanted is None or got is None:
                raise AssertionError(f'Table/source length mismatch after {count} rows')
            key, cells, source = wanted
            if key != got[0] or cells != got[1]:
                raise AssertionError(f'Cell mismatch at expected {key!r}, actual {got[0]!r}')
            fingerprint(digest, got[0], got[1])
            year = int(key[4:8])
            totals[year]['rows'] += 1
            # Decode the actual stored bytes, not the expected source values.
            for name, column in [('recorded_sum', b'd:recorded_trip_count'), ('target_sum', b'd:target_trip_count')]:
                totals[year][name] += int(got[1].get(column, b'0'))
            for name, column in FLAG_COLUMNS.items():
                totals[year][name] += int(got[1][column])
            if any(a <= key < b for a, b in ranges):
                samples[key] = cells
            count += 1
            if count % 250000 == 0:
                report.update(rows=count, elapsed_seconds=round(time.monotonic()-started, 2))
                save()
                print(f'VERIFIED {count} rows', flush=True)
        for year in audits:
            assert totals[year] == audits[year]['totals'], (year, totals[year])
        for start, stop in ranges:
            wanted = {k: v for k, v in samples.items() if start <= k < stop}
            assert dict(table.scan(row_start=start, row_stop=stop)) == wanted
            for key in (min(wanted), max(wanted)):
                assert table.row(key) == wanted[key]
        report.update(complete=True, rows=count, mismatches=0, content_sha256=digest.hexdigest(), totals=totals, source_sha256={y:a['sha256'] for y,a in audits.items()}, range_queries=3, point_queries=6, elapsed_seconds=round(time.monotonic()-started, 2))
        if args.compare:
            previous = json.loads(Path(args.compare).read_text())
            assert previous['complete'] and previous['rows'] == count and previous['content_sha256'] == report['content_sha256']
            report['identical_to'] = args.compare
        save()
        print(json.dumps(report, indent=2))
    finally:
        connection.close()


if __name__ == '__main__':
    main()
