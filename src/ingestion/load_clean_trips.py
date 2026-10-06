"""Stream cleaned trips with a common schema; no quarantine files are loaded."""
import argparse
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from src.processing.normalize_schema import normalize


def files_for(year, include_january_2024=False):
    manifest = json.loads(Path(f'data/processed/yellow_{year}_v1/dataset_manifest.json').read_text())
    if not manifest['complete']:
        raise ValueError('Annual processing not complete')
    files = [Path(month['trips_file']) for month in manifest['months']]
    if include_january_2024:
        if year == 2024:
            raise ValueError('Do not add January 2024 twice')
        files.append(Path('data/processed/trial_2024-01_v1/trips.parquet'))
    return files


def iter_clean_batches(year=2023, include_january_2024=False, batch_size=32768):
    for path in files_for(year, include_january_2024):
        with pq.ParquetFile(path) as parquet:
            for batch in parquet.iter_batches(batch_size=batch_size):
                yield normalize(pa.Table.from_batches([batch]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, default=2023)
    parser.add_argument('--include-january-2024', action='store_true')
    args = parser.parse_args()
    paths = files_for(args.year, args.include_january_2024)
    print('Files:', len(paths))
    print('Rows:', sum(pq.ParquetFile(path).metadata.num_rows for path in paths))
    print(next(iter_clean_batches(args.year, args.include_january_2024)).slice(0, 3).to_pylist())
