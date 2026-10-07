"""Accept stage-3 infrastructure evidence and run the current unit suite."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest


def main():
    folder = Path('artifacts/metrics')
    def read(name):
        return json.loads((folder / name).read_text(encoding='utf-8-sig'))
    spark = read('spark_trial_2024-01.json')
    assert spark['complete'] and spark['mismatched_zone_hours'] == 0 and spark['python_worker_passed']
    assert spark['observed_zone_hours'] == 76190 and spark['totals']['retained_rows'] == 2951871
    assert spark['cgroup_memory_max'] == '4294967296' and spark['cgroup_cpu_max'] == '200000 100000'
    assert read('spark_output_readback.json')['all_zone_hours_equal']
    for name in ('spark_hbase_trial.json', 'spark_hbase_managed_trial.json'):
        report = read(name)
        assert report['complete'] and report['row_count'] == 168 and report['write_passes'] == 2
        assert all(c['mismatches'] == 0 and c['scan_rows'] == 168 for c in report['checks'])
    edges = read('hbase_edge_cases.json')
    assert edges['complete'] and set(edges['passed_cases']) == {'zero', 'zero_to_missing', 'missing_to_zero', 'dst'}
    recovery = read('hbase_recovery.json')
    assert recovery['complete'] and recovery['clean_stop_exit_code'] == 0
    assert recovery['source_container'] != recovery['restored_container']
    assert recovery['source_volume'] != recovery['restored_volume']
    assert read('hbase_before_backup.json')['tables'] == read('hbase_after_restore.json')['tables']
    restored = read('hbase_restored_readback.json')
    assert restored['complete'] and restored['rows'] == 168 and restored['recorded_trips'] == 26365 and restored['mismatches'] == 0
    archive = Path(recovery['archive'])
    assert hashlib.sha256(archive.read_bytes()).hexdigest().upper() == recovery['archive_sha256'].upper()
    suite = unittest.defaultTestLoader.discover('tests')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('Unit suite failed')
    evidence = ['spark_trial_2024-01.json', 'spark_output_readback.json', 'spark_hbase_trial.json',
                'spark_hbase_managed_trial.json', 'hbase_edge_cases.json', 'hbase_recovery.json',
                'hbase_before_backup.json', 'hbase_after_restore.json', 'hbase_restored_readback.json']
    report = {'complete': True, 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
              'unit_tests_passed': result.testsRun, 'scope': 'Local Spark/HBase infrastructure and bounded integration trials',
              'evidence_sha256': {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in evidence},
              'limitations': ['Not a production cluster or crash-consistency guarantee.',
                             'No full-dataset HBase load, model training, or dashboard.',
                             'Fresh container/volume tested locally, not yet executed on teammate hardware.']}
    (folder / 'stage3_acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
