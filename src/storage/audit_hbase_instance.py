"""Read-only logical fingerprint for the isolated stage-3 recovery instance."""
import argparse
import hashlib
import json
from pathlib import Path
import happybase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--compare')
    args = parser.parse_args()
    connection = happybase.Connection('127.0.0.1', port=args.port, timeout=10000)
    try:
        tables = {}
        for name in sorted(connection.tables()):
            if name != b'transport_demand_hourly_trial_v1' and not name.startswith(b'bigdata_edge_'):
                raise ValueError('Recovery audit is restricted to the isolated trial tables')
            table = connection.table(name)
            rows = list(table.scan(limit=1001))
            if len(rows) > 1000:
                raise ValueError('Unexpected table size')
            canonical = [(key.hex(), sorted((c.hex(), v.hex()) for c, v in cells.items())) for key, cells in rows]
            tables[name.decode()] = {'rows': len(rows), 'sha256': hashlib.sha256(json.dumps(canonical).encode()).hexdigest(),
                                     'family_versions': {k.decode(): v['max_versions'] for k,v in table.families().items()}}
        if not tables or 'transport_demand_hourly_trial_v1' not in tables:
            raise ValueError('Expected trial table missing')
        if args.compare and tables != json.loads(Path(args.compare).read_text())['tables']:
            raise AssertionError('Restored contents or schema differ')
        result = {'complete': True, 'port': args.port, 'tables': tables, 'compared_with': args.compare}
        Path(args.report).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    finally:
        connection.close()


if __name__ == '__main__':
    main()
