"""Exercise time causality, masking and zone isolation in real Spark windows."""
from datetime import datetime, timedelta
import json
from pathlib import Path

from pyspark.sql import SparkSession, functions as F
from src.models.features import add_features, NUMERIC


def main():
    spark = SparkSession.builder.appName('stage4-feature-tests').config('spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    report = {'complete': False, 'checks': []}
    try:
        start = datetime(2023, 12, 25)
        rows = [(zone, start + timedelta(hours=i), float(i + zone * 1000))
                for zone in (1, 2) for i in range(220)]
        grid = spark.createDataFrame(rows, ['PULocationID', 'pickup_hour', 'target_trip_count']).withColumn(
                    'pickup_hour', F.col('pickup_hour').cast('timestamp_ntz'))
        target = start + timedelta(hours=180)
        def extract(frame, at=target, zone=1):
            return add_features(frame).filter((F.col('pickup_hour') == F.lit(at)) &
                 (F.col('PULocationID') == zone)).select(*NUMERIC, 'features_complete').first().asDict()
        actual = extract(grid)
        assert actual['lag_1'] == 1179 and actual['lag_2'] == 1178
        assert actual['lag_24'] == 1156 and actual['lag_168'] == 1012
        assert actual['mean_24'] == (1156 + 1179) / 2
        assert actual['mean_168'] == (1012 + 1179) / 2 and actual['features_complete']
        report['checks'].append('known lags/windows cross year boundary')
        changed = grid.withColumn('target_trip_count', F.when(F.col('pickup_hour') >= F.lit(target),
                                 F.lit(999999.0)).otherwise(F.col('target_trip_count')))
        assert extract(changed) == actual
        report['checks'].append('target and future mutations do not affect target features')
        masked = grid.withColumn('target_trip_count', F.when((F.col('PULocationID') == 1) &
                   (F.col('pickup_hour') == F.lit(target - timedelta(hours=2))), F.lit(None).cast('double'))
                   .otherwise(F.col('target_trip_count')))
        missing = extract(masked)
        assert missing['lag_2'] is None and missing['mean_24'] is None and missing['mean_168'] is None
        assert not missing['features_complete'] and extract(masked, zone=2)['features_complete']
        report['checks'].append('masked history stays missing; windows require full valid coverage; zones isolated')
        gap = grid.filter(F.col('pickup_hour') != F.lit(target - timedelta(hours=1)))
        assert extract(gap)['lag_1'] is None
        assert extract(grid, at=start)['lag_1'] is None
        report['checks'].append('missing hour and start boundary never substitute adjacent row')
        zero = grid.withColumn('target_trip_count', F.when(F.col('pickup_hour') == F.lit(target - timedelta(hours=1)),
                                                        F.lit(0.0)).otherwise(F.col('target_trip_count')))
        assert extract(zero)['lag_1'] == 0.0 and extract(zero)['features_complete']
        report['checks'].append('valid zero is retained as observed history')
        report.update(complete=True, spark_version=spark.version)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        Path('artifacts/metrics/stage4_feature_tests.json').write_text(json.dumps(report, indent=2) + '\n')
        spark.stop()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
