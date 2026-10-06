"""Select approved temporal label splits without copying or mixing holdout rows."""
from datetime import datetime
import json
from pathlib import Path

import pyarrow.dataset as ds
from src.ingestion.open_dataset import open_hourly


def split_spec(experiment='A_2024_only', role='train', fold=0):
    config = json.loads(Path('configs/temporal_splits.json').read_text())
    train_start = config['experiments'][experiment]['train_start']
    if role in ('train', 'validation'):
        selected = config['validation_folds'][fold]
        start = train_start if role == 'train' else selected['validation_start']
        end = selected['train_end'] if role == 'train' else selected['validation_end']
    elif role == 'final_train':
        start, end = train_start, config['final_train_end']
    elif role == 'test':
        start, end = config['test_start'], config['test_end']
    else:
        raise ValueError('Unknown role')
    return datetime.fromisoformat(start), datetime.fromisoformat(end)


def label_scanner(experiment='A_2024_only', role='train', fold=0, columns=None):
    start, end = split_spec(experiment, role, fold)
    years = list(range(start.year, end.year + (end.month != 1 or end.day != 1)))
    dataset = open_hourly(years)
    predicate = ((ds.field('pickup_hour') >= start) & (ds.field('pickup_hour') < end)
                 & ds.field('model_eligible'))
    # The full grid should be used separately for causal lags; this scanner selects labels only.
    return dataset.scanner(filter=predicate, columns=columns, batch_size=32768)
