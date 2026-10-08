"""Read-only audit of approved hourly inputs before stage 4 model work."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pyarrow.parquet as pq


def checksum(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    report = {'complete': False, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'python': sys.version, 'checks': [], 'scope': 'input integrity and schema only; no model scores'}
    output = Path('artifacts/metrics/stage4_preflight.json')
    try:
        acceptance = json.loads(Path('artifacts/metrics/stage3_full_acceptance.json').read_text())
        if not acceptance['complete']:
            raise ValueError('Stage 3 acceptance is incomplete')
        for name, expected in acceptance['evidence_sha256'].items():
            if checksum(Path('artifacts/metrics') / name) != expected:
                raise ValueError(f'Changed stage 3 evidence: {name}')
        expected_types = {'PULocationID': 'int64', 'pickup_hour': 'timestamp[us]',
                          'recorded_trip_count': 'int64', 'target_trip_count': 'int64',
                          'q_source_hour_missing': 'bool', 'q_dst_day': 'bool',
                          'q_zero_recorded': 'bool', 'model_eligible': 'bool'}
        for year in (2023, 2024, 2025):
            audit = json.loads(Path(f'data/processed/hourly_grid_v1/{year}/audit.json').read_text())
            path = Path(audit['file'])
            actual_hash = checksum(path)
            if not audit['complete'] or actual_hash != audit['sha256']:
                raise ValueError(f'Invalid source manifest/checksum: {year}')
            parquet = pq.ParquetFile(path)
            schema = {field.name: str(field.type) for field in parquet.schema_arrow}
            if schema != expected_types:
                raise ValueError(f'Unexpected hourly schema: {schema}')
            expected_rows = 263 * (8784 if year == 2024 else 8760)
            if parquet.metadata.num_rows != expected_rows or len(audit['zones']) != 263:
                raise ValueError(f'Unexpected grid size: {year}')
            report['checks'].append({'year': year, 'file': str(path), 'bytes': path.stat().st_size,
                                     'rows': expected_rows, 'sha256': actual_hash, 'schema': schema})
        report['temporal_config_sha256'] = checksum('configs/temporal_splits.json')
        report['complete'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
