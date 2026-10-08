"""Lock the winner using only the three approved 2024 validation folds."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from src.models.evaluation import pool_metrics
from src.models.preflight import checksum


def main():
    root = Path('artifacts/metrics')
    config = json.loads(Path('configs/stage4_model.json').read_text())
    candidates, hashes, context, coverage = [], {}, None, {}
    for experiment in ('A_2024_only', 'B_add_2023'):
        baseline_metrics = None
        for depth in config['rf']['maxDepth_candidates']:
            folds = []
            for fold in range(3):
                name = f'stage4_validation_{experiment}_f{fold}_d{depth}.json'
                record = json.loads((root / name).read_text())
                if not record['complete'] or record['mode'] != 'validation':
                    raise ValueError(f'Incomplete fold: {name}')
                if context is None:
                    context = record['context_sha256']
                if record['context_sha256'] != context:
                    raise ValueError('Validation inputs/code differ')
                if record['intervals']['evaluation_end'] > '2025-01-01T00:00:00':
                    raise ValueError('Holdout accessed during validation')
                n = record['system']['n']
                if n != record['baseline']['n'] or n != sum(record['methods'].values()):
                    raise ValueError('Baseline/model coverage differs')
                if fold in coverage and n != coverage[fold]:
                    raise ValueError('Candidates have different fold coverage')
                coverage[fold] = n
                hashes[name] = checksum(root / name)
                folds.append(record)
            metrics = pool_metrics([r['system'] for r in folds])
            candidates.append(dict(model='random_forest', experiment=experiment, depth=depth, metrics=metrics))
            baseline_now = pool_metrics([r['baseline'] for r in folds])
            if baseline_metrics is not None and not math.isclose(baseline_now['mae'], baseline_metrics['mae'], rel_tol=1e-10):
                raise ValueError('Baseline changed between RF parameter runs')
            baseline_metrics = baseline_now
        candidates.append(dict(model='seasonal_naive', experiment=experiment, depth=None, metrics=baseline_metrics))
    for name, expected in context.items():
        if checksum(name) != expected:
            raise ValueError(f'Context changed: {name}')
    candidates.sort(key=lambda r: (r['metrics']['mae'], r['model'] != 'seasonal_naive',
                                   r['experiment'] != 'A_2024_only', r['depth'] or 0))
    result = dict(complete=True, locked_at_utc=datetime.now(timezone.utc).isoformat(),
                  selection_data='2024-10 through 2024-12 only', criterion='pooled MAE on all eligible targets',
                  context_sha256=context, validation_sha256=hashes, candidates=candidates, winner=candidates[0])
    path = root / 'stage4_selection.json'
    if path.exists():
        prior = json.loads(path.read_text())
        if prior['context_sha256'] != context or prior['validation_sha256'] != hashes:
            raise ValueError('Selection already locked; inspect before replacing')
        print(json.dumps(prior, indent=2))
        return
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
