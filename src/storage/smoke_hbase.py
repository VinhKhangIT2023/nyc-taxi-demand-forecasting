"""Check isolated synthetic HBase data before/after an externally controlled restart.

prepare creates a unique table and retains it; verify performs reads only.
No production tables or real trip data are modified.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

import happybase


def check(connection, name, expected):
    table = connection.table(name)
    for key, values in expected.items():
        actual = table.row(key.encode())
        wanted = {column.encode(): value.encode() for column, value in values.items()}
        if actual != wanted:
            raise RuntimeError(f'Point read mismatch: {key}')
    rows = list(table.scan(row_start=b'001#', row_stop=b'002#', limit=10))
    wanted_keys = [key.encode() for key in sorted(expected) if key.startswith('001#')]
    if [key for key, _ in rows] != wanted_keys:
        raise RuntimeError('Range scan mismatch')
    all_rows = list(table.scan(limit=len(expected) + 1))
    if len(all_rows) != len(expected):
        raise RuntimeError('Unexpected row count after repeated writes')
    return {'point_reads': len(expected), 'range_scan_rows': len(rows),
            'table_rows': len(all_rows), 'passed': True}


def run(args):
    state_path = Path(args.state)
    if args.mode == 'prepare' and state_path.exists():
        raise FileExistsError('Preserve prior evidence: use verify or choose a new --state path')
    connection = happybase.Connection(host=args.host, port=args.port, timeout=5000,
                                      transport='buffered', protocol='binary', autoconnect=False)
    try:
        if args.mode == 'prepare':
            connection.open()
            name = 'bigdata_smoke_' + uuid.uuid4().hex
            expected = {
                '001#2024010100': {'d:recorded': '3', 'q:eligible': '1', 'm:synthetic': '1'},
                '001#2024010101': {'d:recorded': '0', 'q:eligible': '1', 'm:synthetic': '1'},
                '002#2024010100': {'d:recorded': '5', 'q:eligible': '1', 'm:synthetic': '1'},
            }
            state = {'table': name, 'host': args.host, 'port': args.port,
                     'created_at_utc': datetime.now(timezone.utc).isoformat(),
                     'synthetic_only': True, 'expected': expected,
                     'before_restart': None, 'after_restart': None}
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
            connection.create_table(name, {family: {'max_versions': 1} for family in ['d', 'q', 'm']})
            table = connection.table(name)
            # Same logical keys and same timestamp: repeat the batch without extra rows/versions.
            stamp = int(time.time() * 1000)
            for _ in range(2):
                with table.batch(timestamp=stamp, batch_size=10) as batch:
                    for key, values in expected.items():
                        batch.put(key.encode(), {k.encode(): v.encode() for k, v in values.items()})
            state['before_restart'] = check(connection, name, expected)
            state['before_restart']['identical_batches_written'] = 2
        else:
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if not state['table'].startswith('bigdata_smoke_') or not state.get('synthetic_only'):
                raise ValueError('Expected an isolated smoke-test state')
            if (state['host'], state['port']) != (args.host, args.port):
                raise ValueError('Verify must use the same endpoint')
            if not state.get('before_restart', {}).get('passed'):
                raise ValueError('Before-restart check must pass first')
            deadline = time.monotonic() + args.wait_seconds
            while True:
                try:
                    connection.open()
                    result = check(connection, state['table'], state['expected'])
                    break
                except Exception:
                    connection.close()
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(2)
            # External Docker evidence is needed to prove a restart happened between calls.
            state['after_restart'] = {**result, 'verified_at_utc': datetime.now(timezone.utc).isoformat()}
        state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(state, indent=2))
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'verify'])
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9090)
    parser.add_argument('--state', default='artifacts/metrics/hbase_smoke.json')
    parser.add_argument('--wait-seconds', type=int, default=45)
    run(parser.parse_args())
