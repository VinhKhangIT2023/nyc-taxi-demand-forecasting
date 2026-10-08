"""Accept stage 4 only from complete, intact experiment and artifact evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

import pyarrow.parquet as pq

from src.models.preflight import checksum


def main():
    root = Path('artifacts/metrics')
    output = root / 'stage4_acceptance.json'
    report = {'complete': False}
    try:
        evidence = {}
        def read(name):
            data = json.loads((root / name).read_text(encoding='utf-8-sig'))
            if not data['complete']:
                raise ValueError(f'Incomplete: {name}')
            evidence[name] = checksum(root / name)
            return data
        read('stage4_preflight.json')
        read('stage4_spark_smoke.json')
        read('stage4_environment.json')
        tests = read('stage4_feature_tests.json')
        features = read('stage4_features.json')
        if features['rows'] != 6917952 or len(tests['checks']) != 5:
            raise ValueError('Incomplete feature scope/tests')
        pilot = read('stage4_pilot.json')
        if not pilot['save_reload_predictions_equal']:
            raise ValueError('Pilot reload failed')
        selection = read('stage4_selection.json')
        if len(selection['validation_sha256']) != 12:
            raise ValueError('Missing validation folds')
        for name, expected in selection['validation_sha256'].items():
            fold = read(name)
            if evidence[name] != expected or fold['context_sha256'] != selection['context_sha256']:
                raise ValueError('Changed validation evidence')
        final = read('stage4_final.json')
        if (final['selection_sha256'] != evidence['stage4_selection.json'] or
            final['context_sha256'] != selection['context_sha256'] or
            final['intervals']['evaluation_start'] != '2025-01-01T00:00:00' or
            final['intervals']['evaluation_end'] != '2026-01-01T00:00:00' or
            final['intervals']['train_end'] != '2025-01-01T00:00:00' or
            not final['save_reload_predictions_equal']):
            raise ValueError('Final fit/evaluation mismatch')
        if datetime.fromisoformat(selection['locked_at_utc']) > datetime.fromisoformat(final['started_at_utc']):
            raise ValueError('Model was not locked before holdout evaluation')
        expected_test = next(r['eligible'] for r in features['by_year'] if r['year'] == 2025)
        reload_check = read('stage4_saved_model_full_check.json')
        if reload_check['rows'] != expected_test or reload_check['mismatches'] != 0:
            raise ValueError('Full saved-model comparison failed')
        if final['system']['n'] != expected_test or final['baseline']['n'] != expected_test:
            raise ValueError('Not all valid 2025 targets evaluated')
        if (sum(final['methods'].values()) != expected_test or len(final['by_zone']) != 263
                or len(final['by_hour']) != 24 or len(final['by_month']) != 12):
            raise ValueError('Incomplete methods/zone summary')
        for name, expected in selection['context_sha256'].items():
            if checksum(name) != expected:
                raise ValueError(f'Changed experiment code/config: {name}')
        for name, item in features['files'].items():
            if checksum(name) != item['sha256']:
                raise ValueError('Changed feature file')
        for section in ('model_files_sha256', 'prediction_files_sha256'):
            if not final[section]:
                raise ValueError(f'Missing artifacts: {section}')
            for name, expected in final[section].items():
                if checksum(name) != expected:
                    raise ValueError(f'Changed artifact: {name}')
        stored_rows = sum(pq.ParquetFile(name).metadata.num_rows for name in final['prediction_files_sha256'])
        if stored_rows != expected_test:
            raise ValueError('Stored predictions do not cover all test targets')
        suite = unittest.defaultTestLoader.discover('tests')
        test_result = unittest.TextTestRunner(verbosity=1).run(suite)
        if not test_result.wasSuccessful():
            raise ValueError('Unit tests failed')
        report['unit_tests_passed'] = test_result.testsRun
        tracked_code = list(Path('src/models').glob('*.py')) + list(Path('tests').glob('test_model*.py'))
        tracked_code += [Path('scripts/run_stage4.ps1'), Path('docker/spark/Dockerfile.models'),
                         Path('docker/spark/compose.models.yaml'), Path('requirements/requirements-stage4-windows-lock.txt')]
        report['code_sha256'] = {str(path): checksum(path) for path in tracked_code}
        report.update(complete=True, verified_at_utc=datetime.now(timezone.utc).isoformat(),
                      scope='263 zones, one-step forecasting, 12 validation fits, locked 2025 holdout',
                      winner=selection['winner'], test_system=final['system'], test_baseline=final['baseline'],
                      feature_rows=features['rows'], test_rows=expected_test, evidence_sha256=evidence,
                      limitations=['Retrospective cleaned TLC labels; no real-time data availability claim.',
                                   'DST target days excluded; fallback reported for missing history.',
                                   'Single-machine Spark; dashboard/HBase forecast publication is stage 5.'])
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
