"""Read-only readiness check after starting Docker; never reloads the dataset."""
from datetime import datetime, timezone
import json
from pathlib import Path
from pyspark.sql import SparkSession, functions as F
from src.processing.spark_full import dst_dates
from src.storage.hourly_codec import encode
from src.storage.spark_hbase_full import connect, TABLE


def main():
    report_path = Path('artifacts/metrics/stage3_services_ready.json')
    report_path.write_text(json.dumps({'complete': False})+'\n')
    spark = SparkSession.builder.appName('BigData-readiness').config('spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    connection = connect()
    try:
        table = connection.table(TABLE)
        point_count = range_count = 0
        for year in (2023, 2024, 2025):
            source = spark.read.parquet(f'data/processed/hourly_grid_v1/{year}/zone_hours.parquet')
            spring, autumn = dst_dates(year)
            timestamps = [f'{year}-01-01 00:00:00', f'{year}-12-31 23:00:00', spring+' 02:00:00', autumn+' 01:00:00']
            selected = source.filter(F.col('PULocationID').isin(1, 161) & F.date_format('pickup_hour', 'yyyy-MM-dd HH:mm:ss').isin(timestamps)).collect()
            assert len(selected) == 8
            for row in selected:
                key, cells, _ = encode(row.asDict())
                assert table.row(key) == cells, key
                point_count += 1
            day = source.filter((F.col('PULocationID') == 161) & (F.col('pickup_hour') >= F.lit(f'{year}-01-01').cast('timestamp')) & (F.col('pickup_hour') < F.lit(f'{year}-01-02').cast('timestamp'))).collect()
            expected = {encode(row.asDict())[0]: encode(row.asDict())[1] for row in day}
            assert len(expected) == 24
            actual = dict(table.scan(row_start=f'161#{year}010100'.encode(), row_stop=f'161#{year}010200'.encode()))
            assert actual == expected
            range_count += 1
        report = dict(complete=True, verified_at_utc=datetime.now(timezone.utc).isoformat(), spark=spark.version, master=spark.sparkContext.master, table=TABLE, point_queries=point_count, range_queries=range_count, mismatches=0, scope='Read-only bounded readiness check across all years, year endpoints and DST; full verification is in separate reports')
        report_path.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
    finally:
        connection.close()
        spark.stop()


if __name__ == '__main__':
    main()
