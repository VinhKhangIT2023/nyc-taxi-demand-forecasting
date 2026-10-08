"""Accept the full scope only after all runs, source comparisons and restore pass."""
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from src.storage.verify_hbase_full import checksum


def main():
    root = Path('artifacts/metrics')
    output = root / 'stage3_full_acceptance.json'
    output.write_text(json.dumps({'complete': False, 'status': 'verifying'})+'\n')
    evidence = []
    def read(name):
        evidence.append(name)
        value = json.loads((root/name).read_text(encoding='utf-8-sig'))
        assert value['complete'], name
        return value
    spark = read('spark_full.json')
    assert {m['month'] for m in spark['months']} == {f'{y}-{m:02d}' for y in (2023, 2024, 2025) for m in range(1, 13)}
    assert spark['raw_rows'] == 128202548 and spark['retained_rows'] == 126994028 and spark['grid_rows'] == 6917952
    assert all(m['observed_mismatches'] == m['grid_mismatches'] == 0 for m in spark['months'])
    reports = []
    for pass_number in (1, 2):
        load = read(f'hbase_full_load_pass{pass_number}.json')
        assert load['rows'] == 6917952 and len(load['months']) == 36 and load['wal']
        report = read(f'hbase_full_verify_pass{pass_number}.json')
        assert report['rows'] == 6917952 and report['mismatches'] == 0 and report['range_queries'] == 3
        reports.append(report)
    restored = read('hbase_full_after_restore.json')
    assert restored['rows'] == 6917952 and restored['mismatches'] == 0
    assert reports[0]['content_sha256'] == reports[1]['content_sha256'] == restored['content_sha256']
    if (root / 'hbase_full_post_restart.json').exists():
        restarted = read('hbase_full_post_restart.json')
        assert restarted['rows'] == 6917952 and restarted['mismatches'] == 0
        assert restarted['content_sha256'] == restored['content_sha256']
    if (root / 'stage3_services_ready.json').exists():
        ready = read('stage3_services_ready.json')
        assert ready['mismatches'] == 0 and ready['point_queries'] == 24 and ready['range_queries'] == 3
    recovery = read('hbase_full_recovery.json')
    assert recovery['clean_stop_exit_code'] == 0 and recovery['source_volume'] != recovery['restored_volume'] and recovery['source_container'] != recovery['restored_container']
    assert checksum(recovery['archive']).upper() == recovery['archive_sha256'].upper()
    assert read('hbase_full_restored_trial_readback.json')['rows'] == 168
    for year, expected_hash in restored['source_sha256'].items():
        assert checksum(f'data/processed/hourly_grid_v1/{year}/zone_hours.parquet') == expected_hash
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('tests'))
    assert result.wasSuccessful()
    if (root / 'hbase_runtime_incident.json').exists():
        evidence.append('hbase_runtime_incident.json')
    final = dict(complete=True, verified_at_utc=datetime.now(timezone.utc).isoformat(), scope='Spark all 36 months, full hourly HBase twice, full offline restore', raw_rows=spark['raw_rows'], retained_trips=spark['retained_rows'], hbase_rows=restored['rows'], content_sha256=restored['content_sha256'], unit_tests_passed=result.testsRun, evidence_sha256={n:checksum(root/n) for n in evidence}, limitations=['Single-machine local[2] Spark and standalone HBase; no cluster performance claim.', 'Offline clean-shutdown backup verified; abrupt crash recovery is not proven.', 'Trips remain in Parquet. HBase stores the full 2023–2025 hourly grid.', 'Models, dashboard and final Word/PPT are later phases.'])
    final['code_sha256'] = {name: checksum(name) for name in (
        'src/processing/spark_full.py', 'src/storage/spark_hbase_full.py',
        'src/storage/hourly_codec.py', 'src/storage/verify_hbase_full.py',
        'scripts/test_hbase_full_recovery.ps1', 'docker/spark/compose.full.yaml',
        'docker/hbase/compose.yaml', 'docker/hbase/hbase-site.xml')}
    output.write_text(json.dumps(final, indent=2)+'\n')
    print(json.dumps(final, indent=2))


if __name__ == '__main__':
    main()
