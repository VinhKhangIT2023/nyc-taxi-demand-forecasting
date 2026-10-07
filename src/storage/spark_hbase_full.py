"""Load every Spark-produced zone-hour with WAL and stable keys; resumable upserts."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import happybase
from pyspark.sql import SparkSession
from src.storage.hourly_codec import encode

TABLE = 'transport_demand_hourly_v1'


def connect():
    return happybase.Connection(host=os.environ.get('HBASE_HOST', 'host.docker.internal'), port=int(os.environ.get('HBASE_PORT', '19090')), timeout=120000, transport='buffered', protocol='binary')


def write_partition(rows):
    connection = connect()
    count = 0
    try:
        table = connection.table(TABLE)
        with table.batch(batch_size=500, wal=True) as batch:
            for row in rows:
                key, cells, deletes = encode(row.asDict())
                if deletes:
                    batch.delete(key, columns=deletes)
                batch.put(key, cells)
                count += 1
        yield count
    finally:
        connection.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--pass-number', type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    accepted = json.loads(Path('artifacts/metrics/spark_full.json').read_text())
    if not accepted['complete'] or accepted['grid_rows'] != 6917952 or len(accepted['months']) != 36:
        raise ValueError('Full Spark acceptance required')
    report_path = Path(f'artifacts/metrics/hbase_full_load_pass{args.pass_number}.json')
    report = dict(complete=False, table=TABLE, pass_number=args.pass_number, months=[], started_at_utc=datetime.now(timezone.utc).isoformat())
    def save():
        report_path.write_text(json.dumps(report, indent=2)+'\n')
    save()
    started = time.monotonic()
    spark = SparkSession.builder.appName(f'BigData-HBase-full-pass-{args.pass_number}').config('spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    connection = connect()
    try:
        if TABLE.encode() not in connection.tables():
            connection.create_table(TABLE, {f: {'max_versions': 1} for f in ('d', 'q', 'm')})
        families = connection.table(TABLE).families()
        if set(families) != {b'd', b'q', b'm'} or any(v['max_versions'] != 1 for v in families.values()):
            raise ValueError('Unexpected table schema')
        for month in accepted['months']:
            tick = time.monotonic()
            df = spark.read.parquet('/output/'+month['month']).repartition(2, 'PULocationID').sortWithinPartitions('PULocationID', 'pickup_hour')
            count = sum(df.rdd.mapPartitions(write_partition).collect())
            if count != month['grid_rows']:
                raise AssertionError('Unexpected loaded row count')
            report['months'].append(dict(month=month['month'], rows=count, elapsed_seconds=round(time.monotonic()-tick, 2)))
            save()
            print(f'LOADED pass {args.pass_number} {month["month"]}: {count}', flush=True)
        report.update(complete=True, rows=sum(m['rows'] for m in report['months']), elapsed_seconds=round(time.monotonic()-started, 2), endpoint=os.environ.get('HBASE_HOST', 'host.docker.internal')+':'+os.environ.get('HBASE_PORT', '19090'), wal=True, batch_size=500, spark=spark.version)
        save()
    finally:
        connection.close()
        spark.stop()


if __name__ == '__main__':
    main()
