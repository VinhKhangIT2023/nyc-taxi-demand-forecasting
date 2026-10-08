"""Compare every stored holdout forecast with the reloaded serving components."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession, functions as F
from src.models.train import baseline, predict


def main():
    root = Path('artifacts/metrics')
    final = json.loads((root / 'stage4_final.json').read_text())
    if not final['complete']:
        raise ValueError('Final experiment is incomplete')
    directory = Path(final['model_directory'])
    metadata = json.loads((directory / 'metadata.json').read_text())
    if metadata['context_sha256'] != final['context_sha256']:
        raise ValueError('Model context differs from final run')
    report = {'complete': False, 'scope': 'all eligible 2025 forecasts, including fallback',
              'checked_at_utc': datetime.now(timezone.utc).isoformat()}
    started = time.monotonic()
    spark = SparkSession.builder.appName('stage4-full-model-reload-check').config('spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        feature_path = json.loads((root / 'stage4_features.json').read_text())['output']
        features = spark.read.parquet(feature_path).filter('year = 2025 and model_eligible')
        means = spark.read.parquet(str(directory / 'fallback_zone_means'))
        pipeline = PipelineModel.load(str(directory / 'pipeline')) if metadata['model'] == 'random_forest' else None
        actual = predict(baseline(features, means, metadata['global_mean']), pipeline).select(
                'PULocationID', 'pickup_hour', F.col('prediction').alias('reloaded_prediction'),
                F.col('method').alias('reloaded_method'))
        expected = spark.read.parquet(final['predictions_directory']).select(
                'PULocationID', 'pickup_hour', 'prediction', 'method')
        compared = actual.join(expected, ['PULocationID', 'pickup_hour'], 'full')
        different = (~F.col('reloaded_prediction').eqNullSafe(F.col('prediction')) |
                     ~F.col('reloaded_method').eqNullSafe(F.col('method')) |
                     F.col('prediction').isNull() | F.col('reloaded_prediction').isNull())
        values = compared.agg(F.count('*').alias('rows'),
                     F.sum(different.cast('long')).alias('mismatches')).first().asDict()
        if values['rows'] != final['system']['n'] or values['mismatches'] != 0:
            raise ValueError(f'Reloaded forecasts differ: {values}')
        report.update(complete=True, **values, spark_version=spark.version,
                      elapsed_seconds=time.monotonic() - started)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        (root / 'stage4_saved_model_full_check.json').write_text(json.dumps(report, indent=2) + '\n')
        spark.stop()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
