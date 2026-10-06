from datetime import datetime
import json
from pathlib import Path
import unittest


class SplitConfigTest(unittest.TestCase):
    def test_validation_and_test_do_not_overlap_training(self):
        config = json.loads(Path('configs/temporal_splits.json').read_text())
        test_start = datetime.fromisoformat(config['test_start'])
        for fold in config['validation_folds']:
            train_end = datetime.fromisoformat(fold['train_end'])
            val_start = datetime.fromisoformat(fold['validation_start'])
            val_end = datetime.fromisoformat(fold['validation_end'])
            self.assertLessEqual(train_end, val_start)
            self.assertLess(val_start, val_end)
            self.assertLessEqual(val_end, test_start)
            for experiment in config['experiments'].values():
                self.assertLess(datetime.fromisoformat(experiment['train_start']), train_end)
        self.assertLessEqual(datetime.fromisoformat(config['final_train_end']), test_start)
