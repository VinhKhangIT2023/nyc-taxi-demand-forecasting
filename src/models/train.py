"""One bounded Spark ML experiment; 2025 is accessible only in final mode."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time

from pyspark import StorageLevel
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.sql import SparkSession, functions as F

from src.models.evaluation import finalize_sums
from src.models.features import checksum, NUMERIC


METRICS = Path('artifacts/metrics')


def select_range(frame, start, end):
    return frame.filter((F.col('pickup_hour') >= F.lit(start).cast('timestamp')) &
                        (F.col('pickup_hour') < F.lit(end).cast('timestamp')) & F.col('model_eligible'))


def fallback_stats(training):
    global_mean = training.agg(F.avg('target_trip_count').alias('mean')).first().mean
    if global_mean is None:
        raise ValueError('No eligible training labels')
    means = training.groupBy('PULocationID').agg(F.avg('target_trip_count').alias('zone_mean'))
    return means, float(global_mean)


def baseline(frame, means, global_mean):
    return (frame.join(means, 'PULocationID', 'left')
            .withColumn('baseline_prediction', F.greatest(F.lit(0.0),
                F.coalesce(F.col('lag_168'), F.col('zone_mean'), F.lit(global_mean))))
            .withColumn('baseline_method', F.when(F.col('lag_168').isNotNull(), 'weekly')
                .when(F.col('zone_mean').isNotNull(), 'train_zone_mean').otherwise('train_global_mean')))


def score(frame, column):
    error = F.col(column) - F.col('target_trip_count')
    if frame.filter(F.col(column).isNull() | F.isnan(column)).limit(1).count():
        raise ValueError(f'Missing predictions: {column}')
    result = frame.agg(F.count('*').alias('n'), F.sum(F.abs(error)).alias('absolute_error'),
                       F.sum(error * error).alias('squared_error'),
                       F.sum('target_trip_count').alias('actual_sum')).first().asDict()
    return finalize_sums(result)


def fit_rf(training, depth, config):
    rf_config = config['rf']
    params = {key: value for key, value in rf_config.items() if key != 'maxDepth_candidates'}
    rf = RandomForestRegressor(labelCol='target_trip_count', maxDepth=depth, **params)
    pipeline = Pipeline(stages=[StringIndexer(inputCol='zone', outputCol='zone_index', handleInvalid='keep'),
                               VectorAssembler(inputCols=config['feature_columns'], outputCol='features'), rf])
    return pipeline.fit(training)


def predict(frame, model=None):
    if model is None:
        return frame.withColumn('prediction', F.col('baseline_prediction')).withColumn('method', F.col('baseline_method'))
    ready = model.transform(frame.filter('features_complete')).withColumn('prediction',
             F.greatest(F.lit(0.0), F.col('prediction'))).withColumn('method', F.lit('random_forest'))
    unavailable = (frame.filter('not features_complete').withColumn('prediction', F.col('baseline_prediction'))
                   .withColumn('method', F.concat(F.lit('fallback_'), F.col('baseline_method'))))
    columns = frame.columns + ['prediction', 'method']
    return ready.select(*columns).unionByName(unavailable.select(*columns))


def grouped_scores(frame, group):
    error = F.col('prediction') - F.col('target_trip_count')
    rows = frame.groupBy(group).agg(F.count('*').alias('n'), F.sum(F.abs(error)).alias('absolute_error'),
        F.sum(error * error).alias('squared_error'), F.sum('target_trip_count').alias('actual_sum')).orderBy(group).collect()
    return [dict(r.asDict(), **{k: v for k, v in finalize_sums(r.asDict()).items() if k not in r.asDict()}) for r in rows]


def context_hashes():
    return {str(p): checksum(p) for p in [Path('configs/stage4_model.json'), Path('configs/temporal_splits.json'),
             METRICS / 'stage4_features.json', Path('src/models/train.py'), Path('src/models/features.py'),
             Path('src/models/evaluation.py'), Path('src/models/choose_model.py'),
             METRICS / 'stage4_feature_tests.json']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['pilot', 'validation', 'final'], required=True)
    parser.add_argument('--experiment', choices=['A_2024_only', 'B_add_2023'], default='A_2024_only')
    parser.add_argument('--fold', type=int, choices=[0, 1, 2], default=0)
    parser.add_argument('--depth', type=int, choices=[8, 12], default=8)
    args = parser.parse_args()
    config = json.loads(Path('configs/stage4_model.json').read_text())
    temporal = json.loads(Path('configs/temporal_splits.json').read_text())
    features_report = json.loads((METRICS / 'stage4_features.json').read_text())
    if not features_report['complete']:
        raise ValueError('Features incomplete')
    for filename, item in features_report['files'].items():
        if checksum(filename) != item['sha256']:
            raise ValueError(f'Changed features: {filename}')
    context = context_hashes()
    selection = None
    if args.mode == 'final':
        selection = json.loads((METRICS / 'stage4_selection.json').read_text())
        if not selection['complete'] or selection['context_sha256'] != context:
            raise ValueError('Selection missing or context changed after validation')
        for name, expected in selection['validation_sha256'].items():
            if checksum(METRICS / name) != expected:
                raise ValueError('Selection evidence changed')
        args.experiment = selection['winner']['experiment']
        args.depth = selection['winner'].get('depth') or 8
    name = ('stage4_final' if args.mode == 'final' else 'stage4_pilot' if args.mode == 'pilot' else
            f'stage4_validation_{args.experiment}_f{args.fold}_d{args.depth}')
    report_path = METRICS / (name + '.json')
    if report_path.exists():
        existing = json.loads(report_path.read_text())
        if existing.get('complete') and existing.get('context_sha256') == context:
            print(f'Already complete with identical inputs: {report_path}')
            return
        raise ValueError('Prior incomplete/changed run; inspect and archive its report before rerun')
    report = dict(complete=False, mode=args.mode, experiment=args.experiment, depth=args.depth,
                  context_sha256=context, started_at_utc=datetime.now(timezone.utc).isoformat())
    started = time.monotonic()
    spark = SparkSession.builder.appName(name).config('spark.sql.session.timeZone', 'UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    try:
        # Partition pruning excludes 2025 during all model selection/pilot jobs.
        frame = spark.read.parquet(features_report['output'])
        if args.mode != 'final':
            frame = frame.filter('year <= 2024')
        train_start = temporal['experiments'][args.experiment]['train_start']
        if args.mode == 'pilot':
            train_start, train_end, val_start, val_end = [config['pilot'][key] for key in
                ('train_start', 'train_end', 'validation_start', 'validation_end')]
        elif args.mode == 'validation':
            fold = temporal['validation_folds'][args.fold]
            train_end, val_start, val_end = [fold[key] for key in ('train_end', 'validation_start', 'validation_end')]
            report['fold'] = args.fold
        else:
            train_end, val_start, val_end = [temporal[key] for key in ('final_train_end', 'test_start', 'test_end')]
            report['selection_sha256'] = checksum(METRICS / 'stage4_selection.json')
        report['intervals'] = dict(train_start=train_start, train_end=train_end, evaluation_start=val_start, evaluation_end=val_end)
        training = select_range(frame, train_start, train_end)
        means, global_mean = fallback_stats(training)
        evaluation = baseline(select_range(frame, val_start, val_end), means, global_mean).persist(StorageLevel.DISK_ONLY)
        expected_n = evaluation.count()
        report['baseline'] = score(evaluation, 'baseline_prediction')
        report['baseline_methods'] = {r.baseline_method: r['count'] for r in evaluation.groupBy('baseline_method').count().collect()}
        report['training_eligible_rows'] = training.count()
        warmup = (datetime.fromisoformat(train_start) + timedelta(hours=168)).isoformat()
        rf_training = training.filter(F.col('features_complete') &
                        (F.col('pickup_hour') >= F.lit(warmup).cast('timestamp'))).persist(StorageLevel.DISK_ONLY)
        report['rf_training_rows'] = rf_training.count()
        print(f'TRAIN {name}: rows={report["rf_training_rows"]}, eval={expected_n}', flush=True)
        train_time = time.monotonic()
        use_rf = args.mode != 'final' or selection['winner']['model'] == 'random_forest'
        model = fit_rf(rf_training, args.depth, config) if use_rf else None
        report['training_seconds'] = time.monotonic() - train_time
        result = predict(evaluation, model).persist(StorageLevel.DISK_ONLY)
        report['system'] = score(result, 'prediction')
        if report['system']['n'] != expected_n:
            raise ValueError('Prediction coverage differs from baseline')
        report['methods'] = {r.method: r['count'] for r in result.groupBy('method').count().collect()}
        ready_n = result.filter('features_complete').count()
        report['features_ready_evaluation_rows'] = ready_n
        if ready_n:
            report['system_on_complete_features'] = score(result.filter('features_complete'), 'prediction')
            report['baseline_on_complete_features'] = score(result.filter('features_complete'), 'baseline_prediction')
        if args.mode in ('pilot', 'final'):
            destination = Path('artifacts/models') / name
            if destination.exists():
                raise ValueError('Model destination exists; do not overwrite')
            destination.mkdir()
            # Means are an explicit model component even when the winner is baseline.
            means.write.mode('error').parquet(str(destination / 'fallback_zone_means'))
            (destination / 'metadata.json').write_text(json.dumps(dict(global_mean=global_mean,
                model='random_forest' if use_rf else 'seasonal_naive', version=name,
                context_sha256=context, intervals=report['intervals']), indent=2) + '\n')
            if model is not None:
                model.save(str(destination / 'pipeline'))
                loaded = PipelineModel.load(str(destination / 'pipeline'))
                # Fixed keys; no holdout labels used to choose or tune anything here.
                sample = evaluation.filter('features_complete').orderBy('PULocationID', 'pickup_hour').limit(100)
                before = [(r.PULocationID, str(r.pickup_hour), r.prediction) for r in model.transform(sample)
                          .orderBy('PULocationID', 'pickup_hour').select('PULocationID', 'pickup_hour', 'prediction').collect()]
                after = [(r.PULocationID, str(r.pickup_hour), r.prediction) for r in loaded.transform(sample)
                         .orderBy('PULocationID', 'pickup_hour').select('PULocationID', 'pickup_hour', 'prediction').collect()]
                if before != after:
                    raise ValueError('Saved model predictions differ')
                report['reload_sample_rows'] = len(before)
                report['save_reload_predictions_equal'] = True
                report['feature_importances'] = dict(zip(config['feature_columns'], model.stages[-1].featureImportances.toArray().tolist()))
            else:
                restored_means = spark.read.parquet(str(destination / 'fallback_zone_means'))
                sample = select_range(frame, val_start, val_end).orderBy('PULocationID', 'pickup_hour').limit(100)
                before = baseline(sample, means, global_mean).orderBy('PULocationID', 'pickup_hour').select('baseline_prediction').collect()
                after = baseline(sample, restored_means, global_mean).orderBy('PULocationID', 'pickup_hour').select('baseline_prediction').collect()
                if before != after:
                    raise ValueError('Restored baseline changed predictions')
                report['save_reload_predictions_equal'] = True
            report['model_directory'] = str(destination)
            report['model_files_sha256'] = {str(p): checksum(p) for p in sorted(destination.rglob('*')) if p.is_file()}
        if args.mode == 'final':
            report['by_zone'] = grouped_scores(result, 'PULocationID')
            report['by_hour'] = grouped_scores(result, 'hour')
            report['by_month'] = grouped_scores(result.withColumn('month', F.month('pickup_hour')), 'month')
            report['macro_zone_mae'] = sum(r['mae'] for r in report['by_zone']) / len(report['by_zone'])
            report['by_train_demand_group'] = grouped_scores(result.withColumn('train_demand_group',
                        F.when(F.col('zone_mean') < 1, 'under_1_trip_per_hour')
                         .when(F.col('zone_mean') < 10, '1_to_under_10').otherwise('10_plus')), 'train_demand_group')
            predictions = (result.select('PULocationID', 'pickup_hour', 'target_trip_count',
                           'prediction', 'baseline_prediction', 'method', 'features_complete')
                           .withColumn('origin_hour', F.expr('pickup_hour - INTERVAL 1 HOUR'))
                           .withColumn('model_version', F.lit(name)).withColumn('month', F.month('pickup_hour')))
            pred_path = 'data/processed/model_predictions_v1/test_2025'
            predictions.write.mode('error').partitionBy('month').parquet(pred_path)
            report['predictions_directory'] = pred_path
            report['prediction_files_sha256'] = {str(p): checksum(p) for p in sorted(Path(pred_path).rglob('*.parquet'))}
        report.update(complete=True, spark_version=spark.version, elapsed_seconds=time.monotonic()-started,
                      ended_at_utc=datetime.now(timezone.utc).isoformat())
        result.unpersist()
        evaluation.unpersist()
        rf_training.unpersist()
    except Exception as error:
        report.update(complete=False, error=str(error), elapsed_seconds=time.monotonic()-started)
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + '\n')
        spark.stop()
    print(json.dumps({k: v for k, v in report.items() if not k.endswith('sha256') and k not in ('by_zone',)}, indent=2))


if __name__ == '__main__':
    main()
