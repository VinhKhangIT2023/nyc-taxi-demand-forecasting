"""Recompute all approved months and dense grids; compare every hour to stage 2."""
import calendar
import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time

from pyspark.sql import SparkSession, functions as F, types as T
from src.processing.spark_trial import sha256

YEARS = (2023, 2024, 2025)
REPORT = Path('artifacts/metrics/spark_full.json')


def save(report):
    REPORT.write_text(json.dumps(report, indent=2) + '\n')


def count_if(condition, name):
    return F.sum(F.when(condition, 1).otherwise(0)).cast('long').alias(name)


def dst_dates(year):
    # US rules for the approved 2023–2025 scope, retaining local wall-clock labels.
    march, november = datetime(year, 3, 1), datetime(year, 11, 1)
    return [(march + timedelta(days=(6-march.weekday()) % 7 + 7)).date().isoformat(),
            (november + timedelta(days=(6-november.weekday()) % 7)).date().isoformat()]


def main():
    started = time.monotonic()
    report = dict(complete=False, scope='all 36 months 2023–2025', months=[],
                  started_at_utc=datetime.now(timezone.utc).isoformat())
    save(report)
    spark = SparkSession.builder.appName('BigData-full-36-months').config('spark.sql.session.timeZone', 'UTC').config('spark.sql.parquet.datetimeRebaseModeInRead', 'CORRECTED').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    lookup = Path('data/reference/taxi_zone_lookup.csv')
    with lookup.open(encoding='utf-8') as stream:
        zones = [int(r['LocationID']) for r in csv.DictReader(stream)]
    zone_df = spark.createDataFrame([(z,) for z in zones if z not in (264, 265)], 'PULocationID long')
    hourly_schema = 'PULocationID long, pickup_hour timestamp, trip_count long'
    try:
        for year in YEARS:
            clean = json.loads(Path(f'artifacts/metrics/processed_{year}.json').read_text())
            downloads = json.loads(Path(f'artifacts/metrics/download_manifest_{year}.json').read_text())
            grid_audit = json.loads(Path(f'data/processed/hourly_grid_v1/{year}/audit.json').read_text())
            assert clean['complete'] and grid_audit['complete']
            assert sha256(lookup) == clean['reference_sha256']
            assert sha256(Path(grid_audit['file'])) == grid_audit['sha256']
            reference_grid = spark.read.parquet(grid_audit['file'])
            for month in range(1, 13):
                tick = time.monotonic()
                label = f'{year}-{month:02d}'
                start = datetime(year, month, 1)
                end = start + timedelta(days=calendar.monthrange(year, month)[1])
                source = Path(f'data/raw/yellow_tripdata_{label}.parquet')
                expected_hash = next(x['sha256'] for x in downloads['files'] if Path(x['file']).name == source.name)
                assert sha256(source) == expected_hash, label
                expected = next(x for x in clean['months'] if x['month'] == label)
                audit = json.loads(Path(f'data/processed/yellow_{year}_v1/{label}/audit.json').read_text())
                observed_path = Path(f'data/processed/yellow_{year}_v1/{label}/hourly_observed.csv')
                assert sha256(observed_path) == audit['output_sha256']['hourly_observed.csv']
                raw = spark.read.parquet(str(source))
                pickup, dropoff = F.col('tpep_pickup_datetime').cast('timestamp'), F.col('tpep_dropoff_datetime').cast('timestamp')
                duration = F.unix_micros(dropoff) - F.unix_micros(pickup)
                within = (pickup >= F.lit(start)) & (pickup < F.lit(end))
                zone_ok, positive = ~F.col('PULocationID').isin(264, 265), duration > 0
                assert raw.filter(pickup.isNull() | dropoff.isNull() | F.col('PULocationID').isNull() | ~F.col('PULocationID').isin(zones)).limit(1).count() == 0
                totals = raw.agg(F.count('*').alias('raw_rows'), count_if(~within, 'outside_month'), count_if(within & ~zone_ok, 'unspecified_zone'), count_if(within & zone_ok & ~positive, 'nonpositive_duration'), count_if(within & zone_ok & positive, 'retained_rows')).first().asDict()
                assert all(totals[k] == expected[k] for k in totals), (label, totals)
                flags = {'q_duration_gt_24h': duration > 86400000000, 'q_distance_zero': F.col('trip_distance') == 0, 'q_distance_negative': F.col('trip_distance') < 0, 'q_fare_negative': F.col('fare_amount') < 0, 'q_total_negative': F.col('total_amount') < 0, 'q_passenger_missing': F.col('passenger_count').isNull(), 'q_passenger_zero': F.col('passenger_count') == 0}
                kept = raw.filter(within & zone_ok & positive).withColumn('duration_minutes', duration / 60000000.0)
                for name, expression in flags.items():
                    kept = kept.withColumn(name, F.coalesce(expression, F.lit(False)))
                # Handle physical schema differences month by month before aggregation.
                if 'airport_fee' in kept.columns:
                    kept = kept.withColumnRenamed('airport_fee', 'Airport_fee')
                if 'cbd_congestion_fee' not in kept.columns:
                    kept = kept.withColumn('cbd_congestion_fee', F.lit(None).cast('double'))
                integer_cols = {'VendorID', 'PULocationID', 'DOLocationID', 'payment_type'}
                kept = kept.select(*[F.col(c).cast('long' if c in integer_cols else 'timestamp' if c.startswith('tpep_') else 'boolean' if c in flags else 'string' if c == 'store_and_fwd_flag' else 'double').alias(c) for c in kept.columns]).cache()
                assert len(kept.columns) == 28
                actual_flags = kept.agg(*[count_if(F.col(k), k) for k in flags]).first().asDict()
                assert actual_flags == audit['retained_flag_counts'], (label, actual_flags)
                hourly = kept.groupBy('PULocationID', F.date_trunc('hour', 'tpep_pickup_datetime').alias('pickup_hour')).agg(F.count('*').alias('trip_count')).cache()
                ref = spark.read.schema(hourly_schema).option('header', True).csv(str(observed_path))
                mismatch = hourly.alias('a').join(ref.alias('b'), ['PULocationID', 'pickup_hour'], 'full').filter(~F.col('a.trip_count').eqNullSafe(F.col('b.trip_count'))).count()
                assert mismatch == 0
                coverage = raw.filter(within).select(F.date_trunc('hour', pickup).alias('pickup_hour')).distinct().withColumn('source_present', F.lit(True))
                hours = spark.range(int((end-start).total_seconds()/3600)).select((F.lit(start).cast('long') + F.col('id') * 3600).cast('timestamp').alias('pickup_hour'))
                dense = zone_df.crossJoin(hours).join(coverage, 'pickup_hour', 'left').join(hourly, ['PULocationID', 'pickup_hour'], 'left')
                dense = dense.withColumn('q_source_hour_missing', F.col('source_present').isNull()).withColumn('q_dst_day', F.date_format('pickup_hour', 'yyyy-MM-dd').isin(dst_dates(year)))
                dense = dense.withColumn('recorded_trip_count', F.when(~F.col('q_source_hour_missing'), F.coalesce('trip_count', F.lit(0).cast('long'))))
                dense = dense.withColumn('model_eligible', ~F.col('q_source_hour_missing') & ~F.col('q_dst_day')).withColumn('q_zero_recorded', F.coalesce(F.col('recorded_trip_count') == 0, F.lit(False)))
                dense = dense.withColumn('target_trip_count', F.when(F.col('model_eligible'), F.col('recorded_trip_count'))).select(*reference_grid.columns).cache()
                reference = reference_grid.filter((F.col('pickup_hour') >= F.lit(start)) & (F.col('pickup_hour') < F.lit(end)))
                comparison = dense.alias('a').join(reference.alias('b'), ['PULocationID', 'pickup_hour'], 'full')
                different = F.lit(False)
                for c in reference_grid.columns:
                    if c not in ('PULocationID', 'pickup_hour'):
                        different = different | ~F.col('a.'+c).eqNullSafe(F.col('b.'+c))
                assert comparison.filter(different).count() == 0, label
                nrows = dense.count()
                assert nrows == 263 * int((end-start).total_seconds()/3600)
                assert dense.select('PULocationID', 'pickup_hour').distinct().count() == nrows
                # Each partition may be regenerated after a failed run; phase-2 files are read-only.
                dense.write.mode('overwrite').parquet(f'/output/{label}')
                report['months'].append(dict(month=label, totals=totals, flags=actual_flags, grid_rows=nrows, observed_mismatches=0, grid_mismatches=0, normalized_columns=kept.columns, source_sha256=expected_hash, reference_grid_sha256=grid_audit['sha256'], elapsed_seconds=round(time.monotonic()-tick, 2)))
                save(report)
                print(f'ACCEPTED {label}: {totals["retained_rows"]} trips, {nrows} hours', flush=True)
                dense.unpersist(); hourly.unpersist(); kept.unpersist()
        report.update(complete=True, spark=spark.version, master=spark.sparkContext.master, grid_rows=sum(m['grid_rows'] for m in report['months']), raw_rows=sum(m['totals']['raw_rows'] for m in report['months']), retained_rows=sum(m['totals']['retained_rows'] for m in report['months']), elapsed_seconds=round(time.monotonic()-started, 2))
        save(report)
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
