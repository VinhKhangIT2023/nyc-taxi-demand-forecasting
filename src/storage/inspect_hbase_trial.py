"""Read the approved HBase trial from Windows and compare it with the local Parquet source."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

import happybase
import pyarrow.dataset as ds
from src.ingestion.open_dataset import open_hourly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=9090)
    parser.add_argument('--report', default='artifacts/metrics/hbase_windows_readback.json')
    args = parser.parse_args()
    source = open_hourly([2024]).to_table(filter=(ds.field('PULocationID') == 161)
        & (ds.field('pickup_hour') >= datetime(2024, 1, 1))
        & (ds.field('pickup_hour') < datetime(2024, 1, 8)))
    expected = sorted(source.to_pylist(), key=lambda r: r['pickup_hour'])
    connection = happybase.Connection(host='127.0.0.1', port=args.port, timeout=10000)
    try:
        table = connection.table('transport_demand_hourly_trial_v1')
        rows = list(table.scan(row_start=b'161#2024010100', row_stop=b'161#2024010800', limit=169))
        actual = []
        for key, cells in rows:
            zone, hour = key.decode('ascii').split('#')
            decoded = {'PULocationID': int(zone), 'pickup_hour': datetime.strptime(hour, '%Y%m%d%H')}
            for name in ('recorded_trip_count', 'target_trip_count'):
                value = cells.get(('d:' + name).encode())
                decoded[name] = None if value is None else int(value)
            for name, qualifier in [('q_source_hour_missing', 'source_hour_missing'), ('q_dst_day', 'dst_day'),
                                    ('q_zero_recorded', 'zero_recorded'), ('model_eligible', 'model_eligible')]:
                value = cells[('q:' + qualifier).encode()]
                if value not in (b'0', b'1'):
                    raise ValueError('Invalid boolean encoding')
                decoded[name] = value == b'1'
            if cells[b'm:dataset_version'] != b'hourly_grid_v1' or cells[b'm:timezone'] != b'America/New_York':
                raise ValueError('Unexpected metadata')
            actual.append(decoded)
        if len(actual) != 168 or actual != expected:
            raise AssertionError('Windows HBase readback differs from Parquet')
        result = {'complete': True, 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                  'port': args.port, 'table': 'transport_demand_hourly_trial_v1', 'rows': len(actual), 'mismatches': 0,
                  'recorded_trips': sum(r['recorded_trip_count'] or 0 for r in actual),
                  'examples': actual[:3]}
        Path(args.report).write_text(json.dumps(result, indent=2, default=str) + '\n')
        print(json.dumps(result, indent=2, default=str))
    finally:
        connection.close()


if __name__ == '__main__':
    main()
