"""Open only curated trip partitions, or model-label grids, without loading all rows."""
import argparse
import json
from pathlib import Path

import pyarrow.dataset as ds
from src.processing.normalize_schema import common_schema


def open_trips(years):
    if len(set(years)) != len(years):
        raise ValueError('Duplicate year would count trips twice')
    paths = []
    for year in years:
        manifest = json.loads(Path(f'data/processed/yellow_{year}_v1/dataset_manifest.json').read_text())
        if not manifest['complete']:
            raise ValueError(f'Year {year} is incomplete')
        paths.extend(month['trips_file'] for month in manifest['months'])
    # Absent 2025 fee columns in older partitions appear as null, not zero.
    return ds.dataset(paths, format='parquet', schema=common_schema())


def open_hourly(years):
    if len(set(years)) != len(years):
        raise ValueError('Duplicate year')
    paths = []
    for year in years:
        manifest = json.loads(Path(f'data/processed/hourly_grid_v1/{year}/audit.json').read_text())
        if not manifest['complete']:
            raise ValueError(f'Year {year} grid is incomplete')
        paths.append(manifest['file'])
    return ds.dataset(paths, format='parquet')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', nargs='+', type=int, default=[2023, 2024])
    parser.add_argument('--kind', choices=['trips', 'hourly'], default='hourly')
    args = parser.parse_args()
    dataset = open_hourly(args.years) if args.kind == 'hourly' else open_trips(args.years)
    print('Rows:', dataset.count_rows())
    print('Schema:', dataset.schema)
    print(dataset.head(3).to_pylist())
