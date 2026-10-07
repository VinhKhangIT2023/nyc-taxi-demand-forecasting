"""Exercise zero/null/DST and stale-cell deletion in a new synthetic HBase table."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time
import uuid
import happybase
from src.storage.hourly_codec import encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=19090)
    args = parser.parse_args()
    base = dict(PULocationID=1, pickup_hour=datetime(2024, 1, 1), recorded_trip_count=0,
                target_trip_count=0, q_source_hour_missing=False, q_dst_day=False,
                q_zero_recorded=True, model_eligible=True)
    missing = {**base, 'recorded_trip_count': None, 'target_trip_count': None,
               'q_source_hour_missing': True, 'q_zero_recorded': False, 'model_eligible': False}
    dst = {**base, 'pickup_hour': datetime(2024, 3, 10, 1), 'recorded_trip_count': 7,
           'target_trip_count': None, 'q_dst_day': True, 'q_zero_recorded': False, 'model_eligible': False}
    name = 'bigdata_edge_' + uuid.uuid4().hex
    connection = happybase.Connection('127.0.0.1', port=args.port, timeout=10000)
    try:
        connection.create_table(name, {f: {'max_versions': 1} for f in ('d', 'q', 'm')})
        table = connection.table(name)
        stages = []
        for label, row in [('zero', base), ('zero_to_missing', missing), ('missing_to_zero', base), ('dst', dst)]:
            time.sleep(0.01)  # Distinct server timestamps for sequential replacement checks.
            key, puts, deletes = encode(row)
            with table.batch(wal=True) as batch:
                if deletes:
                    batch.delete(key, columns=deletes)
                batch.put(key, puts)
            if table.row(key) != puts:
                raise AssertionError(label)
            stages.append(label)
        result = {'complete': True, 'port': args.port, 'table': name, 'synthetic_only': True,
                  'passed_cases': stages, 'final_rows': len(list(table.scan(limit=3)))}
        Path('artifacts/metrics/hbase_edge_cases.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
    finally:
        connection.close()


if __name__ == '__main__':
    main()
