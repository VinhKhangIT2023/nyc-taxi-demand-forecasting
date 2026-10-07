"""Approved 168-hour integration trial; writes only the fixed trial table."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import happybase
from pyspark.sql import SparkSession, functions as F
from src.storage.hourly_codec import encode

TABLE = 'transport_demand_hourly_trial_v1'
START, STOP = b'161#2024010100', b'161#2024010800'


def connect():
    return happybase.Connection(host=os.environ.get('HBASE_HOST', 'host.docker.internal'),
                                port=int(os.environ.get('HBASE_PORT', '9090')), timeout=10000, transport='buffered', protocol='binary')


def write_partition(rows):
    connection = connect()
    try:
        table = connection.table(TABLE)
        with table.batch(batch_size=100, wal=True) as batch:
            for row in rows:
                key, cells, deletes = encode(row.asDict())
                if deletes:
                    batch.delete(key, columns=deletes)
                batch.put(key, cells)
    finally:
        connection.close()


def verify(table, expected):
    actual = dict(table.scan(row_start=START, row_stop=STOP, limit=169))
    if actual != expected:
        raise AssertionError('Range scan does not match source cells exactly')
    for key, cells in expected.items():
        if table.row(key) != cells:
            raise AssertionError(f'Point read mismatch: {key!r}')
    if len(list(table.scan(limit=169))) != 168:
        raise AssertionError('Trial table must contain exactly the approved 168 rows')
    return {'point_reads': 168, 'scan_rows': len(actual), 'mismatches': 0}


def main():
    metrics = Path(os.environ.get('HBASE_TRIAL_METRICS', 'artifacts/metrics/spark_hbase_trial.json'))
    result = {'complete': False, 'table': TABLE, 'zone': 161,
              'start': '2024-01-01T00:00:00', 'end_exclusive': '2024-01-08T00:00:00',
              'started_at_utc': datetime.now(timezone.utc).isoformat()}
    metrics.write_text(json.dumps(result, indent=2) + '\n')
    manifest = json.loads(Path('data/processed/hourly_grid_v1/2024/audit.json').read_text())
    source = Path(manifest['file'])
    h = hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    if not manifest['complete'] or h.hexdigest() != manifest['sha256']:
        raise ValueError('Hourly source checksum mismatch')
    spark = (SparkSession.builder.appName('BigData-Spark-HBase-168-hours')
             .config('spark.sql.session.timeZone', 'UTC').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    connection = None
    try:
        dataset = spark.read.parquet(str(source))
        selected = dataset.filter((F.col('PULocationID') == 161)
                                  & (F.col('pickup_hour') >= F.lit('2024-01-01').cast('timestamp'))
                                  & (F.col('pickup_hour') < F.lit('2024-01-08').cast('timestamp'))).repartition(2).cache()
        if selected.count() != 168:
            raise AssertionError('Expected exactly 168 source rows')
        # Only this bounded sample, never the entire year, is collected for full comparison.
        expected = {}
        for row in selected.collect():
            key, cells, _ = encode(row.asDict())
            if key in expected or not START <= key < STOP:
                raise ValueError('Duplicate/out-of-scope row key')
            expected[key] = cells
        connection = connect()
        created = TABLE.encode() not in connection.tables()
        if created:
            connection.create_table(TABLE, {f: {'max_versions': 1} for f in ('d', 'q', 'm')})
        table = connection.table(TABLE)
        families = table.families()
        if set(families) != {b'd', b'q', b'm'} or any(info['max_versions'] != 1 for info in families.values()):
            raise ValueError('Existing trial table has unexpected families/versions')
        for key, cells in table.scan(limit=169):
            if key not in expected or cells.get(b'm:dataset_version') != b'hourly_grid_v1':
                raise ValueError('Existing trial table contains data outside the approved scope')
        checks = []
        for _ in range(2):
            selected.foreachPartition(write_partition)
            checks.append(verify(table, expected))
        result.update(complete=True, created_table=created, source_sha256=h.hexdigest(),
                      row_count=168, write_passes=2, checks=checks,
                      spark=spark.version, master=spark.sparkContext.master,
                      endpoint=os.environ.get('HBASE_HOST', 'host.docker.internal') + ':' + os.environ.get('HBASE_PORT', '9090'),
                      finished_at_utc=datetime.now(timezone.utc).isoformat(),
                      limitations=['January sample does not exercise DST/missing labels in HBase.',
                                   'No full-year load or model training; no multi-row transaction guarantee.'])
        metrics.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    finally:
        if connection is not None:
            connection.close()
        spark.stop()


if __name__ == '__main__':
    main()
