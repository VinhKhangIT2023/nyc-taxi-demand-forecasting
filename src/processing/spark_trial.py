"""Reproduce approved January 2024 cleaning in Spark and compare every observed zone-hour.

Inputs are read-only. This is a local[2] integration trial, not a new dataset policy.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

from pyspark import StorageLevel
from pyspark.sql import SparkSession, functions as F, types as T


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    started = time.monotonic()
    source = Path('data/raw/yellow_tripdata_2024-01.parquet')
    manifest = json.loads(Path('artifacts/metrics/processed_2024.json').read_text())
    expected_month = next(m for m in manifest['months'] if m['month'] == '2024-01')
    raw_manifest = json.loads(Path('artifacts/metrics/download_manifest_2024.json').read_text())
    source_expected = next(f for f in raw_manifest['files'] if Path(f['file']).name == source.name)
    if sha256(source) != source_expected['sha256']:
        raise ValueError('Raw checksum mismatch')
    audit_path = Path('data/processed/yellow_2024_v1/2024-01/audit.json')
    audit = json.loads(audit_path.read_text())
    expected_hourly = audit_path.parent / 'hourly_observed.csv'
    if sha256(expected_hourly) != audit['output_sha256']['hourly_observed.csv']:
        raise ValueError('Reference hourly checksum mismatch')
    lookup = Path('data/reference/taxi_zone_lookup.csv')
    if sha256(lookup) != manifest['reference_sha256']:
        raise ValueError('Lookup checksum mismatch')
    with lookup.open(encoding='utf-8', newline='') as stream:
        zones = [int(r['LocationID']) for r in csv.DictReader(stream)]
    output = Path('/output')
    if any(output.iterdir()):
        raise FileExistsError('Trial output must be empty; do not overwrite an accepted run')
    spark = (SparkSession.builder.appName('BigData-January2024-acceptance')
             .config('spark.sql.session.timeZone', 'UTC')
             .config('spark.sql.parquet.datetimeRebaseModeInRead', 'CORRECTED')
             .getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        if spark.sparkContext.master != 'local[2]':
            raise ValueError('Expected approved local[2] mode')
        # Exercise a real Python worker in addition to JVM DataFrame execution.
        if spark.sparkContext.parallelize([1, 2, 3], 2).map(lambda x: x * 2).sum() != 12:
            raise RuntimeError('Python worker smoke check failed')
        raw = spark.read.parquet(str(source))
        pickup = F.col('tpep_pickup_datetime').cast('timestamp')
        dropoff = F.col('tpep_dropoff_datetime').cast('timestamp')
        duration_us = F.unix_micros(dropoff) - F.unix_micros(pickup)
        within = (pickup >= F.lit('2024-01-01').cast('timestamp')) & (pickup < F.lit('2024-02-01').cast('timestamp'))
        valid_zone = ~F.col('PULocationID').isin(264, 265)
        positive = duration_us > 0
        def count_if(condition, name):
            return F.sum(F.when(condition, 1).otherwise(0)).cast('long').alias(name)
        invalid = raw.filter(pickup.isNull() | dropoff.isNull() | F.col('PULocationID').isNull()
                             | ~F.col('PULocationID').isin(zones)).limit(1).count()
        if invalid:
            raise ValueError('Missing time/unknown zone requires explicit policy')
        totals = raw.agg(F.count('*').alias('raw_rows'),
                        count_if(~within, 'outside_month'),
                        count_if(within & ~valid_zone, 'unspecified_zone'),
                        count_if(within & valid_zone & ~positive, 'nonpositive_duration'),
                        count_if(within & valid_zone & positive, 'retained_rows')).first().asDict()
        if any(totals[key] != expected_month[key] for key in totals):
            raise AssertionError(f'Cleaning counts differ: {totals}')
        flags = {
            'q_duration_gt_24h': duration_us > 86400000000,
            'q_distance_zero': F.col('trip_distance') == 0,
            'q_distance_negative': F.col('trip_distance') < 0,
            'q_fare_negative': F.col('fare_amount') < 0,
            'q_total_negative': F.col('total_amount') < 0,
            'q_passenger_missing': F.col('passenger_count').isNull(),
            'q_passenger_zero': F.col('passenger_count') == 0,
        }
        kept = raw.filter(within & valid_zone & positive).withColumn('duration_minutes', duration_us / 60000000.0)
        for name, expression in flags.items():
            kept = kept.withColumn(name, F.coalesce(expression, F.lit(False)))
        kept.persist(StorageLevel.MEMORY_AND_DISK)
        actual_flags = kept.agg(*[count_if(F.col(name), name) for name in flags]).first().asDict()
        if actual_flags != audit['retained_flag_counts']:
            raise AssertionError(f'Quality flags differ: {actual_flags}')
        hourly = (kept.groupBy('PULocationID', F.date_trunc('hour', F.col('tpep_pickup_datetime').cast('timestamp')).alias('pickup_hour'))
                  .agg(F.count('*').alias('trip_count')).persist(StorageLevel.MEMORY_AND_DISK))
        schema = T.StructType([T.StructField('PULocationID', T.LongType()),
                               T.StructField('pickup_hour', T.TimestampType()),
                               T.StructField('trip_count', T.LongType())])
        reference = spark.read.schema(schema).option('header', True).csv(str(expected_hourly))
        mismatch = (hourly.alias('actual').join(reference.alias('expected'), ['PULocationID', 'pickup_hour'], 'full')
                    .filter(~F.col('actual.trip_count').eqNullSafe(F.col('expected.trip_count'))).count())
        hourly_totals = hourly.agg(F.count('*').alias('groups'), F.sum('trip_count').alias('trips')).first().asDict()
        if mismatch or hourly_totals['groups'] != audit['observed_zone_hours'] or hourly_totals['trips'] != totals['retained_rows']:
            raise AssertionError(f'Hourly mismatch: {mismatch}, totals={hourly_totals}')
        hourly.write.mode('errorifexists').parquet(str(output / 'hourly_observed'))
        # This trial writes aggregates only; authoritative trip partitions remain stage-2 outputs.
        result = {'complete': True, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  'scope': 'January 2024 raw cleaning and observed hourly aggregation; no dense grid/model/HBase writes',
                  'spark': spark.version, 'python': platform.python_version(),
                  'java': spark.sparkContext._jvm.java.lang.System.getProperty('java.version'),
                  'master': spark.sparkContext.master, 'driver_memory': spark.sparkContext.getConf().get('spark.driver.memory'),
                  'shuffle_partitions': spark.conf.get('spark.sql.shuffle.partitions'),
                  'timestamp_policy': 'UTC session preserves naive source wall-clock labels; no timezone conversion or UTC reconstruction',
                  'totals': totals, 'quality_flags': actual_flags,
                  'observed_zone_hours': hourly_totals['groups'], 'mismatched_zone_hours': mismatch,
                  'python_worker_passed': True, 'source_sha256': source_expected['sha256'],
                  'reference_hourly_sha256': sha256(expected_hourly),
                  'cgroup_memory_max': Path('/sys/fs/cgroup/memory.max').read_text().strip(),
                  'cgroup_cpu_max': Path('/sys/fs/cgroup/cpu.max').read_text().strip(),
                  'elapsed_seconds': round(time.monotonic() - started, 2)}
        payload = json.dumps(result, indent=2) + '\n'
        (output / 'audit.json').write_text(payload)
        Path('artifacts/metrics/spark_trial_2024-01.json').write_text(payload)
        print(payload)
    finally:
        spark.stop()


if __name__ == '__main__':
    main()
