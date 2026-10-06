"""Acceptance checks for the three-year stage-2 dataset, without training a model."""
from datetime import datetime
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from src.ingestion.check_pickup_zones import digest
from src.ingestion.load_split import label_scanner
from src.processing.build_hourly_grid import dst_dates


def truth(array):
    return bool(pc.all(pc.fill_null(array, False)).as_py())


def verify():
    summaries = []
    for year in [2023, 2024, 2025]:
        raw_path = Path(f'artifacts/metrics/download_manifest_{year}.json')
        clean_path = Path(f'data/processed/yellow_{year}_v1/dataset_manifest.json')
        grid_path = Path(f'data/processed/hourly_grid_v1/{year}/audit.json')
        duplicates_path = Path(f'artifacts/metrics/duplicate_audit_{year}.json')
        raw = json.loads(raw_path.read_text())
        clean = json.loads(clean_path.read_text())
        grid = json.loads(grid_path.read_text())
        duplicates = json.loads(duplicates_path.read_text())
        assert raw['complete'] and clean['complete'] and grid['complete'] and duplicates['complete']
        assert len(raw['files']) == len(clean['months']) == len(duplicates['months']) == 12
        assert len({item['month'] for item in clean['months']}) == 12
        assert sum(item['retained_rows'] for item in duplicates['months']) == clean['totals']['retained_rows']
        assert all(count == 0 for item in duplicates['months'] for count in item['nonfinite_counts'].values())
        for item in raw['files']:
            assert digest(Path(item['file'])) == item['sha256']
        for item in clean['months']:
            assert digest(Path(item['trips_file'])) == item['trips_sha256']
            assert pq.ParquetFile(item['trips_file']).metadata.num_rows == item['retained_rows']
        totals = clean['totals']
        assert totals['raw_rows'] == sum(item['rows'] for item in raw['files'])
        assert totals['raw_rows'] == sum(totals[key] for key in ['outside_month','unspecified_zone','nonpositive_duration','retained_rows'])
        assert digest(raw_path) == grid['raw_manifest_sha256']
        assert digest(clean_path) == grid['clean_manifest_sha256']
        assert digest(Path(grid['file'])) == grid['sha256']
        rows = count_sum = eligible = target_sum = 0
        with pq.ParquetFile(grid['file']) as reader:
            for batch in reader.iter_batches():
                hour = batch.column('pickup_hour')
                # Each zone must contain every calendar label exactly once, in output order.
                zone_index = pc.index_in(batch.column('PULocationID'), value_set=pa.array(grid['zones']))
                assert zone_index.null_count == 0
                elapsed_us = pc.subtract(pc.cast(hour, pa.int64()), pa.scalar(datetime(year,1,1), type=pa.timestamp('us')).cast(pa.int64()))
                elapsed_hours = pc.divide_checked(elapsed_us, 3600000000)
                assert truth(pc.equal(elapsed_us, pc.multiply(elapsed_hours, 3600000000)))
                position = pc.add(pc.multiply(pc.cast(zone_index, pa.int64()), grid['wall_clock_hours']), elapsed_hours)
                assert truth(pc.equal(position, pa.array(range(rows, rows + batch.num_rows))))
                recorded = batch.column('recorded_trip_count')
                target = batch.column('target_trip_count')
                valid = batch.column('model_eligible')
                source_missing = batch.column('q_source_hour_missing')
                dst = batch.column('q_dst_day')
                expected_dst = pc.is_in(pc.cast(hour, pa.date32()), value_set=pa.array(sorted(dst_dates(year)), type=pa.date32()))
                assert truth(pc.equal(dst, expected_dst))
                assert truth(pc.equal(valid, pc.invert(pc.or_(source_missing, dst))))
                assert truth(pc.equal(pc.is_null(recorded), source_missing))
                assert truth(pc.equal(pc.is_valid(target), valid))
                assert truth(pc.fill_null(pc.greater_equal(recorded, 0), True))
                assert truth(pc.fill_null(pc.equal(target, recorded), True))
                assert truth(pc.equal(batch.column('q_zero_recorded'), pc.fill_null(pc.equal(recorded, 0), False)))
                assert truth(pc.and_(pc.greater_equal(hour, pa.scalar(datetime(year,1,1))),
                                     pc.less(hour, pa.scalar(datetime(year+1,1,1)))))
                rows += batch.num_rows
                count_sum += pc.sum(recorded).as_py() or 0
                target_sum += pc.sum(target).as_py() or 0
                eligible += pc.sum(pc.cast(valid, pa.int64())).as_py() or 0
        assert count_sum == totals['retained_rows'] == grid['totals']['recorded_sum']
        assert rows == grid['totals']['rows']
        assert eligible == grid['totals']['model_eligible']
        assert target_sum == grid['totals']['target_sum']
        summaries.append({'year':year, **totals, 'grid_rows':rows, 'model_eligible_rows':eligible,
                          'duplicate_excess_retained':duplicates['duplicate_excess'],
                          'missing_source_hours':grid['missing_source_hours']})
        print(f'{year}: acceptance passed', flush=True)
    split_counts = {}
    for experiment in ['A_2024_only', 'B_add_2023']:
        split_counts[experiment] = [
            {'fold':fold, 'train_labels':label_scanner(experiment,'train',fold).count_rows(),
             'validation_labels':label_scanner(experiment,'validation',fold).count_rows()}
            for fold in range(3)]
    assert [r['validation_labels'] for r in split_counts['A_2024_only']] == [r['validation_labels'] for r in split_counts['B_add_2023']]
    result = {'complete':True, 'years':summaries,
              'total_retained_trips':sum(r['retained_rows'] for r in summaries),
              'split_counts':split_counts,
              'holdout_2025_labels':label_scanner(role='test').count_rows(),
              'split_config_sha256':digest(Path('configs/temporal_splits.json')),
              'scope':'Data preparation only; no predictive model trained or evaluated.'}
    Path('artifacts/metrics/stage2_acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    verify()
