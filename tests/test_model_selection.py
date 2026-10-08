import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.models.choose_model import main
from src.models.preflight import checksum


class ModelSelectionTest(unittest.TestCase):
    def fixture(self):
        Path('configs').mkdir()
        Path('artifacts/metrics').mkdir(parents=True)
        Path('configs/stage4_model.json').write_text(json.dumps({'rf': {'maxDepth_candidates': [8, 12]}}))
        context = {'configs/stage4_model.json': checksum('configs/stage4_model.json')}
        for exp in ('A_2024_only', 'B_add_2023'):
            for depth in (8, 12):
                for fold in range(3):
                    # Adding 2023 is deliberately worse, to verify it cannot win by assumption.
                    error = (1 if exp == 'A_2024_only' else 3) + (0 if depth == 8 else 1)
                    metric = dict(n=2, absolute_error=error, squared_error=error * error, actual_sum=10,
                                  mae=error / 2)
                    record = dict(complete=True, mode='validation', context_sha256=context,
                                  intervals={'evaluation_end': '2025-01-01T00:00:00'},
                                  system=metric, baseline=dict(metric, absolute_error=8, squared_error=32, mae=4),
                                  methods={'random_forest': 2})
                    Path(f'artifacts/metrics/stage4_validation_{exp}_f{fold}_d{depth}.json').write_text(json.dumps(record))

    def in_workspace(self, action):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                self.fixture()
                action()
            finally:
                os.chdir(original)

    def test_shorter_history_wins_when_validation_is_better(self):
        def run():
            with patch('builtins.print'):
                main()
            winner = json.loads(Path('artifacts/metrics/stage4_selection.json').read_text())['winner']
            self.assertEqual(winner['experiment'], 'A_2024_only')
            self.assertEqual(winner['depth'], 8)
        self.in_workspace(run)

    def test_contaminated_holdout_fold_is_rejected(self):
        def run():
            path = Path('artifacts/metrics/stage4_validation_A_2024_only_f0_d8.json')
            data = json.loads(path.read_text())
            data['intervals']['evaluation_end'] = '2025-02-01T00:00:00'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                main()
        self.in_workspace(run)

    def test_different_model_and_baseline_coverage_is_rejected(self):
        def run():
            path = Path('artifacts/metrics/stage4_validation_A_2024_only_f0_d8.json')
            data = json.loads(path.read_text())
            data['baseline']['n'] = 1
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                main()
        self.in_workspace(run)
