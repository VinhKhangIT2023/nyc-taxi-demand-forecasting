"""Causal wall-clock features from the approved complete hourly grid."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from pyspark.sql import SparkSession, Window, functions as F


NUMERIC = ['lag_1', 'lag_2', 'lag_24', 'lag_168', 'mean_24', 'mean_168', 'hour', 'weekday']


def checksum(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def add_features(grid):
    # UTC here is a neutral axis for naive local labels, not inferred NYC UTC offsets.
    timed = grid.withColumn('_seconds', F.col('pickup_hour').cast('timestamp').cast('long'))
    history = Window.partitionBy('PULocationID').orderBy('_seconds')
    for lag in (1, 2, 24, 168):
        window = history.rangeBetween(-lag * 3600, -lag * 3600)
        timed = timed.withColumn(f'lag_{lag}', F.max('target_trip_count').over(window).cast('double'))
    for hours in (24, 168):
        window = history.rangeBetween(-hours * 3600, -3600)
        timed = timed.withColumn(f'mean_{hours}', F.when(
            F.count('target_trip_count').over(window) == hours,
            F.avg('target_trip_count').over(window)))
    timed = (timed.withColumn('hour', F.hour('pickup_hour').cast('double'))
             .withColumn('weekday', F.pmod(F.dayofweek('pickup_hour') + 5, F.lit(7)).cast('double'))
             .withColumn('zone', F.col('PULocationID').cast('string'))
             .withColumn('year', F.year('pickup_hour')))
    complete = F.lit(True)
    for field in NUMERIC:
        complete = complete & F.col(field).isNotNull()
    return timed.withColumn('features_complete', complete).drop('_seconds')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/processed/model_features_v1/features')
    args = parser.parse_args()
    report_path = Path('artifacts/metrics/stage4_features.json')
    output = Path(args.output)
    if output.exists():
        raise ValueError('Output already exists; inspect manifest before rerun, do not overwrite silently')
    started = time.monotonic()
    report = {'complete': False, 'sources': {}, 'timezone_axis': 'UTC for naive wall-clock arithmetic'}
    spark = SparkSession.builder.appName('stage4-causal-features').config('spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        paths = []
        for year in (2023, 2024, 2025):
            audit = json.loads(Path(f'data/processed/hourly_grid_v1/{year}/audit.json').read_text())
            if not audit['complete'] or checksum(audit['file']) != audit['sha256']:
                raise ValueError(f'Changed input {year}')
            report['sources'][str(year)] = {'file': audit['file'], 'sha256': audit['sha256']}
            paths.append(audit['file'])
        grid = spark.read.parquet(*paths)
        if grid.groupBy('PULocationID', 'pickup_hour').count().filter('count != 1').limit(1).count():
            raise ValueError('Duplicate keys')
        coverage = grid.groupBy('PULocationID').agg(F.count('*').alias('n'),
                         F.min('pickup_hour').alias('start'), F.max('pickup_hour').alias('end')).collect()
        if len(coverage) != 263 or any(r.n != 26304 or str(r.start) != '2023-01-01 00:00:00'
                                     or str(r.end) != '2025-12-31 23:00:00' for r in coverage):
            raise ValueError('Incomplete hourly grid')
        if grid.filter(F.col('model_eligible') != F.col('target_trip_count').isNotNull()).limit(1).count():
            raise ValueError('Eligibility and target disagree')
        featured = add_features(grid.repartition(8, 'PULocationID'))
        featured.write.mode('error').partitionBy('year').parquet(str(output))
        stored = spark.read.parquet(str(output))
        report['by_year'] = [r.asDict() for r in stored.groupBy('year').agg(
            F.count('*').alias('rows'), F.sum(F.col('model_eligible').cast('long')).alias('eligible'),
            F.sum((F.col('model_eligible') & F.col('features_complete')).cast('long')).alias('rf_ready')
        ).orderBy('year').collect()]
        report['files'] = {str(p): {'bytes': p.stat().st_size, 'sha256': checksum(p)}
                           for p in sorted(output.rglob('*.parquet'))}
        report.update(complete=True, output=str(output), rows=sum(r['rows'] for r in report['by_year']),
                      schema=stored.schema.jsonValue(), elapsed_seconds=time.monotonic() - started,
                      built_at_utc=datetime.now(timezone.utc).isoformat(), spark_version=spark.version)
        if report['rows'] != 6917952:
            raise ValueError('Wrong feature row count')
    except Exception as error:
        report.update(complete=False, error=str(error))
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        spark.stop()
    print(json.dumps({k: v for k, v in report.items() if k not in ('files', 'schema')}, indent=2))


if __name__ == '__main__':
    main()
